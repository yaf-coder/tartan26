"""
Convert a natural-language research question into a short arXiv search query.
Prints the search query to stdout for use by the API.
"""
import argparse
import asyncio
import os
import re

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

SYSTEM = (
    "You convert research questions into precise arXiv search queries. "
    "arXiv works best with technical terms joined by boolean operators (AND, OR). "
    "STRATEGY: Always expand acronyms. Use a multi-part query: (Full Name OR Acronym) AND Technical Keywords. "
    "Example for PFAS: (\"Per- and polyfluoroalkyl substances\" OR PFAS) AND chemistry. "
    "Output ONLY the search query, no quotes, no explanation."
)


async def main_async():
    parser = argparse.ArgumentParser(description="Convert question to arXiv search query.")
    parser.add_argument("--query", required=True, help="User's research question")
    args = parser.parse_args()

    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        # Fallback: sanitize the question into a simple keyword query
        out = re.sub(r"\s+", " ", args.query.strip()).strip()[:200]
        print(out)
        return

    user = f"""Research question: {args.query.strip()}

Convert this into a short arXiv search query (keywords or phrase) that would find relevant academic papers. Output only the search query, nothing else."""

    client = AsyncDedalus(api_key=api_key)
    resp = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    text = getattr(resp.choices[0].message, "content", None) or str(resp)
    text = re.sub(r"\s+", " ", text.strip()).strip()
    # Remove quotes if the model wrapped the query
    if len(text) >= 2 and text[0] in '"\'' and text[-1] == text[0]:
        text = text[1:-1].strip()
    print(text[:300])


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
