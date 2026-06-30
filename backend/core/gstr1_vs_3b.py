import logging
import datetime
from typing import Dict, Any, List

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# ─── Tolerance ────────────────────────────────────────────────────────────────

AMOUNT_TOLERANCE = 1.0


# ─── Row definitions (section, description) ──────────────────────────────────
# Each tuple: (data_key, section_ref, description)
# These are the SAME rows shown in the monthly detail table.

RECON_ROWS = [
    ("outward_taxable_value", "3.1(a)", "Outward Taxable Value"),
    ("outward_igst",          "3.1(a)", "IGST"),
    ("outward_cgst",          "3.1(a)", "CGST"),
    ("outward_sgst",          "3.1(a)", "SGST"),
    ("outward_cess",          "3.1(a)", "Cess"),
    ("zero_rated_value",      "3.1(b)", "Exports / Zero Rated Value"),
    ("zero_rated_igst",       "3.1(b)", "Exports IGST"),
    ("nil_exempt_value",      "3.1(c)", "Nil / Exempt Supplies"),
    ("reverse_charge_value",  "3.1(d)", "Reverse Charge Value"),
    ("reverse_charge_igst",   "3.1(d)", "Reverse Charge IGST"),
    ("reverse_charge_cgst",   "3.1(d)", "Reverse Charge CGST"),
    ("reverse_charge_sgst",   "3.1(d)", "Reverse Charge SGST"),
]

# Human-readable description list (used for column headers in annual sheet)
ROW_DESCRIPTIONS = [desc for _, _, desc in RECON_ROWS]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_float(value) -> float:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return round(float(value or 0), 2)
    except (ValueError, TypeError):
        return 0.0


def normalize_gstr1_summary(gstr1_data: dict) -> dict:
    """Map GSTR-1 extracted fields to the RECON_ROWS keys."""
    sf = safe_float
    return {
        "outward_taxable_value": sf(gstr1_data.get("4A_Value", 0)) + sf(gstr1_data.get("7_Value", 0)),
        "outward_igst":          sf(gstr1_data.get("4A_IGST", 0))  + sf(gstr1_data.get("7_IGST", 0)),
        "outward_cgst":          sf(gstr1_data.get("4A_CGST", 0))  + sf(gstr1_data.get("7_CGST", 0)),
        "outward_sgst":          sf(gstr1_data.get("4A_SGST", 0))  + sf(gstr1_data.get("7_SGST", 0)),
        "outward_cess":          sf(gstr1_data.get("4A_Cess", 0))  + sf(gstr1_data.get("7_Cess", 0)),
        "zero_rated_value":      sf(gstr1_data.get("6A_Value", 0)) + sf(gstr1_data.get("6B_Value", 0)),
        "zero_rated_igst":       sf(gstr1_data.get("6A_IGST", 0))  + sf(gstr1_data.get("6B_IGST", 0)),
        "nil_exempt_value":      sf(gstr1_data.get("8_Total", 0)),
        "reverse_charge_value":  sf(gstr1_data.get("4B_Value", 0)),
        "reverse_charge_igst":   sf(gstr1_data.get("4B_IGST", 0)),
        "reverse_charge_cgst":   sf(gstr1_data.get("4B_CGST", 0)),
        "reverse_charge_sgst":   sf(gstr1_data.get("4B_SGST", 0)),
    }


def extract_gstr3b_summary(gstr3b_data: dict) -> dict:
    """Map GSTR-3B extracted fields to the RECON_ROWS keys."""
    sf = safe_float
    return {
        "outward_taxable_value": sf(gstr3b_data.get("outward_taxable_value", 0)),
        "outward_igst":          sf(gstr3b_data.get("outward_igst", 0)),
        "outward_cgst":          sf(gstr3b_data.get("outward_cgst", 0)),
        "outward_sgst":          sf(gstr3b_data.get("outward_sgst", 0)),
        "outward_cess":          sf(gstr3b_data.get("outward_cess", 0)),
        "zero_rated_value":      sf(gstr3b_data.get("zero_rated_value", 0)),
        "zero_rated_igst":       sf(gstr3b_data.get("zero_rated_igst", 0)),
        "nil_exempt_value":      sf(gstr3b_data.get("nil_exempt_value", 0)),
        "reverse_charge_value":  sf(gstr3b_data.get("inward_reverse_charge_value", 0)),
        "reverse_charge_igst":   sf(gstr3b_data.get("inward_reverse_charge_igst", 0)),
        "reverse_charge_cgst":   sf(gstr3b_data.get("inward_reverse_charge_cgst", 0)),
        "reverse_charge_sgst":   sf(gstr3b_data.get("inward_reverse_charge_sgst", 0)),
    }


# ─── Core reconciliation ──────────────────────────────────────────────────────

