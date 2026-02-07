# tartan_backend/core/paper_pipeline.py
import os
from typing import Callable, Dict, Optional

from tartan_backend import full_paper_pipeline


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


async def run_paper_pipeline(
    *,
    rq: str,
    topic: str,
    papers_dir: str,
    notes_csv: str,
    out_dir: str,
    model: str = full_paper_pipeline.DEFAULT_MODEL,
    # header defaults (override from frontend if desired)
    title: str = "Research Paper",
    author: str = "Your Name",
    institution: str = "Your Institution",
    course: str = "Course",
    instructor: str = "Instructor",
    date: str = "Date",
    # constraints
    min_words: int = 1400,
    max_words: int = 2400,
    max_iters: int = 4,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> Dict[str, str]:
    """
    Generate a paper (.md + .pdf) from PDFs + notes CSV.

    Expects:
      - papers_dir contains PDFs (downloaded by seek_bot)
      - notes_csv points to a CSV (usually all_quotes_with_ideas.csv)

    Writes outputs into out_dir:
      - paper.md
      - paper.pdf
      - citations.json
    """
    _ensure_dir(out_dir)

    out_md = os.path.join(out_dir, "paper.md")
    out_pdf = os.path.join(out_dir, "paper.pdf")
    citations_json = os.path.join(out_dir, "citations.json")

    def prog(p: int):
        if callable(progress_cb):
            try:
                progress_cb(int(p))
            except Exception:
                pass

    prog(1)

    artifacts = await full_paper_pipeline.generate(
        papers_dir=papers_dir,
        notes_csv=notes_csv,
        topic=topic,
        rq=rq,
        out_md=out_md,
        out_pdf=out_pdf,
        model=model,
        citations_json=citations_json,
        title=title,
        author=author,
        institution=institution,
        course=course,
        instructor=instructor,
        date=date,
        min_words=min_words,
        max_words=max_words,
        max_iters=max_iters,
        progress_cb=prog,
    )

    prog(100)

    # full_paper_pipeline.generate already returns the paths; keep our canonical ones too.
    return {
        "out_dir": out_dir,
        "paper_md": artifacts.get("out_md", out_md),
        "paper_pdf": artifacts.get("out_pdf", out_pdf),
        "citations_json": artifacts.get("citations_json", citations_json),
    }
