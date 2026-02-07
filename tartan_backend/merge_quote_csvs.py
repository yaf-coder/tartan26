import argparse
import csv
import os
from typing import List, Dict


def normalize(s: str) -> str:
    return " ".join((s or "").split())


def merge_csvs(
    *,
    csv_dir: str = "./csvs",
    output_csv: str = "./all_quotes.csv",
    no_dedupe: bool = False,
) -> str:
    """
    Merge quote CSVs in *csv_dir* into a single CSV at *output_csv*.

    Expected input schema per row:
      - quote
      - page_number
      - filename

    If no_dedupe=False (default), identical quotes (normalized, case-insensitive)
    are deduplicated across all inputs.

    Returns the output CSV path.
    """
    dedupe = not no_dedupe

    if not os.path.isdir(csv_dir):
        raise SystemExit(f"CSV folder not found: {csv_dir}")

    csv_files = [
        os.path.join(csv_dir, f)
        for f in os.listdir(csv_dir)
        if f.lower().endswith(".csv")
    ]
    if not csv_files:
        raise SystemExit(f"No CSV files found in: {csv_dir}")

    all_rows: List[Dict[str, str]] = []
    seen_quotes = set()

    for path in sorted(csv_files):
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            required = {"quote", "page_number", "filename"}
            if not required.issubset(reader.fieldnames or []):
                print(f"Skipping {os.path.basename(path)} (invalid schema)")
                continue

            for row in reader:
                quote = row.get("quote", "")
                page = row.get("page_number", "")
                fname = row.get("filename", "")

                if not quote or not page or not fname:
                    continue

                if dedupe:
                    key = normalize(quote).lower()
                    if key in seen_quotes:
                        continue
                    seen_quotes.add(key)

                all_rows.append({"quote": quote, "page_number": page, "filename": fname})

    # Ensure output directory exists if a directory component was provided
    out_dir = os.path.dirname(os.path.abspath(output_csv))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["quote", "page_number", "filename"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Merged {len(csv_files)} CSVs → {output_csv} ({len(all_rows)} total quotes)")
    return output_csv


def main():
    parser = argparse.ArgumentParser(description="Merge quote CSVs into one big CSV.")
    parser.add_argument("--csv_dir", default="./csvs", help="Folder containing cleaned CSVs.")
    parser.add_argument("--output_csv", default="./all_quotes.csv", help="Output merged CSV path.")
    parser.add_argument("--no-dedupe", action="store_true", help="Do not deduplicate identical quotes.")
    args = parser.parse_args()

    merge_csvs(csv_dir=args.csv_dir, output_csv=args.output_csv, no_dedupe=args.no_dedupe)


if __name__ == "__main__":
    main()
