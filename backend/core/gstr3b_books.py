# import logging
# import datetime
# import tempfile
# import os
# from typing import Optional

# from openpyxl import Workbook
# from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
# from openpyxl.utils import get_column_letter

# logger = logging.getLogger(__name__)

# # ─── Recon row definitions ────────────────────────────────────────────────────

# RECON_ROWS = [
#     ("sales",         "Sales / Outward Value"),
#     ("taxable_value", "Taxable Value"),
#     ("igst",          "IGST"),
#     ("cgst",          "CGST"),
#     ("sgst",          "SGST"),
#     ("cess",          "Cess"),
#     ("itc",           "ITC (Input Tax Credit)"),
#     ("rcm",           "RCM (Reverse Charge)"),
# ]

# TOLERANCE_MATCH  = 1.0
# TOLERANCE_MINOR  = 100.0

# def _status(diff: float) -> str:
#     abs_diff = abs(diff)
#     if abs_diff <= TOLERANCE_MATCH:  return "Match"
#     if abs_diff <= TOLERANCE_MINOR:  return "Minor Difference"
#     return "Mismatch"

# # ─── GSTR-3B normalizer ───────────────────────────────────────────────────────

# def normalize_gstr3b(g3b: dict) -> dict:
#     def sf(v):
#         try:
#             return round(float(str(v).replace(",","") or 0), 2)
#         except Exception:
#             return 0.0
#     return {
#         "sales":         sf(g3b.get("outward_taxable_value", 0)) + sf(g3b.get("zero_rated_value", 0)),
#         "taxable_value": sf(g3b.get("outward_taxable_value", 0)),
#         "igst":          sf(g3b.get("outward_igst", 0)) + sf(g3b.get("zero_rated_igst", 0)),
#         "cgst":          sf(g3b.get("outward_cgst", 0)),
#         "sgst":          sf(g3b.get("outward_sgst", 0)),
#         "cess":          sf(g3b.get("outward_cess", 0)),
#         "itc":           sf(g3b.get("other_itc_igst", 0)) + sf(g3b.get("other_itc_cgst", 0)) + sf(g3b.get("other_itc_sgst", 0)),
#         "rcm":           sf(g3b.get("inward_reverse_charge_igst", 0)) + sf(g3b.get("inward_reverse_charge_cgst", 0)) + sf(g3b.get("inward_reverse_charge_sgst", 0)),
#     }

# # ─── Per-period reconciliation ────────────────────────────────────────────────

# def reconcile_period(period: str, books: dict, g3b_norm: dict) -> dict:
#     rows = []
#     total_variance = 0.0
#     for key, description in RECON_ROWS:
#         bv   = books.get(key, 0.0)
#         g3bv = g3b_norm.get(key, 0.0)
#         diff = round(bv - g3bv, 2)
#         total_variance += abs(diff)
#         rows.append({
#             "description": description,
#             "books":       bv,
#             "gstr3b":      g3bv,
#             "difference":  diff,
#             "status":      _status(diff),
#         })
#     overall = (
#         "Matched" if total_variance <= TOLERANCE_MATCH
#         else "Minor Difference" if total_variance <= TOLERANCE_MINOR
#         else "Mismatch"
#     )
#     return {
#         "period":         period,
#         "rows":           rows,
#         "total_variance": round(total_variance, 2),
#         "overall_status": overall,
#     }

# # ─── Full reconciliation ──────────────────────────────────────────────────────

# def reconcile_gstr3b_vs_books(
#     g3b_records: list[dict],
#     books_data:  dict,
#     gstin_warning: Optional[str] = None,
# ) -> dict:
#     """
#     g3b_records: list of extracted GSTR-3B dicts (one per month from existing extractor)
#     books_data:  output of extract_books() — { "gstin", "periods", "audit" }
#     """
#     def get_period(r: dict) -> str:
#         tp = r.get("TaxPeriod") or r.get("tax_period") or r.get("period") or ""
#         fy = r.get("FinancialYear") or r.get("year") or ""
#         if tp and fy:
#             return f"{tp} {fy}"
#         return tp or r.get("filename", "Unknown")

#     g3b_by_period = {}
#     for r in g3b_records:
#         p = get_period(r)
#         g3b_by_period[p] = normalize_gstr3b(r)

