# GST Returns Extractor (Web + API)

Enhanced tool for extracting comprehensive data from GSTR-1 and GSTR-3B returns in both PDF and JSON formats. Now ships a single backend service that also serves the React SPA.

## 🚀 New Features (v2.0)

- ✅ **JSON Import Support**: Import data from official GSTN JSON files
- ✅ **Comprehensive Field Coverage**: 200+ fields for GSTR-1, 150+ fields for GSTR-3B
- ✅ **Dual Format Support**: Process both PDF and JSON files
- ✅ **Enhanced Validation**: Built-in data quality checks and scoring
- ✅ **Batch Processing**: Process multiple files in one go
- ✅ **Web & CLI Interfaces**: Use via browser or command line

## 📋 Features

### Supported Formats
- **PDF**: Extract from PDF returns downloaded from GSTN portal
- **JSON**: Import from official GSTN JSON format

### Supported Returns
- **GSTR-1**: All tables (4A-19) including B2B, B2CL, Exports, SEZ, HSN, amendments
- **GSTR-3B**: All sections including supplies, ITC, exempt supplies, payment details

### Data Extraction
- **200+ fields** for GSTR-1 (all tables and sub-categories)
- **150+ fields** for GSTR-3B (complete coverage)
- Automatic validation and quality scoring
- Summary statistics and calculated totals

## 🔧 Installation & Setup

### Prerequisites
- Python 3.11
- Node 18.x (for building the frontend)

### Install backend dependencies
```bash
pip install -r requirements.txt
```

### Install frontend dependencies
```bash
cd frontend
npm ci
```

## 💻 Running

### Dev (recommended)
- Backend API:
```bash
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```
- Frontend dev server:
```bash
cd frontend
npm run dev
```
Optional: create `frontend/.env.development` with `VITE_API_BASE=http://127.0.0.1:8000` to ensure the dev app points to the local backend.

### Backend-served SPA (no dev server)
Build the frontend, then run the backend which serves the SPA from `frontend/dist`:
```bash
cd frontend && npm run build
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/`.

### Docker (single service)
```bash
docker compose build
docker compose up -d
```
Open `http://localhost:8000/` (SPA) and `http://localhost:8000/docs` (API docs).

## 🧩 Environment
- Frontend uses `VITE_API_BASE` to select the API endpoint.
  - Dev: set `VITE_API_BASE=http://127.0.0.1:8000` in `frontend/.env.development`.
  - Prod: default same-origin (no env var required), or set `VITE_API_BASE=https://yourdomain`.
  - See `frontend/.env.example`.

## 🛠 CLI (optional)

#### Process PDF files:
```bash
python gstr1.py --input /path/to/pdfs --output output.xlsx --format pdf
```

#### Process JSON files:
```bash
python gstr1.py --input /path/to/jsons --output output.xlsx --format json
```

#### With verbose logging:
```bash
python gstr1.py --input /path/to/files --output output.xlsx --format pdf --verbose
```

### 3. Python API

#### Extract from PDF:
```python
from gstr1 import extract_gstr1_data

data = extract_gstr1_data('path/to/gstr1.pdf')
```

#### Import from JSON:
```python
from json_import import extract_gstr1_from_json, load_json_file

json_data = load_json_file('path/to/gstr1.json')
data = extract_gstr1_from_json(json_data)
```

## 📊 Output Format

### Excel Sheets

#### GSTR-1:
1. **GSTR1_Data**: Complete extracted data (200+ fields)
2. **Summary_Statistics**: Key metrics and totals
3. **Validation_Results**: Data quality and validation status

#### GSTR-3B:
1. **GSTR-3B Data**: Complete extracted data (150+ fields)

## 📖 Documentation

- **USAGE.md**: Comprehensive usage guide with examples
- **ENHANCEMENT_SUMMARY.md**: Details of v2.0 enhancements
- **GSTR1_Comprehensive_Fields.md**: Complete field reference for GSTR-1
- **GSTR3B_Comprehensive_Fields.md**: Complete field reference for GSTR-3B

## ✨ Key Benefits

1. **Complete Data Capture**: All fields extracted, no data loss
2. **Flexible Input**: Support for both PDF and JSON formats
3. **Batch Processing**: Process multiple files efficiently
4. **Quality Assurance**: Built-in validation and quality scoring
5. **User-Friendly**: Web interface and command-line options

## ⚠️ Disclaimer

This tool is for informational purposes only! Always verify extracted data with official GSTN portal records before making filing decisions. The developers are not liable for any errors or omissions in extracted data.

## 📝 Version History

### v2.0 (Current)
- Added JSON import support
- Enhanced field extraction (200+ fields for GSTR-1, 150+ for GSTR-3B)
- Added comprehensive validation
- Improved error handling
- Enhanced documentation

### v1.0
- Initial PDF extraction
- Basic field extraction
- Excel export
