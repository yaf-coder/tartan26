"""
=============================================================================
SUMMARIZE REVIEW — Executive summary from quote CSV
=============================================================================

Reads a merged quote CSV (with optional "idea" column), builds a short evidence
pack for the LLM, and prints a single paragraph executive summary to stdout.
Used by the Veritas API after the pipeline completes to show the user a quick
overview before the full literature review.

Usage
-----
  python summarize_review.py --input_csv ./all_quotes_with_ideas.csv --rq "Your question"
  # Summary printed to stdout; API captures it for the streamed result.

Environment
----------
- DEDALUS_API_KEY : Required. Uses gpt-4o for summary quality.
"""
import argparse
import asyncio
import csv
import os
import sys

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

SUMMARY_SYSTEM = (
    "You are a research assistant. Given a research question and a list of verbatim quotes "
    "from sources, write ONE short paragraph (3–5 sentences) that summarizes the key evidence "
    "and how it relates to the research question. Use neutral academic tone. Do not invent facts."
)


async def main_async():
    parser = argparse.ArgumentParser(description="Generate literature review summary from quote CSV.")
    parser.add_argument("--input_csv", required=True, help="Merged CSV with quote, page_number, filename [, idea]")
    parser.add_argument("--rq", required=True, help="Research question")
    parser.add_argument("--max_quotes", type=int, default=30, help="Max quotes to include in prompt (default 30)")
    args = parser.parse_args()

    if not os.path.isfile(args.input_csv):
        print("", file=sys.stderr)
        sys.exit(1)

    rows = []
    with open(args.input_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("quote"):
                rows.append(row)

    if not rows:
        print("No relevant evidence was found for this question.")
        return

    # Build prompt with first N quotes (and ideas if present)
    quote_lines = []
    for i, r in enumerate(rows[: args.max_quotes]):
        idea = r.get("idea", "").strip()
        quote = (r.get("quote", "") or "").strip()
        if idea:
            quote_lines.append(f"- [{r.get('filename', '')}]: {idea}")
        else:
            quote_lines.append(f"- [{r.get('filename', '')}]: \"{quote[:200]}{'...' if len(quote) > 200 else ''}\"")

    user = f"""
Research question: {args.rq}

Evidence from sources (quotes/ideas):
{chr(10).join(quote_lines)}

Task: Write one short paragraph summarizing what this evidence shows regarding the research question.
""".strip()

    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        print("No relevant evidence could be summarized (API not configured).")
        return

    client = AsyncDedalus(api_key=api_key)
    # TEMPORARILY using gpt-4o instead of Claude due to Dedalus API issues
    # TODO: Switch back to claude-3-5-sonnet-20241022 once API is fixed
    resp = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    text = getattr(resp.choices[0].message, "content", None) or str(resp)
    print(text.strip())


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
