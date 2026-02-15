"""
=============================================================================
FULL PAPER PIPELINE — Generate academic paper draft + PDF from quote CSV
=============================================================================

Standalone pipeline: given a papers directory, a merged quote CSV with "idea"
column, and a research question, builds APA-style citations per PDF, then
asks an LLM to write a concise academic paper with footnotes. Outputs Markdown
and a rendered PDF. Not used by the main Veritas API; intended for CLI or
batch use.

Usage
-----
  python full_paper_pipeline.py --papers_dir ./papers --notes_csv ./all_quotes_with_ideas.csv --topic "PFAS" --rq "Your question" [--out_md ./paper.md] [--out_pdf ./paper.pdf]

Output
------
- citations.json (APA reference + footnote per PDF)
- out_md (default paper.md)
- out_pdf (default paper.pdf)

Environment
----------
- DEDALUS_API_KEY : Required for citation inference and paper generation.
"""

import argparse
import asyncio
import csv
import json
import os
import re
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from pypdf import PdfReader
from dedalus_labs import (
    AsyncDedalus,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

# PDF output
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER

# ------------------------------------------------------------------------------
# ENV + DEFAULTS
# ------------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

DEFAULT_MODEL = "anthropic/claude-opus-4-6"

# ------------------------------------------------------------------------------
# UTILS
# ------------------------------------------------------------------------------

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def safe_json_loads(s: str) -> Optional[Any]:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        return None


# ------------------------------------------------------------------------------
# FAST + SAFE CHAT
# ------------------------------------------------------------------------------

async def chat(
    client: AsyncDedalus,
    model: str,
    system: str,
    user: str,
    *,
    timeout_s: float = 45.0,
    max_retries: int = 3,
) -> str:
    """
    Fast, bounded chat helper.
    """
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=timeout_s,
            )
            return resp.choices[0].message.content

        except (
            APITimeoutError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.RemoteProtocolError,
            APIConnectionError,
            RateLimitError,
        ) as e:
            last_err = e
        except Exception as e:
            last_err = e

        sleep_s = min(1.2 * attempt + random.random(), 6.0)
        print(
            f"⚠️ chat() attempt {attempt}/{max_retries} failed "
            f"({type(last_err).__name__}: {last_err}). Retrying in {sleep_s:.1f}s..."
        )
        await asyncio.sleep(sleep_s)

    raise RuntimeError(f"chat() failed after {max_retries} retries: {last_err}")


# ------------------------------------------------------------------------------
# PDF HELPERS
# ------------------------------------------------------------------------------

def extract_pdf_snippet(pdf_path: str, max_pages: int = 2, max_chars: int = 10000) -> str:
    reader = PdfReader(pdf_path)
    parts = []
    for i in range(min(max_pages, len(reader.pages))):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(f"[PAGE {i+1}]\n{text.strip()}")
    return "\n\n".join(parts)[:max_chars]


# ------------------------------------------------------------------------------
# CSV + EVIDENCE
# ------------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    eid: str
    filename: str
    page: str
    idea: str
    quote: str
    footnote: str
    reference: str


def read_quotes_with_ideas(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            if r.get("quote") and r.get("page_number") and r.get("filename"):
                rows.append(r)
        return rows


def build_evidence(rows: List[Dict[str, str]], citations: Dict[str, Any], max_items: int = 80) -> List[EvidenceItem]:
    out = []
    for i, r in enumerate(rows[:max_items], 1):
        fname = r["filename"]
        c = citations.get(fname, {})
        out.append(EvidenceItem(
            eid=f"E{i}",
            filename=fname,
            page=r["page_number"],
            idea=r.get("idea", ""),
            quote=r.get("quote", ""),
            footnote=c.get("footnote", f"{fname}, n.d."),
            reference=c.get("reference", f"{fname}. (n.d.)."),
        ))
    return out


def evidence_pack_text(evidence: List[EvidenceItem]) -> str:
    return "\n\n".join(
        f"[{e.eid}] {e.idea or e.quote} (p. {e.page})"
        for e in evidence
    )


def references_text(evidence: List[EvidenceItem]) -> str:
    refs = {e.filename: e.reference for e in evidence}
    return "\n".join(sorted(refs.values()))


# ------------------------------------------------------------------------------
# CITATIONS
# ------------------------------------------------------------------------------

CITE_SYSTEM = "Infer the best APA-style reference. Return JSON only."

async def build_citations_json(
    client: AsyncDedalus,
    model: str,
    papers_dir: str,
    out_path: str,
) -> Dict[str, Any]:
    citations = {}
    for fname in os.listdir(papers_dir):
        if not fname.lower().endswith(".pdf"):
            continue

        snippet = extract_pdf_snippet(os.path.join(papers_dir, fname))
        if not snippet:
            citations[fname] = {
                "reference": f"{fname}. (n.d.).",
                "footnote": f"{fname}, n.d.",
            }
            continue

        prompt = f"{snippet}\n\nReturn JSON {{reference, footnote}}."
        raw = await chat(client, model, CITE_SYSTEM, prompt, timeout_s=30, max_retries=2)
        obj = safe_json_loads(raw) or {}
        citations[fname] = {
            "reference": obj.get("reference", f"{fname}. (n.d.)."),
            "footnote": obj.get("footnote", f"{fname}, n.d."),
        }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(citations, f, indent=2)

    return citations


# ------------------------------------------------------------------------------
# PDF RENDER
# ------------------------------------------------------------------------------

def markdown_to_pdf(text: str, path: str):
    doc = SimpleDocTemplate(path, pagesize=letter,
        leftMargin=1*inch, rightMargin=1*inch,
        topMargin=1*inch, bottomMargin=1*inch)

    styles = getSampleStyleSheet()
    base = ParagraphStyle("Base", parent=styles["Normal"], fontSize=12, leading=20)
    title = ParagraphStyle("Title", parent=base, alignment=TA_CENTER, fontName="Times-Bold")

    story = []
    for block in text.split("\n\n"):
        if block.startswith("# "):
            story.append(Paragraph(block[2:], title))
        elif block.startswith("## "):
            story.append(Paragraph(block[3:], ParagraphStyle("H", parent=base, fontName="Times-Bold")))
        else:
            story.append(Paragraph(block.replace("\n", "<br/>"), base))
        story.append(Spacer(1, 8))

    doc.build(story)


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers_dir", default="./papers")
    parser.add_argument("--notes_csv", default="./all_quotes_with_ideas.csv")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--rq", required=True)
    parser.add_argument("--out_md", default="./paper.md")
    parser.add_argument("--out_pdf", default="./paper.pdf")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max_iters", type=int, default=1)
    args = parser.parse_args()

    client = AsyncDedalus(api_key=os.getenv("DEDALUS_API_KEY"))

    print("▶ Building citations")
    citations = await build_citations_json(client, args.model, args.papers_dir, "./citations.json")

    rows = read_quotes_with_ideas(args.notes_csv)
    evidence = build_evidence(rows, citations)
    evidence_pack = evidence_pack_text(evidence)
    refs = references_text(evidence)

    print("▶ Writing paper")
    draft = await chat(
        client,
        args.model,
        "Write a concise academic paper. Use footnotes.",
        f"RQ: {args.rq}\n\nEvidence:\n{evidence_pack}\n\nReferences:\n{refs}",
        timeout_s=60,
    )

    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(draft)

    markdown_to_pdf(draft, args.out_pdf)
    print("✅ Done")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
