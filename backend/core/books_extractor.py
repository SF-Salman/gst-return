# import re
# import logging
# from typing import Optional
# import pandas as pd

# logger = logging.getLogger(__name__)

# # ─── Sheet classification patterns ───────────────────────────────────────────

# SHEET_PATTERNS: dict[str, list[str]] = {
#     "sales":     ["sales", "revenue", "outward", "output", "gstr1", "gstr-1"],
#     "igst":      ["igst", "input igst", "igst input", "integrated"],
#     "cgst":      ["cgst", "input cgst", "cgst input", "central"],
#     "sgst":      ["sgst", "input sgst", "sgst input", "state"],
#     "itc":       ["itc", "input tax credit", "eligible itc", "itc avail"],
#     "rcm":       ["rcm", "reverse charge", "reverse chg"],
#     "purchase":  ["purchase", "inward", "pr", "purch reg"],
#     "summary":   ["summary", "summery", "total", "consolidated"],
# }

# # ─── Column aliases ───────────────────────────────────────────────────────────

# COLUMN_ALIASES: dict[str, list[str]] = {
#     "period":        ["month", "period", "date", "tax period", "mon", "yr", "year month"],
#     "taxable_value": ["taxable", "taxable value", "taxable amount", "value", "amount", "base amount"],
#     "igst":          ["igst", "input igst", "igst amount", "integrated tax", "i.g.s.t"],
#     "cgst":          ["cgst", "input cgst", "cgst amount", "central tax", "c.g.s.t"],
#     "sgst":          ["sgst", "input sgst", "sgst amount", "state tax", "s.g.s.t", "utgst"],
#     "cess":          ["cess", "cess amount"],
#     "itc":           ["itc", "input tax credit", "eligible itc", "itc credit", "credit"],
#     "rcm":           ["rcm", "reverse charge", "rcm amount"],
#     "classification":["classification", "type", "category", "class", "nature"],
#     "credit_debit":  ["cr", "dr", "credit", "debit", "cr/dr"],
#     "sales":         ["sales", "revenue", "turnover", "supply value"],
# }

# ITC_INCLUDE_KEYWORDS = {"itc", "input", "eligible itc", "eligible", "credit", "cr"}

# # ─── Helpers ──────────────────────────────────────────────────────────────────

# def _norm(s: str) -> str:
#     return re.sub(r"\s+", " ", str(s).lower().strip())

# def _safe_float(v) -> float:
#     try:
#         if pd.isna(v):
#             return 0.0
#         return round(float(str(v).replace(",", "").strip()), 2)
#     except Exception:
#         return 0.0

# def _classify_sheet(name: str, df: pd.DataFrame) -> Optional[str]:
#     """Return best matching sheet type or None."""
#     norm_name = _norm(name)
#     for sheet_type, patterns in SHEET_PATTERNS.items():
#         if any(p in norm_name for p in patterns):
#             return sheet_type

#     # Inspect headers
#     headers = [_norm(c) for c in df.columns if c]
#     header_str = " ".join(headers)
#     for sheet_type, patterns in SHEET_PATTERNS.items():
#         if any(p in header_str for p in patterns):
#             return sheet_type

#     return None

# def _detect_column(df: pd.DataFrame, field: str) -> Optional[str]:
#     """Find the first column matching any alias for `field`."""
#     aliases = COLUMN_ALIASES.get(field, [])
#     for col in df.columns:
#         norm_col = _norm(col)
#         if any(a == norm_col or a in norm_col for a in aliases):
#             return col
#     return None

