import os
import csv

# ----------------------------
# EDIT THESE
# ----------------------------
CSV_FOLDER = "./csvs"
OUTPUT_CSV = "./all_quotes.csv"
DEDUPLICATE = True   # set False if you want raw concatenation


def normalize(s: str) -> str:
    return " ".join((s or "").split())


def main():
    if not os.path.isdir(CSV_FOLDER):
        raise SystemExit(f"CSV folder not found: {CSV_FOLDER}")

    csv_files = [
        os.path.join(CSV_FOLDER, f)
        for f in os.listdir(CSV_FOLDER)
        if f.lower().endswith(".csv")
    ]

    if not csv_files:
        raise SystemExit(f"No CSV files found in: {CSV_FOLDER}")

    all_rows = []
    seen_quotes = set()

    for path in sorted(csv_files):
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            # sanity check
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

                if DEDUPLICATE:
                    key = normalize(quote).lower()
                    if key in seen_quotes:
                        continue
                    seen_quotes.add(key)

                all_rows.append({
                    "quote": quote,
                    "page_number": page,
                    "filename": fname
                })

    # write merged CSV
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["quote", "page_number", "filename"]
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(
        f"Merged {len(csv_files)} CSVs → {OUTPUT_CSV} "
        f"({len(all_rows)} total quotes)"
    )


if __name__ == "__main__":
    main()