def reconcile_gstr1_vs_gstr3b(
    gstr1_data: dict,
    gstr3b_data: dict,
    period: str = None,
) -> Dict[str, Any]:
    """
    Compare GSTR-1 and GSTR-3B for one period.
    Returns a dict with `rows` (list matching RECON_ROWS order),
    `overall_status`, `total_variance`, `gstin`, and `period`.
    """
    g1  = normalize_gstr1_summary(gstr1_data)
    g3b = extract_gstr3b_summary(gstr3b_data)

    rows = []
    total_variance = 0.0

    for key, section, description in RECON_ROWS:
        g1_val  = g1.get(key, 0.0)
        g3b_val = g3b.get(key, 0.0)
        diff    = round(g3b_val - g1_val, 2)
        status  = "Match" if abs(diff) <= AMOUNT_TOLERANCE else "Mismatch"
        total_variance += abs(diff)
        rows.append({
            "section":     section,
            "description": description,
            "gstr1":       g1_val,
            "gstr3b":      g3b_val,
            "difference":  diff,
            "status":      status,
        })

    # Backward-compat summary_comparison dict keyed by description
    summary_comparison = {r["description"]: r for r in rows}

    return {
        "period":             period or datetime.datetime.now().strftime("%b-%Y"),
        "gstin":              gstr1_data.get("GSTIN") or gstr3b_data.get("gstin", ""),
        "rows":               rows,
        "summary_comparison": summary_comparison,
        "overall_status":     "Matched" if total_variance <= 10 else "Mismatch",
        "total_variance":     round(total_variance, 2),
    }


# ─── Excel styles ─────────────────────────────────────────────────────────────

_GREEN  = PatternFill("solid", fgColor="D6F5D6")
_RED    = PatternFill("solid", fgColor="FFD6D6")
_HEADER = PatternFill("solid", fgColor="2D3748")
_SUB    = PatternFill("solid", fgColor="F0F4F8")
_TOTAL  = PatternFill("solid", fgColor="E2E8F0")

def _border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def _hdr_font(white=True):
    return Font(bold=True, color="FFFFFF" if white else "1A1A1A", size=10)

def _num_fmt(cell):
    cell.number_format = '#,##0.00'
    cell.alignment     = Alignment(horizontal="right")

def _set_col_width(ws, col_idx, width):
    ws.column_dimensions[get_column_letter(col_idx)].width = width


# ─── Monthly sheet writer ─────────────────────────────────────────────────────

def _write_period_sheet(ws, result: dict):
    """
    Write one period's full row-by-row reconciliation to a worksheet.
    Columns: Section | Description | GSTR-1 | GSTR-3B | Difference | Status
    """
    ws.freeze_panes = "A4"

    # Title
    ws.append([f"GSTR-1 vs GSTR-3B Reconciliation  —  {result['period']}"])
    ws["A1"].font = Font(bold=True, size=12, color="1A1A1A")
    if result.get("gstin"):
        ws.append([f"GSTIN: {result['gstin']}"])
        ws["A2"].font = Font(italic=True, size=10, color="555555")
    else:
        ws.append([])
    ws.append([])  # blank spacer

    # Header row
    headers = ["Section", "Description", "GSTR-1 (₹)", "GSTR-3B (₹)", "Difference (₹)", "Status"]
    ws.append(headers)
    hrow = ws.max_row
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(hrow, ci)
        cell.fill      = _HEADER
        cell.font      = _hdr_font()
        cell.border    = _border()
        cell.alignment = Alignment(horizontal="center" if ci in (1, 6) else "right" if ci >= 3 else "left")

    # Data rows
    prev_section = None
    for row in result.get("rows", []):
        section_changed = row["section"] != prev_section
        prev_section = row["section"]

        ws.append([
            row["section"],
            row["description"],
            row["gstr1"],
            row["gstr3b"],
            row["difference"],
            row["status"],
        ])
        r = ws.max_row
        fill = _GREEN if row["status"] == "Match" else _RED

        for ci in range(1, 7):
            cell = ws.cell(r, ci)
            cell.fill   = fill
            cell.border = _border()
            cell.alignment = Alignment(horizontal="right" if ci >= 3 else "left")
            if ci >= 3 and ci <= 5:
                _num_fmt(cell)
            if ci == 1 and section_changed:
                cell.font = Font(bold=True, size=9)

    # Total variance footer
    ws.append([])
    ws.append(["", "Total Variance", "", "", result.get("total_variance", 0),
               result.get("overall_status", "")])
    r = ws.max_row
    fill = _GREEN if result.get("overall_status") == "Matched" else _RED
    for ci in range(1, 7):
        cell = ws.cell(r, ci)
        cell.fill   = fill
        cell.font   = Font(bold=True)
        cell.border = _border()
        if ci == 5:
            _num_fmt(cell)

    # Column widths
    for ci, w in enumerate([10, 32, 18, 18, 18, 12], 1):
        _set_col_width(ws, ci, w)


# ─── Annual summary sheet writer ──────────────────────────────────────────────