#     books_periods = books_data.get("periods", {})

#     # Union of all periods
#     all_periods = sorted(
#         set(list(g3b_by_period.keys()) + list(books_periods.keys()))
#     )

#     period_results = []
#     exceptions     = []
#     for period in all_periods:
#         books_p = books_periods.get(period, {
#             k: 0.0 for k, _ in RECON_ROWS
#         })
#         g3b_p = g3b_by_period.get(period, {
#             k: 0.0 for k, _ in RECON_ROWS
#         })
#         pr = reconcile_period(period, books_p, g3b_p)
#         period_results.append(pr)
#         if pr["overall_status"] != "Matched":
#             exceptions.append(pr)

#     # Summary totals
#     summary = {
#         "books_total": round(sum(
#             sum(books_periods.get(p, {}).get(k, 0) for k, _ in RECON_ROWS)
#             for p in all_periods
#         ), 2),
#         "gstr3b_total": round(sum(
#             sum(g3b_by_period.get(p, {}).get(k, 0) for k, _ in RECON_ROWS)
#             for p in all_periods
#         ), 2),
#         "months": len(all_periods),
#         "matched": sum(1 for p in period_results if p["overall_status"] == "Matched"),
#         "mismatches": sum(1 for p in period_results if p["overall_status"] == "Mismatch"),
#         "minor": sum(1 for p in period_results if p["overall_status"] == "Minor Difference"),
#         "gstin_warning": gstin_warning,
#         "audit": books_data.get("audit", {}),
#     }

#     return {
#         "status":   "success",
#         "summary":  summary,
#         "monthly":  period_results,
#         "exceptions": exceptions,
#     }

# # ─── Excel styles ─────────────────────────────────────────────────────────────

# _GREEN  = PatternFill("solid", fgColor="D6F5D6")
# _YELLOW = PatternFill("solid", fgColor="FFF3CD")
# _RED    = PatternFill("solid", fgColor="FFD6D6")
# _HEADER = PatternFill("solid", fgColor="2D3748")
# _SUB    = PatternFill("solid", fgColor="F0F4F8")

# def _border():
#     s = Side(style="thin", color="CCCCCC")
#     return Border(left=s, right=s, top=s, bottom=s)

# def _hfont(): return Font(bold=True, color="FFFFFF", size=10)
# def _bfont(): return Font(bold=True, size=10)

# def _num(cell):
#     cell.number_format = '#,##0.00'
#     cell.alignment = Alignment(horizontal="right")

# def _w(ws, col, width):
#     ws.column_dimensions[get_column_letter(col)].width = width

# def _status_fill(status: str):
#     if status == "Matched":       return _GREEN
#     if status == "Minor Difference": return _YELLOW
#     return _RED

# # ─── Sheet writers ────────────────────────────────────────────────────────────

# def _sheet_summary(ws, result: dict, gstin_3b: str, gstin_books: str):
#     ws.append(["GSTR-3B vs Books — Reconciliation Summary"])
#     ws["A1"].font = Font(bold=True, size=13)
#     ws.append([])
#     s = result["summary"]

#     rows = [
#         ("GSTIN (GSTR-3B)", gstin_3b),
#         ("GSTIN (Books)",   gstin_books or "Not detected"),
#         ("Periods",         s["months"]),
#         ("Months Matched",  s["matched"]),
#         ("Minor Differences", s["minor"]),
#         ("Mismatches",      s["mismatches"]),
#         ("Books Total (₹)", s["books_total"]),
#         ("GSTR-3B Total (₹)", s["gstr3b_total"]),
#         ("Net Difference (₹)", round(s["books_total"] - s["gstr3b_total"], 2)),
#     ]
#     if s.get("gstin_warning"):
#         rows.append(("⚠ GSTIN Warning", s["gstin_warning"]))

#     for label, value in rows:
#         ws.append([label, value])
#         r = ws.max_row
#         ws.cell(r, 1).font = Font(bold=True)
#         for c in range(1, 3):
#             ws.cell(r, c).border = _border()
#         if isinstance(value, float):
#             _num(ws.cell(r, 2))

#     _w(ws, 1, 30); _w(ws, 2, 22)


