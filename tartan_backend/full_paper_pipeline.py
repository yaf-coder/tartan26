import argparse
import asyncio
import csv
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pypdf import PdfReader
from dedalus_labs import AsyncDedalus

# PDF output
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER

# NOTE: these were referenced in chat() but not imported in the original file.
# Keeping behavior the same (retry/backoff) requires these imports.
import random
import httpx
from httpx import TimeoutException as APITimeoutError  # fallback alias for compatibility

# Load .env next to this file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Most recent/powerful Claude listed in Dedalus docs: Claude Opus 4.6
DEFAULT_MODEL = "anthropic/claude-opus-4-6"


# ----------------------------
# Helpers
# ----------------------------
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


async def chat(
    client: AsyncDedalus,
    model: str,
    system: str,
    user: str,
    *,
    timeout_s: float = 180.0,
    max_retries: int = 6,
) -> str:
    """
    Robust chat call with retries + exponential backoff.
    timeout_s applies to the underlying HTTP request.
    """
    last_err: Optional[Exception] = None
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
            try:
                return resp.choices[0].message.content
            except Exception:
                return str(resp)

        except (APITimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_err = e
        except Exception as e:
            # Transient errors sometimes show up as generic exceptions; retry a few times.
            last_err = e

        # Backoff
        sleep_s = min(2 ** attempt + random.random(), 30.0)
        print(
            f"⚠️  chat() attempt {attempt}/{max_retries} failed ({type(last_err).__name__}). "
            f"Retrying in {sleep_s:.1f}s..."
        )
        await asyncio.sleep(sleep_s)

    raise RuntimeError(f"chat() failed after {max_retries} retries: {last_err}")


def extract_pdf_snippet(pdf_path: str, max_pages: int = 2, max_chars: int = 12000) -> str:
    """
    Extract text from the first max_pages pages.
    Used to let the model infer a citation/reference entry for citations.json.
    """
    reader = PdfReader(pdf_path)
    parts = []
    for i in range(min(max_pages, len(reader.pages))):
        try:
            t = reader.pages[i].extract_text() or ""
        except Exception:
            t = ""
        t = t.strip()
        if t:
            parts.append(f"[PAGE {i+1}]\n{t}")
    text = "\n\n".join(parts)
    return text[:max_chars]


def read_quotes_with_ideas(csv_path: str) -> List[Dict[str, str]]:
    """
    Notes sheet = all_quotes_with_ideas.csv
    Required columns: quote,page_number,filename
    Strongly recommended: idea
    """
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row.")

        required = {"quote", "page_number", "filename"}
        if not required.issubset(set(reader.fieldnames)):
            raise SystemExit(f"CSV must include {required}. Found: {reader.fieldnames}")

        rows = []
        for r in reader:
            quote = (r.get("quote") or "").strip()
            page = (r.get("page_number") or "").strip()
            fname = (r.get("filename") or "").strip()
            idea = (r.get("idea") or "").strip()
            if quote and page and fname:
                rows.append({"quote": quote, "page_number": page, "filename": fname, "idea": idea})
        return rows


# ----------------------------
# citations.json builder (from PDFs)
# ----------------------------
CITE_SYSTEM = (
    "You are a meticulous bibliographic assistant.\n"
    "Given the first pages of a PDF, infer the best possible APA reference.\n"
    "Do NOT invent details that are not reasonably inferable from the text.\n"
    "If missing, use (n.d.) and omit unknown fields.\n"
    "Return ONLY valid JSON in the specified schema.\n"
)

CITE_SCHEMA = """
Return JSON:
{
  "reference": "APA reference entry (one line)",
  "footnote": "Footnote-style short citation (one line)"
}
""".strip()


async def build_citations_json(
    client: AsyncDedalus,
    model: str,
    papers_dir: str,
    out_path: str,
    max_pages: int = 2,
) -> Dict[str, Any]:
    pdfs = [
        os.path.join(papers_dir, f)
        for f in os.listdir(papers_dir)
        if f.lower().endswith(".pdf")
    ]
    if not pdfs:
        raise SystemExit(f"No PDFs found in {papers_dir}")

    citations: Dict[str, Any] = {}

    async def one(pdf_path: str):
        fname = os.path.basename(pdf_path)
        snippet = extract_pdf_snippet(pdf_path, max_pages=max_pages)
        if not snippet:
            citations[fname] = {
                "reference": f"{os.path.splitext(fname)[0]}. (n.d.). [PDF].",
                "footnote": f"{os.path.splitext(fname)[0]}, n.d.",
            }
            return

        prompt = f"""
You are given an excerpt from the first pages of a research paper PDF. Create an APA reference entry.

FILENAME:
{fname}

PDF EXCERPT:
{snippet}

{CITE_SCHEMA}
""".strip()

        raw = await chat(client, model, CITE_SYSTEM, prompt)
        obj = safe_json_loads(raw)
        if not isinstance(obj, dict) or "reference" not in obj or "footnote" not in obj:
            base = os.path.splitext(fname)[0].replace("_", " ")
            citations[fname] = {
                "reference": f"{base}. (n.d.). [PDF].",
                "footnote": f"{base}, n.d.",
            }
            return

        ref = norm_ws(str(obj.get("reference", "")))
        foot = norm_ws(str(obj.get("footnote", "")))
        if not ref:
            base = os.path.splitext(fname)[0].replace("_", " ")
            ref = f"{base}. (n.d.). [PDF]."
        if not foot:
            base = os.path.splitext(fname)[0].replace("_", " ")
            foot = f"{base}, n.d."

        citations[fname] = {"reference": ref, "footnote": foot}

    # modest parallelism
    sem = asyncio.Semaphore(6)

    async def wrapped(path: str):
        async with sem:
            await one(path)

    await asyncio.gather(*(wrapped(p) for p in pdfs))

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(citations, f, ensure_ascii=False, indent=2)

    return citations


# ----------------------------
# Evidence pack
# ----------------------------
@dataclass
class EvidenceItem:
    eid: str
    filename: str
    page: str
    idea: str
    quote: str
    footnote: str
    reference: str


def build_evidence(rows: List[Dict[str, str]], citations: Dict[str, Any], max_items: int = 100) -> List[EvidenceItem]:
    out: List[EvidenceItem] = []
    for i, r in enumerate(rows[:max_items], 1):
        fname = r["filename"]
        page = r["page_number"]
        idea = r.get("idea", "").strip()
        quote = r.get("quote", "").strip()

        c = citations.get(fname, {})
        foot = c.get("footnote") or f"{os.path.splitext(fname)[0]}, n.d."
        ref = c.get("reference") or f"{os.path.splitext(fname)[0]}. (n.d.). [PDF]."

        out.append(
            EvidenceItem(
                eid=f"E{i}",
                filename=fname,
                page=page,
                idea=idea,
                quote=quote,
                footnote=foot,
                reference=ref,
            )
        )
    return out


def evidence_pack_text(evidence: List[EvidenceItem], max_items: int = 80) -> str:
    lines = []
    for e in evidence[:max_items]:
        lines.append(
            f"[{e.eid}] FILE={e.filename} PAGE={e.page}\n"
            f"IDEA: {e.idea if e.idea else '(missing idea; paraphrase carefully from quote)'}\n"
            f"QUOTE: {e.quote}\n"
            f"FOOTNOTE: {e.footnote}"
        )
    return "\n\n".join(lines)


def references_text(evidence: List[EvidenceItem]) -> str:
    used: Dict[str, str] = {}
    for e in evidence:
        used[e.filename] = e.reference
    refs = sorted(used.values(), key=lambda s: s.lower())
    return "\n".join(refs)


# ----------------------------
# Outline -> Expand -> Grade loop
# ----------------------------
OUTLINE_SYSTEM = (
    "You are an expert argument planner.\n"
    "Create a persuasive outline that answers the research question.\n"
    "Prefer using IDEA paraphrases as evidence; use QUOTES only when absolutely necessary.\n"
    "Do not fabricate sources, quotes, or page numbers.\n"
    "Return ONLY valid JSON.\n"
)

OUTLINE_SCHEMA = """
Return JSON:
{
  "paper_title": "...",
  "thesis": "1-2 sentences",
  "sections": [
    {
      "heading": "Heading name",
      "purpose": "why this section exists",
      "claims": [
        {
          "claim": "arguable point",
          "evidence_ids": ["E1","E7"],
          "quote_only_ids": ["E7"],
          "analysis_notes": "how to connect evidence to claim"
        }
      ]
    }
  ]
}
""".strip()


def outline_prompt(topic: str, rq: str, notes: str, evidence_pack: str) -> str:
    return f"""
TOPIC:
{topic}

RESEARCH QUESTION:
{rq}

NOTES (your entire notes sheet; treat as ground truth for what you want to say):
{notes}

EVIDENCE PACK (allowed evidence IDs):
{evidence_pack}

TASK:
Draft a strong argumentative outline with:
- Abstract
- Introduction
- 2–4 body sections with headings
- Conclusion
- Footnotes + References

Constraints:
- Use ideas more than quotes.
- Quote only when it adds unique force/precision; otherwise paraphrase via IDEA and cite it.

{OUTLINE_SCHEMA}
""".strip()


EXPAND_SYSTEM = (
    "You are an expert academic writer.\n"
    "Write an APA-like student research paper (clear headings, abstract, intro, conclusion).\n"
    "Citations must be FOOTNOTES using [^1], [^2], ... markers.\n"
    "Use IDEA paraphrases as default evidence and cite them with footnotes.\n"
    "Use direct quotes sparingly and only when marked quote_only_ids.\n"
    "Do not invent any citations, sources, or page numbers.\n"
    "Return ONLY the full paper text.\n"
)

def expand_prompt(
    header: Dict[str, str],
    topic: str,
    rq: str,
    notes: str,
    outline_json: Dict[str, Any],
    evidence_pack: str,
    references: str,
    min_words: int,
    max_words: int,
) -> str:
    return f"""
Write the full paper now.

HEADER BLOCK (put at top):
{header["title"]}
{header["author"]}
{header["institution"]}
{header["course"]}
{header["instructor"]}
{header["date"]}

TOPIC:
{topic}

RESEARCH QUESTION:
{rq}

NOTES (what you want to say; use as content constraints):
{notes}

OUTLINE (follow exactly):
{json.dumps(outline_json, ensure_ascii=False, indent=2)}

EVIDENCE PACK (allowed citations only):
{evidence_pack}

REFERENCES (must appear at end):
{references}

FOOTNOTE RULES:
- In text, cite with markers like [^1] where needed.
- After Conclusion, include a "Footnotes" section listing [^1]: ... etc.
- Each footnote must include the FOOTNOTE text and the page number from the evidence item (p. X).
  Example: "[^3]: Smith (2021), p. 12."
- Do NOT flood with quotes; paraphrase IDEA most of the time.
- Only use direct QUOTE for evidence IDs in quote_only_ids and still cite.

LENGTH:
- {min_words} to {max_words} words (approx; +/- 10% ok).

OUTPUT:
Return ONLY the full paper in Markdown-friendly formatting:
- Use "# " for the title line (optional)
- Use "## " for headings
- Include "Footnotes" and "References"
""".strip()


GRADER_SYSTEM = (
    "You are a strict grader for an academic argument essay.\n"
    "Check structure, argument quality, evidence discipline, and footnote correctness.\n"
    "Return ONLY JSON.\n"
)

def grade_prompt(draft: str, rq: str, min_words: int, max_words: int) -> str:
    return f"""
Grade if satisfactory.

PASS/FAIL RUBRIC:
1) Strong thesis and consistent argument answering the research question.
2) Clear structure: header block, Abstract, Introduction, headed body sections, Conclusion, Footnotes, References.
3) Evidence discipline: IDEA paraphrases mostly; quotes are rare and purposeful.
4) Footnotes: every [^n] marker has a matching footnote entry; each footnote includes a page number.
5) No fabricated sources/pages.
6) Length ~ {min_words}-{max_words} (+/-10%).

Return ONLY JSON:
{{
  "satisfactory": true/false,
  "score": 0-100,
  "major_issues": ["..."],
  "minor_issues": ["..."],
  "revision_plan": ["...concrete edits..."]
}}

RESEARCH QUESTION:
{rq}

DRAFT:
{draft}
""".strip()


def revise_prompt(draft: str, grade_json: Dict[str, Any], notes: str, evidence_pack: str, references: str) -> str:
    return f"""
Revise the paper to address grader feedback.

GRADER JSON:
{json.dumps(grade_json, ensure_ascii=False, indent=2)}

NOTES (do not add content beyond these ideas):
{notes}

EVIDENCE PACK (allowed citations only):
{evidence_pack}

REFERENCES (must appear at end):
{references}

RULES:
- Fix footnote numbering/mismatches.
- Reduce quote usage if too high; prefer idea paraphrases with footnotes.
- Strengthen analysis and transitions.
- Do not invent sources or page numbers.

Return ONLY the revised full paper text.
""".strip()


# ----------------------------
# PDF renderer
# ----------------------------
def markdown_to_pdf(md_text: str, pdf_path: str):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        title="Research Paper",
    )

    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "Base",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=12,
        leading=24,  # double-ish spacing
        spaceAfter=12,
    )
    title_style = ParagraphStyle(
        "Title",
        parent=base,
        alignment=TA_CENTER,
        fontName="Times-Bold",
        spaceAfter=18,
    )
    h_style = ParagraphStyle(
        "Heading",
        parent=base,
        fontName="Times-Bold",
        spaceBefore=12,
        spaceAfter=6,
    )

    story: List[Any] = []

    blocks = [b.strip() for b in md_text.split("\n\n") if b.strip()]
    for b in blocks:
        if b.startswith("# "):
            story.append(Paragraph(b[2:].strip(), title_style))
            continue
        if b.startswith("## "):
            story.append(Paragraph(b[3:].strip(), h_style))
            continue
        if b.strip() == "---":
            story.append(PageBreak())
            continue

        safe = b.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br/>")
        story.append(Paragraph(safe, base))
        story.append(Spacer(1, 6))

    doc.build(story)


