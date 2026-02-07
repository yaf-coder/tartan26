import argparse
import asyncio
import csv
import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus

# Load .env next to this file (bulletproof)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_CONCURRENCY = 12


SYSTEM = (
    "You are a research writing assistant. "
    "Given a verbatim quote from a source, write ONE concise sentence that captures the quote's core idea "
    "in neutral academic language suitable for a paper. "
    "Do not include quotation marks. Do not add facts not present in the quote. "
    "Do not mention page numbers or filenames. Keep it a single sentence."
)

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

async def synthesize_one(client: AsyncDedalus, model: str, quote: str, rq: Optional[str]) -> str:
    quote = normalize_ws(quote)

    user = f"""
Research question (context):
{rq or "N/A"}

Quote:
{quote}

Task:
Write exactly ONE sentence that rephrases the quote into a strong, paper-usable idea/claim.
Constraints:
- Neutral academic tone.
- No new facts beyond the quote.
- No quotes, no citations, no source mentions.
- One sentence only.
""".strip()

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )

    try:
        text = resp.choices[0].message.content
    except Exception:
        text = str(resp)

    # Make it cleaner and enforce "single sentence-ish"
    text = normalize_ws(text)
    # If the model returned multiple lines/sentences, keep the first sentence-like chunk.
    # (Still not perfect, but helps.)
    for sep in ["\n", "  "]:
        if sep in text:
            text = text.split(sep)[0].strip()

    return text


async def main_async():
    parser = argparse.ArgumentParser(description="Add synthesized 'idea' column to cleaned quote CSV.")
    parser.add_argument("--input_csv", required=True, help="Path to cleaned CSV (quote,page_number,filename)")
    parser.add_argument("--output_csv", default=None, help="Path to write output CSV (default: *_with_ideas.csv)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Dedalus model identifier")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent requests")
    parser.add_argument("--rq", default=None, help="Optional research question context")
    parser.add_argument("--in_place", action="store_true", help="Overwrite input CSV (not recommended)")
    args = parser.parse_args()

    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        raise SystemExit("DEDALUS_API_KEY is not set. Put it in .env or export it.")

    if not os.path.isfile(args.input_csv):
        raise SystemExit(f"Input CSV not found: {args.input_csv}")

    if args.in_place and args.output_csv is not None:
        raise SystemExit("Use either --in_place OR --output_csv, not both.")

    if args.in_place:
        output_csv = args.input_csv
    else:
        if args.output_csv:
            output_csv = args.output_csv
        else:
            base, ext = os.path.splitext(args.input_csv)
            output_csv = f"{base}_with_ideas{ext}"

    # Read rows
    with open(args.input_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"quote", "page_number", "filename"}
        if not required.issubset(reader.fieldnames or []):
            raise SystemExit(f"CSV schema must include {required}. Found: {reader.fieldnames}")
        rows: List[Dict[str, str]] = list(reader)

    client = AsyncDedalus(api_key=api_key)
    sem = asyncio.Semaphore(args.concurrency)

    # Simple cache so identical quotes don't cost extra
    cache: Dict[str, str] = {}

    async def worker(i: int):
        quote = rows[i].get("quote", "")
        qkey = normalize_ws(quote).lower()
        if not qkey:
            rows[i]["idea"] = ""
            return

        if qkey in cache:
            rows[i]["idea"] = cache[qkey]
            return

        async with sem:
            idea = await synthesize_one(client, args.model, quote, args.rq)
            cache[qkey] = idea
            rows[i]["idea"] = idea

    await asyncio.gather(*(worker(i) for i in range(len(rows))))

    # Write output
    fieldnames = ["quote", "page_number", "filename", "idea"]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "quote": r.get("quote", ""),
                "page_number": r.get("page_number", ""),
                "filename": r.get("filename", ""),
                "idea": r.get("idea", ""),
            })

    print(f"Wrote ideas to: {output_csv}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
