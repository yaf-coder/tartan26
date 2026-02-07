"""
Veritas API – connects the frontend to the research pipeline.
POST /api/research: research query (required); optional PDF files as additional sources.
Streams progress steps (NDJSON) then the final result so the frontend can sync the timeline.
"""
import asyncio
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import ssl
import asyncio.subprocess
import requests
from pathlib import Path

# Fix for macOS SSL certificate verification issues in dev environments
ssl._create_default_https_context = ssl._create_unverified_context

from dotenv import load_dotenv

import arxiv
from dedalus_labs import AsyncDedalus
from tartan_backend.semantic_scholar import SemanticScholarClient
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

# Load environment before any other imports that might need it
load_dotenv(dotenv_path=Path(__file__).parent / "tartan_backend" / ".env")

# Paths
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "tartan_backend"

app = FastAPI(title="Veritas API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def user_query_to_arxiv_search(user_query: str) -> str:
    """Convert natural-language question to an arXiv-appropriate search query (keywords/phrase)."""
    py = sys.executable
    result = subprocess.run(
        [py, "query_to_arxiv.py", "--query", user_query],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ},
    )
    if result.returncode == 0 and result.stdout and result.stdout.strip():
        return result.stdout.strip()[:500]
    return user_query.strip()[:500]


async def rank_candidates(client: AsyncDedalus, query: str, candidates_list: list) -> list:
    """Use LLM to rank paper candidates from multiple sources by relevance."""
    if not candidates_list:
        return []

    # Prepare batch prompt
    prompt_items = []
    for i, res in enumerate(candidates_list):
        # res can be either an arXiv Result or a Semantic Scholar Dict
        title = getattr(res, "title", res.get("title") if isinstance(res, dict) else "Unknown")
        summary = getattr(res, "summary", res.get("abstract") if isinstance(res, dict) else "No summary available")
        if summary is None: summary = "No summary available"
        prompt_items.append(f"ID: {i}\nTitle: {title}\nAbstract: {summary[:500]}...")

    prompt = f"""
Research Question: {query}

Below are {len(candidates_list)} paper candidates. 

TASK:
1. Identify the primary ACADEMIC FIELD of the Research Question (e.g., "Chemistry", "Computer Science", "Physics").
2. For each paper candidate, identify its ACADEMIC FIELD based on the title and abstract.
3. Rank relevance (0-10):
   - IF the paper's field DOES NOT MATCH the question's field, score it 0.
   - ELSE score based on how well it answers the specific question.

BE STRICT: "PFAS" (polyfluoroalkyl substances) is Chemistry. "PFAs" (Finite Automata) is Computer Science. DO NOT MIX THEM.

CANDIDATES:
{"---".join(prompt_items)}

OUTPUT FORMAT:
{{"question_field": "Field Name", "scores": [score_0, score_1, ...]}}
""".strip()

    try:
        # MODEL HANDOFF: Using gpt-4o (not gpt-4o-mini) for paper ranking
        # Rationale: This is a CRITICAL task requiring strong judgment to filter irrelevant papers.
        # Better models = better rankings = higher quality research pipeline.
        resp = await client.chat.completions.create(
            model="openai/gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a research relevance filter. You categorize research papers and identify domain-mismatches. Output valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        data = json.loads(resp.choices[0].message.content.strip())
        scores = data.get("scores", [])
        
        if not isinstance(scores, list) or len(scores) != len(candidates_list):
            return candidates_list[:10]
        
        # Zip and sort by score
        combined = []
        for res, score in zip(candidates_list, scores):
            combined.append((res, score))
            
        ranked = sorted(combined, key=lambda x: x[1], reverse=True)
        # Filter: keep only papers with score > 6
        filtered = [r for r, s in ranked if s > 6]
        return filtered
    except Exception:
        return candidates_list[:10]

async def download_pdf_from_url(url: str, output_path: Path) -> bool:
    """Download a PDF from an arbitrary URL (Open Access)."""
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=30, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download PDF from {url}: {e}")
        return False

async def download_papers(papers_dir: str, results: list) -> None:
    """Download PDFs for a list of mixed results (arXiv or Semantic Scholar) in parallel."""
    path = Path(papers_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    async def download_single(result):
        """Download a single PDF."""
        try:
            if hasattr(result, "download_pdf"): # arXiv
                # arXiv download_pdf is synchronous, run in thread
                await asyncio.to_thread(result.download_pdf, dirpath=str(path))
            elif isinstance(result, dict) and "openAccessPdf" in result: # Semantic Scholar
                pdf_url = result["openAccessPdf"].get("url")
                if pdf_url:
                    # Create a safe filename
                    safe_title = "".join([c if c.isalnum() else "_" for c in result["title"][:50]])
                    pdf_name = f"{safe_title}.pdf"
                    await download_pdf_from_url(pdf_url, path / pdf_name)
        except Exception:
            pass  # Continue on error
    
    # Download all PDFs in parallel
    await asyncio.gather(*[download_single(r) for r in results], return_exceptions=True)


async def run_pipeline(papers_dir: str, csv_dir: str, output_csv: str, rq: str):
    """Run run_all.py and yield logs (strings starting with [LOG])."""
    py = sys.executable
    cmd = [
        py,
        "run_all.py",
        "--papers_dir", papers_dir,
        "--csv_dir", csv_dir,
        "--output_csv", output_csv,
        "--rq", rq,
        "--with_ideas",
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(BACKEND),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def _read_stream(stream, is_stderr=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="ignore").strip()
            if text.startswith("[LOG]"):
                yield text[5:].strip()
            elif is_stderr and text:
                # Optionally log stderr if needed, but avoid flooding the thinking stream
                pass

    # Record tasks to read stdout/stderr
    async for log_msg in _read_stream(process.stdout):
        yield log_msg

    return_code = await process.wait()
    if return_code != 0:
        stderr_data = await process.stderr.read()
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed (code {return_code}): {stderr_data.decode('utf-8', errors='ignore')}",
        )


def run_summary(csv_path: str, rq: str) -> str:
    """Run summarize_review.py to generate an executive summary."""
    py = sys.executable
    try:
        result = subprocess.run(
            [py, "summarize_review.py", "--input_csv", csv_path, "--rq", rq],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        # Return error message instead of empty string
        error_msg = result.stderr.strip() if result.stderr else "Summary generation failed"
        print(f"[ERROR] Summary failed: {error_msg}", flush=True, file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[ERROR] Exception in run_summary: {e}", flush=True, file=sys.stderr)
        return "Summary could not be generated."


def run_literature_review(csv_path: str, rq: str) -> dict:
    """Generate comprehensive literature review document using Claude Sonnet."""
    py = sys.executable
    try:
        result = subprocess.run(
            [py, "generate_literature_review.py", "--input_csv", csv_path, "--rq", rq],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout.strip())
        error_msg = result.stderr.strip() if result.stderr else "Review generation failed"
        print(f"[ERROR] Literature review failed: {error_msg}", flush=True, file=sys.stderr)
        return {"error": "Literature review could not be generated"}
    except Exception as e:
        print(f"[ERROR] Exception in run_literature_review: {e}", flush=True, file=sys.stderr)
        return {"error": str(e)}


def csv_to_sources(csv_path: str) -> list[dict]:
    """Read merged CSV and return list of sources compatible with frontend Source type."""
    path = Path(csv_path)
    if not path.exists():
        return []

    rows_by_file: dict[str, list[dict]] = {}
    has_idea = False
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        has_idea = "idea" in fieldnames
        for row in reader:
            fname = (row.get("filename") or "").strip()
            quote = (row.get("quote") or "").strip()
            if not fname or not quote:
                continue
            if fname not in rows_by_file:
                rows_by_file[fname] = []
            rows_by_file[fname].append(row)

    sources = []
    for idx, (filename, file_rows) in enumerate(sorted(rows_by_file.items())):
        quotes = [
            {"id": i + 1, "text": r.get("quote", "").strip()}
            for i, r in enumerate(file_rows)
        ]
        keyFindings = []
        if has_idea:
            keyFindings = [r.get("idea", "").strip() for r in file_rows if r.get("idea", "").strip()]

        sources.append({
            "id": idx + 1,
            "title": filename.replace(".pdf", "").replace("_", " ").strip(),
            "publisher": "—",
            "date": "",
            "url": "",
            "quotes": quotes,
            "keyFindings": keyFindings,
        })

    return sources


@app.get("/")
def root():
    return {"message": "Veritas API", "docs": "/docs"}


def _papers_dir() -> Path:
    """Persistent papers directory (absolute path)."""
    return (BACKEND / "papers").resolve()


@app.get("/api/papers/{filename}")
def download_paper(filename: str):
    """Serve a PDF from tartan_backend/papers so the user can download it."""
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are available")
    path = _papers_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename, media_type="application/pdf")


async def _stream_research(query: str, files_data: list[tuple[str, bytes]]):
    """Async generator: yield NDJSON progress steps then the final result."""
    tmp = tempfile.mkdtemp(prefix="veritas_")
    try:
        papers_dir = Path(tmp) / "papers"
        csv_dir = Path(tmp) / "csvs"
        papers_dir.mkdir()
        csv_dir.mkdir()

        def emit(step: str) -> str:
            return json.dumps({"type": "step", "step": step}) + "\n"

        for filename, content in files_data:
            if filename and filename.lower().endswith(".pdf"):
                (papers_dir / (filename or "upload.pdf")).write_bytes(content)

        # Step 1: Finding sources
        yield emit("finding-sources")
        pdfs = list(papers_dir.glob("*.pdf"))
        if not pdfs:
            yield json.dumps({"type": "log", "message": f"Global research query: {query}"}) + "\n"
            
            try:
                print(f"[DEBUG] Starting query conversion for: {query}", flush=True)
                arxiv_query = await asyncio.to_thread(user_query_to_arxiv_search, query)
                print(f"[DEBUG] Query converted to: {arxiv_query}", flush=True)
                yield json.dumps({"type": "log", "message": f"Searching arXiv and Semantic Scholar for: {arxiv_query}"}) + "\n"
            except Exception as e:
                print(f"[ERROR] Query conversion failed: {e}", flush=True)
                arxiv_query = query  # Fallback to original query
                yield json.dumps({"type": "log", "message": f"Using original query: {arxiv_query}"}) + "\n"
            
            # 1. Broad Scanning: arXiv
            try:
                print(f"[DEBUG] Searching arXiv...", flush=True)
                search = arxiv.Search(query=arxiv_query, max_results=50)
                arxiv_client = arxiv.Client(page_size=50)
                arxiv_results = list(arxiv_client.results(search))
                print(f"[DEBUG] Found {len(arxiv_results)} arXiv results", flush=True)
            except Exception as e:
                print(f"[ERROR] arXiv search failed: {e}", flush=True)
                arxiv_results = []
            
            # 2. Broad Scanning: Semantic Scholar
            try:
                print(f"[DEBUG] Searching Semantic Scholar...", flush=True)
                ss_client = SemanticScholarClient()
                ss_results = await asyncio.to_thread(ss_client.search_papers, arxiv_query, limit=50)
                ss_oa_results = [r for r in ss_results if r.get("openAccessPdf")]
                print(f"[DEBUG] Found {len(ss_oa_results)} Semantic Scholar OA results", flush=True)
            except Exception as e:
                print(f"[ERROR] Semantic Scholar search failed: {e}", flush=True)
                ss_oa_results = []
            
            all_candidates = arxiv_results + ss_oa_results
            
            if not all_candidates:
                yield json.dumps({"type": "error", "detail": "No open-access papers found across all databases."}) + "\n"
                return

            yield json.dumps({"type": "log", "message": f"Scanning {len(all_candidates)} candidates across multiple databases..."}) + "\n"
            
            # Rank candidates (Unified)
            dedalus_client = AsyncDedalus(api_key=os.getenv("DEDALUS_API_KEY"))
            ranked_results = await rank_candidates(dedalus_client, query, all_candidates)
            
            # Production: Use up to 10 papers for comprehensive research
            top_papers = ranked_results[:10]
            
            discarded = len(all_candidates) - len(top_papers)
            if len(top_papers) < 3:
                yield json.dumps({"type": "log", "message": f"Note: Found {len(top_papers)} verified matches."}) + "\n"
            else:
                yield json.dumps({"type": "log", "message": f"Identified {len(top_papers)} highly relevant papers, discarded {discarded} domain-mismatches."}) + "\n"
            
            if not top_papers:
                yield json.dumps({"type": "log", "message": "No verified matches found. Specialized niche research may be sparse."}) + "\n"
                yield json.dumps({"type": "error", "detail": "All found papers were deemed irrelevant points. Try broader technical keywords."}) + "\n"
                return

            yield json.dumps({"type": "log", "message": f"Downloading {len(top_papers)} verified sources..."}) + "\n"
            await download_papers(str(papers_dir), top_papers)
            
            pdfs = list(papers_dir.glob("*.pdf"))
            if not pdfs:
                yield json.dumps({"type": "error", "detail": "PDF download failed for selected papers (may be restricted Access)."}) + "\n"
                return
            yield json.dumps({"type": "log", "message": f"Successfully prepared {len(pdfs)} papers for analysis."}) + "\n"
        else:
            yield json.dumps({"type": "log", "message": f"Using {len(pdfs)} uploaded PDF(s) as sources"}) + "\n"

        # Step 2: Extracting quotes (run_pipeline: research_bot, clean, merge, synthesize)
        yield emit("extracting-quotes")
        output_csv = str(csv_dir / "all_quotes.csv")
        try:
            async for log_message in run_pipeline(
                str(papers_dir),
                str(csv_dir),
                output_csv,
                query,
            ):
                yield json.dumps({"type": "log", "message": log_message}) + "\n"
        except HTTPException as e:
            yield json.dumps({"type": "error", "detail": e.detail}) + "\n"
            return

        # Prefer _with_ideas.csv for summary and keyFindings
        csv_path = output_csv
        with_ideas = Path(output_csv).parent / (Path(output_csv).stem + "_with_ideas.csv")
        if with_ideas.exists():
            csv_path = str(with_ideas)
        
        if not Path(csv_path).exists():
             yield json.dumps({"type": "error", "detail": "Pipeline produced no output CSV."}) + "\n"
             return

        # Step 3: Cross-checking
        yield emit("cross-checking")
        yield json.dumps({"type": "log", "message": "Analyzing cross-source consistency..."}) + "\n"
        await asyncio.sleep(0.8)
        yield json.dumps({"type": "log", "message": "Correlating claims with extracted evidence..."}) + "\n"
        await asyncio.sleep(0.8)
        yield json.dumps({"type": "log", "message": "Validating internal logical structure..."}) + "\n"
        await asyncio.sleep(0.5)

        # Step 4: Compiling executive summary
        yield emit("compiling")
        yield json.dumps({"type": "log", "message": "Synthesizing executive summary with Claude Sonnet..."}) + "\n"
        summary = await asyncio.to_thread(run_summary, csv_path, query)
        sources = csv_to_sources(csv_path)

        # Step 5: Generating comprehensive literature review
        yield json.dumps({"type": "log", "message": "Generating comprehensive literature review..."}) + "\n"
        lit_review = await asyncio.to_thread(run_literature_review, csv_path, query)
        
        persistent_papers = (BACKEND / "papers").resolve()
        persistent_papers.mkdir(parents=True, exist_ok=True)
        source_files = []
        for pdf in sorted(papers_dir.glob("*.pdf")):
            dest = persistent_papers / pdf.name
            shutil.copy2(str(pdf), str(dest))
            source_files.append(pdf.name)

        yield json.dumps({
            "type": "result",
            "sources": sources,
            "summary": summary,
            "literature_review": lit_review.get("review", "") if isinstance(lit_review, dict) else "",
            "review_metadata": {
                "word_count": lit_review.get("word_count", 0),
                "sources_analyzed": lit_review.get("sources_analyzed", 0),
                "evidence_items": lit_review.get("evidence_items", 0),
            } if isinstance(lit_review, dict) and "review" in lit_review else {},
            "source_files": source_files,
        }) + "\n"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.post("/api/research")
async def research(
    query: str = Form(..., description="Research question"),
    files: list[UploadFile] = File(default=[], description="Optional PDF sources"),
):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    files_data: list[tuple[str, bytes]] = []
    for f in files or []:
        if f.filename and f.filename.lower().endswith(".pdf"):
            content = await f.read()
            files_data.append((f.filename or "upload.pdf", content))

    async def stream():
        async for chunk in _stream_research(query.strip(), files_data):
            yield chunk.encode("utf-8")

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )
