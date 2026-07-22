# GSTR-1 Comprehensive Field Extraction Guide

## Overview
The enhanced GSTR-1 tool now captures ALL available information from GSTR-1 returns, providing comprehensive coverage of every field and table present in the return.

## Basic Information Fields

### 1. Registration Details
- **FileName**: Name of the processed PDF file
- **GSTIN**: GSTIN of the supplier (15-digit alphanumeric)
- **LegalName**: Legal name of the registered person
- **TradeName**: Trade name (if any)
- **ARN**: ARN (Acknowledgement Reference Number)
- **ARNDate**: Date of ARN
- **TaxPeriod**: Tax period (month)
- **FinancialYear**: Financial year (YYYY-YY format)

### 2. Authorized Signatory
- **AuthorizedSignatory**: Name of authorized signatory
- **Designation**: Designation/Status of signatory
- **VerificationDate**: Date of verification

## Table-wise Data Extraction

### 3. Table 4A - B2B Regular Supplies
- **4A_Value**: Total invoice value
- **4A_IGST**: Total IGST amount
- **4A_CGST**: Total CGST amount
- **4A_SGST**: Total SGST amount
- **4A_Cess**: Total CESS amount

### 4. Table 4B - B2B Reverse Charge Supplies
- **4B_Value**: Total invoice value
- **4B_IGST**: Total IGST amount
- **4B_CGST**: Total CGST amount
- **4B_SGST**: Total SGST amount
- **4B_Cess**: Total CESS amount

### 5. Table 5 - B2CL Inter-State Supplies
- **5_Value**: Total invoice value
- **5_IGST**: Total IGST amount
- **5_Cess**: Total CESS amount

### 6. Table 6A - Exports
- **6A_Value**: Total export value
- **6A_IGST**: Total IGST amount
- **6A_Cess**: Total CESS amount
- **6A_EXPWP_Value**: Export with payment value
- **6A_EXPWP_IGST**: Export with payment IGST
- **6A_EXPWP_Cess**: Export with payment CESS
- **6A_EXPWOP_Value**: Export without payment value

### 7. Table 6B - SEZ Supplies
- **6B_Value**: Total SEZ supply value
- **6B_IGST**: Total IGST amount
- **6B_Cess**: Total CESS amount

### 8. Table 6C - Deemed Exports
- **6C_Value**: Total deemed export value
- **6C_IGST**: Total IGST amount
- **6C_CGST**: Total CGST amount
- **6C_SGST**: Total SGST amount
- **6C_Cess**: Total CESS amount

### 9. Table 7 - B2CS (Others)
- **7_Value**: Total B2CS value
- **7_IGST**: Total IGST amount
- **7_CGST**: Total CGST amount
- **7_SGST**: Total SGST amount
- **7_Cess**: Total CESS amount

### 10. Table 8 - Nil Rated, Exempted and Non-GST
- **8_Total**: Total value
- **8_Nil**: Nil rated supplies value
- **8_Exempted**: Exempted supplies value
- **8_NonGST**: Non-GST supplies value

### 11. Table 9A - Amendments to Taxable Supplies
- **9A_B2BRegular_Value**: B2B Regular amendment value
- **9A_B2BRegular_IGST**: B2B Regular amendment IGST
- **9A_B2BRegular_CGST**: B2B Regular amendment CGST
- **9A_B2BRegular_SGST**: B2B Regular amendment SGST
- **9A_B2BRegular_Cess**: B2B Regular amendment CESS
- **9A_B2BReverse_Value**: B2B Reverse charge amendment value
- **9A_B2BReverse_IGST**: B2B Reverse charge amendment IGST
- **9A_B2BReverse_CGST**: B2B Reverse charge amendment CGST
- **9A_B2BReverse_SGST**: B2B Reverse charge amendment SGST
- **9A_B2BReverse_Cess**: B2B Reverse charge amendment CESS
- **9A_B2CL_Value**: B2CL amendment value
- **9A_B2CL_IGST**: B2CL amendment IGST
- **9A_B2CL_Cess**: B2CL amendment CESS
- **9A_EXPWP_Value**: Export with payment amendment value
- **9A_EXPWP_IGST**: Export with payment amendment IGST
- **9A_EXPWP_Cess**: Export with payment amendment CESS
- **9A_EXPWOP_Value**: Export without payment amendment value
- **9A_SEZWP_Value**: SEZ with payment amendment value
- **9A_SEZWP_IGST**: SEZ with payment amendment IGST
- **9A_SEZWP_Cess**: SEZ with payment amendment CESS
- **9A_SEZWOP_Value**: SEZ without payment amendment value
- **9A_DE_Value**: Deemed export amendment value
- **9A_DE_IGST**: Deemed export amendment IGST
- **9A_DE_CGST**: Deemed export amendment CGST
- **9A_DE_SGST**: Deemed export amendment SGST
- **9A_DE_Cess**: Deemed export amendment CESS