def outline_sections(outline: Dict[str, Any]) -> List[Dict[str, Any]]:
    secs = outline.get("sections")
    if isinstance(secs, list):
        return [s for s in secs if isinstance(s, dict)]
    return []

SECTION_SYSTEM = EXPAND_SYSTEM

def section_expand_prompt(
    header: Dict[str, str],
    topic: str,
    rq: str,
    outline_json: Dict[str, Any],
    section_obj: Dict[str, Any],
    evidence_pack: str,
    references: str,
    already_written: str,
) -> str:
    """
    Expand ONE section at a time. already_written helps maintain continuity.
    """
    return f"""
We are writing a paper section-by-section.

HEADER (for context):
Title: {header["title"]}
Author: {header["author"]}
Institution: {header["institution"]}
Course: {header["course"]}
Instructor: {header["instructor"]}
Date: {header["date"]}

TOPIC:
{topic}

RESEARCH QUESTION:
{rq}

FULL OUTLINE (for global coherence):
{json.dumps(outline_json, ensure_ascii=False, indent=2)}

SECTION TO WRITE NOW:
{json.dumps(section_obj, ensure_ascii=False, indent=2)}

EVIDENCE PACK (allowed citations only):
{evidence_pack}

REFERENCES (must appear at end eventually):
{references}

WHAT'S ALREADY WRITTEN (do not repeat; continue smoothly):
{already_written if already_written.strip() else "(nothing yet)"}

RULES:
- Use IDEA paraphrases by default with footnote markers [^n].
- Use direct quotes only for IDs in quote_only_ids for this section.
- Don’t flood with quotes.
- Keep footnote numbering consistent across the whole paper. If already_written ends at [^k], continue at [^(k+1)].

OUTPUT:
Return ONLY the text for THIS section (Markdown-friendly).
Do NOT include References yet unless this section is the final "References".
""".strip()