# def _sheet_monthly(ws, monthly: list):
#     ws.freeze_panes = "A3"
#     headers = ["Period", "Books (₹)", "GSTR-3B (₹)", "Difference (₹)", "Status"]
#     ws.append(headers)
#     for ci, h in enumerate(headers, 1):
#         c = ws.cell(1, ci)
#         c.fill = _HEADER; c.font = _hfont(); c.border = _border()
#         c.alignment = Alignment(horizontal="center")

#     # One row per period (summed across all RECON_ROWS)
#     for p in monthly:
#         bk  = sum(r["books"]   for r in p["rows"])
#         g3b = sum(r["gstr3b"]  for r in p["rows"])
#         diff = round(bk - g3b, 2)
#         ws.append([p["period"], bk, g3b, diff, p["overall_status"]])
#         ri = ws.max_row
#         fill = _status_fill(p["overall_status"])
#         for ci in range(1, 6):
#             ws.cell(ri, ci).fill = fill
#             ws.cell(ri, ci).border = _border()
#             if 2 <= ci <= 4:
#                 _num(ws.cell(ri, ci))

#     for ci, w in enumerate([16, 18, 18, 18, 18], 1):
#         _w(ws, ci, w)


# def _sheet_tax(ws, monthly: list):
#     ws.freeze_panes = "A3"
#     fields = ["igst", "cgst", "sgst", "cess", "itc", "rcm"]
#     headers = ["Period"] + [f.upper() for f in fields] + ["Status"]
#     ws.append(headers)
#     for ci, h in enumerate(headers, 1):
#         c = ws.cell(1, ci)
#         c.fill = _HEADER; c.font = _hfont(); c.border = _border()
#         c.alignment = Alignment(horizontal="center")

#     desc_map = {r["description"]: r for rows in [p["rows"] for p in monthly] for r in rows}
#     for p in monthly:
#         row_by_desc = {r["description"]: r for r in p["rows"]}
#         label_map = {
#             "igst": "IGST", "cgst": "CGST", "sgst": "SGST",
#             "cess": "Cess", "itc": "ITC (Input Tax Credit)", "rcm": "RCM (Reverse Charge)"
#         }
#         row_data = [p["period"]]
#         for f in fields:
#             lbl = label_map[f]
#             r = row_by_desc.get(lbl, {})
#             row_data.append(r.get("difference", 0.0))
#         row_data.append(p["overall_status"])
#         ws.append(row_data)
#         ri = ws.max_row
#         fill = _status_fill(p["overall_status"])
#         for ci in range(1, len(headers) + 1):
#             ws.cell(ri, ci).fill = fill
#             ws.cell(ri, ci).border = _border()
#             if 2 <= ci <= len(fields) + 1:
#                 _num(ws.cell(ri, ci))

#     for ci, w in enumerate([16] + [14]*len(fields) + [18], 1):
#         _w(ws, ci, w)


# def _sheet_exceptions(ws, exceptions: list):
#     if not exceptions:
#         ws.append(["No mismatches — all periods matched."])
#         return

#     ws.freeze_panes = "A3"
#     headers = ["Period", "Description", "Books (₹)", "GSTR-3B (₹)", "Difference (₹)", "Status"]
#     ws.append(headers)
#     for ci, h in enumerate(headers, 1):
#         c = ws.cell(1, ci)
#         c.fill = _HEADER; c.font = _hfont(); c.border = _border()
#         c.alignment = Alignment(horizontal="center")

#     for p in exceptions:
#         for row in p["rows"]:
#             if row["status"] == "Match":
#                 continue
#             ws.append([p["period"], row["description"], row["books"], row["gstr3b"], row["difference"], row["status"]])
#             ri = ws.max_row
#             fill = _status_fill(row["status"])
#             for ci in range(1, 7):
#                 ws.cell(ri, ci).fill = fill
#                 ws.cell(ri, ci).border = _border()
#                 if 3 <= ci <= 5:
#                     _num(ws.cell(ri, ci))

#     for ci, w in enumerate([16, 28, 16, 16, 16, 18], 1):
#         _w(ws, ci, w)


# def _sheet_audit(ws, audit: dict):
#     ws.append(["Extraction Audit"])
#     ws["A1"].font = Font(bold=True, size=12)
#     ws.append([])

#     ws.append(["Sheets Detected"])
#     ws.cell(ws.max_row, 1).font = _bfont()
#     for s in audit.get("sheets_detected", []):
#         ws.append([s.get("sheet",""), s.get("type","unknown")])