### 12. Table 9B - Credit/Debit Notes
- **9B_Value**: Total credit/debit note value
- **9B_IGST**: Total IGST amount
- **9B_Cess**: Total CESS amount
- **9B_B2CL_Value**: B2CL credit/debit note value
- **9B_B2CL_IGST**: B2CL credit/debit note IGST
- **9B_B2CL_Cess**: B2CL credit/debit note CESS
- **9B_EXPWP_Value**: EXPWP credit/debit note value
- **9B_EXPWP_IGST**: EXPWP credit/debit note IGST
- **9B_EXPWP_Cess**: EXPWP credit/debit note CESS
- **9B_EXPWOP_Value**: EXPWOP credit/debit note value

### 13. Table 9C - Amended Credit/Debit Notes
- **9C_Value**: Total amended credit/debit note value
- **9C_IGST**: Total IGST amount
- **9C_CGST**: Total CGST amount
- **9C_SGST**: Total SGST amount
- **9C_Cess**: Total CESS amount
- **9C_B2CL_Value**: B2CL amended credit/debit note value
- **9C_B2CL_IGST**: B2CL amended credit/debit note IGST
- **9C_B2CL_Cess**: B2CL amended credit/debit note CESS
- **9C_EXPWP_Value**: EXPWP amended credit/debit note value
- **9C_EXPWP_IGST**: EXPWP amended credit/debit note IGST
- **9C_EXPWP_Cess**: EXPWP amended credit/debit note CESS
- **9C_EXPWOP_Value**: EXPWOP amended credit/debit note value

### 14. Table 10 - Amendment to B2C Supplies
- **10_Value**: Total amendment value
- **10_CGST**: Total CGST amount
- **10_SGST**: Total SGST amount
- **10_Cess**: Total CESS amount

### 15. Table 11A and 11B - Advances and Adjustments
- **11A_Value**: Total advance value
- **11A_CGST**: Total CGST amount
- **11A_SGST**: Total SGST amount
- **11A_Cess**: Total CESS amount
- **11B_Value**: Total adjustment value
- **11B_CGST**: Total CGST amount
- **11B_SGST**: Total SGST amount
- **11B_Cess**: Total CESS amount

### 16. Table 12 - HSN-wise Summary
- **12_Value**: Total HSN summary value
- **12_IGST**: Total IGST amount
- **12_CGST**: Total CGST amount
- **12_SGST**: Total SGST amount
- **12_Cess**: Total CESS amount

### 17. Table 13 - Documents Issued
- **13_Value**: Total document value
- **13_IGST**: Total IGST amount
- **13_CGST**: Total CGST amount
- **13_SGST**: Total SGST amount
- **13_Cess**: Total CESS amount

### 18. Table 14 - E-Commerce Supplies
- **14_Value**: Total e-commerce value
- **14_CGST**: Total CGST amount
- **14_SGST**: Total SGST amount
- **14_Cess**: Total CESS amount
- **14_U52_Value**: U52 (Regular) value
- **14_U52_CGST**: U52 CGST amount
- **14_U52_SGST**: U52 SGST amount
- **14_U95_Value**: U95 (Reverse charge) value
- **14_U95_CGST**: U95 CGST amount
- **14_U95_SGST**: U95 SGST amount

### 19. Table 14A - Amended E-Commerce Supplies
- **14A_Value**: Total amended e-commerce value
- **14A_CGST**: Total CGST amount
- **14A_SGST**: Total SGST amount
- **14A_Cess**: Total CESS amount
- **14A_U52_Value**: U52 amended value
- **14A_U52_CGST**: U52 amended CGST
- **14A_U52_SGST**: U52 amended SGST
- **14A_U52_Cess**: U52 amended CESS
- **14A_U95_Value**: U95 amended value
- **14A_U95_CGST**: U95 amended CGST
- **14A_U95_SGST**: U95 amended SGST
- **14A_U95_Cess**: U95 amended CESS

