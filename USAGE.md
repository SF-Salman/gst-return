# GST Returns Extractor - Usage Guide

## Overview
This tool extracts comprehensive data from GSTR-1 and GSTR-3B returns in both PDF and JSON formats. It supports batch processing and exports data to Excel for easy analysis.

## Features

### Supported Formats
- **PDF**: Extract data from PDF returns downloaded from GSTN portal
- **JSON**: Import data from official GSTN JSON format

### Supported Returns
- **GSTR-1**: All tables (4A through 19), including B2B, B2CL, Exports, SEZ, HSN summaries, and amendments
- **GSTR-3B**: All sections including outward/inward supplies, ITC, exempt supplies, and payment details

### Comprehensive Field Extraction
- **200+ fields** for GSTR-1
- **150+ fields** for GSTR-3B
- Automatic validation and quality scoring
- Summary statistics and totals

## Installation

### Prerequisites
- Python 3.11
- Node 18.x (for frontend development/build)

### Backend setup
```bash
pip install -r requirements.txt
```

### Frontend setup
```bash
cd frontend
npm ci
```

## Usage

### 1. Web App (SPA + FastAPI)

Dev mode:
```bash
# Backend
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev
```
Optionally set `frontend/.env.development`:
```
VITE_API_BASE=http://127.0.0.1:8000
```

Backend-served SPA (no dev server):
```bash
cd frontend && npm run build
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/`.

Docker (single service):
```bash
docker compose build
docker compose up -d
```
Open `http://localhost:8000/`.

### 2. Command Line Interface

#### GSTR-1 Extraction

##### From PDF files:
```bash
python gstr1.py --input /path/to/pdf/directory --output output.xlsx --format pdf
```

##### From JSON files:
```bash
python gstr1.py --input /path/to/json/directory --output output.xlsx --format json
```

##### With verbose logging:
```bash
python gstr1.py --input /path/to/files --output output.xlsx --format pdf --verbose
```

#### Command Line Arguments:
- `--input` or `-i`: Directory containing input files (required)
- `--output` or `-o`: Output Excel file path (required)
- `--format` or `-f`: Input format - 'pdf' or 'json' (default: pdf)
- `--verbose` or `-v`: Enable verbose logging

### 3. Python API

#### GSTR-1 PDF Extraction:
```python
from gstr1 import extract_gstr1_data

# Extract from single PDF
data = extract_gstr1_data('path/to/gstr1.pdf')

# Process directory
from gstr1 import process_directory
process_directory('/path/to/pdfs', 'output.xlsx')
```

#### GSTR-1 JSON Import:
```python
from json_import import extract_gstr1_from_json, load_json_file

# Load JSON file
json_data = load_json_file('path/to/gstr1.json')

# Extract data
data = extract_gstr1_from_json(json_data)
```

#### GSTR-3B JSON Import:
```python
from json_import import extract_gstr3b_from_json, load_json_file

# Load JSON file
json_data = load_json_file('path/to/gstr3b.json')

# Extract data
data = extract_gstr3b_from_json(json_data)
```

## JSON Format Support

### GSTR-1 JSON Structure
The tool supports the official GSTN JSON format with the following sections:
- `b2b`: B2B invoices
- `b2ba`: B2B amended invoices
- `b2cl`: B2C Large invoices
- `b2cs`: B2C Small invoices
- `exp`: Export invoices
- `sez`: SEZ supplies
- `de`: Deemed exports
- `cdnr`: Credit/Debit notes (registered)
- `cdnur`: Credit/Debit notes (unregistered)
- `at`: Advance tax
- `hsn`: HSN summary
- `doc_issue`: Documents issued
- `nil`: Nil rated supplies

### GSTR-3B JSON Structure
The tool supports the official GSTN JSON format with the following sections:
- `sup_details`: Outward supplies details
- `inter_sup`: Inter-state supplies
- `itc_elg`: ITC eligible
- `inward_sup`: Inward supplies
- `intr_details`: Interest and late fee
- `tax_pmt`: Payment of tax

## Output Format

### Excel Sheets

#### For GSTR-1:
1. **GSTR1_Data**: Complete extracted data with all fields
2. **Summary_Statistics**: Key metrics and totals
3. **Validation_Results**: Field validation status and quality scores

