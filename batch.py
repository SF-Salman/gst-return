"""
batch.py — drop-in replacement for the separate process_directory() calls
          in gstr1.py and gstr3b.py.

Usage:
    python batch.py -i ./pdfs/ -o output.xlsx

Drops mixed GSTR-1, GSTR-3B (and eventually GSTR-2B) PDFs into one folder;
auto-detects each one and writes a single Excel with one sheet per form type.
"""

import os
import sys
import argparse
import pandas as pd
from parser import parse_gst_return

# Sheet name mapping — add 'GSTR2B' here when ready
SHEET_NAMES = {
    "GSTR1":  "GSTR-1",
    "GSTR3B": "GSTR-3B",
    "GSTR2B": "GSTR-2B",   # slot reserved
    "UNKNOWN": "Errors",
}


def process_folder(folder_path: str, output_excel: str):
    buckets = {k: [] for k in SHEET_NAMES}

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return

    print(f"Found {len(pdf_files)} PDF file(s)\n")

    for fname in sorted(pdf_files):
        fpath = os.path.join(folder_path, fname)
        print(f"  Processing: {fname}")
        try:
            data = parse_gst_return(fpath)
            form_type = data.get("form_type", "UNKNOWN")
            bucket_key = form_type if form_type in buckets else "UNKNOWN"
            buckets[bucket_key].append(data)
            print(f"    → detected as {form_type}")
        except Exception as exc:
            print(f"    → ERROR: {exc}")
            buckets["UNKNOWN"].append({
                "source_file": fname,
                "_error": str(exc),
                "form_type": "UNKNOWN",
            })

    # Write Excel — one sheet per form type that has rows
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        wrote_any = False
        for key, sheet_name in SHEET_NAMES.items():
            rows = buckets[key]
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"\n  Sheet '{sheet_name}': {len(rows)} row(s)")
            wrote_any = True

    if wrote_any:
        print(f"\nOutput saved → {output_excel}")
    else:
        print("Nothing to write.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Process a folder of mixed GST PDFs")
    ap.add_argument("--input",  "-i", required=True, help="Folder containing PDF files")
    ap.add_argument("--output", "-o", required=True, help="Output Excel path (.xlsx)")
    args = ap.parse_args()

    if not os.path.isdir(args.input):
        print(f"Error: '{args.input}' is not a directory")
        sys.exit(1)

    process_folder(args.input, args.output)