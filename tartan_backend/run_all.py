import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd=HERE):
    print("\n▶ Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Run research pipeline end-to-end.")
    parser.add_argument("--papers_dir", default=os.path.join(HERE, "papers"),
                        help="Folder containing PDF research papers (default: ./papers)")
    parser.add_argument("--csv_dir", default=os.path.join(HERE, "csvs"),
                        help="Folder where CSVs are written/cleaned/merged (default: ./csvs)")
    parser.add_argument("--output_csv", default=os.path.join(HERE, "all_quotes.csv"),
                        help="Merged output CSV path (default: ./all_quotes.csv)")
    parser.add_argument("--rq", required=True,
                        help="Research question (string) used for quote extraction.")
    parser.add_argument("--skip_tester", action="store_true",
                        help="Skip running tester.py (default runs it last if present).")

    args = parser.parse_args()

    # ensure directories exist
    os.makedirs(args.csv_dir, exist_ok=True)
    if not os.path.isdir(args.papers_dir):
        raise SystemExit(f"papers_dir not found: {args.papers_dir}")

    python = sys.executable

    # 1) generate quotes CSVs from PDFs
    run([python, "research_bot.py",
         "--papers_dir", args.papers_dir,
         "--csv_dir", args.csv_dir,
         "--rq", args.rq])

    # 2) clean CSVs in place (drops unverifiable rows)
    run([python, "clean_quotes_in_place.py",
         "--papers_dir", args.papers_dir,
         "--csv_dir", args.csv_dir])

    # 3) merge into one CSV
    run([python, "merge_quote_csvs.py",
         "--csv_dir", args.csv_dir,
         "--output_csv", args.output_csv])

    # 4) optionally run tester.py if you want
    if not args.skip_tester and os.path.isfile(os.path.join(HERE, "tester.py")):
        run([python, "tester.py"])

    print("\n✅ Pipeline complete.")
    print("Merged CSV:", args.output_csv)

if __name__ == "__main__":
    main()