### 20. Table 15 - Supplies U/s 9(5)
- **15_Value**: Total supplies value
- **15_IGST**: Total IGST amount
- **15_CGST**: Total CGST amount
- **15_SGST**: Total SGST amount
- **15_Cess**: Total CESS amount
- **15_Regular_Value**: Regular supplies value
- **15_Regular_IGST**: Regular supplies IGST
- **15_Regular_CGST**: Regular supplies CGST
- **15_Regular_SGST**: Regular supplies SGST
- **15_Regular_Cess**: Regular supplies CESS
- **15_DE_Value**: Deemed export supplies value
- **15_DE_IGST**: Deemed export supplies IGST
- **15_DE_CGST**: Deemed export supplies CGST
- **15_DE_SGST**: Deemed export supplies SGST
- **15_DE_Cess**: Deemed export supplies CESS
- **15_SEZWP_Value**: SEZ with payment value
- **15_SEZWP_IGST**: SEZ with payment IGST
- **15_SEZWP_Cess**: SEZ with payment CESS
- **15_SEZWOP_Value**: SEZ without payment value
- **15_Unreg_Value**: Unregistered recipient value
- **15_Unreg_IGST**: Unregistered recipient IGST
- **15_Unreg_CGST**: Unregistered recipient CGST
- **15_Unreg_SGST**: Unregistered recipient SGST
- **15_Unreg_Cess**: Unregistered recipient CESS

### 21. Table 15A - Amended Supplies U/s 9(5)
- **15A_Reg_Value**: Registered recipient amended value
- **15A_Reg_IGST**: Registered recipient amended IGST
- **15A_Reg_CGST**: Registered recipient amended CGST
- **15A_Reg_SGST**: Registered recipient amended SGST
- **15A_Reg_Cess**: Registered recipient amended CESS
- **15A_Regular_Value**: Regular amended value
- **15A_Regular_IGST**: Regular amended IGST
- **15A_Regular_CGST**: Regular amended CGST
- **15A_Regular_SGST**: Regular amended SGST
- **15A_Regular_Cess**: Regular amended CESS
- **15A_DE_Value**: Deemed export amended value
- **15A_DE_IGST**: Deemed export amended IGST
- **15A_DE_CGST**: Deemed export amended CGST
- **15A_DE_SGST**: Deemed export amended SGST
- **15A_DE_Cess**: Deemed export amended CESS
- **15A_SEZWP_Value**: SEZ with payment amended value
- **15A_SEZWP_IGST**: SEZ with payment amended IGST
- **15A_SEZWP_Cess**: SEZ with payment amended CESS
- **15A_SEZWOP_Value**: SEZ without payment amended value
- **15A_Unreg_Value**: Unregistered recipient amended value
- **15A_Unreg_IGST**: Unregistered recipient amended IGST
- **15A_Unreg_CGST**: Unregistered recipient amended CGST
- **15A_Unreg_SGST**: Unregistered recipient amended SGST
- **15A_Unreg_Cess**: Unregistered recipient amended CESS

### 22. HSN-wise Summaries (Tables 16-19)
- **HSN16_Value**: HSN 16 summary value
- **HSN16_IGST**: HSN 16 IGST amount
- **HSN16_CGST**: HSN 16 CGST amount
- **HSN16_SGST**: HSN 16 SGST amount
- **HSN16_Cess**: HSN 16 CESS amount
- **HSN17_Value**: HSN 17 summary value
- **HSN17_IGST**: HSN 17 IGST amount
- **HSN17_CGST**: HSN 17 CGST amount
- **HSN17_SGST**: HSN 17 SGST amount
- **HSN17_Cess**: HSN 17 CESS amount
- **HSN18_Value**: HSN 18 summary value
- **HSN18_IGST**: HSN 18 IGST amount
- **HSN18_CGST**: HSN 18 CGST amount
- **HSN18_SGST**: HSN 18 SGST amount
- **HSN18_Cess**: HSN 18 CESS amount
- **HSN19_Value**: HSN 19 summary value
- **HSN19_IGST**: HSN 19 IGST amount
- **HSN19_CGST**: HSN 19 CGST amount
- **HSN19_SGST**: HSN 19 SGST amount
- **HSN19_Cess**: HSN 19 CESS amount