#     ws.append([])
#     ws.append(["Skipped Sheets"])
#     ws.cell(ws.max_row, 1).font = _bfont()
#     for s in audit.get("skipped_sheets", []):
#         ws.append([s])

#     ws.append([])
#     ws.append(["Columns Detected per Sheet"])
#     ws.cell(ws.max_row, 1).font = _bfont()
#     for sheet, cols in audit.get("columns_detected", {}).items():
#         ws.append([sheet])
#         for field, col in cols.items():
#             ws.append(["", field, col])

#     _w(ws, 1, 28); _w(ws, 2, 22); _w(ws, 3, 22)


# # ─── Public: generate Excel ───────────────────────────────────────────────────

# def generate_gstr3b_books_excel(
#     result:       dict,
#     output_path:  str,
#     gstin_3b:     str = "",
#     gstin_books:  str = "",
# ) -> str:
#     wb = Workbook()
#     wb.remove(wb.active)

#     ws1 = wb.create_sheet("Summary")
#     _sheet_summary(ws1, result, gstin_3b, gstin_books)

#     ws2 = wb.create_sheet("Monthly Comparison")
#     _sheet_monthly(ws2, result["monthly"])

#     ws3 = wb.create_sheet("Tax Comparison")
#     _sheet_tax(ws3, result["monthly"])

#     ws4 = wb.create_sheet("Exceptions")
#     _sheet_exceptions(ws4, result["exceptions"])

#     ws5 = wb.create_sheet("Extraction Audit")
#     _sheet_audit(ws5, result["summary"].get("audit", {}))

#     wb.save(output_path)
#     logger.info(f"GSTR-3B vs Books Excel saved: {output_path}")
#     return output_path

import logging
import re
import datetime
import tempfile
import os
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .books_extractor import period_label as _period_label

logger = logging.getLogger(__name__)

# ─── Canonical period key helpers ─────────────────────────────────────────────
#
# GSTR-3B PDFs are extracted with a separate month name ("period": "April")
# and financial year ("year": "2025-26"). Books periods (from books_extractor)
# use canonical "YYYY-MM" calendar keys (e.g. "2025-04"). Previously these two
# were combined into an incompatible string like "April 2025-26" on the
# GSTR-3B side, which could never match the Books side's "YYYY-MM" keys —
# every period showed up as a 100% mismatch regardless of actual figures.
# This maps GSTR-3B's period/year into the SAME canonical "YYYY-MM" key.

_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _canonical_period_from_g3b(period_name: str, fy: str) -> Optional[str]:
    """
    period_name: month name, e.g. "April", "December", "January"
    fy: financial-year string, e.g. "2025-26"
    Returns "YYYY-MM" (calendar year-month), or None if unparseable.
    """
    if not period_name:
        return None
    month_num = _MONTH_NUM.get(str(period_name).strip().lower())
    if not month_num:
        return None

    m = re.match(r"^(\d{4})-(\d{2})$", str(fy or "").strip())
    if m:
        start_year = int(m.group(1))
        end_year = int(str(start_year)[:2] + m.group(2))
        # FY runs Apr(start_year) .. Mar(end_year)
        year = start_year if month_num >= 4 else end_year
    else:
        m2 = re.match(r"^(\d{4})$", str(fy or "").strip())
        year = int(m2.group(1)) if m2 else datetime.datetime.now().year

    return f"{year:04d}-{month_num:02d}"

# ─── Recon row definitions ────────────────────────────────────────────────────

RECON_ROWS = [
    ("sales",         "Sales / Outward Value"),
    ("taxable_value", "Taxable Value"),
    ("igst",          "IGST"),
    ("cgst",          "CGST"),
    ("sgst",          "SGST"),
    ("cess",          "Cess"),
    ("itc",           "ITC (Input Tax Credit)"),
    ("rcm",           "RCM (Reverse Charge)"),
]

TOLERANCE_MATCH  = 1.0
TOLERANCE_MINOR  = 100.0

def _status(diff: float) -> str:
    abs_diff = abs(diff)
    if abs_diff <= TOLERANCE_MATCH:  return "Match"
    if abs_diff <= TOLERANCE_MINOR:  return "Minor Difference"
    return "Mismatch"