# ----------------------------
# Public async entrypoint (backend-friendly)
# ----------------------------
async def generate(
    *,
    papers_dir: str,
    notes_csv: str,
    topic: str,
    rq: str,
    out_md: str,
    out_pdf: str,
    model: str = DEFAULT_MODEL,
    citations_json: Optional[str] = None,
    # APA-ish header block fields
    title: str = "Research Paper",
    author: str = "Your Name",
    institution: str = "Your Institution",
    course: str = "Course",
    instructor: str = "Instructor",
    date: str = "Date",
    min_words: int = 1400,
    max_words: int = 2400,
    max_iters: int = 4,
    progress_cb=None,
) -> Dict[str, str]:
    """
    Backend-friendly equivalent of main_async().

    Generates citations.json (unless citations_json provided), then outline,
    then section-by-section expansion, then grade/revise loop, and finally
    writes out_md and out_pdf.

    Returns artifact paths.
    """
    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        raise SystemExit("DEDALUS_API_KEY is not set. Put it in .env or export it.")

    if not os.path.isdir(papers_dir):
        raise SystemExit(f"papers_dir not found: {papers_dir}")

    if not os.path.isfile(notes_csv):
        raise SystemExit(f"notes_csv not found: {notes_csv}")

    # Default citations_json next to out_md if not provided
    if citations_json is None:
        out_base_dir = os.path.dirname(os.path.abspath(out_md))
        citations_json = os.path.join(out_base_dir, "citations.json")

    # Ensure output directories exist
    os.makedirs(os.path.dirname(os.path.abspath(out_md)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(citations_json)), exist_ok=True)

    client = AsyncDedalus(api_key=api_key)

    def prog(p: int):
        if callable(progress_cb):
            try:
                progress_cb(int(p))
            except Exception:
                pass

    prog(3)

    # 1) Build citations.json from PDFs
    print(f"▶ Building citations.json from PDFs in {papers_dir} ...")
    citations = await build_citations_json(
        client=client,
        model=model,
        papers_dir=papers_dir,
        out_path=citations_json,
        max_pages=2,
    )
    print(f"✅ Wrote: {citations_json} ({len(citations)} entries)")

    prog(15)

    # 2) Read notes CSV (all_quotes_with_ideas.csv)
    rows = read_quotes_with_ideas(notes_csv)
    if not rows:
        raise SystemExit("Your notes_csv has no valid rows.")

    # Notes text = compact "idea bank"
    notes_lines = []
    for r in rows[:250]:
        idea = r.get("idea", "").strip()
        if idea:
            notes_lines.append(f"- {idea}")
    notes_text = "\n".join(notes_lines) if notes_lines else "No ideas column found; will rely more on quotes."

    evidence = build_evidence(rows, citations, max_items=100)
    evidence_pack = evidence_pack_text(evidence, max_items=80)
    refs = references_text(evidence)

    prog(25)

    # 3) Outline first
    print("▶ Drafting outline ...")
    outline_raw = await chat(
        client=client,
        model=model,
        system=OUTLINE_SYSTEM,
        user=outline_prompt(topic, rq, notes_text, evidence_pack),
    )
    outline = safe_json_loads(outline_raw)
    if not isinstance(outline, dict):
        outline_raw2 = await chat(
            client=client,
            model=model,
            system=OUTLINE_SYSTEM,
            user="Return ONLY valid JSON.\n\n" + outline_prompt(topic, rq, notes_text, evidence_pack),
        )
        outline = safe_json_loads(outline_raw2)
    if not isinstance(outline, dict):
        raise SystemExit("Failed to parse outline JSON. Try reducing notes/evidence size.")

    prog(35)

    # 4) Expand into a paper (section-by-section)
    header = {
        "title": title,
        "author": author,
        "institution": institution,
        "course": course,
        "instructor": instructor,
        "date": date,
    }

    print("▶ Expanding outline into full draft (section-by-section) ...")

    sections = outline_sections(outline)

    paper_parts: List[str] = []

    # Title/header block so PDF looks good
    paper_parts.append(
        f"# {header['title']}\n\n"
        f"{header['author']}\n"
        f"{header['institution']}\n"
        f"{header['course']}\n"
        f"{header['instructor']}\n"
        f"{header['date']}\n"
    )

    already = "\n\n".join(paper_parts)

    for idx, sec in enumerate(sections, 1):
        # spread progress across sections
        # (35 -> 70 range)
        if sections:
            prog(35 + int((idx - 1) * 35 / max(1, len(sections))))

        sec_text = await chat(
            client=client,
            model=model,
            system=SECTION_SYSTEM,
            user=section_expand_prompt(
                header=header,
                topic=topic,
                rq=rq,
                outline_json=outline,
                section_obj=sec,
                evidence_pack=evidence_pack,
                references=refs,
                already_written=already,
            ),
            timeout_s=240.0,
            max_retries=6,
        )
        sec_text = sec_text.strip()
        paper_parts.append(sec_text)
        already = "\n\n".join(paper_parts)

    # Ensure References present.
    if "## References" not in already and "\nReferences\n" not in already:
        paper_parts.append("## References\n\n" + refs)

    draft = "\n\n".join(paper_parts)

    prog(70)

    # 5) Grade/revise loop
    best = draft
    best_score = -1
    last_grade: Optional[Dict[str, Any]] = None

    for it in range(max_iters):
        prog(70 + int(it * 20 / max(1, max_iters)))

        grade_raw = await chat(
            client=client,
            model=model,
            system=GRADER_SYSTEM,
            user=grade_prompt(draft, rq, min_words, max_words),
        )
        grade = safe_json_loads(grade_raw)
        if not isinstance(grade, dict):
            grade_raw2 = await chat(
                client=client,
                model=model,
                system=GRADER_SYSTEM,
                user="Return ONLY valid JSON.\n\n" + grade_prompt(draft, rq, min_words, max_words),
            )
            grade = safe_json_loads(grade_raw2)

        if not isinstance(grade, dict):
            last_grade = {
                "satisfactory": False,
                "score": 0,
                "major_issues": ["Could not parse grader JSON."],
                "minor_issues": [],
                "revision_plan": [],
            }
            break

        last_grade = grade
        score = int(grade.get("score", 0)) if str(grade.get("score", "")).isdigit() else 0
        if score > best_score:
            best_score = score
            best = draft

        if bool(grade.get("satisfactory")):
            best = draft
            break

        print("▶ Revising draft ...")
        draft = await chat(
            client=client,
            model=model,
            system=EXPAND_SYSTEM,
            user=revise_prompt(draft, grade, notes_text, evidence_pack, refs),
        )

    prog(92)

    # 6) Write outputs
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(best.strip() + "\n")

    markdown_to_pdf(best, out_pdf)

    print(f"✅ Wrote: {out_md}")
    print(f"✅ Wrote: {out_pdf}")
    if last_grade:
        print("Final grade snapshot:", json.dumps(last_grade, ensure_ascii=False))

    prog(100)

    return {"out_md": out_md, "out_pdf": out_pdf, "citations_json": citations_json}


