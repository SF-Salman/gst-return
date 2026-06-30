import re
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Required template headers (exact case-insensitive match, trimmed) ───────

REQUIRED_HEADERS = {
    "month":         "month",
    "category":      "category",
    "taxable value": "taxable_value",
    "igst":          "igst",
    "cgst":          "cgst",
    "sgst":          "sgst",
    "cess":          "cess",
}

OPTIONAL_HEADERS = {
    "voucher date": "voucher_date",
    "voucher no":   "voucher_no",
    "ledger":       "ledger",
    "type":         "type",
    "remarks":      "remarks",
}

ALL_HEADERS = {**REQUIRED_HEADERS, **OPTIONAL_HEADERS}

VALID_CATEGORIES = {"OUTPUT", "ITC", "RCM", "REVERSAL", "EXEMPT"}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _norm_header(s: str) -> str:
    """Case-insensitive, whitespace-trimmed header normalization."""
    return re.sub(r"\s+", " ", str(s).strip().lower())

def _safe_float(v) -> float:
    try:
        if pd.isna(v):
            return 0.0
        return round(float(str(v).replace(",", "").strip()), 2)
    except Exception:
        return 0.0

def _parse_period(val) -> Optional[str]:
    """Convert a cell value to YYYY-MM string. Accepts Apr-25, April 2025, 04/2025, 2025-04, etc."""
    if pd.isna(val):
        return None
    s = str(val).strip()

    if re.match(r"^\d{4}-\d{2}$", s):
        return s

    MONTH_NUM = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    # "Apr-25", "Apr-2025", "April 2025", "April-25"
    m = re.match(r"^([A-Za-z]{3,9})[-\s](\d{2,4})$", s)
    if m:
        mon_key = m.group(1).lower()[:3]
        if mon_key in MONTH_NUM:
            year = m.group(2)
            year = "20" + year if len(year) == 2 else year
            return f"{year}-{MONTH_NUM[mon_key]:02d}"

    # "04/2025", "04-2025"
    m2 = re.match(r"^(\d{1,2})[/-](\d{4})$", s)
    if m2:
        return f"{m2.group(2)}-{int(m2.group(1)):02d}"

    # Last resort: pandas, but only if the above patterns didn't match
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime("%Y-%m")
    except Exception:
        pass

    return None

def _find_template_sheet(df_map: dict[str, "pd.DataFrame"]) -> Optional[tuple[str, "pd.DataFrame", dict[str, str]]]:
    """
    Scan all sheets for one whose header row matches all REQUIRED_HEADERS
    (case-insensitive, trimmed). Returns (sheet_name, df, column_map) or None.
    column_map maps normalized field name -> actual column name in df.
    """
    for sheet_name, df in df_map.items():
        if df.empty or len(df.columns) < len(REQUIRED_HEADERS):
            continue

        header_lookup = {_norm_header(c): c for c in df.columns}

        column_map: dict[str, str] = {}
        missing = []
        for header_key, field_name in ALL_HEADERS.items():
            actual_col = header_lookup.get(header_key)
            if actual_col is not None:
                column_map[field_name] = actual_col
            elif header_key in REQUIRED_HEADERS:
                missing.append(header_key)

        if not missing:
            return sheet_name, df, column_map

    return None

# ─── Main extractor ───────────────────────────────────────────────────────────