### 23. Summary (Page 2 Total)
- **Summary_Value**: Total summary value
- **Summary_IGST**: Total summary IGST
- **Summary_CGST**: Total summary CGST
- **Summary_SGST**: Total summary SGST
- **Summary_Cess**: Total summary CESS

## Calculated Summary Statistics

### 24. Business Category Totals
- **Total_B2B_Value**: Total B2B supplies (4A + 4B)
- **Total_Export_Value**: Total export supplies (6A + 6B + 6C)
- **Total_B2C_Value**: Total B2C supplies (7 + 8)

### 25. Tax Totals
- **Total_Taxable_Supplies**: Sum of all taxable supplies
- **Total_IGST**: Sum of all IGST amounts
- **Total_CGST**: Sum of all CGST amounts
- **Total_SGST**: Sum of all SGST amounts
- **Total_Cess**: Sum of all CESS amounts

## Validation and Quality Metrics

### 26. Field Validation
- **GSTIN_missing**: Whether GSTIN is missing
- **GSTIN_validation**: GSTIN validation status
- **GSTIN_format**: GSTIN format validation
- **ARN_missing**: Whether ARN is missing
- **ARN_validation**: ARN validation status
- **ARN_format**: ARN format validation
- **ARNDate_missing**: Whether ARN date is missing
- **ARNDate_validation**: ARN date validation status
- **ARNDate_format**: ARN date format validation
- **TaxPeriod_missing**: Whether tax period is missing
- **TaxPeriod_validation**: Tax period validation status
- **TaxPeriod_format**: Tax period format validation
- **FinancialYear_missing**: Whether financial year is missing
- **FinancialYear_validation**: Financial year validation status
- **FinancialYear_format**: Financial year format validation
- **VerificationDate_missing**: Whether verification date is missing
- **VerificationDate_validation**: Verification date validation status
- **VerificationDate_format**: Verification date format validation
- **AuthorizedSignatory_missing**: Whether authorized signatory is missing
- **AuthorizedSignatory_validation**: Authorized signatory validation status
- **Designation_missing**: Whether designation is missing
- **Designation_validation**: Designation validation status

### 27. Data Consistency Validation
- **Summary_consistency**: Summary consistency check
- **Summary_difference**: Difference between calculated and reported summary
- **Overall_Validation_Score**: Overall validation score (0-100%)
- **Overall_Status**: Overall validation status (EXCELLENT/GOOD/FAIR/POOR)

## Error Handling and Processing Status

### 28. Processing Information
- **parsing_error**: Any parsing errors encountered
- **processing_status**: Processing status (SUCCESS/FAILED)

## Usage Instructions

### Command Line Usage
```bash
python gstr1.py --input /path/to/pdf/directory --output /path/to/output.xlsx --verbose
```

### Python API Usage
```python
from gstr1 import extract_gstr1_data

# Extract data from a single PDF
data = extract_gstr1_data('path/to/file.pdf')

# Process multiple files
from gstr1 import process_directory
process_directory('/path/to/pdf/directory', '/path/to/output.xlsx')
```

## Output Format

The tool generates an Excel file with three sheets:
1. **GSTR1_Data**: Complete extracted data for all files
2. **Summary_Statistics**: Key metrics and totals for each file
3. **Validation_Results**: Validation status and quality metrics

## Features

### Enhanced Pattern Matching
- Multiple fallback patterns for each field
- Case-insensitive matching
- Flexible regex patterns to handle format variations

### Comprehensive Error Handling
- Graceful handling of parsing errors
- Detailed logging for debugging
- Fallback extraction methods

### Data Validation
- Format validation for critical fields
- Consistency checks for summary data
- Quality scoring and status assessment

### Multi-format Support
- Handles various PDF layouts and formats
- Supports different GSTR-1 versions
- Robust text extraction with pdfplumber

## Total Fields Extracted

The enhanced GSTR-1 tool extracts **200+ fields** covering:
- Basic registration information
- All table data (4A through 19)
- Sub-category breakdowns
- Amendment details
- HSN summaries
- Calculated totals
- Validation metrics
- Quality assessments

This comprehensive coverage ensures that no information is missed from GSTR-1 returns, making it suitable for audit, compliance, and analysis purposes.
