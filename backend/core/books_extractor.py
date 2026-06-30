import re
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Sheet classification patterns ───────────────────────────────────────────

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

# ─── Column aliases ───────────────────────────────────────────────────────────

COLUMN_ALIASES: dict[str, list[str]] = {
    "period":        ["month", "period", "date", "tax period", "mon", "yr", "year month"],
    "taxable_value": ["taxable", "taxable value", "taxable amount", "value", "amount", "base amount"],
    "igst":          ["igst", "input igst", "igst amount", "integrated tax", "i.g.s.t"],
    "cgst":          ["cgst", "input cgst", "cgst amount", "central tax", "c.g.s.t"],
    "sgst":          ["sgst", "input sgst", "sgst amount", "state tax", "s.g.s.t", "utgst"],
    "cess":          ["cess", "cess amount"],
    "itc":           ["itc", "input tax credit", "eligible itc", "itc credit", "credit"],
    "rcm":           ["rcm", "reverse charge", "rcm amount"],
    "classification":["classification", "type", "category", "class", "nature"],
    "credit_debit":  ["cr", "dr", "credit", "debit", "cr/dr"],
    "sales":         ["sales", "revenue", "turnover", "supply value"],
}

ITC_INCLUDE_KEYWORDS = {"itc", "input", "eligible itc", "eligible", "credit", "cr"}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower().strip())

def _safe_float(v) -> float:
    try:
        if pd.isna(v):
            return 0.0
        return round(float(str(v).replace(",", "").strip()), 2)
    except Exception:
        return 0.0

def _classify_sheet(name: str, df: pd.DataFrame) -> Optional[str]:
    """Return best matching sheet type or None."""
    norm_name = _norm(name)
    for sheet_type, patterns in SHEET_PATTERNS.items():
        if any(p in norm_name for p in patterns):
            return sheet_type

    # Inspect headers
    headers = [_norm(c) for c in df.columns if c]
    header_str = " ".join(headers)
    for sheet_type, patterns in SHEET_PATTERNS.items():
        if any(p in header_str for p in patterns):
            return sheet_type

    return None

def _detect_column(df: pd.DataFrame, field: str) -> Optional[str]:
    """Find the first column matching any alias for `field`."""
    aliases = COLUMN_ALIASES.get(field, [])
    for col in df.columns:
        norm_col = _norm(col)
        if any(a == norm_col or a in norm_col for a in aliases):
            return col
    return None

def _parse_period(val) -> Optional[str]:
    """Convert a cell value to YYYY-MM string."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    # Already YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", s):
        return s
    # Try pandas
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime("%Y-%m")
    except Exception:
        pass
    # Month name patterns: "Mar 2026", "March 2026", "03/2026"
    m = re.match(r"([A-Za-z]+)[- /](\d{4})", s)
    if m:
        try:
            dt = pd.to_datetime(f"01 {m.group(1)} {m.group(2)}", dayfirst=True)
            return dt.strftime("%Y-%m")
        except Exception:
            pass
    m2 = re.match(r"(\d{1,2})[/-](\d{4})", s)
    if m2:
        return f"{m2.group(2)}-{int(m2.group(1)):02d}"
    return None

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
    """
    fname = filename.lower()

    # ── Load workbook / CSV ──────────────────────────────────────────────────
    if fname.endswith(".csv"):
        df_map = {"Sheet1": pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype=str)}
    else:
        xl = pd.ExcelFile(pd.io.common.BytesIO(file_bytes))
        df_map = {
            sheet: xl.parse(sheet, dtype=str)
            for sheet in xl.sheet_names
        }

    periods: dict[str, dict] = {}
    audit = {"sheets_detected": [], "columns_detected": {}, "skipped_sheets": []}
    gstin: Optional[str] = None

    def _ensure_period(p: str):
        if p not in periods:
            periods[p] = {
                "sales": 0.0, "taxable_value": 0.0,
                "igst": 0.0, "cgst": 0.0, "sgst": 0.0,
                "cess": 0.0, "itc": 0.0, "rcm": 0.0,
            }

    for sheet_name, df in df_map.items():
        if df.empty or len(df.columns) < 2:
            audit["skipped_sheets"].append(f"{sheet_name} (too few columns)")
            continue

        sheet_type = _classify_sheet(sheet_name, df)

        # Try to find GSTIN in any cell of the first few rows
        if not gstin:
            for r in range(min(5, len(df))):
                for c in df.columns:
                    cell = str(df.iloc[r][c]).strip()
                    if re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9]$', cell):
                        gstin = cell
                        break

        # Detect columns
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
            continue

        for _, row in df.iterrows():
            # Determine period
            period_val = row[col_period] if col_period else None
            period_key = _parse_period(period_val)
            if not period_key:
                continue

            # Classification filter
            if col_class:
                cls_val = _norm(row[col_class])
                if cls_val and not any(kw in cls_val for kw in ITC_INCLUDE_KEYWORDS):
                    continue  # skip non-ITC rows in ITC sheets

            _ensure_period(period_key)

            # Sales / taxable
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

            # Tax
            periods[period_key]["igst"] += _safe_float(row[col_igst]) if col_igst else 0.0
            periods[period_key]["cgst"] += _safe_float(row[col_cgst]) if col_cgst else 0.0
            periods[period_key]["sgst"] += _safe_float(row[col_sgst]) if col_sgst else 0.0
            periods[period_key]["cess"] += _safe_float(row[col_cess]) if col_cess else 0.0

            # ITC / RCM
            if sheet_type in ("itc", "purchase") or col_itc:
                periods[period_key]["itc"] += _safe_float(row[col_itc]) if col_itc else taxable
            if sheet_type == "rcm" or col_rcm:
                periods[period_key]["rcm"] += _safe_float(row[col_rcm]) if col_rcm else taxable

    # Round all values
    for p in periods:
        periods[p] = {k: round(v, 2) for k, v in periods[p].items()}

    return {"gstin": gstin, "periods": periods, "audit": audit}