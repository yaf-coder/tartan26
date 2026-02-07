import os
import re
import csv
from typing import Optional

from pypdf import PdfReader


# ----------------------------
# EDIT THESE
# ----------------------------
CSV_FOLDER = "./csvs"
PDF_FOLDER = "./pdfs"


# ----------------------------
# Helpers
# ----------------------------
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

    # strict normalized match
    if q in p:
        return True

    # relaxed prefix match for PDF extraction artifacts
    if len(q) >= 60:
        prefix = q[:120]
        if prefix in p:
            return True

    return False


# ----------------------------
# Core logic
# ----------------------------
def clean_csv_in_place(csv_path: str, pdf_folder: str):
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
                kept_rows.append({
                    "quote": quote,
                    "page_number": page_num,
                    "filename": filename
                })

    # Overwrite original CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["quote", "page_number", "filename"]
        )
        writer.writeheader()
        writer.writerows(kept_rows)

    print(
        f"{os.path.basename(csv_path)} | "
        f"kept {len(kept_rows)}/{total} rows"
    )


def main():
    if not os.path.isdir(CSV_FOLDER):
        raise SystemExit(f"CSV folder not found: {CSV_FOLDER}")
    if not os.path.isdir(PDF_FOLDER):
        raise SystemExit(f"PDF folder not found: {PDF_FOLDER}")

    csv_files = [
        os.path.join(CSV_FOLDER, f)
        for f in os.listdir(CSV_FOLDER)
        if f.lower().endswith(".csv")
    ]

    if not csv_files:
        raise SystemExit(f"No CSV files found in: {CSV_FOLDER}")

    for csv_path in sorted(csv_files):
        clean_csv_in_place(csv_path, PDF_FOLDER)


if __name__ == "__main__":
    main()
