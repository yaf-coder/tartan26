"""
Veritas API – connects the frontend to the research pipeline.
POST /api/research: research query (required); optional PDF files as additional sources.
If no files are sent, the API searches arXiv and downloads papers for the question.
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import arxiv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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


def fetch_papers_from_arxiv(papers_dir: str, query: str, max_results: int = 5) -> None:
    """Search arXiv for the query and download PDFs into papers_dir."""
    path = Path(papers_dir)
    path.mkdir(parents=True, exist_ok=True)
    dirpath = str(path)
    # Use small page_size so the API request asks for few results (arXiv rate-limits large requests)
    client = arxiv.Client(page_size=max_results)
    search = arxiv.Search(query=query.strip(), max_results=max_results)
    for result in client.results(search):
        try:
            result.download_pdf(dirpath=dirpath)
        except Exception:
            continue


def run_pipeline(papers_dir: str, csv_dir: str, output_csv: str, rq: str) -> str | None:
    """Run run_all.py in tartan_backend. Returns path to merged CSV (with_ideas if generated)."""
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
    result = subprocess.run(
        cmd,
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {result.stderr or result.stdout or 'Unknown error'}",
        )

    # Prefer _with_ideas.csv for summary and keyFindings
    with_ideas = Path(output_csv).parent / (Path(output_csv).stem + "_with_ideas.csv")
    if with_ideas.exists():
        return str(with_ideas)
    if Path(output_csv).exists():
        return output_csv
    raise HTTPException(status_code=500, detail="Pipeline produced no output CSV.")


def run_summary(csv_path: str, rq: str) -> str:
    """Run summarize_review.py and return summary text."""
    py = sys.executable
    result = subprocess.run(
        [py, "summarize_review.py", "--input_csv", csv_path, "--rq", rq],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ},
    )
    if result.returncode != 0:
        return "Summary could not be generated."
    return (result.stdout or "").strip() or "Summary could not be generated."


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


@app.post("/api/research")
async def research(
    query: str = Form(..., description="Research question"),
    files: list[UploadFile] = File(default=[], description="Optional PDF sources"),
):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    with tempfile.TemporaryDirectory(prefix="veritas_") as tmp:
        papers_dir = Path(tmp) / "papers"
        csv_dir = Path(tmp) / "csvs"
        papers_dir.mkdir()
        csv_dir.mkdir()

        # Optional: save uploaded PDFs as sources
        for f in files or []:
            if f.filename and f.filename.lower().endswith(".pdf"):
                path = papers_dir / (f.filename or "upload.pdf")
                content = await f.read()
                path.write_bytes(content)

        pdfs = list(papers_dir.glob("*.pdf"))
        if not pdfs:
            # No files: convert question to arXiv search query, then search and download papers
            arxiv_query = user_query_to_arxiv_search(query.strip())
            fetch_papers_from_arxiv(str(papers_dir), arxiv_query, max_results=5)
            pdfs = list(papers_dir.glob("*.pdf"))
            if not pdfs:
                raise HTTPException(
                    status_code=503,
                    detail="No papers could be found for this question. Try uploading PDFs as sources.",
                )

        output_csv = str(csv_dir / "all_quotes.csv")
        csv_path = run_pipeline(
            papers_dir=str(papers_dir),
            csv_dir=str(csv_dir),
            output_csv=output_csv,
            rq=query.strip(),
        )
        summary = run_summary(csv_path, query.strip())
        sources = csv_to_sources(csv_path)

        # Persist PDFs to tartan_backend/papers (absolute path so they always land on disk)
        persistent_papers = (BACKEND / "papers").resolve()
        persistent_papers.mkdir(parents=True, exist_ok=True)
        source_files: list[str] = []
        for pdf in sorted(papers_dir.glob("*.pdf")):
            dest = persistent_papers / pdf.name
            try:
                shutil.copy2(str(pdf), str(dest))
                source_files.append(pdf.name)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save paper {pdf.name}: {e}",
                )

    return {"sources": sources, "summary": summary, "source_files": source_files}
