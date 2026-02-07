import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pypdf import PdfReader

from dedalus_labs import AsyncDedalus, RateLimitError

# Load .env from same directory as this file (bulletproof)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

# ----------------------------
# Defaults (override via CLI)
# ----------------------------
DEFAULT_MODEL = "openai/gpt-4o-mini"
# Reduced from 20 to 15 for faster processing
DEFAULT_MAX_QUOTES_PER_PDF = 15
# Bumping concurrency for faster parallel paper processing
DEFAULT_CONCURRENCY = 3
DEFAULT_CHARS_PER_CHUNK = 10_000
DEFAULT_OUTPUT_NAME = "rq_quotes.csv"

# Global rate limit: at most 1 request start per second (60/min)
_rate_lock = asyncio.Lock()
_last_request_time = 0.0
MIN_REQUEST_INTERVAL = 0.5
RATE_LIMIT_WAIT_SEC = 62


# ----------------------------
# Text utilities
# ----------------------------
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def sanitize_text(text: str) -> str:
    """
    Clean text to remove invalid Unicode characters (surrogates, etc).
    
    PDFs with mathematical symbols often contain Unicode surrogate pairs
    that cannot be encoded in UTF-8, causing UnicodeEncodeError.
    """
    if not text:
        return text
    
    cleaned = []
    for char in text:
        # Remove surrogate characters (U+D800 to U+DFFF)
        if 0xD800 <= ord(char) <= 0xDFFF:
            cleaned.append(' ')
        # Remove other problematic control characters
        elif ord(char) < 32 and char not in '\n\t\r':
            cleaned.append(' ')
        else:
            cleaned.append(char)
    
    return ''.join(cleaned)



def extract_pdf_pages(pdf_path: str) -> List[Tuple[int, str]]:
    reader = PdfReader(pdf_path)
    pages: List[Tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages.append((i + 1, t))
    return pages


def chunk_pages(pages: List[Tuple[int, str]], chars_per_chunk: int) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    cur: List[str] = []
    cur_len = 0
    start: Optional[int] = None
    end: Optional[int] = None

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

    if cur and start is not None and end is not None:
        chunks.append({"page_start": start, "page_end": end, "text": "".join(cur)})

    return chunks


def safe_json_loads(s: str) -> Optional[Any]:
    s = (s or "").strip()
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
    q = normalize_ws(quote)
    if not q:
        return None

    for pnum, ptext in pages:
        if q in normalize_ws(ptext):
            return pnum

    q2 = normalize_ws(quote)
    if len(q2) >= 40:
        needle = q2[: min(120, len(q2))]
        for pnum, ptext in pages:
            if needle and needle in normalize_ws(ptext):
                return pnum

    return None


def dedupe_quotes(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for q in quotes:
        key = normalize_ws(q.get("quote", "")).lower()
        if not key or key in seen:
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
    # Sanitize text to remove Unicode surrogates from math PDFs
    text = sanitize_text(text)
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
      "quote": "verbatim text here"
    }}
  ]
}}