#### For GSTR-3B:
1. **GSTR-3B Data**: Complete extracted data with all fields

### Key Fields Extracted

#### GSTR-1 (200+ fields):
- Basic info: GSTIN, Legal Name, ARN, Tax Period, Financial Year
- Table 4A: B2B Regular (Value, IGST, CGST, SGST, Cess)
- Table 4B: B2B Reverse Charge
- Table 5: B2CL
- Tables 6A-6C: Exports, SEZ, Deemed Exports
- Table 7: B2CS
- Table 8: Nil Rated/Exempted
- Tables 9A-9C: Amendments and Credit/Debit Notes
- Tables 10-11: B2C Amendments and Advances
- Table 12: HSN Summary
- Tables 13-15: Documents, E-Commerce, Section 9(5)
- Summary statistics and validation results

#### GSTR-3B (150+ fields):
- Basic info: GSTIN, Legal Name, ARN, Tax Period
- Table 3.1: Outward supplies (Taxable, Zero-rated, Nil, Non-GST)
- Table 3.1.1: Section 9(5) supplies
- Table 3.2: Inter-state supplies
- Table 4: ITC (Available, Reversed, Net)
- Table 5: Exempt supplies
- Table 5.1: Interest and late fee
- Table 6.1: Payment of tax
- HSN summary
- Additional tax details (TDS/TCS)

## Validation and Quality Checks

The tool performs automatic validation:
- **GSTIN format validation**: Ensures 15-character alphanumeric format
- **ARN format validation**: Validates acknowledgement number format
- **Date format validation**: Checks DD/MM/YYYY format
- **Data consistency checks**: Compares calculated totals with reported values
- **Overall quality score**: 0-100% based on validation results

Quality Status:
- EXCELLENT: 80-100%
- GOOD: 60-79%
- FAIR: 40-59%
- POOR: Below 40%

## Error Handling

The tool includes comprehensive error handling:
- Individual file errors don't stop batch processing
- Errors are logged with detailed information
- Failed files are marked in output with error details
- Partial data is saved even if some fields fail to extract

## Logging

Logs are generated with the following information:
- INFO: Successful operations and progress
- WARNING: Missing data or non-critical issues
- ERROR: Failed operations with stack traces

Enable verbose logging:
```bash
python gstr1.py --input files/ --output output.xlsx --verbose
```

## Tips for Best Results

### PDF Files:
1. Use high-quality PDFs downloaded directly from GSTN portal
2. Avoid scanned or image-based PDFs
3. Ensure PDFs are not password-protected
4. Check that PDFs are not corrupted

### JSON Files:
1. Use official JSON format from GSTN portal
2. Ensure proper UTF-8 encoding
3. Validate JSON syntax before processing
4. Check that all required fields are present

## Troubleshooting

### Common Issues:

**Issue**: "No PDF files found"
- **Solution**: Check that files have .pdf extension and are in the specified directory

**Issue**: "Error extracting text from PDF"
- **Solution**: PDF may be corrupted or password-protected. Try re-downloading from GSTN portal

**Issue**: "Missing fields in output"
- **Solution**: PDF format may vary. Check logs for specific extraction errors

**Issue**: "JSON parsing error"
- **Solution**: Validate JSON syntax using online validators like jsonlint.com

**Issue**: Low validation score
- **Solution**: Check source file quality and completeness

## Support

For issues or questions:
1. Check the comprehensive field guides:
   - GSTR1_Comprehensive_Fields.md
   - GSTR3B_Comprehensive_Fields.md
2. Review error logs for specific issues
3. Ensure input files are from official GSTN portal

## Disclaimer

This tool is for informational purposes only. Always verify extracted data with official GSTN portal records before making filing decisions. The tool developers are not liable for any errors or omissions in extracted data.

## Version History

### Version 2.0
- Added JSON import support for GSTR-1 and GSTR-3B
- Enhanced field extraction to capture all available data
- Added comprehensive validation and quality scoring
- Improved error handling and logging
- Updated Streamlit UI to support multiple file formats

### Version 1.0
- Initial PDF extraction for GSTR-1 and GSTR-3B
- Basic field extraction
- Excel export functionality