# ─── GSTR-3B normalizer ───────────────────────────────────────────────────────

def normalize_gstr3b(g3b: dict) -> dict:
    def sf(v):
        try:
            return round(float(str(v).replace(",","") or 0), 2)
        except Exception:
            return 0.0
    return {
        "sales":         sf(g3b.get("outward_taxable_value", 0)) + sf(g3b.get("zero_rated_value", 0)),
        "taxable_value": sf(g3b.get("outward_taxable_value", 0)),
        "igst":          sf(g3b.get("outward_igst", 0)) + sf(g3b.get("zero_rated_igst", 0)),
        "cgst":          sf(g3b.get("outward_cgst", 0)),
        "sgst":          sf(g3b.get("outward_sgst", 0)),
        "cess":          sf(g3b.get("outward_cess", 0)),
        "itc":           sf(g3b.get("other_itc_igst", 0)) + sf(g3b.get("other_itc_cgst", 0)) + sf(g3b.get("other_itc_sgst", 0)),
        "rcm":           sf(g3b.get("inward_reverse_charge_igst", 0)) + sf(g3b.get("inward_reverse_charge_cgst", 0)) + sf(g3b.get("inward_reverse_charge_sgst", 0)),
    }

# ─── Per-period reconciliation ────────────────────────────────────────────────

def reconcile_period(period: str, books: dict, g3b_norm: dict) -> dict:
    rows = []
    total_variance = 0.0
    for key, description in RECON_ROWS:
        bv   = books.get(key, 0.0)
        g3bv = g3b_norm.get(key, 0.0)
        diff = round(bv - g3bv, 2)
        total_variance += abs(diff)
        rows.append({
            "description": description,
            "books":       bv,
            "gstr3b":      g3bv,
            "difference":  diff,
            "status":      _status(diff),
        })
    overall = (
        "Matched" if total_variance <= TOLERANCE_MATCH
        else "Minor Difference" if total_variance <= TOLERANCE_MINOR
        else "Mismatch"
    )
    return {
        "period":         period,
        "period_label":   _period_label(period),
        "rows":           rows,
        "total_variance": round(total_variance, 2),
        "overall_status": overall,
    }

# ─── Full reconciliation ──────────────────────────────────────────────────────

def reconcile_gstr3b_vs_books(
    g3b_records: list[dict],
    books_data:  dict,
    gstin_warning: Optional[str] = None,
) -> dict:
    """
    g3b_records: list of extracted GSTR-3B dicts (one per month from existing extractor)
    books_data:  output of extract_books() — { "gstin", "periods", "audit" }
    """
    def get_period(r: dict) -> str:
        tp = r.get("TaxPeriod") or r.get("tax_period") or r.get("period") or ""
        fy = r.get("FinancialYear") or r.get("year") or ""
        canonical = _canonical_period_from_g3b(tp, fy)
        if canonical:
            return canonical
        # Fallback for records missing period/year (keeps them visible instead
        # of silently dropping them, but they won't line up with Books).
        if tp and fy:
            return f"{tp} {fy}"
        return tp or r.get("filename", "Unknown")

    g3b_by_period = {}
    for r in g3b_records:
        p = get_period(r)
        g3b_by_period[p] = normalize_gstr3b(r)

    books_periods = books_data.get("periods", {})

    # Union of all periods
    all_periods = sorted(
        set(list(g3b_by_period.keys()) + list(books_periods.keys()))
    )

    period_results = []
    exceptions     = []
    for period in all_periods:
        books_p = books_periods.get(period, {
            k: 0.0 for k, _ in RECON_ROWS
        })
        g3b_p = g3b_by_period.get(period, {
            k: 0.0 for k, _ in RECON_ROWS
        })
        pr = reconcile_period(period, books_p, g3b_p)
        period_results.append(pr)
        if pr["overall_status"] != "Matched":
            exceptions.append(pr)

    # Summary totals
    summary = {
        "books_total": round(sum(
            sum(books_periods.get(p, {}).get(k, 0) for k, _ in RECON_ROWS)
            for p in all_periods
        ), 2),
        "gstr3b_total": round(sum(
            sum(g3b_by_period.get(p, {}).get(k, 0) for k, _ in RECON_ROWS)
            for p in all_periods
        ), 2),
        "months": len(all_periods),
        "matched": sum(1 for p in period_results if p["overall_status"] == "Matched"),
        "mismatches": sum(1 for p in period_results if p["overall_status"] == "Mismatch"),
        "minor": sum(1 for p in period_results if p["overall_status"] == "Minor Difference"),
        "gstin_warning": gstin_warning,
        "audit": books_data.get("audit", {}),
    }

    return {
        "status":   "success",
        "summary":  summary,
        "monthly":  period_results,
        "exceptions": exceptions,
    }