# def _parse_period(val) -> Optional[str]:
#     """Convert a cell value to YYYY-MM string."""
#     if pd.isna(val):
#         return None
#     s = str(val).strip()
#     # Already YYYY-MM
#     if re.match(r"^\d{4}-\d{2}$", s):
#         return s
#     # Try pandas
#     try:
#         dt = pd.to_datetime(s, dayfirst=True)
#         return dt.strftime("%Y-%m")
#     except Exception:
#         pass
#     # Month name patterns: "Mar 2026", "March 2026", "03/2026"
#     m = re.match(r"([A-Za-z]+)[- /](\d{4})", s)
#     if m:
#         try:
#             dt = pd.to_datetime(f"01 {m.group(1)} {m.group(2)}", dayfirst=True)
#             return dt.strftime("%Y-%m")
#         except Exception:
#             pass
#     m2 = re.match(r"(\d{1,2})[/-](\d{4})", s)
#     if m2:
#         return f"{m2.group(2)}-{int(m2.group(1)):02d}"
#     return None

# # ─── Main extractor ───────────────────────────────────────────────────────────

# def extract_books(file_bytes: bytes, filename: str) -> dict:
#     """
#     Extract and normalise books data from xlsx or csv.
#     Returns:
#     {
#       "gstin": str | None,
#       "periods": { "YYYY-MM": { "sales", "taxable_value", "igst", "cgst", "sgst", "cess", "itc", "rcm" } },
#       "audit": { "sheets_detected": [...], "columns_detected": {...}, "skipped_sheets": [...] }
#     }
#     """
#     fname = filename.lower()

#     # ── Load workbook / CSV ──────────────────────────────────────────────────
#     if fname.endswith(".csv"):
#         df_map = {"Sheet1": pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype=str)}
#     else:
#         xl = pd.ExcelFile(pd.io.common.BytesIO(file_bytes))
#         df_map = {
#             sheet: xl.parse(sheet, dtype=str)
#             for sheet in xl.sheet_names
#         }

#     periods: dict[str, dict] = {}
#     audit = {"sheets_detected": [], "columns_detected": {}, "skipped_sheets": []}
#     gstin: Optional[str] = None

#     def _ensure_period(p: str):
#         if p not in periods:
#             periods[p] = {
#                 "sales": 0.0, "taxable_value": 0.0,
#                 "igst": 0.0, "cgst": 0.0, "sgst": 0.0,
#                 "cess": 0.0, "itc": 0.0, "rcm": 0.0,
#             }

#     for sheet_name, df in df_map.items():
#         if df.empty or len(df.columns) < 2:
#             audit["skipped_sheets"].append(f"{sheet_name} (too few columns)")
#             continue

#         sheet_type = _classify_sheet(sheet_name, df)

#         # Try to find GSTIN in any cell of the first few rows
#         if not gstin:
#             for r in range(min(5, len(df))):
#                 for c in df.columns:
#                     cell = str(df.iloc[r][c]).strip()
#                     if re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9]$', cell):
#                         gstin = cell
#                         break

#         # Detect columns
#         col_period  = _detect_column(df, "period")
#         col_taxable = _detect_column(df, "taxable_value")
#         col_igst    = _detect_column(df, "igst")
#         col_cgst    = _detect_column(df, "cgst")
#         col_sgst    = _detect_column(df, "sgst")
#         col_cess    = _detect_column(df, "cess")
#         col_itc     = _detect_column(df, "itc")
#         col_rcm     = _detect_column(df, "rcm")
#         col_class   = _detect_column(df, "classification")
#         col_sales   = _detect_column(df, "sales")
#         col_cr_dr   = _detect_column(df, "credit_debit")

#         detected_cols = {k: v for k, v in {
#             "period": col_period, "taxable_value": col_taxable,
#             "igst": col_igst, "cgst": col_cgst, "sgst": col_sgst,
#             "cess": col_cess, "itc": col_itc, "rcm": col_rcm,
#             "classification": col_class, "sales": col_sales,
#         }.items() if v}

#         audit["sheets_detected"].append({"sheet": sheet_name, "type": sheet_type or "unknown"})
#         audit["columns_detected"][sheet_name] = detected_cols

#         if not col_period and not col_taxable and not col_igst:
#             audit["skipped_sheets"].append(f"{sheet_name} (no recognisable columns)")
#             continue

#         for _, row in df.iterrows():
#             # Determine period
#             period_val = row[col_period] if col_period else None
#             period_key = _parse_period(period_val)
#             if not period_key:
#                 continue

