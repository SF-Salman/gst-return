"""
Purchase Register extractor.

Accepts an Excel or CSV file uploaded by the user and normalizes it
into a list of InvoiceRecord dicts — the same shape used by gstr2a.py
and the reconciliation engine.

Column detection strategy (Option A — keyword matching):
  We scan the first 10 rows for headers that contain known keywords.
  This handles most Tally / ERP exports without requiring a fixed template.

Expected columns (flexible naming):
  GSTIN       → "gstin", "supplier gstin", "party gstin", "vendor gstin"
  Invoice No  → "invoice", "inv no", "bill no", "voucher"
  Date        → "date", "invoice date", "bill date"
  Taxable     → "taxable", "taxable value", "taxable amount", "assessable"
  CGST        → "cgst"
  SGST        → "sgst"
  IGST        → "igst"
"""

import io
import re
import logging
from datetime import datetime

import pandas as pd

from backend.core.models import InvoiceRecord
from backend.utils import safe_float

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword maps — lowercase keywords that identify each logical column
# ---------------------------------------------------------------------------
COLUMN_KEYWORDS: dict[str, list[str]] = {
    "gstin":         ["gstin", "gst no", "gst number", "supplier gstin",
                      "party gstin", "vendor gstin", "supplier gst"],
    "invoice_no":    ["invoice no", "invoice number", "inv no", "inv number",
                      "bill no", "bill number", "voucher no", "voucher number",
                      "document no", "doc no"],
    "invoice_date":  ["invoice date", "inv date", "bill date", "date",
                      "voucher date", "doc date", "transaction date"],
    "taxable_value": ["taxable value", "taxable amount", "taxable",
                      "assessable value", "assessable amount", "base amount",
                      "taxable val"],
    "cgst":          ["cgst", "cgst amount", "central gst", "cgst amt"],
    "sgst":          ["sgst", "sgst amount", "state gst", "sgst amt",
                      "utgst", "utgst amount"],
    "igst":          ["igst", "igst amount", "integrated gst", "igst amt"],
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_purchase_register(file_bytes: bytes, filename: str) -> list[InvoiceRecord]:
    """
    Parse an uploaded Excel (.xlsx / .xls) or CSV file and return a list
    of InvoiceRecord dicts ready for the reconciliation engine.

    Raises ValueError with a user-friendly message if the file cannot be
    parsed or required columns are missing.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext in ("xlsx", "xls"):
            df = _read_excel(file_bytes)
        elif ext == "csv":
            df = _read_csv(file_bytes)
        else:
            raise ValueError(
                f"Unsupported file type '.{ext}'. "
                "Please upload an Excel (.xlsx / .xls) or CSV file."
            )
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not read file: {e}") from e

    col_map = _detect_columns(df)
    _validate_required_columns(col_map)

    return _build_records(df, col_map)


# ---------------------------------------------------------------------------
# File readers
# ---------------------------------------------------------------------------

def _read_excel(file_bytes: bytes) -> pd.DataFrame:
    """Read Excel, auto-detecting the header row (first row with 4+ non-empty cells)."""
    buf = io.BytesIO(file_bytes)

    # Try to find the real header row (skip logo/title rows at top)
    for skip in range(10):
        try:
            df = pd.read_excel(buf, header=skip, dtype=str)
            buf.seek(0)
            non_empty = df.columns.notna().sum()
            if non_empty >= 4:
                return df.reset_index(drop=True)
        except Exception:
            buf.seek(0)
            continue

    # Fallback — just read from row 0
    buf.seek(0)
    return pd.read_excel(buf, dtype=str).reset_index(drop=True)


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    """Read CSV, trying common encodings."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            buf = io.StringIO(file_bytes.decode(encoding))
            return pd.read_csv(buf, dtype=str).reset_index(drop=True)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode CSV file. Try saving it as UTF-8.")


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def _detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Match each logical field to an actual DataFrame column name using
    keyword matching on lowercased column headers.

    Returns a dict like:
        { "gstin": "Supplier GSTIN", "invoice_no": "Invoice No", ... }
    Values are None if no match found.
    """
    actual_cols = list(df.columns)
    lower_cols = [str(c).lower().strip() for c in actual_cols]

    col_map: dict[str, str | None] = {}

    for field, keywords in COLUMN_KEYWORDS.items():
        matched_col = None
        for keyword in keywords:
            for i, lc in enumerate(lower_cols):
                if keyword in lc:
                    matched_col = actual_cols[i]
                    break
            if matched_col:
                break
        col_map[field] = matched_col

    logger.info("Column mapping detected: %s", col_map)
    return col_map


def _validate_required_columns(col_map: dict[str, str | None]) -> None:
    """Raise ValueError listing any required columns that could not be found."""
    required = ["gstin", "invoice_no", "taxable_value"]
    missing = [f for f in required if col_map.get(f) is None]
    if missing:
        raise ValueError(
            f"Could not find these required columns in your file: "
            f"{', '.join(missing)}. "
            "Please ensure the file has columns for GSTIN, Invoice Number, "
            "and Taxable Value. Column names can vary but must contain "
            "recognisable keywords."
        )


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def _build_records(df: pd.DataFrame, col_map: dict[str, str | None]) -> list[InvoiceRecord]:
    """Convert each DataFrame row into an InvoiceRecord."""
    records: list[InvoiceRecord] = []
    skipped = 0

    for idx, row in df.iterrows():
        gstin = _get_str(row, col_map["gstin"])
        invoice_no = _get_str(row, col_map["invoice_no"])

        # Skip rows that look like subtotals, blanks, or section headers
        if not gstin and not invoice_no:
            skipped += 1
            continue

        # Normalize GSTIN — strip spaces, uppercase
        gstin = re.sub(r"\s+", "", gstin).upper()

        invoice_date = _parse_date(_get_str(row, col_map.get("invoice_date")))
        taxable_value = safe_float(_get_val(row, col_map["taxable_value"]))
        cgst = safe_float(_get_val(row, col_map.get("cgst"))) if col_map.get("cgst") else 0.0
        sgst = safe_float(_get_val(row, col_map.get("sgst"))) if col_map.get("sgst") else 0.0
        igst = safe_float(_get_val(row, col_map.get("igst"))) if col_map.get("igst") else 0.0

        records.append(InvoiceRecord(
            gstin=gstin,
            invoice_no=invoice_no,
            invoice_date=invoice_date,
            taxable_value=taxable_value,
            cgst=cgst,
            sgst=sgst,
            igst=igst,
            source="PR"
        ))

    if skipped:
        logger.info("Skipped %d blank/subtotal rows", skipped)

    logger.info("Extracted %d purchase register records", len(records))
    return records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_str(row: pd.Series, col: str | None) -> str:
    if col is None:
        return ""
    val = row.get(col, "")
    return "" if pd.isna(val) else str(val).strip()


def _get_val(row: pd.Series, col: str | None):
    if col is None:
        return None
    val = row.get(col)
    return None if pd.isna(val) else val


def _parse_date(raw: str) -> str:
    """
    Try to parse common Indian date formats and return DD/MM/YYYY string.
    Returns the original string unchanged if parsing fails.
    """
    if not raw:
        return ""
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y",
        "%d %b %Y", "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return raw  # return as-is if nothing matched