# ─── Excel styles ─────────────────────────────────────────────────────────────

_GREEN  = PatternFill("solid", fgColor="D6F5D6")
_YELLOW = PatternFill("solid", fgColor="FFF3CD")
_RED    = PatternFill("solid", fgColor="FFD6D6")
_HEADER = PatternFill("solid", fgColor="2D3748")
_SUB    = PatternFill("solid", fgColor="F0F4F8")

def _border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def _hfont(): return Font(bold=True, color="FFFFFF", size=10)
def _bfont(): return Font(bold=True, size=10)

def _num(cell):
    cell.number_format = '#,##0.00'
    cell.alignment = Alignment(horizontal="right")

def _w(ws, col, width):
    ws.column_dimensions[get_column_letter(col)].width = width

def _status_fill(status: str):
    if status == "Matched":       return _GREEN
    if status == "Minor Difference": return _YELLOW
    return _RED

# ─── Sheet writers ────────────────────────────────────────────────────────────

def _sheet_summary(ws, result: dict, gstin_3b: str, gstin_books: str):
    ws.append(["GSTR-3B vs Books — Reconciliation Summary"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([])
    s = result["summary"]

    rows = [
        ("GSTIN (GSTR-3B)", gstin_3b),
        ("GSTIN (Books)",   gstin_books or "Not detected"),
        ("Periods",         s["months"]),
        ("Months Matched",  s["matched"]),
        ("Minor Differences", s["minor"]),
        ("Mismatches",      s["mismatches"]),
        ("Books Total (₹)", s["books_total"]),
        ("GSTR-3B Total (₹)", s["gstr3b_total"]),
        ("Net Difference (₹)", round(s["books_total"] - s["gstr3b_total"], 2)),
    ]
    if s.get("gstin_warning"):
        rows.append(("⚠ GSTIN Warning", s["gstin_warning"]))

    for label, value in rows:
        ws.append([label, value])
        r = ws.max_row
        ws.cell(r, 1).font = Font(bold=True)
        for c in range(1, 3):
            ws.cell(r, c).border = _border()
        if isinstance(value, float):
            _num(ws.cell(r, 2))

    _w(ws, 1, 30); _w(ws, 2, 22)


def _sheet_monthly(ws, monthly: list):
    ws.freeze_panes = "A3"
    headers = ["Period", "Books (₹)", "GSTR-3B (₹)", "Difference (₹)", "Status"]
    ws.append(headers)
    for ci, h in enumerate(headers, 1):
        c = ws.cell(1, ci)
        c.fill = _HEADER; c.font = _hfont(); c.border = _border()
        c.alignment = Alignment(horizontal="center")

    # One row per period (summed across all RECON_ROWS)
    for p in monthly:
        bk  = sum(r["books"]   for r in p["rows"])
        g3b = sum(r["gstr3b"]  for r in p["rows"])
        diff = round(bk - g3b, 2)
        ws.append([p.get("period_label", p["period"]), bk, g3b, diff, p["overall_status"]])
        ri = ws.max_row
        fill = _status_fill(p["overall_status"])
        for ci in range(1, 6):
            ws.cell(ri, ci).fill = fill
            ws.cell(ri, ci).border = _border()
            if 2 <= ci <= 4:
                _num(ws.cell(ri, ci))

    for ci, w in enumerate([16, 18, 18, 18, 18], 1):
        _w(ws, ci, w)


def _sheet_tax(ws, monthly: list):
    ws.freeze_panes = "A3"
    fields = ["igst", "cgst", "sgst", "cess", "itc", "rcm"]
    headers = ["Period"] + [f.upper() for f in fields] + ["Status"]
    ws.append(headers)
    for ci, h in enumerate(headers, 1):
        c = ws.cell(1, ci)
        c.fill = _HEADER; c.font = _hfont(); c.border = _border()
        c.alignment = Alignment(horizontal="center")

    desc_map = {r["description"]: r for rows in [p["rows"] for p in monthly] for r in rows}
    for p in monthly:
        row_by_desc = {r["description"]: r for r in p["rows"]}
        label_map = {
            "igst": "IGST", "cgst": "CGST", "sgst": "SGST",
            "cess": "Cess", "itc": "ITC (Input Tax Credit)", "rcm": "RCM (Reverse Charge)"
        }
        row_data = [p.get("period_label", p["period"])]
        for f in fields:
            lbl = label_map[f]
            r = row_by_desc.get(lbl, {})
            row_data.append(r.get("difference", 0.0))
        row_data.append(p["overall_status"])
        ws.append(row_data)
        ri = ws.max_row
        fill = _status_fill(p["overall_status"])
        for ci in range(1, len(headers) + 1):
            ws.cell(ri, ci).fill = fill
            ws.cell(ri, ci).border = _border()
            if 2 <= ci <= len(fields) + 1:
                _num(ws.cell(ri, ci))

    for ci, w in enumerate([16] + [14]*len(fields) + [18], 1):
        _w(ws, ci, w)


def _sheet_exceptions(ws, exceptions: list):
    if not exceptions:
        ws.append(["No mismatches — all periods matched."])
        return

    ws.freeze_panes = "A3"
    headers = ["Period", "Description", "Books (₹)", "GSTR-3B (₹)", "Difference (₹)", "Status"]
    ws.append(headers)
    for ci, h in enumerate(headers, 1):
        c = ws.cell(1, ci)
        c.fill = _HEADER; c.font = _hfont(); c.border = _border()
        c.alignment = Alignment(horizontal="center")

    for p in exceptions:
        for row in p["rows"]:
            if row["status"] == "Match":
                continue
            ws.append([p.get("period_label", p["period"]), row["description"], row["books"], row["gstr3b"], row["difference"], row["status"]])
            ri = ws.max_row
            fill = _status_fill(row["status"])
            for ci in range(1, 7):
                ws.cell(ri, ci).fill = fill
                ws.cell(ri, ci).border = _border()
                if 3 <= ci <= 5:
                    _num(ws.cell(ri, ci))

    for ci, w in enumerate([16, 28, 16, 16, 16, 18], 1):
        _w(ws, ci, w)


def _sheet_audit(ws, audit: dict):
    ws.append(["Extraction Audit"])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append([])

    ws.append(["Sheets Detected"])
    ws.cell(ws.max_row, 1).font = _bfont()
    for s in audit.get("sheets_detected", []):
        ws.append([s.get("sheet",""), s.get("type","unknown")])

    ws.append([])
    ws.append(["Skipped Sheets"])
    ws.cell(ws.max_row, 1).font = _bfont()
    for s in audit.get("skipped_sheets", []):
        ws.append([s])

    ws.append([])
    ws.append(["Columns Detected per Sheet"])
    ws.cell(ws.max_row, 1).font = _bfont()
    for sheet, cols in audit.get("columns_detected", {}).items():
        ws.append([sheet])
        for field, col in cols.items():
            ws.append(["", field, col])

    _w(ws, 1, 28); _w(ws, 2, 22); _w(ws, 3, 22)


# ─── Public: generate Excel ───────────────────────────────────────────────────

def generate_gstr3b_books_excel(
    result:       dict,
    output_path:  str,
    gstin_3b:     str = "",
    gstin_books:  str = "",
) -> str:
    wb = Workbook()
    wb.remove(wb.active)

    ws1 = wb.create_sheet("Summary")
    _sheet_summary(ws1, result, gstin_3b, gstin_books)

    ws2 = wb.create_sheet("Monthly Comparison")
    _sheet_monthly(ws2, result["monthly"])

    ws3 = wb.create_sheet("Tax Comparison")
    _sheet_tax(ws3, result["monthly"])

    ws4 = wb.create_sheet("Exceptions")
    _sheet_exceptions(ws4, result["exceptions"])

    ws5 = wb.create_sheet("Extraction Audit")
    _sheet_audit(ws5, result["summary"].get("audit", {}))

    wb.save(output_path)
    logger.info(f"GSTR-3B vs Books Excel saved: {output_path}")
    return output_path