"""
=============================================================================
RUN ALL — Full research quote pipeline (extract → clean → merge → ideas)
=============================================================================

Orchestrates the full sequence of scripts used by the Veritas API and CLI to
turn a folder of PDFs and a research question into a single merged CSV of
verified quotes, optionally with an "idea" column synthesized per quote.

Steps (in order)
----------------
1. research_bot.py   : Extract quotes from each PDF (LLM + verification).
2. clean_quotes_in_place.py : Verify each quote against PDF text; drop invalid rows.
3. merge_quote_csvs.py     : Merge all CSVs into one (with optional dedupe).
4. synthesize_ideas.py     : (if --with_ideas) Add "idea" column via LLM.

Usage
-----
  python run_all.py --papers_dir ./papers --csv_dir ./csvs --output_csv ./all_quotes.csv --rq "Your question" [--with_ideas]

Output
------
- output_csv (e.g. all_quotes.csv); if --with_ideas, also <stem>_with_ideas.csv.
"""

import argparse
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    """Run a command in this project directory. Raises on non-zero exit."""
    print("\n▶", " ".join(cmd))
    subprocess.run(cmd, cwd=HERE, check=True)


def main():
    parser = argparse.ArgumentParser(description="Run the full research quote pipeline.")
    parser.add_argument(
        "--papers_dir",
        default=os.path.join(HERE, "papers"),
        help="Folder with PDF research papers (default: ./papers)",
    )
    parser.add_argument(
        "--csv_dir",
        default=os.path.join(HERE, "csvs"),
        help="Folder for intermediate CSVs (default: ./csvs)",
    )
    parser.add_argument(
        "--output_csv",
        default=os.path.join(HERE, "all_quotes.csv"),
        help="Merged output CSV path (default: ./all_quotes.csv)",
    )
    parser.add_argument(
        "--rq",
        required=True,
        help="Research question (string) used for quote extraction.",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not deduplicate quotes when merging.",
    )
    parser.add_argument(
        "--with_ideas",
        action="store_true",
        help="After merging, add an 'idea' column using the AI agent.",
    )
    parser.add_argument(
        "--ideas_model",
        default="openai/gpt-4o-mini",
        help="Model to use for idea synthesis (default: openai/gpt-4o-mini).",
    )


    args = parser.parse_args()

    if not os.path.isdir(args.papers_dir):
        raise SystemExit(f"papers_dir not found: {args.papers_dir}")

    os.makedirs(args.csv_dir, exist_ok=True)

    py = sys.executable

    # 1) Extract quotes -> writes csv_dir/rq_quotes.csv by default
    run(
        [
            py,
            "research_bot.py",
            "--papers_dir",
            args.papers_dir,
            "--csv_dir",
            args.csv_dir,
            "--rq",
            args.rq,
        ]
    )

    # 2) Clean CSVs in place (destructive)
    run(
        [
            py,
            "clean_quotes_in_place.py",
            "--papers_dir",
            args.papers_dir,
            "--csv_dir",
            args.csv_dir,
        ]
    )

    # 3) Merge CSVs
    merge_cmd = [
        py,
        "merge_quote_csvs.py",
        "--csv_dir",
        args.csv_dir,
        "--output_csv",
        args.output_csv,
    ]
    if args.no_dedupe:
        merge_cmd.append("--no-dedupe")
    run(merge_cmd)

        # 4) Optionally add synthesized ideas column
    if args.with_ideas:
        merged_with_ideas = os.path.splitext(args.output_csv)[0] + "_with_ideas.csv"
        run(
            [
                py,
                "synthesize_ideas.py",
                "--input_csv",
                args.output_csv,
                "--output_csv",
                merged_with_ideas,
                "--model",
                args.ideas_model,
                "--rq",
                args.rq,
            ]
        )
        print("Ideas CSV:", merged_with_ideas)


    print("\n✅ Done.")
    print("Merged CSV:", args.output_csv)


if __name__ == "__main__":
    main()