#             # Classification filter
#             if col_class:
#                 cls_val = _norm(row[col_class])
#                 if cls_val and not any(kw in cls_val for kw in ITC_INCLUDE_KEYWORDS):
#                     continue  # skip non-ITC rows in ITC sheets

#             _ensure_period(period_key)

#             # Sales / taxable
#             taxable = _safe_float(row[col_taxable]) if col_taxable else 0.0
#             if col_sales:
#                 sales_raw = _safe_float(row[col_sales])
#                 if col_cr_dr:
#                     cr_dr = _norm(row[col_cr_dr])
#                     sales_val = sales_raw if "cr" in cr_dr else -sales_raw
#                 else:
#                     sales_val = abs(sales_raw)
#                 periods[period_key]["sales"] += sales_val
#             else:
#                 periods[period_key]["sales"] += taxable

#             periods[period_key]["taxable_value"] += taxable

#             # Tax
#             periods[period_key]["igst"] += _safe_float(row[col_igst]) if col_igst else 0.0
#             periods[period_key]["cgst"] += _safe_float(row[col_cgst]) if col_cgst else 0.0
#             periods[period_key]["sgst"] += _safe_float(row[col_sgst]) if col_sgst else 0.0
#             periods[period_key]["cess"] += _safe_float(row[col_cess]) if col_cess else 0.0

#             # ITC / RCM
#             if sheet_type in ("itc", "purchase") or col_itc:
#                 periods[period_key]["itc"] += _safe_float(row[col_itc]) if col_itc else taxable
#             if sheet_type == "rcm" or col_rcm:
#                 periods[period_key]["rcm"] += _safe_float(row[col_rcm]) if col_rcm else taxable

#     # Round all values
#     for p in periods:
#         periods[p] = {k: round(v, 2) for k, v in periods[p].items()}

#     return {"gstin": gstin, "periods": periods, "audit": audit}



import re
import logging
import datetime
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Sheet classification patterns (generic / flat-sheet fallback) ──────────

SHEET_PATTERNS: dict[str, list[str]] = {
    "sales":     ["sales", "revenue", "outward", "output", "gstr1", "gstr-1"],
    "igst":      ["igst", "input igst", "igst input", "integrated"],
    "cgst":      ["cgst", "input cgst", "cgst input", "central"],
    "sgst":      ["sgst", "input sgst", "sgst input", "state"],
    "itc":       ["itc", "input tax credit", "eligible itc", "itc avail"],
    "rcm":       ["rcm", "reverse charge", "reverse chg"],
    "purchase":  ["purchase", "inward", "pr", "purch reg"],
    "summary":   ["summary", "summery", "total", "consolidated"],
}

# ─── Column aliases (generic / flat-sheet fallback) ──────────────────────────

COLUMN_ALIASES: dict[str, list[str]] = {
    "period":        ["month", "period", "date", "tax period", "mon", "yr", "year month"],
    "taxable_value": ["taxable value", "taxable amount", "taxable", "base amount", "value", "amount"],
    "igst":          ["igst", "input igst", "igst amount", "integrated tax", "i.g.s.t"],
    "cgst":          ["cgst", "input cgst", "cgst amount", "central tax", "c.g.s.t"],
    "sgst":          ["sgst", "input sgst", "sgst amount", "state tax", "s.g.s.t", "utgst"],
    "cess":          ["cess amount", "cess"],
    "itc":           ["input tax credit", "eligible itc", "itc credit", "itc", "credit"],
    "rcm":           ["reverse charge", "rcm amount", "rcm"],
    "classification":["classification", "type", "category", "class", "nature"],
    "credit_debit":  ["cr", "dr", "credit", "debit", "cr/dr"],
    "sales":         ["sales", "revenue", "turnover", "supply value"],
}

ITC_INCLUDE_KEYWORDS = {"itc", "input", "eligible itc", "eligible", "credit", "cr"}

# ─── Month / period helpers ───────────────────────────────────────────────────

