from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import tempfile
import os
import io
import json
import logging
import datetime
import decimal
import re
from collections import OrderedDict, defaultdict

from gstr3b import parse_gstr3b, create_excel
from gstr1 import extract_gstr1_data
from json_import import extract_gstr1_from_json, extract_gstr3b_from_json


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="GST Returns Extractor API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lightweight health endpoint for orchestration and uptime checks
@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

# Serve frontend (Vite build) as static SPA
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
try:
    if os.path.exists(DIST_DIR):
        # html=True enables SPA fallback to index.html for unknown paths
        app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
        logger.info(f"Mounted frontend dist at: {DIST_DIR}")
    else:
        logger.warning(f"Frontend dist not found at {DIST_DIR}; static SPA serving disabled.")
except Exception as e:
    logger.exception(f"Failed to mount StaticFiles for frontend: {e}")


def _json_safe(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        # Prefer float for numeric fields; fallback to string if NaN/Inf
        try:
            return float(value)
        except Exception:
            return str(value)
    if isinstance(value, bytes):
        # Represent bytes as hex string to avoid binary issues
        return value.hex()
    return value


def to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    return _json_safe(obj)


@app.post("/api/gstr3b/pdf")
async def parse_gstr3b_pdf(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        data = parse_gstr3b(tmp_path)
        data['filename'] = file.filename
        os.unlink(tmp_path)
        return JSONResponse(content=to_jsonable(data))
    except Exception as e:
        logger.exception("Failed to parse GSTR-3B PDF")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/gstr1/pdf")
async def parse_gstr1_pdf(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        data = extract_gstr1_data(tmp_path)
        data['filename'] = file.filename
        os.unlink(tmp_path)
        return JSONResponse(content=to_jsonable(data))
    except Exception as e:
        logger.exception("Failed to parse GSTR-1 PDF")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/gstr3b/json")
async def parse_gstr3b_json(payload: dict):
    try:
        data = extract_gstr3b_from_json(payload)
        return JSONResponse(content=to_jsonable(data))
    except Exception as e:
        logger.exception("Failed to parse GSTR-3B JSON")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/gstr1/json")
async def parse_gstr1_json(payload: dict):
    try:
        data = extract_gstr1_from_json(payload)
        return JSONResponse(content=to_jsonable(data))
    except Exception as e:
        logger.exception("Failed to parse GSTR-1 JSON")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/excel")
async def export_excel(records: list[dict]):
    try:
        output: io.BytesIO = create_excel(records)
        output.seek(0)
        headers = {
            "Content-Disposition": "attachment; filename=returns_data.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return StreamingResponse(output, headers=headers)
    except Exception as e:
        logger.exception("Failed to create Excel export")
        return JSONResponse(status_code=500, content={"error": str(e)})


# -----------------------------
# Summarization Helpers & API
# -----------------------------

def _normalize_key(s: str) -> str:
    try:
        return re.sub(r"[^a-z0-9]", "", str(s).lower()).strip()
    except Exception:
        return str(s)

# Treat common sentinel values as missing and provide normalization helpers
def _is_missing_value(s: str) -> bool:
    if s is None:
        return True
    v = str(s).strip().lower()
    return v in ("", "none", "null", "n/a", "na", "-", "—")

def _normalize_category(cat: str, heading: str) -> str:
    cat_str = (cat or "").strip()
    if _is_missing_value(cat_str):
        return (heading or "").strip()
    return cat_str

def _normalize_optional(s: str) -> str | None:
    if s is None:
        return None
    s_str = str(s).strip()
    if _is_missing_value(s_str):
        return None
    return s_str


def _get_period_label(record: dict, return_type: str) -> str:
    # Attempt to derive a user-friendly period label
    # Prefer explicit period strings; fall back to financial year where appropriate
    for k in ("TaxPeriod", "tax_period", "period", "ret_period"):
        v = record.get(k)
        if v:
            return str(v)
    if return_type == "GSTR-1":
        for k in ("FinancialYear", "financial_year", "fy", "year"):
            v = record.get(k)
            if v:
                return str(v)
    # Last resort: filename or index
    return str(record.get("filename", ""))

def _month_order_index(label: str) -> int | None:
    """Return index 0..11 for April..March if label contains a matching month, else None."""
    months = [
        ("april", ["apr", "april"]),
        ("may", ["may"]),
        ("june", ["jun", "june"]),
        ("july", ["jul", "july"]),
        ("august", ["aug", "august"]),
        ("september", ["sep", "sept", "september"]),
        ("october", ["oct", "october"]),
        ("november", ["nov", "november"]),
        ("december", ["dec", "december"]),
        ("january", ["jan", "january"]),
        ("february", ["feb", "february"]),
        ("march", ["mar", "march"]),
    ]
    lc = str(label).lower()
    for i, (_m, syns) in enumerate(months):
        for s in syns:
            if s in lc:
                return i
    return None

def _sort_summary_columns(summary: dict) -> dict:
    """Sort columns (Period/TaxPeriod) April..March and reorder row values accordingly."""
    cols = list(summary.get("columns", []))
    if not cols:
        return summary
    items = [(idx, c, _month_order_index(c)) for idx, c in enumerate(cols)]
    known = [it for it in items if it[2] is not None]
    unknown = [it for it in items if it[2] is None]
    known.sort(key=lambda x: (x[2], x[0]))  # by month index, stable by original index
    order = [idx for idx, _c, _m in known] + [idx for idx, _c, _m in unknown]
    # Apply reorder to columns
    summary["columns"] = [cols[i] for i in order]
    # Apply reorder to values in each row
    for section in summary.get("sections", []):
        for cat in section.get("categories", []):
            if cat.get("subcategories"):
                for sub in cat.get("subcategories", []):
                    for row in sub.get("rows", []):
                        vals = row.get("values", [])
                        row["values"] = [vals[i] if i < len(vals) else None for i in order]
            for row in (cat.get("rows", []) or []):
                vals = row.get("values", [])
                row["values"] = [vals[i] if i < len(vals) else None for i in order]
    return summary


def _load_schema(return_type: str) -> list[dict]:
    """
    Load schema rows from JSON files moved into backend/schemas.
    Supports keys:
      - Headings / Heading -> heading
      - Category -> category
      - Sub Category / Subcategory -> subcategory (optional for GSTR-3B)
      - Field Name / Field / Key -> field_name
      - Field Description / Description / Label -> field_description
      - Column Index / Index / Order -> column_index (optional)
    """
    file_map = {
        "GSTR-1": "gstr1.json",
        "GSTR-3B": "gstr3b.json",
    }
    filename = file_map.get(return_type)
    if not filename:
        raise FileNotFoundError(f"Unknown return type for schema: {return_type}")

    # Prefer backend/schemas, fallback to project root if not found
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    schema_path = os.path.join(base_dir, "schemas", filename)
    if not os.path.exists(schema_path):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        alt_path = os.path.join(project_root, filename)
        if os.path.exists(alt_path):
            schema_path = alt_path
        else:
            raise FileNotFoundError(f"Schema JSON not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows: list[dict] = []
    for item in data if isinstance(data, list) else []:
        def pick(*keys):
            for k in keys:
                v = item.get(k)
                if v is not None:
                    return v
            return None

        heading = pick("Headings", "Heading")
        category = pick("Category", "Table", "Group")
        subcategory = pick("Sub Category", "Subcategory", "Subcat")
        if isinstance(subcategory, str) and _normalize_key(subcategory) in {"none", "null", ""}:
            subcategory = None
        field_name = pick("Field Name", "Field", "Key", "Column Name", "Name")
        field_description = pick("Field Description", "Description", "Label", "Desc")
        column_index_raw = pick("Column Index", "Index", "Order", "Idx", "Column")
        column_index = None
        if column_index_raw is not None and str(column_index_raw).strip() != "":
            try:
                column_index = int(column_index_raw)
            except Exception:
                try:
                    column_index = int(float(column_index_raw))
                except Exception:
                    column_index = None

        if field_name:
            rows.append({
                "heading": heading,
                "category": category,
                "subcategory": subcategory,
                "field_name": field_name,
                "field_description": field_description,
                "column_index": column_index,
            })

    return rows


def _build_summary(records: list[dict], schema_rows: list[dict], return_type: str) -> dict:
    # Column labels derived from records
    col_labels = [_get_period_label(r, return_type) for r in records]

    # Precompute normalized key maps per record for robust lookup
    normalized_records = []
    for r in records:
        norm_map = { _normalize_key(k): k for k in r.keys() }
        normalized_records.append((r, norm_map))

    def lookup_value(rec: dict, norm_map: dict, field_name: str):
        # Direct match first
        if field_name in rec:
            return rec.get(field_name)
        # Normalized match
        nk = _normalize_key(field_name)
        actual_key = norm_map.get(nk)
        if actual_key is not None:
            return rec.get(actual_key)
        # Try simple underscore/space variations
        variants = {
            field_name.replace(" ", "_"),
            field_name.replace("_", " "),
            field_name.lower(),
            field_name.upper(),
        }
        for v in variants:
            if v in rec:
                return rec.get(v)
        return None

    # Group by heading -> category -> optional subcategory
    sections = OrderedDict()
    for row in schema_rows:
        heading = row.get("heading") or ""
        # Normalize category names to match preferences schema (fallback to heading when empty)
        category = _normalize_category(row.get("category"), heading)
        subcategory = row.get("subcategory") or None
        field_name = row.get("field_name") or ""
        field_description = row.get("field_description") or field_name
        column_index = row.get("column_index")

        if heading not in sections:
            sections[heading] = {"heading": heading, "categories": OrderedDict()}
        cats = sections[heading]["categories"]
        if category not in cats:
            cats[category] = {"name": category, "rows": [], "subcategories": OrderedDict()}
        cat_obj = cats[category]

        # Collect values for this field across all records
        values = []
        for rec, nm in normalized_records:
            values.append(lookup_value(rec, nm, field_name))

        row_obj = {
            "description": field_description,
            "key": field_name,
            "column_index": column_index,
            "values": values,
        }

        if return_type == "GSTR-3B" and subcategory:
            subcats = cat_obj["subcategories"]
            if subcategory not in subcats:
                subcats[subcategory] = {"name": subcategory, "rows": []}
            subcats[subcategory]["rows"].append(row_obj)
        else:
            cat_obj["rows"].append(row_obj)

    # Sort rows within each category/subcategory by column_index if available
    for heading_obj in sections.values():
        for cat_key, cat_obj in heading_obj["categories"].items():
            if cat_obj["rows"]:
                cat_obj["rows"].sort(key=lambda r: (r["column_index"] is None, r["column_index"] if r["column_index"] is not None else 0))
            subcats = cat_obj.get("subcategories") or {}
            for sub_key in list(subcats.keys()):
                sub = subcats[sub_key]
                sub["rows"].sort(key=lambda r: (r["column_index"] is None, r["column_index"] if r["column_index"] is not None else 0))

    # Convert OrderedDict to lists for JSON
    sections_list = []
    for heading_obj in sections.values():
        cats_list = []
        for cat_obj in heading_obj["categories"].values():
            item = {"name": cat_obj["name"]}
            # Attach rows or subcategories
            if return_type == "GSTR-3B" and cat_obj.get("subcategories"):
                subs_list = []
                for sub in cat_obj["subcategories"].values():
                    subs_list.append({"name": sub["name"], "rows": sub["rows"]})
                item["subcategories"] = subs_list
            if cat_obj["rows"]:
                item["rows"] = cat_obj["rows"]
            cats_list.append(item)
        sections_list.append({"heading": heading_obj["heading"], "categories": cats_list})

    summary = {"returnType": return_type, "columns": col_labels, "sections": sections_list}
    return _sort_summary_columns(summary)


@app.post("/api/summarize")
async def summarize(payload: dict):
    try:
        records = payload.get("records") or []
        return_type = payload.get("returnType") or "GSTR-3B"
        selected_categories = payload.get("selectedCategories") or None
        books_values = payload.get("booksValues") or {}
        if not isinstance(records, list):
            return JSONResponse(status_code=400, content={"error": "Invalid records payload"})

        schema_rows = _load_schema(return_type)
        # Filter by selected categories if provided
        if selected_categories and isinstance(selected_categories, list):
            selected_set = {str(c).strip() for c in selected_categories}
            def row_cat(row: dict):
                heading = (row.get("heading") or "").strip()
                cat = (row.get("category") or "").strip()
                return _normalize_category(cat, heading)
            schema_rows = [row for row in schema_rows if row_cat(row) in selected_set]
        summary = _build_summary(records, schema_rows, return_type)
        return JSONResponse(content=to_jsonable(summary))
    except Exception as e:
        logger.exception("Failed to summarize records")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/schema_categories")
async def schema_categories():
    try:
        result = {}
        for rt in ("GSTR-1", "GSTR-3B"):
            rows = _load_schema(rt)
            cats_set = set()
            for row in rows:
                heading = (row.get("heading") or "").strip()
                cat = _normalize_category(row.get("category"), heading)
                if cat:
                    cats_set.add(cat)
            cats = sorted(cats_set)
            result[rt] = {"categories": cats}
        return JSONResponse(content=to_jsonable(result))
    except Exception as e:
        logger.exception("Failed to load schema categories")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/schema_structure")
async def schema_structure():
    """Return schema organized by heading -> categories -> subcategories preserving order."""
    try:
        def build(rt: str):
            rows = _load_schema(rt)
            sections: "OrderedDict[str, OrderedDict[str, OrderedDict[str, bool]]]" = OrderedDict()
            for r in rows:
                heading = (r.get("heading") or "").strip()
                category = _normalize_category(r.get("category"), heading)
                subcat = r.get("subcategory")
                if isinstance(subcat, str):
                    subcat = _normalize_optional(subcat)
                if heading not in sections:
                    sections[heading] = OrderedDict()
                cats = sections[heading]
                if category not in cats:
                    cats[category] = OrderedDict()
                if subcat:
                    if subcat not in cats[category]:
                        cats[category][subcat] = True

            # Convert to list form preserving order
            out = []
            for heading_name, cats in sections.items():
                cat_list = []
                for cname, subdict in cats.items():
                    subs = list(subdict.keys())
                    item = {"name": cname}
                    if subs:
                        item["subcategories"] = subs
                    cat_list.append(item)
                out.append({"heading": heading_name, "categories": cat_list})
            return out

        return JSONResponse(content={
            "GSTR-1": build("GSTR-1"),
            "GSTR-3B": build("GSTR-3B"),
        })
    except Exception as e:
        logger.exception("Failed to build schema structure")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/tables_excel")
async def tables_excel(payload: dict):
    """Generate an Excel with all multi-level tables in a single sheet."""
    try:
        from openpyxl import Workbook
        from openpyxl.utils import get_column_letter
        from openpyxl.styles import Font
        from openpyxl.worksheet.table import Table, TableStyleInfo

        records = payload.get("records") or []
        return_type = payload.get("returnType") or "GSTR-3B"
        selected_categories = payload.get("selectedCategories") or None
        if not isinstance(records, list):
            return JSONResponse(status_code=400, content={"error": "Invalid records payload"})

        schema_rows = _load_schema(return_type)
        if selected_categories and isinstance(selected_categories, list):
            selected_set = {str(c).strip() for c in selected_categories}
            def row_cat(row: dict):
                heading = (row.get("heading") or "").strip()
                cat = (row.get("category") or "").strip()
                return _normalize_category(cat, heading)
            schema_rows = [row for row in schema_rows if row_cat(row) in selected_set]

        # Allow client-side edited summary to override computed values
        summary_override = payload.get("summaryOverride")
        if isinstance(summary_override, dict) and summary_override.get("sections") and summary_override.get("columns"):
            summary = summary_override
        else:
            summary = _build_summary(records, schema_rows, return_type)

        # If categories were provided, ensure the final summary is filtered to match
        if selected_categories and isinstance(selected_categories, list):
            selected_set = {str(c).strip() for c in selected_categories}
            def cat_in_selected(sec_heading: str, cat_name: str):
                return _normalize_category(cat_name or "", sec_heading or "") in selected_set
            filtered_sections = []
            for section in summary.get("sections", []):
                sec_heading = section.get("heading") or ""
                cats = [c for c in section.get("categories", []) if cat_in_selected(sec_heading, c.get("name") or "")]
                # Only keep sections that still have visible categories
                if cats:
                    new_section = dict(section)
                    new_section["categories"] = cats
                    filtered_sections.append(new_section)
            summary["sections"] = filtered_sections

        wb = Workbook()
        ws = wb.active
        ws.title = "Tables"

        # Helper to coerce values to numbers for reliable Excel summation
        def _to_number(val):
            try:
                if val is None:
                    return None
                if isinstance(val, (int, float)):
                    return float(val)
                # Support Decimal
                if isinstance(val, decimal.Decimal):
                    return float(val)
                # Try to parse numeric strings (remove commas, trim)
                if isinstance(val, str):
                    s = val.strip()
                    if s == "":
                        return None
                    s = s.replace(",", "")
                    return float(s)
                return val
            except Exception:
                return val

        # Write tables: each category/subcategory becomes a transposed block
        # Summary columns (Total/Books/Difference) are removed per request; only raw metrics are exported.
        tbl_count = 1
        for section in summary.get("sections", []):
            sec_heading = section.get("heading") or ""
            for cat in section.get("categories", []):
                cat_name = cat.get("name") or ""
                if cat.get("subcategories"):
                    for sub in cat["subcategories"]:
                        title = f"{sec_heading} - {cat_name} - {sub.get('name') or ''}".strip(" -")
                        ws.append([title])
                        rows = sub.get("rows", [])
                        headers = ["Period"] + [ (row.get("description") or row.get("key") or "").strip() for row in rows ]
                        ws.append(headers)
                        cols = summary.get("columns", [])

                        # Data rows: one row per period, values across metrics
                        header_row_idx = ws.max_row
                        # Bold header row and title
                        ws.cell(row=header_row_idx-1, column=1).font = Font(bold=True)
                        for c_idx in range(1, 2 + len(rows)):
                            ws.cell(row=header_row_idx, column=c_idx).font = Font(bold=True)
                        data_start_row = header_row_idx + 1
                        first_metric_col_idx = 2  # Column B
                        last_metric_col_idx = 1 + len(rows)
                        for ci in range(len(cols)):
                            row_vals = [cols[ci]]
                            for r in rows:
                                values = r.get("values", [])
                                val = values[ci] if ci < len(values) else None
                                row_vals.append(_to_number(val))
                            ws.append(row_vals)
                        data_end_row = ws.max_row

                        # Append Total row with SUM formulas (bold)
                        totals_row_idx = data_end_row + 1
                        total_row_vals = ["Total"]
                        for col_idx in range(first_metric_col_idx, last_metric_col_idx + 1):
                            col_letter = get_column_letter(col_idx)
                            total_row_vals.append(f"=SUM({col_letter}{data_start_row}:{col_letter}{data_end_row})")
                        ws.append(total_row_vals)
                        for c_idx in range(1, last_metric_col_idx + 1):
                            ws.cell(row=totals_row_idx, column=c_idx).font = Font(bold=True)

                        # Set number format for data cells and totals
                        for r_idx in range(data_start_row, totals_row_idx + 1):
                            for col_idx in range(first_metric_col_idx, last_metric_col_idx + 1):
                                cell = ws.cell(row=r_idx, column=col_idx)
                                cell.number_format = "#,##0"

                        # Add Excel table styling with borders around the block
                        if last_metric_col_idx >= 1 and totals_row_idx >= header_row_idx:
                            end_letter = get_column_letter(last_metric_col_idx)
                            table_ref = f"A{header_row_idx}:{end_letter}{totals_row_idx}"
                            display_name = f"Table{tbl_count}"
                            tbl_count += 1
                            tab = Table(displayName=display_name, ref=table_ref)
                            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
                            tab.tableStyleInfo = style
                            ws.add_table(tab)

                else:
                    title = f"{sec_heading} - {cat_name}".strip(" -")
                    ws.append([title])
                    rows = cat.get("rows", [])
                    headers = ["Period"] + [ (row.get("description") or row.get("key") or "").strip() for row in rows ]
                    ws.append(headers)
                    cols = summary.get("columns", [])

                    # Data rows
                    header_row_idx = ws.max_row
                    # Bold header row and title
                    ws.cell(row=header_row_idx-1, column=1).font = Font(bold=True)
                    for c_idx in range(1, 2 + len(rows)):
                        ws.cell(row=header_row_idx, column=c_idx).font = Font(bold=True)
                    data_start_row = header_row_idx + 1
                    first_metric_col_idx = 2
                    last_metric_col_idx = 1 + len(rows)
                    start_letter = get_column_letter(first_metric_col_idx)
                    end_letter = get_column_letter(last_metric_col_idx)
                    for ci in range(len(cols)):
                        row_vals = [cols[ci]]
                        for r in rows:
                            values = r.get("values", [])
                            val = values[ci] if ci < len(values) else None
                            row_vals.append(_to_number(val))
                        ws.append(row_vals)
                    data_end_row = ws.max_row

                    # Append Total row with SUM formulas (bold)
                    totals_row_idx = data_end_row + 1
                    total_row_vals = ["Total"]
                    for col_idx in range(first_metric_col_idx, last_metric_col_idx + 1):
                        col_letter = get_column_letter(col_idx)
                        total_row_vals.append(f"=SUM({col_letter}{data_start_row}:{col_letter}{data_end_row})")
                    ws.append(total_row_vals)
                    for c_idx in range(1, last_metric_col_idx + 1):
                        ws.cell(row=totals_row_idx, column=c_idx).font = Font(bold=True)

                    # Set number format for data cells and totals
                    for r_idx in range(data_start_row, totals_row_idx + 1):
                        for col_idx in range(first_metric_col_idx, last_metric_col_idx + 1):
                            cell = ws.cell(row=r_idx, column=col_idx)
                            cell.number_format = "#,##0"

                    # Add Excel table styling with borders around the block
                    if last_metric_col_idx >= 1 and totals_row_idx >= header_row_idx:
                        end_letter = get_column_letter(last_metric_col_idx)
                        table_ref = f"A{header_row_idx}:{end_letter}{totals_row_idx}"
                        display_name = f"Table{tbl_count}"
                        tbl_count += 1
                        tab = Table(displayName=display_name, ref=table_ref)
                        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
                        tab.tableStyleInfo = style
                        ws.add_table(tab)

        # Stream the workbook
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        headers = {
            "Content-Disposition": "attachment; filename=multi_tables.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return StreamingResponse(output, headers=headers)
    except Exception as e:
        logger.exception("Failed to create Tables Excel")
        return JSONResponse(status_code=500, content={"error": str(e)})