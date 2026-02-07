# tartan_backend/core/quotes_pipeline.py
import os
from typing import Callable, Dict, Optional

from tartan_backend import (
    seek_bot,
    research_bot,
    clean_quotes_in_place,
    merge_quote_csvs,
    synthesize_ideas,
)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _clear_pdfs(papers_dir: str) -> int:
    """
    Remove existing PDFs so runs don't mix. Returns count removed.
    """
    if not os.path.isdir(papers_dir):
        return 0
    removed = 0
    for f in os.listdir(papers_dir):
        if f.lower().endswith(".pdf"):
            try:
                os.remove(os.path.join(papers_dir, f))
                removed += 1
            except Exception:
                pass
    return removed


async def run_quotes_pipeline(
    *,
    rq: str,
    papers_dir: str,
    csv_dir: str,
    depth: int = 2,
    with_ideas: bool = True,
    ideas_model: str = "openai/gpt-4o-mini",
    no_dedupe: bool = False,
    clear_existing_pdfs: bool = True,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> Dict[str, str]:
    """
    End-to-end "find papers -> extract quotes -> clean -> merge -> (optional) synthesize ideas".

    React/Frontend provides ONLY rq; seek_bot downloads PDFs into papers_dir first.

    Artifacts:
      - rq_quotes_csv: csv_dir/rq_quotes.csv
      - merged_csv: csv_dir/all_quotes.csv
      - final_csv: csv_dir/all_quotes_with_ideas.csv (or merged_csv if with_ideas=False)
    """
    _ensure_dir(papers_dir)
    _ensure_dir(csv_dir)

    def prog(p: int):
        if callable(progress_cb):
            try:
                progress_cb(int(p))
            except Exception:
                pass

    prog(1)

    if clear_existing_pdfs:
        _clear_pdfs(papers_dir)

    # 1) Seek papers (downloads PDFs into papers_dir)
    prog(5)
    await seek_bot.run_seek(prompt_text=rq, depth=depth, papers_dir=papers_dir, print_tools=False)

    # 2) Extract verified quotes from PDFs -> rq_quotes.csv
    prog(30)
    rq_quotes_csv = await research_bot.run_extract(
        papers_dir=papers_dir,
        csv_dir=csv_dir,
        rq=rq,
        output_name="rq_quotes.csv",
    )

    # 3) Clean quotes in place (verifies against PDFs, makes backups)
    prog(55)
    clean_quotes_in_place.clean_csv_in_place(rq_quotes_csv, papers_dir)

    # 4) Merge all CSVs in csv_dir -> all_quotes.csv
    prog(70)
    merged_csv = os.path.join(csv_dir, "all_quotes.csv")
    merge_quote_csvs.merge_csvs(csv_dir=csv_dir, output_csv=merged_csv, no_dedupe=no_dedupe)

    # 5) Optional: add ideas -> all_quotes_with_ideas.csv
    final_csv = merged_csv
    if with_ideas:
        prog(85)
        final_csv = os.path.join(csv_dir, "all_quotes_with_ideas.csv")
        await synthesize_ideas.add_ideas_to_csv(
            input_csv=merged_csv,
            output_csv=final_csv,
            model=ideas_model,
            rq=rq,
            in_place=False,
        )

    prog(100)
    return {
        "papers_dir": papers_dir,
        "rq_quotes_csv": rq_quotes_csv,
        "merged_csv": merged_csv,
        "final_csv": final_csv,
    }