_MONTH_NUM = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_NAME = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def period_label(canonical: str) -> str:
    """'2025-04' -> 'Apr 2025' for display. Falls back to the input if not canonical."""
    m = re.match(r"^(\d{4})-(\d{2})$", str(canonical or ""))
    if not m:
        return canonical
    y, mo = int(m.group(1)), int(m.group(2))
    if 1 <= mo <= 12:
        return f"{_MONTH_NAME[mo]} {y}"
    return canonical


def _norm(s: str) -> str:
    if s is None:
        return ""
    try:
        if pd.isna(s):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"\s+", " ", str(s).lower().strip())


def _safe_float(v) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, float) and pd.isna(v):
            return 0.0
        if pd.isna(v):
            return 0.0
        return round(float(str(v).replace(",", "").strip() or 0), 2)
    except Exception:
        return 0.0


def _parse_period(val) -> Optional[str]:
    """
    Convert a cell value to a canonical 'YYYY-MM' string.

    Handles, in order:
      - already 'YYYY-MM'
      - 'Apr-25', 'Apr-2025', 'April-25', 'April 2025' style month/year text
        (parsed explicitly, NOT via pandas' ambiguous day/month guessing —
        pd.to_datetime("Apr-25") silently reads it as day=25, year=0001)
      - real datetime / pandas Timestamp values (e.g. from Excel date cells)
      - 'MM/YYYY' or 'M-YYYY'
    Returns None if nothing recognisable is found.
    """
    if val is None:
        return None
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        return f"{val.year:04d}-{val.month:02d}"

    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None

    # Already canonical
    if re.match(r"^\d{4}-\d{2}$", s):
        return s

    # 'Apr-25', 'Apr-2025', 'April-25', 'April 2025', 'Apr/25'
    m = re.match(r"^([A-Za-z]{3,9})[\s\-/]+(\d{2,4})$", s)
    if m:
        mon_key = m.group(1).lower()
        year_txt = m.group(2)
        if mon_key in _MONTH_NUM:
            year = int(year_txt)
            if year < 100:
                year += 2000
            return f"{year:04d}-{_MONTH_NUM[mon_key]:02d}"

    # '25-Apr' style (year/month reversed) — rare but guard for it
    m = re.match(r"^(\d{2,4})[\s\-/]+([A-Za-z]{3,9})$", s)
    if m:
        mon_key = m.group(2).lower()
        year_txt = m.group(1)
        if mon_key in _MONTH_NUM:
            year = int(year_txt)
            if year < 100:
                year += 2000
            return f"{year:04d}-{_MONTH_NUM[mon_key]:02d}"

    # 'MM/YYYY' or 'M-YYYY'
    m = re.match(r"^(\d{1,2})[/-](\d{4})$", s)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return f"{m.group(2)}-{month:02d}"

    # Last resort: let pandas try (only trust it if the string clearly has a
    # 4-digit year in it, otherwise its day/month guessing is unreliable)
    if re.search(r"\d{4}", s):
        try:
            dt = pd.to_datetime(s, dayfirst=True)
            return dt.strftime("%Y-%m")
        except Exception:
            pass

    return None


def _detect_column(df: pd.DataFrame, field: str) -> Optional[str]:
    """Find the first column matching any alias for `field` (whole-token match
    preferred over substring, to avoid false hits like 'cess' inside 'excess')."""
    aliases = COLUMN_ALIASES.get(field, [])
    cols = list(df.columns)

    # Pass 1: exact match
    for col in cols:
        norm_col = _norm(col)
        if norm_col in aliases:
            return col

    # Pass 2: whole-word substring match (word-boundary aware)
    for col in cols:
        norm_col = _norm(col)
        for a in aliases:
            if re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", norm_col):
                return col

    return None


def _classify_sheet(name: str, df: pd.DataFrame) -> Optional[str]:
    norm_name = _norm(name)
    for sheet_type, patterns in SHEET_PATTERNS.items():
        if any(p in norm_name for p in patterns):
            return sheet_type

    headers = [_norm(c) for c in df.columns if c]
    header_str = " ".join(headers)
    for sheet_type, patterns in SHEET_PATTERNS.items():
        if any(p in header_str for p in patterns):
            return sheet_type

    return None


