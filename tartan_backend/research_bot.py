import os
import re
import csv
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv
from pypdf import PdfReader

from dedalus_labs import AsyncDedalus, DedalusRunner

load_dotenv()

# ----------------------------
# EDIT THESE
# ----------------------------
PDF_FOLDER = "./pdfs"
OUTPUT_CSV = "./rq_quotes.csv"

RESEARCH_QUESTION = (
    "How do extrajudicial killings persist through social complicity, and what mechanisms normalize them?"
)

MODEL = "openai/gpt-4o-mini"     # Dedalus model string you want
MAX_QUOTES_PER_PDF = 20
CONCURRENCY = 6
CHARS_PER_CHUNK = 12000


# ----------------------------
# Text utilities
# ----------------------------
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def extract_pdf_pages(pdf_path: str) -> List[Tuple[int, str]]:
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages.append((i + 1, t))
    return pages

def chunk_pages(pages: List[Tuple[int, str]], chars_per_chunk: int) -> List[Dict[str, Any]]:
    chunks = []
    cur = []
    cur_len = 0
    start = None
    end = None

    for pnum, ptext in pages:
        if start is None:
            start = pnum
        end = pnum

        add = f"\n\n[PAGE {pnum}]\n{ptext}"
        if cur and cur_len + len(add) > chars_per_chunk:
            chunks.append({"page_start": start, "page_end": end - 1, "text": "".join(cur)})
            cur, cur_len = [], 0
            start = pnum

        cur.append(add)
        cur_len += len(add)

    if cur:
        chunks.append({"page_start": start, "page_end": end, "text": "".join(cur)})

    return chunks

def safe_json_loads(s: str) -> Optional[Any]:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        return None


# ----------------------------
# Quote verification helpers
# ----------------------------
def find_quote_page(quote: str, pages: List[Tuple[int, str]]) -> Optional[int]:
    """
    Try to locate the quote verbatim in extracted page text.
    Returns the first page number where it appears, else None.
    """
    q = normalize_ws(quote)
    if not q:
        return None

    # Exact contains
    for pnum, ptext in pages:
        if q in normalize_ws(ptext):
            return pnum

    # Relaxed match: remove repeated spaces + try a smaller substring
    q2 = re.sub(r"\s+", " ", quote).strip()
    if len(q2) >= 40:
        needle = q2[: min(120, len(q2))]  # first chunk
        needle = normalize_ws(needle)
        for pnum, ptext in pages:
            if needle and needle in normalize_ws(ptext):
                return pnum

    return None

def dedupe_quotes(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for q in quotes:
        key = normalize_ws(q["quote"]).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


# ----------------------------
# LLM prompting
# ----------------------------
SYSTEM = (
    "You extract evidence from documents for academic research.\n"
    "Only return quotes that appear EXACTLY in the provided text. No paraphrase.\n"
    "Prefer quotes that directly answer the research question or provide strong evidence.\n"
    "Keep quotes short and self-contained (1–2 sentences)."
)

def user_prompt(rq: str, page_start: int, page_end: int, text: str, max_quotes: int) -> str:
    return f"""
RESEARCH QUESTION:
{rq}

TASK:
From the text below (pages {page_start}-{page_end}), extract up to {max_quotes} verbatim quotes that directly help answer the research question.
Each quote should be a sentence or two (short contiguous snippet).

OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "quotes": [
    {{
      "page": 12,
      "quote": "verbatim text here",
      "connection": "how this supports the research question (short)"
    }}
  ]
}}

TEXT:
{text}
""".strip()


async def extract_quotes_from_chunk(
    runner: DedalusRunner,
    rq: str,
    chunk: Dict[str, Any],
    max_quotes: int
) -> List[Dict[str, Any]]:
    resp = await runner.run(
        input=user_prompt(rq, chunk["page_start"], chunk["page_end"], chunk["text"], max_quotes),
        model=MODEL,
        system=SYSTEM,
    )
    raw = resp.final_output if hasattr(resp, "final_output") else str(resp)
    parsed = safe_json_loads(raw)
    if not parsed or "quotes" not in parsed or not isinstance(parsed["quotes"], list):
        return []

    out = []
    for item in parsed["quotes"]:
        if not isinstance(item, dict):
            continue
        page = item.get("page")
        quote = item.get("quote")
        conn = item.get("connection", "")
        if isinstance(quote, str) and quote.strip():
            out.append({
                "page": page if isinstance(page, int) else None,
                "quote": quote.strip(),
                "connection": str(conn).strip()
            })
    return out


async def process_pdf(
    runner: DedalusRunner,
    pdf_path: str,
    rq: str,
    max_quotes: int
) -> List[Dict[str, Any]]:
    pages = extract_pdf_pages(pdf_path)
    chunks = chunk_pages(pages, CHARS_PER_CHUNK)
    if not chunks:
        return []

    per_chunk = max(3, max_quotes // max(1, len(chunks)))

    collected: List[Dict[str, Any]] = []
    for ch in chunks:
        collected.extend(await extract_quotes_from_chunk(runner, rq, ch, per_chunk))

    collected = dedupe_quotes(collected)

    # Verify/fix page numbers
    verified: List[Dict[str, Any]] = []
    for q in collected:
        p = find_quote_page(q["quote"], pages)
        if p is None:
            # drop unverified quotes to keep output trustworthy
            continue
        verified.append({
            "page": p,
            "quote": q["quote"],
            "connection": q["connection"]
        })

    verified.sort(key=lambda x: (x["page"], -len(x["quote"])))
    return verified[:max_quotes]


async def main():
    if not os.path.isdir(PDF_FOLDER):
        raise SystemExit(f"PDF folder not found: {PDF_FOLDER}")

    pdfs = [
        os.path.join(PDF_FOLDER, f)
        for f in os.listdir(PDF_FOLDER)
        if f.lower().endswith(".pdf")
    ]
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {PDF_FOLDER}")

    client = AsyncDedalus(api_key=os.getenv("DEDALUS_API_KEY"))
    runner = DedalusRunner(client)

    sem = asyncio.Semaphore(CONCURRENCY)
    rows: List[Dict[str, Any]] = []

    async def worker(path: str):
        async with sem:
            quotes = await process_pdf(runner, path, RESEARCH_QUESTION, MAX_QUOTES_PER_PDF)
            for q in quotes:
                rows.append({
                    "file": os.path.basename(path),
                    "page": q["page"],
                    "quote": q["quote"],
                    "connection": q["connection"],
                    "research_question": RESEARCH_QUESTION
                })

    await asyncio.gather(*(worker(p) for p in pdfs))

    rows.sort(key=lambda r: (r["file"], r["page"]))

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["quote", "page_number", "filename"]
        )
        w.writeheader()
        for r in rows:
            w.writerow({
                "quote": r["quote"],
                "page_number": r["page"],
                "filename": r["file"]
            })


    print(f"Wrote {len(rows)} verified quotes to {OUTPUT_CSV}")


if __name__ == "__main__":
    asyncio.run(main())