TEXT:
{text}
""".strip()


async def _throttle() -> None:
    """Wait until at least MIN_REQUEST_INTERVAL has passed since last request (global)."""
    global _last_request_time
    async with _rate_lock:
        now = time.monotonic()
        wait = _last_request_time + MIN_REQUEST_INTERVAL - now
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_time = time.monotonic()


async def chat_json(client: AsyncDedalus, model: str, system: str, user: str) -> str:
    """
    Call Dedalus chat completions. Throttled to stay under 60/min; retries on 429.
    """
    for attempt in range(1, 4):
        await _throttle()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            try:
                return resp.choices[0].message.content
            except Exception:
                return str(resp)
        except RateLimitError:
            if attempt < 3:
                await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
            else:
                raise


async def extract_quotes_from_chunk(
    client: AsyncDedalus,
    rq: str,
    chunk: Dict[str, Any],
    max_quotes: int,
    model: str,
) -> List[Dict[str, Any]]:
    prompt = user_prompt(rq, chunk["page_start"], chunk["page_end"], chunk["text"], max_quotes)
    raw = await chat_json(client, model=model, system=SYSTEM, user=prompt)

    parsed = safe_json_loads(raw)
    if not parsed or "quotes" not in parsed or not isinstance(parsed["quotes"], list):
        return []

    out: List[Dict[str, Any]] = []
    for item in parsed["quotes"]:
        if not isinstance(item, dict):
            continue
        page = item.get("page")
        quote = item.get("quote")
        if isinstance(quote, str) and quote.strip():
            out.append({"page": page if isinstance(page, int) else None, "quote": quote.strip()})
    return out


async def process_pdf(
    client: AsyncDedalus,
    pdf_path: str,
    rq: str,
    max_quotes: int,
    chars_per_chunk: int,
    model: str,
) -> List[Dict[str, Any]]:
    pages = extract_pdf_pages(pdf_path)
    print(f"[LOG] Read {len(pages)} pages from {os.path.basename(pdf_path)}", flush=True)
    chunks = chunk_pages(pages, chars_per_chunk)
    if not chunks:
        print(f"[LOG] No text content found in {os.path.basename(pdf_path)}", flush=True)
        return []
    
    print(f"[LOG] Analyzing {len(chunks)} text chunks for '{rq[:30]}...'", flush=True)

    per_chunk = max(3, max_quotes // max(1, len(chunks)))

    collected: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        print(f"[LOG] Extracting quotes from chunk {i+1}/{len(chunks)}...", flush=True)
        collected.extend(await extract_quotes_from_chunk(client, rq, ch, per_chunk, model))

    collected = dedupe_quotes(collected)
    print(f"[LOG] Found {len(collected)} candidate quotes. Verifying against source text...", flush=True)

    verified: List[Dict[str, Any]] = []
    for q in collected:
        p = find_quote_page(q["quote"], pages)
        if p is None:
            continue
        verified.append({"page": p, "quote": q["quote"]})

    verified.sort(key=lambda x: (x["page"], -len(x["quote"])))
    print(f"[LOG] Verified {len(verified)} quotes in {os.path.basename(pdf_path)}", flush=True)
    return verified[:max_quotes]


async def async_main():
    parser = argparse.ArgumentParser(description="Extract verified quotes from PDFs into a CSV.")
    parser.add_argument("--papers_dir", default="./papers", help="Folder containing PDF files.")
    parser.add_argument("--csv_dir", default="./csvs", help="Folder to write CSV output into.")
    parser.add_argument("--rq", required=True, help="Research question.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Dedalus model identifier.")
    parser.add_argument("--max_quotes_per_pdf", type=int, default=DEFAULT_MAX_QUOTES_PER_PDF)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--chars_per_chunk", type=int, default=DEFAULT_CHARS_PER_CHUNK)
    parser.add_argument("--output_name", default=DEFAULT_OUTPUT_NAME, help="Output CSV filename.")
    args = parser.parse_args()

    # Create cache directory
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache", "papers")
    os.makedirs(cache_dir, exist_ok=True)

    if os.getenv("DEDALUS_API_KEY") in (None, ""):
        raise SystemExit("DEDALUS_API_KEY is not set. Put it in .env or export it.")

    pdf_folder = args.papers_dir
    if not os.path.isdir(pdf_folder):
        raise SystemExit(f"PDF folder not found: {pdf_folder}")

    pdfs = [
        os.path.join(pdf_folder, f)
        for f in os.listdir(pdf_folder)
        if f.lower().endswith(".pdf")
    ]
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {pdf_folder}")

    os.makedirs(args.csv_dir, exist_ok=True)
    output_csv = os.path.join(args.csv_dir, args.output_name)

    client = AsyncDedalus(api_key=os.getenv("DEDALUS_API_KEY"))

    sem = asyncio.Semaphore(args.concurrency)
    rows: List[Dict[str, Any]] = []

    async def worker(path: str):
        # Calculate hashes
        pdf_hash = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                pdf_hash.update(chunk)
        pdf_h = pdf_hash.hexdigest()
        
        rq_h = hashlib.sha256(args.rq.encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{pdf_h}_{rq_h}.json")

        # Check cache
        if os.path.exists(cache_file):
            print(f"[LOG] Cache hit for {os.path.basename(path)}", flush=True)
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_quotes = json.load(f)
                    for q in cached_quotes:
                        rows.append(
                            {
                                "quote": q["quote"],
                                "page_number": q["page"],
                                "filename": os.path.basename(path),
                            }
                        )
                    return
            except Exception as e:
                print(f"[LOG] Cache read error for {os.path.basename(path)}: {e}", flush=True)

        async with sem:
            quotes = await process_pdf(
                client=client,
                pdf_path=path,
                rq=args.rq,
                max_quotes=args.max_quotes_per_pdf,
                chars_per_chunk=args.chars_per_chunk,
                model=args.model,
            )
            
            # Save to cache
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(quotes, f)
            except Exception as e:
                print(f"[LOG] Cache write error for {os.path.basename(path)}: {e}", flush=True)

            for q in quotes:
                rows.append(
                    {
                        "quote": q["quote"],
                        "page_number": q["page"],
                        "filename": os.path.basename(path),
                    }
                )

    await asyncio.gather(*(worker(p) for p in pdfs))

    rows.sort(key=lambda r: (r["filename"], int(r["page_number"])) if str(r["page_number"]).isdigit() else (r["filename"], 10**9))

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["quote", "page_number", "filename"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} verified quotes to {output_csv}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