# ─── Wide "BOOKS_DATA" template parser (two-row headers) ────────────────────
#
# The official Books template mirrors the GSTR-3B layout: row 1 has merged
# group headers (e.g. "Tax on Outward Supply", "ITC Available"), row 2 has
# the actual sub-headers (Taxable Value / IGST / CGST / SGST ...), and data
# starts on row 3. A plain single-header pandas read mangles this completely
# (row 1 becomes the header, row 2 becomes a garbage first data row), so this
# is parsed explicitly instead of through the generic flat-sheet path.

_WIDE_GROUP_ALIASES = {
    "outward":       ["tax on outward supply", "outward supply", "outward taxable supply"],
    "rcm_supply":    ["outward taxable supply liable to rcm", "rcm supply", "liable to rcm"],
    "itc_available": ["itc available"],
}


def _looks_like_wide_template(raw: pd.DataFrame) -> bool:
    """True if row0/row1 look like the two-row group+sub header layout."""
    if raw.shape[0] < 3 or raw.shape[1] < 4:
        return False
    row0 = [_norm(v) for v in raw.iloc[0].tolist()]
    row1 = [_norm(v) for v in raw.iloc[1].tolist()]
    first_col_is_month = row0[0] in ("month",) or row1[0] in ("month",)
    has_group_headers = any(
        any(alias in cell for aliases in _WIDE_GROUP_ALIASES.values() for alias in aliases)
        for cell in row0
    )
    return first_col_is_month and has_group_headers


def _parse_wide_books_sheet(raw: pd.DataFrame, audit: dict, sheet_name: str) -> dict:
    """Parse the two-row-header BOOKS_DATA template into {period: {fields}}."""
    row0 = [_norm(v) for v in raw.iloc[0].tolist()]
    row1 = [_norm(v) for v in raw.iloc[1].tolist()]

    # Forward-fill merged group header row
    filled_group = []
    last = ""
    for v in row0:
        if v:
            last = v
        filled_group.append(last)

    def _find_col(group_aliases: list[str], subheader: str) -> Optional[int]:
        for idx, (g, sub) in enumerate(zip(filled_group, row1)):
            if any(alias in g for alias in group_aliases) and sub == subheader:
                return idx
        return None

    col_month      = 0
    col_taxable    = _find_col(_WIDE_GROUP_ALIASES["outward"], "taxable value")
    col_zero_rated = _find_col(_WIDE_GROUP_ALIASES["outward"], "zero rated")
    col_out_igst   = _find_col(_WIDE_GROUP_ALIASES["outward"], "igst")
    col_out_cgst   = _find_col(_WIDE_GROUP_ALIASES["outward"], "cgst")
    col_out_sgst   = _find_col(_WIDE_GROUP_ALIASES["outward"], "sgst")
    col_rcm_igst   = _find_col(_WIDE_GROUP_ALIASES["rcm_supply"], "igst")
    col_rcm_cgst   = _find_col(_WIDE_GROUP_ALIASES["rcm_supply"], "cgst")
    col_rcm_sgst   = _find_col(_WIDE_GROUP_ALIASES["rcm_supply"], "sgst")
    col_itc_igst   = _find_col(_WIDE_GROUP_ALIASES["itc_available"], "igst")
    col_itc_cgst   = _find_col(_WIDE_GROUP_ALIASES["itc_available"], "cgst")
    col_itc_sgst   = _find_col(_WIDE_GROUP_ALIASES["itc_available"], "sgst")

    detected = {k: v for k, v in {
        "period (Month)": col_month,
        "taxable_value": col_taxable, "zero_rated": col_zero_rated,
        "outward_igst": col_out_igst, "outward_cgst": col_out_cgst, "outward_sgst": col_out_sgst,
        "rcm_igst": col_rcm_igst, "rcm_cgst": col_rcm_cgst, "rcm_sgst": col_rcm_sgst,
        "itc_igst": col_itc_igst, "itc_cgst": col_itc_cgst, "itc_sgst": col_itc_sgst,
    }.items() if v is not None}
    audit["columns_detected"][sheet_name] = detected
    audit["sheets_detected"].append({"sheet": sheet_name, "type": "books_wide_template"})

    def _cell(row, idx):
        return row[idx] if idx is not None and idx < len(row) else None

    periods: dict[str, dict] = {}
    data_rows = raw.iloc[2:]
    for _, row in data_rows.iterrows():
        row = row.tolist()
        period_key = _parse_period(_cell(row, col_month))
        if not period_key:
            continue

        taxable    = _safe_float(_cell(row, col_taxable))
        zero_rated = _safe_float(_cell(row, col_zero_rated))
        out_igst   = _safe_float(_cell(row, col_out_igst))
        out_cgst   = _safe_float(_cell(row, col_out_cgst))
        out_sgst   = _safe_float(_cell(row, col_out_sgst))
        rcm_igst   = _safe_float(_cell(row, col_rcm_igst))
        rcm_cgst   = _safe_float(_cell(row, col_rcm_cgst))
        rcm_sgst   = _safe_float(_cell(row, col_rcm_sgst))
        itc_igst   = _safe_float(_cell(row, col_itc_igst))
        itc_cgst   = _safe_float(_cell(row, col_itc_cgst))
        itc_sgst   = _safe_float(_cell(row, col_itc_sgst))

        periods[period_key] = {
            "sales":         round(taxable + zero_rated, 2),
            "taxable_value": round(taxable, 2),
            "igst":          round(out_igst, 2),
            "cgst":          round(out_cgst, 2),
            "sgst":          round(out_sgst, 2),
            "cess":          0.0,   # template has no Cess column in the outward section
            "itc":           round(itc_igst + itc_cgst + itc_sgst, 2),
            "rcm":           round(rcm_igst + rcm_cgst + rcm_sgst, 2),
        }

    return periods


