"""
Generate a comprehensive literature review document from extracted quotes.
Uses Claude Sonnet for best-in-class long-form academic writing.
"""
import argparse
import asyncio
import csv
import json
import os
import sys

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

# MODEL: claude-3-5-sonnet - Best for comprehensive academic synthesis
LITERATURE_REVIEW_SYSTEM = (
    "You are an expert research assistant specializing in literature reviews. "
    "Given a research question and evidence from multiple sources, write a comprehensive, "
    "well-structured literature review in academic style. Use proper section headings, "
    "synthesize findings across sources, identify themes, and provide critical analysis. "
    "Maintain neutral, scholarly tone. Cite sources naturally using [Filename] notation."
)


async def generate_review_async(args):
    """Generate comprehensive literature review."""
    if not os.path.isfile(args.input_csv):
        print(json.dumps({"error": "CSV file not found"}))
        return

    # Load quotes/ideas from CSV
    rows = []
    with open(args.input_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("quote"):
                rows.append(row)

    if not rows:
        print(json.dumps({"error": "No evidence found"}))
        return

    # Group by source file
    sources_data = {}
    for row in rows:
        filename = row.get("filename", "Unknown")
        if filename not in sources_data:
            sources_data[filename] = []
        # Prefer idea over raw quote for higher-level synthesis
        content = row.get("idea", "").strip() or row.get("quote", "").strip()
        if content:
            sources_data[filename].append(content)

    # Build comprehensive prompt
    source_count = len(sources_data)
    total_evidence = len(rows)
   
    evidence_by_source = []
    for filename, contents in sources_data.items():
        evidence_str = "\n".join([f"  - {c}" for c in contents[:10]])  # Max 10 per source
        evidence_by_source.append(f"**[{filename}]**\n{evidence_str}")

    prompt = f"""
Research Question: {args.rq}

Sources Analyzed: {source_count} papers
Evidence Items: {total_evidence} findings

Evidence from Sources:
{chr(10).join(evidence_by_source)}

Task: Write a comprehensive literature review (1500-2000 words) structured as follows:

# Literature Review: {args.rq}

## 1. Introduction
- Background and context for this research question
- Why this question matters
- Scope of this review (sources analyzed, approach)

## 2. Methodology
- Search strategy and databases used
- Number of sources analyzed
- Selection criteria

## 3. Key Findings
Organize findings into 2-4 major themes. For each theme:
- Synthesize evidence across multiple sources
- Highlight consensus and contradictions
- Provide critical analysis

## 4. Discussion
- Cross-cutting patterns across all findings
- Gaps in current research
- Conflicting evidence and how to interpret it
- Limitations of reviewed literature

## 5. Conclusions
- Summary of key insights
- Implications for practice/research
- Future directions

## References
List all sources cited (use the filenames provided above)

Requirements:
- Use markdown formatting with proper headings
- Cite sources naturally: [Source_Name]
- Synthesize across sources (don't just list findings)
- Maintain academic tone
- Be comprehensive but concise
- Identify themes, not just summarize
""".strip()

    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        print(json.dumps({"error": "API key not configured"}))
        return

    client = AsyncDedalus(api_key=api_key)
    
    try:
        # TEMPORARILY using gpt-4o instead of Claude due to Dedalus API issues
        # TODO: Switch back to claude-3-5-sonnet-20241022 once API is fixed
        resp = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": LITERATURE_REVIEW_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4000,  # Allow for comprehensive output
        )
        
        review_text = getattr(resp.choices[0].message, "content", None) or str(resp)
        
        # Output as JSON for easy parsing by backend
        output = {
            "review": review_text.strip(),
            "word_count": len(review_text.split()),
            "sources_analyzed": source_count,
            "evidence_items": total_evidence,
        }
        
        print(json.dumps(output))
        
    except Exception as e:
        print(json.dumps({"error": f"Generation failed: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive literature review")
    parser.add_argument("--input_csv", required=True, help="CSV with quotes/ideas")
    parser.add_argument("--rq", required=True, help="Research question")
    args = parser.parse_args()
    
    asyncio.run(generate_review_async(args))


if __name__ == "__main__":
    main()
