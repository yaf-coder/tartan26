import argparse
import csv
import os


def normalize(s: str) -> str:
    return " ".join((s or "").split())


def main():
    parser = argparse.ArgumentParser(description="Merge quote CSVs into one big CSV.")
    parser.add_argument("--csv_dir", default="./csvs", help="Folder containing cleaned CSVs.")
    parser.add_argument("--output_csv", default="./all_quotes.csv", help="Output merged CSV path.")
    parser.add_argument("--no-dedupe", action="store_true", help="Do not deduplicate identical quotes.")
    args = parser.parse_args()

    csv_folder = args.csv_dir
    output_csv = args.output_csv
    dedupe = not args.no_dedupe

    if not os.path.isdir(csv_folder):
        raise SystemExit(f"CSV folder not found: {csv_folder}")

    csv_files = [
        os.path.join(csv_folder, f)
        for f in os.listdir(csv_folder)
        if f.lower().endswith(".csv")
    ]
    if not csv_files:
        raise SystemExit(f"No CSV files found in: {csv_folder}")

    all_rows = []
    seen_quotes = set()

    for path in sorted(csv_files):
        print(f"[LOG] Merging quotes from {os.path.basename(path)}...", flush=True)
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

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["quote", "page_number", "filename"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Merged {len(csv_files)} CSVs → {output_csv} ({len(all_rows)} total quotes)")


if __name__ == "__main__":
    main()