# ─── Generic flat-sheet parser (fallback for simple one-header-row books files)

def _parse_flat_sheet(df: pd.DataFrame, audit: dict, sheet_name: str) -> dict:
    sheet_type = _classify_sheet(sheet_name, df)

    col_period  = _detect_column(df, "period")
    col_taxable = _detect_column(df, "taxable_value")
    col_igst    = _detect_column(df, "igst")
    col_cgst    = _detect_column(df, "cgst")
    col_sgst    = _detect_column(df, "sgst")
    col_cess    = _detect_column(df, "cess")
    col_itc     = _detect_column(df, "itc")
    col_rcm     = _detect_column(df, "rcm")
    col_class   = _detect_column(df, "classification")
    col_sales   = _detect_column(df, "sales")
    col_cr_dr   = _detect_column(df, "credit_debit")

    detected_cols = {k: v for k, v in {
        "period": col_period, "taxable_value": col_taxable,
        "igst": col_igst, "cgst": col_cgst, "sgst": col_sgst,
        "cess": col_cess, "itc": col_itc, "rcm": col_rcm,
        "classification": col_class, "sales": col_sales,
    }.items() if v}

    audit["sheets_detected"].append({"sheet": sheet_name, "type": sheet_type or "unknown"})
    audit["columns_detected"][sheet_name] = detected_cols

    if not col_period and not col_taxable and not col_igst:
        audit["skipped_sheets"].append(f"{sheet_name} (no recognisable columns)")
        return {}

    periods: dict[str, dict] = {}

    def _ensure(p):
        if p not in periods:
            periods[p] = {
                "sales": 0.0, "taxable_value": 0.0,
                "igst": 0.0, "cgst": 0.0, "sgst": 0.0,
                "cess": 0.0, "itc": 0.0, "rcm": 0.0,
            }

    for _, row in df.iterrows():
        period_val = row[col_period] if col_period else None
        period_key = _parse_period(period_val)
        if not period_key:
            continue

        if col_class:
            cls_val = _norm(row[col_class])
            if cls_val and not any(kw in cls_val for kw in ITC_INCLUDE_KEYWORDS):
                continue

        _ensure(period_key)

        taxable = _safe_float(row[col_taxable]) if col_taxable else 0.0
        if col_sales:
            sales_raw = _safe_float(row[col_sales])
            if col_cr_dr:
                cr_dr = _norm(row[col_cr_dr])
                sales_val = sales_raw if "cr" in cr_dr else -sales_raw
            else:
                sales_val = abs(sales_raw)
            periods[period_key]["sales"] += sales_val
        else:
            periods[period_key]["sales"] += taxable

        periods[period_key]["taxable_value"] += taxable
        periods[period_key]["igst"] += _safe_float(row[col_igst]) if col_igst else 0.0
        periods[period_key]["cgst"] += _safe_float(row[col_cgst]) if col_cgst else 0.0
        periods[period_key]["sgst"] += _safe_float(row[col_sgst]) if col_sgst else 0.0
        periods[period_key]["cess"] += _safe_float(row[col_cess]) if col_cess else 0.0

        if sheet_type in ("itc", "purchase") or col_itc:
            periods[period_key]["itc"] += _safe_float(row[col_itc]) if col_itc else taxable
        if sheet_type == "rcm" or col_rcm:
            periods[period_key]["rcm"] += _safe_float(row[col_rcm]) if col_rcm else taxable

    return periods