def extract_books(file_bytes: bytes, filename: str) -> dict:
    """
    Extract Books data using the strict template format.
    Scans all sheets in the workbook for one matching the required headers
    (case-insensitive, whitespace-trimmed). The sheet/file name itself does
    not matter — only the header row content.

    Returns:
    {
      "periods": { "YYYY-MM": { "sales", "taxable_value", "igst", "cgst", "sgst", "cess", "itc", "rcm" } },
      "audit": { "sheet_used": str, "rows_processed": int, "rows_skipped": int, "categories_seen": {...} }
    }

    Raises ValueError if no sheet matches the required template headers.
    """
    fname = filename.lower()

    if fname.endswith(".csv"):
        df_map = {"Sheet1": pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype=str)}
    else:
        xl = pd.ExcelFile(pd.io.common.BytesIO(file_bytes))
        df_map = {sheet: xl.parse(sheet, dtype=str) for sheet in xl.sheet_names}

    found = _find_template_sheet(df_map)
    if not found:
        required_list = ", ".join(sorted(REQUIRED_HEADERS.keys()))
        raise ValueError(
            f"Could not find required columns ({required_list}) in any sheet. "
            f"Please use the downloaded Books template format."
        )

    sheet_name, df, column_map = found

    periods: dict[str, dict] = {}
    categories_seen: dict[str, int] = {}
    rows_processed = 0
    rows_skipped = 0

    def _ensure_period(p: str):
        if p not in periods:
            periods[p] = {
                "sales": 0.0, "taxable_value": 0.0,
                "igst": 0.0, "cgst": 0.0, "sgst": 0.0,
                "cess": 0.0, "itc": 0.0, "rcm": 0.0,
                # Additive, tax-head-split ITC figures — used by GSTR-2B vs Books.
                # Existing 'itc' (combined) field above is untouched for backward
                # compatibility with GSTR-3B vs Books.
                "itc_igst": 0.0, "itc_cgst": 0.0, "itc_sgst": 0.0,
            }

    col_month    = column_map["month"]
    col_category = column_map["category"]
    col_taxable  = column_map["taxable_value"]
    col_igst     = column_map["igst"]
    col_cgst     = column_map["cgst"]
    col_sgst     = column_map["sgst"]
    col_cess     = column_map["cess"]

    for _, row in df.iterrows():
        period_key = _parse_period(row[col_month])
        category_raw = str(row[col_category]).strip().upper() if pd.notna(row[col_category]) else ""

        if not period_key or not category_raw:
            rows_skipped += 1
            continue

        if category_raw not in VALID_CATEGORIES:
            rows_skipped += 1
            continue

        _ensure_period(period_key)
        categories_seen[category_raw] = categories_seen.get(category_raw, 0) + 1

        taxable = _safe_float(row[col_taxable])
        igst    = _safe_float(row[col_igst])
        cgst    = _safe_float(row[col_cgst])
        sgst    = _safe_float(row[col_sgst])
        cess    = _safe_float(row[col_cess])

        if category_raw == "OUTPUT":
            periods[period_key]["sales"] += taxable
            periods[period_key]["taxable_value"] += taxable
            periods[period_key]["igst"] += igst
            periods[period_key]["cgst"] += cgst
            periods[period_key]["sgst"] += sgst
            periods[period_key]["cess"] += cess

        elif category_raw == "ITC":
            periods[period_key]["itc"] += igst + cgst + sgst + cess
            periods[period_key]["itc_igst"] += igst
            periods[period_key]["itc_cgst"] += cgst
            periods[period_key]["itc_sgst"] += sgst

        elif category_raw == "REVERSAL":
            periods[period_key]["itc"] -= (igst + cgst + sgst + cess)
            periods[period_key]["itc_igst"] -= igst
            periods[period_key]["itc_cgst"] -= cgst
            periods[period_key]["itc_sgst"] -= sgst

        elif category_raw == "RCM":
            periods[period_key]["rcm"] += igst + cgst + sgst + cess

        elif category_raw == "EXEMPT":
            # Tracked but not added to taxable/tax totals — informational only
            pass

        rows_processed += 1

    for p in periods:
        periods[p] = {k: round(v, 2) for k, v in periods[p].items()}

    audit = {
        "sheet_used": sheet_name,
        "rows_processed": rows_processed,
        "rows_skipped": rows_skipped,
        "categories_seen": categories_seen,
    }

    return {"periods": periods, "audit": audit}


# ─── Template generator ───────────────────────────────────────────────────────

def generate_books_template() -> bytes:
    """Generate the downloadable BOOKS_DATA template as xlsx bytes."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "BOOKS_DATA"

    headers = [
        "Month", "Voucher Date", "Voucher No", "Ledger", "Category",
        "Taxable Value", "IGST", "CGST", "SGST", "CESS", "Type", "Remarks",
    ]
    ws.append(headers)
    header_fill = PatternFill("solid", fgColor="2D3748")
    for ci in range(1, len(headers) + 1):
        c = ws.cell(1, ci)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")

    sample_rows = [
        ["Apr-25", "01-Apr-2025", "INV001", "Sales",        "OUTPUT", 100000, 18000, 0,    0,    0, "B2B",    "Domestic"],
        ["Apr-25", "05-Apr-2025", "INV002", "Export Sales", "OUTPUT", 50000,  0,     0,    0,    0, "EXPORT", "Zero Rated"],
        ["Apr-25", "08-Apr-2025", "JV001",  "IGST Input",   "ITC",    30000,  5400,  0,    0,    0, "ITC",    "Eligible"],
        ["Apr-25", "10-Apr-2025", "JV002",  "RCM Payable",  "RCM",    20000,  3600,  0,    0,    0, "RCM",    "Reverse Charge"],
    ]
    for row in sample_rows:
        ws.append(row)

    widths = [10, 14, 12, 16, 12, 14, 10, 10, 10, 10, 10, 18]
    for ci, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, ci).column_letter].width = w

    readme = wb.create_sheet("README")
    readme.append(["Books Template — Instructions"])
    readme["A1"].font = Font(bold=True, size=13)
    readme.append([])
    readme.append(["Category values (must match exactly, case-insensitive):"])
    readme.cell(readme.max_row, 1).font = Font(bold=True)
    for cat in ["OUTPUT", "ITC", "RCM", "REVERSAL", "EXEMPT"]:
        readme.append(["", cat])
    readme.append([])
    readme.append(["Type examples:"])
    readme.cell(readme.max_row, 1).font = Font(bold=True)
    for t in ["B2B", "B2C", "EXPORT", "SEZ", "ITC", "RCM"]:
        readme.append(["", t])
    readme.append([])
    readme.append(["Notes:"])
    readme.cell(readme.max_row, 1).font = Font(bold=True)
    readme.append(["", "Required columns: Month, Category, Taxable Value, IGST, CGST, SGST, CESS"])
    readme.append(["", "Month formats accepted: Apr-25, April 2025, 04/2025, 2025-04"])
    readme.append(["", "Sheet name does not matter — only the header row is checked"])
    readme.column_dimensions["A"].width = 4
    readme.column_dimensions["B"].width = 60

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()