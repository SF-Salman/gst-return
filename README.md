# GST Reconciler — Web Application

A full-stack web application for extracting, viewing, and reconciling Indian GST returns (GSTR-1, GSTR-2B, GSTR-3B). Combines a FastAPI backend with a React SPA served from the same single service.

---

## What it does

**Upload & Extract**
Upload GSTR-1 or GSTR-3B returns as PDF or JSON. The app extracts all fields into a structured, categorised summary that you can browse table-by-table and export as a formatted Excel workbook.

**Reconcile**
Three reconciliation modules are available, each with downloadable Excel reports:

| Module | Left side | Right side |
|---|---|---|
| GSTR-1 vs GSTR-3B | GSTR-1 PDF/JSON | GSTR-3B PDF/JSON |
| GSTR-3B vs Books | GSTR-3B PDF (single or multi-month) | Books Excel/CSV |
| GSTR-2B vs Books | GSTR-2B Excel (1–12 months) | Books Excel/CSV |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11 · FastAPI · pdfplumber · openpyxl · rapidfuzz |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS |
| Deployment | Docker (multi-stage build, single service) |

---

## Project structure

```
.
├── backend/
│   ├── api/
│   │   └── main.py              # All API endpoints
│   ├── core/
│   │   ├── books_extractor.py   # Books Excel/CSV parser
│   │   ├── gstr1_vs_3b.py       # GSTR-1 vs GSTR-3B reconciliation
│   │   ├── gstr2b_extractor.py  # GSTR-2B Excel parser
│   │   ├── gstr2b_vs_books.py   # GSTR-2B vs Books reconciliation
│   │   ├── gstr3b_books.py      # GSTR-3B vs Books reconciliation
│   │   ├── reconciliation.py    # Invoice-level fuzzy matching engine
│   │   └── models.py            # Shared type definitions
│   └── schemas/
│       ├── gstr1.json           # GSTR-1 field schema (drives viewer + export)
│       └── gstr3b.json          # GSTR-3B field schema
├── frontend/
│   └── src/
│       ├── App.tsx              # Upload & extraction module
│       └── components/
│           ├── ReconciliationPage.tsx   # All three reconciliation tabs
│           └── ExtractedDataViewer.tsx  # Shared table viewer component
├── gstr1.py                     # Standalone GSTR-1 PDF/JSON extractor
├── gstr3b.py                    # Standalone GSTR-3B PDF extractor
└── json_import.py               # Official GSTN JSON importer
```

---

## Running locally

### Prerequisites

- Python 3.11
- Node 18+

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend dev server

```bash
cd frontend
npm ci
npm run dev
```

Create `frontend/.env.development` with:
```
VITE_API_BASE=http://127.0.0.1:8000
```

Open `http://localhost:5173` (dev) or `http://127.0.0.1:8000` (backend-served SPA).

### Backend-served SPA (no dev server)

```bash
cd frontend && npm run build
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

### Docker

```bash
docker compose build
docker compose up -d
```

Open `http://localhost:8000/`.

---

## Key API endpoints

### Extraction
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/gstr3b/pdf` | Extract GSTR-3B from PDF |
| `POST` | `/api/gstr1/pdf` | Extract GSTR-1 from PDF |
| `POST` | `/api/gstr3b/json` | Extract GSTR-3B from GSTN JSON |
| `POST` | `/api/gstr1/json` | Extract GSTR-1 from GSTN JSON |
| `POST` | `/api/gstr2b/json` | Extract GSTR-2B from GSTN JSON |
| `POST` | `/api/summarize` | Build categorised table summary from extracted records |
| `POST` | `/api/tables_excel` | Export structured multi-sheet Excel from extracted records |
| `POST` | `/api/excel` | Export flat Excel from extracted records |

### Reconciliation
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/reconcile/gstr1-3b/from-pdf` | Reconcile GSTR-1 vs GSTR-3B (PDF uploads) |
| `POST` | `/api/reconcile/gstr1-3b/excel` | Download GSTR-1 vs GSTR-3B Excel report |
| `POST` | `/api/reconcile/gstr3b-books` | Reconcile GSTR-3B vs Books |
| `POST` | `/api/reconcile/gstr3b-books/excel` | Download GSTR-3B vs Books Excel report |
| `GET`  | `/api/reconcile/gstr3b-books/template` | Download blank Books template |
| `POST` | `/api/reconcile/gstr2b-books` | Reconcile GSTR-2B vs Books (1–12 months) |
| `POST` | `/api/reconcile/gstr2b-books/excel` | Download GSTR-2B vs Books Excel report |
| `GET`  | `/api/reconcile/gstr2b-books/template` | Download blank Books template |

Interactive API docs: `http://127.0.0.1:8000/docs`

---

## Books file format

Both GSTR-3B vs Books and GSTR-2B vs Books use the same Books upload format. Download a blank template from either reconciliation tab. The required columns are:

| Column | Values / Notes |
|---|---|
| `Month` | `Apr-25`, `May-25`, … `Mar-26` |
| `Voucher Date` | `DD-MM-YYYY` |
| `Voucher No` | Any string |
| `Ledger` | Ledger/account name |
| `Category` | `OUTPUT` · `ITC` · `RCM` · `REVERSAL` · `EXEMPT` |
| `Taxable Value` | Numeric |
| `IGST` | Numeric |
| `CGST` | Numeric |
| `SGST` | Numeric |
| `CESS` | Numeric |
| `Type` | Any label (e.g. `B2B`, `B2C`, `Import`) |
| `Remarks` | Optional notes |

A single Books file works for both GSTR-3B and GSTR-2B reconciliation — the `Category` column determines which rows each module uses (`OUTPUT`/`RCM` for GSTR-3B, `ITC`/`REVERSAL` for GSTR-2B).

---

## Reconciliation status codes

| Status | Meaning |
|---|---|
| `MATCH` | Difference ≤ ₹1 |
| `WARNING` | Difference ≤ ₹100 |
| `MISMATCH` | Difference > ₹100 |
| `MONTH_MISSING` | Period present in one source only |

---

## CLI (optional)

```bash
# Extract GSTR-1 from a folder of PDFs
python gstr1.py --input /path/to/pdfs --output output.xlsx --format pdf

# Extract from GSTN JSON files
python gstr1.py --input /path/to/jsons --output output.xlsx --format json
```

---

## Disclaimer

This tool is for informational purposes only. Always verify extracted data against official GSTN portal records before making any filing decisions. The developers are not liable for errors or omissions in extracted data.