# ─── Main extractor ───────────────────────────────────────────────────────────

def extract_books(file_bytes: bytes, filename: str) -> dict:
    """
    Extract and normalise books data from xlsx or csv.
    Returns:
    {
      "gstin": str | None,
      "periods": { "YYYY-MM": { "sales", "taxable_value", "igst", "cgst", "sgst", "cess", "itc", "rcm" } },
      "audit": { "sheets_detected": [...], "columns_detected": {...}, "skipped_sheets": [...] }
    }
    Periods use canonical 'YYYY-MM' keys (calendar year-month) so they line up
    exactly with the GSTR-3B side of the reconciliation.
    """
    fname = filename.lower()

    if fname.endswith(".csv"):
        df_map = {"Sheet1": pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype=str)}
        raw_map = {"Sheet1": pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype=str, header=None)}
    else:
        xl = pd.ExcelFile(pd.io.common.BytesIO(file_bytes))
        df_map = {sheet: xl.parse(sheet, dtype=str) for sheet in xl.sheet_names}
        raw_map = {sheet: xl.parse(sheet, dtype=str, header=None) for sheet in xl.sheet_names}

    periods: dict[str, dict] = {}
    audit = {"sheets_detected": [], "columns_detected": {}, "skipped_sheets": []}
    gstin: Optional[str] = None

    for sheet_name, df in df_map.items():
        raw = raw_map[sheet_name]

        if raw.empty or raw.shape[1] < 2:
            audit["skipped_sheets"].append(f"{sheet_name} (too few columns)")
            continue

        # GSTIN scan (first few rows, any column)
        if not gstin:
            for r in range(min(5, len(raw))):
                for c in raw.columns:
                    cell = str(raw.iloc[r][c]).strip()
                    if re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9]$', cell):
                        gstin = cell
                        break

        if _looks_like_wide_template(raw):
            sheet_periods = _parse_wide_books_sheet(raw, audit, sheet_name)
        else:
            if df.empty or len(df.columns) < 2:
                audit["skipped_sheets"].append(f"{sheet_name} (too few columns)")
                continue
            sheet_periods = _parse_flat_sheet(df, audit, sheet_name)

        for p, vals in sheet_periods.items():
            if p not in periods:
                periods[p] = dict(vals)
            else:
                for k, v in vals.items():
                    periods[p][k] = periods[p].get(k, 0.0) + v

    for p in periods:
        periods[p] = {k: round(v, 2) for k, v in periods[p].items()}

    return {"gstin": gstin, "periods": periods, "audit": audit}