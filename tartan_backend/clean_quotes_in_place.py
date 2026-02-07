import argparse
import csv
import os
import re
from typing import Optional

from pypdf import PdfReader

import shutil

def backup_csv(csv_path: str):
    """
    Create a one-time backup of the CSV before destructive cleaning.
    Backup name: originalname_raw.csv
    """
    base, ext = os.path.splitext(csv_path)
    backup_path = f"{base}_raw{ext}"

    if not os.path.exists(backup_path):
        shutil.copy2(csv_path, backup_path)
        print(f"Backup created: {os.path.basename(backup_path)}")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def resolve_pdf_path(pdf_folder: str, filename: str) -> Optional[str]:
    if not filename:
        return None

    direct = os.path.join(pdf_folder, filename)
    if os.path.isfile(direct):
        return direct

    target = filename.lower()
    for f in os.listdir(pdf_folder):
        if f.lower() == target:
            return os.path.join(pdf_folder, f)

    return None


def read_page_text(pdf_path: str, page_number_1indexed: int) -> str:
    reader = PdfReader(pdf_path)
    idx = page_number_1indexed - 1
    if idx < 0 or idx >= len(reader.pages):
        return ""
    try:
        return reader.pages[idx].extract_text() or ""
    except Exception:
        return ""


def quote_exists_on_page(quote: str, page_text: str) -> bool:
    q = norm(quote)
    p = norm(page_text)

    if not q or not p:
        return False

    if q in p:
        return True

    # relaxed prefix match for extraction artifacts
    if len(q) >= 60:
        prefix = q[:120]
        if prefix in p:
            return True

    return False


def clean_csv_in_place(csv_path: str, pdf_folder: str):
    backup_csv(csv_path)
    
    kept_rows = []
    total = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1

            quote = row.get("quote", "")
            filename = row.get("filename", "")
            page_str = (row.get("page_number", "") or "").strip()

            try:
                page_num = int(page_str)
            except Exception:
                continue  # drop row

            pdf_path = resolve_pdf_path(pdf_folder, filename)
            if pdf_path is None:
                continue  # drop row

            page_text = read_page_text(pdf_path, page_num)
            if quote_exists_on_page(quote, page_text):
                kept_rows.append(
                    {
                        "quote": quote,
                        "page_number": page_num,
                        "filename": filename,
                    }
                )

    # Overwrite original CSV (destructive)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["quote", "page_number", "filename"])
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"{os.path.basename(csv_path)} | kept {len(kept_rows)}/{total} rows")


def main():
    parser = argparse.ArgumentParser(description="Clean quote CSVs in place by verifying quotes in PDFs.")
    parser.add_argument("--csv_dir", default="./csvs", help="Folder containing quote CSVs.")
    parser.add_argument("--papers_dir", default="./papers", help="Folder containing PDFs referenced by filename.")
    args = parser.parse_args()

    csv_folder = args.csv_dir
    pdf_folder = args.papers_dir

    if not os.path.isdir(csv_folder):
        raise SystemExit(f"CSV folder not found: {csv_folder}")
    if not os.path.isdir(pdf_folder):
        raise SystemExit(f"PDF folder not found: {pdf_folder}")

    csv_files = [
        os.path.join(csv_folder, f)
        for f in os.listdir(csv_folder)
        if f.lower().endswith(".csv")
    ]
    if not csv_files:
        raise SystemExit(f"No CSV files found in: {csv_folder}")

    for csv_path in sorted(csv_files):
        clean_csv_in_place(csv_path, pdf_folder)


if __name__ == "__main__":
    main()