# ----------------------------
# Main pipeline (CLI)
# ----------------------------
async def main_async():
    parser = argparse.ArgumentParser(description="PDF->citations.json->outline->paper->PDF (Claude Opus 4.6).")
    parser.add_argument("--papers_dir", default="./papers", help="Folder containing PDFs.")
    parser.add_argument("--notes_csv", default="./all_quotes_with_ideas.csv", help="Your notes sheet CSV.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--rq", required=True)

    parser.add_argument("--model", default=DEFAULT_MODEL, help="Dedalus model string.")
    parser.add_argument("--citations_json", default="./citations.json", help="Generated citations mapping file.")

    # APA-ish header block fields
    parser.add_argument("--title", default="Research Paper")
    parser.add_argument("--author", default="Your Name")
    parser.add_argument("--institution", default="Your Institution")
    parser.add_argument("--course", default="Course")
    parser.add_argument("--instructor", default="Instructor")
    parser.add_argument("--date", default="Date")

    parser.add_argument("--min_words", type=int, default=1400)
    parser.add_argument("--max_words", type=int, default=2400)
    parser.add_argument("--max_iters", type=int, default=4)

    parser.add_argument("--out_md", default="./paper.md")
    parser.add_argument("--out_pdf", default="./paper.pdf")
    args = parser.parse_args()

    await generate(
        papers_dir=args.papers_dir,
        notes_csv=args.notes_csv,
        topic=args.topic,
        rq=args.rq,
        out_md=args.out_md,
        out_pdf=args.out_pdf,
        model=args.model,
        citations_json=args.citations_json,
        title=args.title,
        author=args.author,
        institution=args.institution,
        course=args.course,
        instructor=args.instructor,
        date=args.date,
        min_words=args.min_words,
        max_words=args.max_words,
        max_iters=args.max_iters,
    )


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