def _write_annual_sheet(ws, periods: list):
    """
    Write an annual summary sheet where every row from RECON_ROWS
    becomes a column, giving a full picture across all months.

    Layout:
      Row 1: Title
      Row 2: blank
      Row 3: Column headers — Period | GSTIN | [all RECON_ROW descriptions x3 (G1/3B/Diff)] | Total Variance | Status
      Row 4+: One row per period
      Last row: Annual totals
    """
    ws.freeze_panes = "A4"

    # Title
    ws.append(["GSTR-1 vs GSTR-3B  —  Annual Summary"])
    ws["A1"].font = Font(bold=True, size=13, color="1A1A1A")
    ws.append([])

    # Build header groups:
    # Fixed cols: Period, GSTIN
    # For each RECON_ROW: GSTR-1, GSTR-3B, Diff  (3 sub-columns)
    # Final: Total Variance, Status

    fixed_headers   = ["Period", "GSTIN"]
    row_desc_cols   = []   # (description, col_type) where col_type in G1/3B/Diff
    for _, _, desc in RECON_ROWS:
        row_desc_cols.append((desc, "GSTR-1"))
        row_desc_cols.append((desc, "GSTR-3B"))
        row_desc_cols.append((desc, "Diff"))
    tail_headers = ["Total Variance (₹)", "Status"]

    all_headers = fixed_headers + [f"{desc} ({t})" for desc, t in row_desc_cols] + tail_headers

    ws.append(all_headers)
    hrow = ws.max_row
    n_cols = len(all_headers)

    for ci in range(1, n_cols + 1):
        cell = ws.cell(hrow, ci)
        cell.fill      = _HEADER
        cell.font      = _hdr_font()
        cell.border    = _border()
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    ws.row_dimensions[hrow].height = 32  # taller header for wrapped text

    # Data rows
    annual_totals = {key: {"gstr1": 0.0, "gstr3b": 0.0, "difference": 0.0}
                     for key, _, _ in RECON_ROWS}
    annual_variance = 0.0

    for p in periods:
        by_desc = {r["description"]: r for r in p.get("rows", [])}
        row_data = [p.get("period", ""), p.get("gstin", "")]

        for _, _, desc in RECON_ROWS:
            r = by_desc.get(desc, {})
            g1_val  = r.get("gstr1", 0.0)
            g3b_val = r.get("gstr3b", 0.0)
            diff    = r.get("difference", 0.0)
            row_data += [g1_val, g3b_val, diff]
            annual_totals[next(k for k, _, d in RECON_ROWS if d == desc)]["gstr1"]      += g1_val
            annual_totals[next(k for k, _, d in RECON_ROWS if d == desc)]["gstr3b"]     += g3b_val
            annual_totals[next(k for k, _, d in RECON_ROWS if d == desc)]["difference"] += diff

        variance = p.get("total_variance", 0.0)
        annual_variance += variance
        row_data += [variance, p.get("overall_status", "")]

        ws.append(row_data)
        r_idx = ws.max_row
        is_clean = p.get("overall_status") == "Matched"
        row_fill = _GREEN if is_clean else _RED

        for ci in range(1, n_cols + 1):
            cell = ws.cell(r_idx, ci)
            cell.fill   = row_fill
            cell.border = _border()
            # Number format for numeric columns (cols 3 onwards, except last col = status)
            if ci >= 3 and ci < n_cols:
                _num_fmt(cell)

    # Annual totals footer
    totals_row = ["Annual Total", ""]
    for key, _, _ in RECON_ROWS:
        totals_row += [
            round(annual_totals[key]["gstr1"], 2),
            round(annual_totals[key]["gstr3b"], 2),
            round(annual_totals[key]["difference"], 2),
        ]
    all_matched = all(p.get("overall_status") == "Matched" for p in periods)
    totals_row += [round(annual_variance, 2), "Matched" if all_matched else "Mismatch"]

    ws.append(totals_row)
    t_idx = ws.max_row
    t_fill = _GREEN if all_matched else _RED
    for ci in range(1, n_cols + 1):
        cell = ws.cell(t_idx, ci)
        cell.fill   = t_fill
        cell.font   = Font(bold=True)
        cell.border = _border()
        if ci >= 3 and ci < n_cols:
            _num_fmt(cell)

    # Column widths
    _set_col_width(ws, 1, 14)   # Period
    _set_col_width(ws, 2, 22)   # GSTIN
    # Each RECON_ROW group = 3 cols (G1, 3B, Diff) × 16
    for i in range(len(RECON_ROWS) * 3):
        _set_col_width(ws, 3 + i, 16)
    _set_col_width(ws, 3 + len(RECON_ROWS) * 3,     16)  # Total Variance
    _set_col_width(ws, 3 + len(RECON_ROWS) * 3 + 1, 12)  # Status


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_excel_report(periods: list, output_path: str) -> str:
    """
    Generate Excel workbook.
    - If multiple periods: Sheet 1 = Annual Summary (all RECON_ROW fields as columns),
      then one sheet per period with full row detail.
    - If single period: just one sheet with full row detail.

    `periods` is a list of reconcile_gstr1_vs_gstr3b() result dicts.
    """
    wb = Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    if len(periods) > 1:
        ws_annual = wb.create_sheet("Annual Summary")
        _write_annual_sheet(ws_annual, periods)

    for p in periods:
        sheet_name = (p.get("period") or "Period")[:31]
        ws = wb.create_sheet(sheet_name)
        _write_period_sheet(ws, p)

    wb.save(output_path)
    logger.info(f"Excel report saved: {output_path}")
    return output_path