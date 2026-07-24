import os
import re
import pandas as pd
import pdfplumber
import logging
import traceback
import numpy as np
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_text(text):
    text = re.sub(r'(?m)^[LANIF]\s*$', '', text)
    text = re.sub(r'\b[LANIF](\d)', r'\1', text)
    # Remove watermark letter attached to end of words (e.g. "tableN" → "table")
    text = re.sub(r'([a-z])[LANIF]\b', r'\1', text)
    return text

def safe_float(value):
    """Safely convert value to float with error handling."""
    try:
        if value and value != "-" and value != "":
            # Remove commas and convert to float
            clean_value = str(value).replace(',', '')
            return round(float(clean_value), 2)
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def extract_value(text, pattern):
    """Extract a single value using regex pattern with enhanced error handling."""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    except re.error as e:
        logger.error(f"Regex error with pattern '{pattern}': {str(e)}")
        return ""

def extract_table_value(text, pattern):
    """Extract table values using regex pattern with enhanced error handling."""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""
    except re.error as e:
        logger.error(f"Regex error with pattern '{pattern}': {str(e)}")
        return ""

def extract_with_fallback_patterns(text, patterns, field_name):
    """Extract data using multiple fallback patterns for better reliability."""
    for i, pattern in enumerate(patterns):
        try:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                logger.info(f"Successfully extracted {field_name} using pattern {i+1}")
                return match.group(1).strip()
        except re.error as e:
            logger.warning(f"Pattern {i+1} failed for {field_name}: {str(e)}")
            continue
    logger.warning(f"All patterns failed for {field_name}")
    return ""

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF for more reliable data extraction."""
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                if page_tables:
                    logger.info(f"Extracted {len(page_tables)} tables from page {page_num + 1}")
                    tables.extend(page_tables)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        logger.error(traceback.format_exc())
    return tables

def extract_gstr1_data(pdf_path):
    """Extract structured data from a GSTR-1 PDF file with comprehensive coverage."""
    data = {}
    
    try:
        logger.info(f"Starting extraction from {pdf_path}")
        
        # Extract all text content from the PDF
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        logger.info(f"Extracted text from page {page_num + 1}")
                    else:
                        logger.warning(f"No text extracted from page {page_num + 1}")
        except Exception as e:
            logger.error(f"Error opening PDF: {str(e)}")
            raise
        
        # Clean up repeated lines like IP Address and FINAL
        text = re.sub(r'IP Address:.*\n', '', text)
        text = re.sub(r'FINAL\n', '', text)
        text = re.sub(r'\n[A-Z]\n', '\n', text)
        text = re.sub(r'IP Address:.*?\nNo\. of Document\nDescription.*?records Type\n', '', text, flags=re.DOTALL)
        text = clean_text(text)
        os.makedirs("extracted_texts", exist_ok=True)
        filename = os.path.basename(pdf_path).replace(".pdf", ".txt")
        with open(os.path.join("extracted_texts", filename), "w", encoding="utf-8") as f:
            f.write(text)
        # Extract header fields with enhanced patterns
        data['FileName'] = os.path.basename(pdf_path)
        data['GSTIN'] = extract_with_fallback_patterns(text, [
            r'GSTIN\s*:?\s*([A-Z0-9]{15})',
            r'GSTIN\s*([A-Z0-9]{15})',
            r'GSTIN\s*of\s*the\s*supplier\s*:?\s*([A-Z0-9]{15})'
        ], 'GSTIN')
        
        data['LegalName'] = extract_with_fallback_patterns(text, [
            r'Legal\s+name\s+of\s+the\s+registered\s+person\s*:?\s*([^\r\n]+)',
            r'Legal\s+name\s*:?\s*([^\r\n]+)',
            r'Registered\s+Person\s*:?\s*([^\r\n]+)'
        ], 'LegalName')
        
        data['TradeName'] = extract_with_fallback_patterns(text, [
            r'Trade\s+name\s+if\s+any\s*:?\s*([^\r\n]+)',
            r'Trade\s+name\s*:?\s*([^\r\n]+)',
            r'Trade\s*:?\s*([^\r\n]+)'
        ], 'TradeName')
        
        data['ARN'] = extract_with_fallback_patterns(text, [
            r'ARN\s*:?\s*([A-Z0-9]+)',
            r'ARN\s*([A-Z0-9]+)',
            r'Acknowledgement\s+Reference\s+Number\s*:?\s*([A-Z0-9]+)'
        ], 'ARN')
        
        data['ARNDate'] = extract_with_fallback_patterns(text, [
            r'ARN\s+date\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'Date\s+of\s+ARN\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'ARN\s*:?\s*[A-Z0-9]+\s*(\d{2}/\d{2}/\d{4})'
        ], 'ARNDate')
        
        data['TaxPeriod'] = extract_with_fallback_patterns(text, [
            r'Tax\s+period\s*:?\s*([^\r\n]+)',
            r'Period\s*:?\s*([^\r\n]+)',
            r'Tax\s*:?\s*([^\r\n]+)'
        ], 'TaxPeriod')
        
        data['FinancialYear'] = extract_with_fallback_patterns(text, [
            r'Financial\s+year\s*:?\s*(\d{4}-\d{2})',
            r'FY\s*:?\s*(\d{4}-\d{2})',
            r'Year\s*:?\s*(\d{4}-\d{2})'
        ], 'FinancialYear')
        
        # Extract verification details
        data['VerificationDate'] = extract_with_fallback_patterns(text, [
            r'Date\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'Verification\s+Date\s*:?\s*(\d{2}/\d{2}/\d{4})'
        ], 'VerificationDate')
        
        data['AuthorizedSignatory'] = extract_with_fallback_patterns(text, [
            r'Name\s+of\s+Authorized\s+Signatory\s*:?\s*([^\r\n]+)',
            r'Authorized\s+Signatory\s*:?\s*([^\r\n]+)',
            r'Signatory\s*:?\s*([^\r\n]+)'
        ], 'AuthorizedSignatory')
        
        data['Designation'] = extract_with_fallback_patterns(text, [
            r'Designation/Status\s*:?\s*([^\r\n]+)',
            r'Designation\s*:?\s*([^\r\n]+)',
            r'Status\s*:?\s*([^\r\n]+)'
        ], 'Designation')
        
        # Extract table-wise totals with enhanced patterns
        
        # 4A - B2B Regular
        data.update(extract_table_4a_values(text))
        
        # 4B - B2B Reverse charge
        data.update(extract_table_4b_values(text))
        
        # 5 - B2CL (Large)
        data.update(extract_table_5_values(text))
        
        # 6A - Exports
        data.update(extract_table_6a_values(text))
        
        # 6B - SEZ Supplies
        data.update(extract_table_6b_values(text))
        
        # 6C - Deemed Exports
        data.update(extract_table_6c_values(text))
        
        # 7 - B2CS (Others)
        data.update(extract_table_7_values(text))
        
        # 8 - Nil rated, exempted and non GST
        data.update(extract_table_8_values(text))
        
        # 9A - Amendments to Taxable Supplies
        data.update(extract_table_9a_values(text))
        
        # 9B - Credit/Debit Notes (Unregistered)
        data.update(extract_table_9b_values(text))
        data.update(extract_table_9b_registered_values(text))
        data.update(extract_table_9b_cdnur_values(text))
        # 9C - Amended Credit/Debit Notes
        pass
        
        # 10 - Amendment to B2C Supplies
        data.update(extract_table_10_values(text))
                
        # 11A and 11B - Advances and Adjustments
        data.update(extract_table_11_values(text))
        
        # 12 - HSN-wise summary 
        data.update(extract_table_12_values(text))
        
        # 13 - Documents issued during the tax period
        data.update(extract_table_13_values(text))
        
        # 14 - E-Commerce Supplies
        data.update(extract_table_14_values(text))
        
        # 14A - Amended E-Commerce Supplies
        data.update(extract_table_14a_values(text))
        
        # 15 - Supplies U/s 9(5)
        data.update(extract_table_15_values(text))
        
        # 15A - Amended Supplies U/s 9(5)
        data.update(extract_table_15a_values(text))
        
        # 16-19 - HSN-wise summaries
        data.update(extract_hsn_summaries(text))
        
        # Summary (Page 2 Total)
        data.update(extract_summary_values(text))
        
        # Calculate summary statistics and validate data
        summary_stats = calculate_summary_statistics(data)
        data.update(summary_stats)
        
        # Validate extracted data
        # Validate extracted data
        validation_results = validate_extracted_data(data)
        data.update(validation_results)
        

        # Add defaults for missing values (important for PDF alignment)
        for key, value in data.items():
            if value is None:             
                data[key] = ""
        
                # Ensure all keys expected by gstr1_vs_3b.py exist (prevents KeyError)
        reconciliation_keys = [
            '4A_Value', '4A_IGST', '4A_CGST', '4A_SGST', '4A_Cess',
            '6B_Value', '6B_IGST', '6B_Cess',
            '6C_Value', '6C_IGST', '6C_CGST', '6C_SGST', '6C_Cess',
            '5_Value', '5_IGST', '5_Cess',
            '7_Value', '7_IGST', '7_CGST', '7_SGST', '7_Cess',
            '8_Total',
            # 9A Net Diffs
            '9A_B2BRegular_NetDiff_Value', '9A_B2BRegular_NetDiff_IGST',
            '9A_B2BRegular_NetDiff_CGST', '9A_B2BRegular_NetDiff_SGST',
            '9A_DE_NetDiff_Value', '9A_DE_NetDiff_IGST', '9A_DE_NetDiff_CGST',
            '9A_B2CL_NetDiff_Value', '9A_B2CL_NetDiff_IGST',
            '9A_EXPWP_NetDiff_Value', '9A_EXPWP_NetDiff_IGST',
            '9A_SEZWP_NetDiff_Value', '9A_SEZWP_NetDiff_IGST',
            # 9B CDNR
            '9B_CDNR_B2BRegular_Value', '9B_CDNR_B2BRegular_IGST',
            '9B_CDNR_B2BRegular_CGST', '9B_CDNR_B2BRegular_SGST',
            '9B_CDNR_SEZ_Value', '9B_CDNR_SEZ_IGST',
            '9B_CDNR_DE_Value', '9B_CDNR_DE_IGST', '9B_CDNR_DE_CGST',
            '9B_CDNUR_B2CL_Value', '9B_CDNUR_B2CL_IGST',
            # 10 Amendments
            '10_NetDiff_Value', '10_NetDiff_IGST', '10_NetDiff_CGST',
            '10_NetDiff_SGST',
        ]
        for key in reconciliation_keys:
            data.setdefault(key, "")

        # Ensure required fields always exist
        data.setdefault('processing_status', 'SUCCESS')
        data.setdefault('parsing_error', "")

        logger.info(f"Successfully extracted data from {pdf_path}")
        logger.info(f"Total fields extracted: {len(data)}")
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        logger.error(traceback.format_exc())
        data['processing_status'] = 'FAILED'
        data['parsing_error'] = str(e)
        data['FileName'] = os.path.basename(pdf_path)
        
    return data

def extract_table_4a_values(text):
    """Extract Table 4A - B2B Regular supplies with enhanced patterns."""
    data = {}
    
    # Multiple patterns for better extraction
    patterns = [
        r'4A\s*-\s*Taxable\s+outward\s+supplies.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'4A.*?B2B\s+Regular.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'4A.*?Total.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['4A_Value'] = match.group(1).strip()
            data['4A_IGST'] = match.group(2).strip()
            data['4A_CGST'] = match.group(3).strip()
            data['4A_SGST'] = match.group(4).strip()
            data['4A_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted Table 4A values")
            break
    else:
        data['4A_Value'] = ""
        data['4A_IGST'] = ""
        data['4A_CGST'] = ""
        data['4A_SGST'] = ""
        data['4A_Cess'] = ""
        logger.warning("Failed to extract Table 4A values")
    
    return data

def extract_table_4b_values(text):
    """Extract Table 4B - B2B Reverse charge supplies with enhanced patterns."""
    data = {}
    
    patterns = [
        r'4B\s*-\s*Taxable\s+outward\s+supplies.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'4B.*?B2B\s+Reverse\s+charge.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'4B.*?Total.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['4B_Value'] = match.group(1).strip()
            data['4B_IGST'] = match.group(2).strip()
            data['4B_CGST'] = match.group(3).strip()
            data['4B_SGST'] = match.group(4).strip()
            data['4B_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted Table 4B values")
            break
    else:
        data['4B_Value'] = ""
        data['4B_IGST'] = ""
        data['4B_CGST'] = ""
        data['4B_SGST'] = ""
        data['4B_Cess'] = ""
        logger.warning("Failed to extract Table 4B values")
    
    return data

def extract_table_5_values(text):
    """Extract Table 5 - B2CL inter-state supplies with enhanced patterns."""
    data = {}
    
    patterns = [
        r'5\s*-\s*Taxable\s+outward\s+inter-state\s+supplies.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'5.*?B2CL.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'5.*?Total.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['5_Value'] = match.group(1).strip()
            data['5_IGST'] = match.group(2).strip()
            data['5_Cess'] = match.group(3).strip()
            logger.info("Successfully extracted Table 5 values")
            break
    else:
        data['5_Value'] = ""
        data['5_IGST'] = ""
        data['5_Cess'] = ""
        logger.warning("Failed to extract Table 5 values")
    
    return data

def extract_table_6a_values(text):
    """Enhanced extraction for Table 6A - Exports with multiple patterns."""
    data = {}
    
    # Total exports with multiple patterns
    total_patterns = [
        r'6A\s*–?\s*Exports.*?\nTotal\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6A.*?Exports.*?\nTotal\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6A.*?Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['6A_Value'] = match.group(1).strip()
            data['6A_IGST'] = match.group(2).strip()
            data['6A_Cess'] = match.group(3).strip()
            logger.info("Successfully extracted Table 6A total values")
            break
    else:
        data['6A_Value'] = ""
        data['6A_IGST'] = ""
        data['6A_Cess'] = ""
        logger.warning("Failed to extract Table 6A total values")
    
    # Export with payment (EXPWP)
    expwp_patterns = [
        r'-?\s*EXPWP\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'EXPWP.*?\n.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in expwp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['6A_EXPWP_Value'] = match.group(1).strip()
            data['6A_EXPWP_IGST'] = match.group(2).strip()
            data['6A_EXPWP_Cess'] = match.group(3).strip()
            logger.info("Successfully extracted Table 6A EXPWP values")
            break
    else:
        data['6A_EXPWP_Value'] = ""
        data['6A_EXPWP_IGST'] = ""
        data['6A_EXPWP_Cess'] = ""
    
    # Export without payment (EXPWOP)
    expwop_patterns = [
        r'-?\s*EXPWOP\s+\d+\s+Invoice\s+(-?[\d,.]+)',
        r'EXPWOP.*?\n.*?Invoice\s+(-?[\d,.]+)'
    ]
    
    for pattern in expwop_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['6A_EXPWOP_Value'] = match.group(1).strip()
            logger.info("Successfully extracted Table 6A EXPWOP values")
            break
    else:
        data['6A_EXPWOP_Value'] = ""
    
    return data

def extract_table_6b_values(text):
    """Enhanced extraction for Table 6B - SEZ supplies."""
    data = {}
    
    patterns = [
        r'6B\s*-\s*Supplies\s+made\s+to\s+SEZ.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6B.*?SEZ.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6B.*?Total.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['6B_Value'] = match.group(1).strip()
            data['6B_IGST'] = match.group(2).strip()
            data['6B_Cess'] = match.group(3).strip()
            logger.info("Successfully extracted Table 6B values")
            break
    else:
        data['6B_Value'] = ""
        data['6B_IGST'] = ""
        data['6B_Cess'] = ""
        logger.warning("Failed to extract Table 6B values")
    
    return data

def extract_table_6c_values(text):
    """Enhanced extraction for Table 6C - Deemed Exports."""
    data = {}
    
    patterns = [
        r'6C\s*-\s*Deemed\s+Exports.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6C.*?Deemed\s+Exports.*?\nTotal.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'6C.*?Total.*?Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['6C_Value'] = match.group(1).strip()
            data['6C_IGST'] = match.group(2).strip()
            data['6C_CGST'] = match.group(3).strip()
            data['6C_SGST'] = match.group(4).strip()
            data['6C_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted Table 6C values")
            break
    else:
        data['6C_Value'] = ""
        data['6C_IGST'] = ""
        data['6C_CGST'] = ""
        data['6C_SGST'] = ""
        data['6C_Cess'] = ""
        logger.warning("Failed to extract Table 6C values")
    
    return data

def extract_table_7_values(text):
    """Enhanced extraction for Table 7 - B2CS (Others) with multiple patterns."""
    data = {}
    
    patterns = [
        r'7\s*-\s*Taxable\s+supplies.*?unregistered\s+persons.*?\n.*?\n.*?Total\s+\d+\s+Net\s+Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'7.*?B2CS.*?\n.*?Total\s+\d+\s+Net\s+Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'7.*?Total\s+\d+\s+Net\s+Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['7_Value'] = match.group(1).strip()
            data['7_IGST'] = match.group(2).strip()
            data['7_CGST'] = match.group(3).strip()
            data['7_SGST'] = match.group(4).strip()
            data['7_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted Table 7 values")
            break
    else:
        data['7_Value'] = ""
        data['7_IGST'] = ""
        data['7_CGST'] = ""
        data['7_SGST'] = ""
        data['7_Cess'] = ""
        logger.warning("Failed to extract Table 7 values")
    
    return data

def extract_table_8_values(text):
    """Enhanced extraction for Table 8 - Nil rated, exempted and non GST."""
    data = {}
    
    # Total with multiple patterns
    total_patterns = [
        r'8\s*-\s*Nil\s+rated.*?\nTotal\s+(-?[\d,.]+)',
        r'8.*?Nil\s+rated.*?\nTotal\s+(-?[\d,.]+)',
        r'8.*?Total\s+(-?[\d,.]+)'
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['8_Total'] = match.group(1).strip()
            logger.info("Successfully extracted Table 8 total")
            break
    else:
        data['8_Total'] = ""
        logger.warning("Failed to extract Table 8 total")
    
    # Extract sub-categories with multiple patterns
    nil_patterns = [
        r'-\s*Nil\s+(-?[\d,.]+)',
        r'Nil\s+rated\s+(-?[\d,.]+)',
        r'Nil\s+(-?[\d,.]+)'
    ]
    
    for pattern in nil_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['8_Nil'] = match.group(1).strip()
            break
    else:
        data['8_Nil'] = ""
    
    exempted_patterns = [
        r'-\s*Exempted\s+(-?[\d,.]+)',
        r'Exempted\s+(-?[\d,.]+)',
        r'Exempt\s+(-?[\d,.]+)'
    ]
    
    for pattern in exempted_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['8_Exempted'] = match.group(1).strip()
            break
    else:
        data['8_Exempted'] = ""
    
    non_gst_patterns = [
        r'-\s*Non-GST\s+(-?[\d,.]+)',
        r'Non-GST\s+(-?[\d,.]+)',
        r'Non\s+GST\s+(-?[\d,.]+)'
    ]
    
    for pattern in non_gst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['8_NonGST'] = match.group(1).strip()
            break
    else:
        data['8_NonGST'] = ""
    
    return data

def extract_table_9a_values(text):
    """Extract Table 9A - Amendments to Taxable Supplies."""
    data = {}
    
    # B2B Regular
    b2b_reg_match = re.search(r'9A - Amendment to taxable outward supplies.*B2B Regular.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if b2b_reg_match:
        data['9A_B2BRegular_Value'] = b2b_reg_match.group(1).strip()
        data['9A_B2BRegular_IGST'] = b2b_reg_match.group(2).strip()
        data['9A_B2BRegular_CGST'] = b2b_reg_match.group(3).strip()
        data['9A_B2BRegular_SGST'] = b2b_reg_match.group(4).strip()
        data['9A_B2BRegular_Cess'] = b2b_reg_match.group(5).strip()
    else:
        data['9A_B2BRegular_Value'] = ""
        data['9A_B2BRegular_IGST'] = ""
        data['9A_B2BRegular_CGST'] = ""
        data['9A_B2BRegular_SGST'] = ""
        data['9A_B2BRegular_Cess'] = ""
    b2b_reg_net_match = re.search(
    r'9A - Amendment to taxable outward supplies.*?B2B Regular.*?'
    r'Net differential amount.*?\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)',
    text, re.DOTALL
    )
    if b2b_reg_net_match:
        data['9A_B2BRegular_NetDiff_Value'] = b2b_reg_net_match.group(1).strip()
        data['9A_B2BRegular_NetDiff_IGST'] = b2b_reg_net_match.group(2).strip()
        data['9A_B2BRegular_NetDiff_CGST'] = b2b_reg_net_match.group(3).strip()
        data['9A_B2BRegular_NetDiff_SGST'] = b2b_reg_net_match.group(4).strip()
        data['9A_B2BRegular_NetDiff_Cess'] = b2b_reg_net_match.group(5).strip()
    else:
        data['9A_B2BRegular_NetDiff_Value'] = ""
        data['9A_B2BRegular_NetDiff_IGST'] = ""
        data['9A_B2BRegular_NetDiff_CGST'] = ""
        data['9A_B2BRegular_NetDiff_SGST'] = ""
        data['9A_B2BRegular_NetDiff_Cess'] = ""
    
    # B2B Reverse Charge
    b2b_rev_match = re.search(r'9A - Amendment to taxable outward supplies.*B2B Reverse charge.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if b2b_rev_match:
        data['9A_B2BReverse_Value'] = b2b_rev_match.group(1).strip()
        data['9A_B2BReverse_IGST'] = b2b_rev_match.group(2).strip()
        data['9A_B2BReverse_CGST'] = b2b_rev_match.group(3).strip()
        data['9A_B2BReverse_SGST'] = b2b_rev_match.group(4).strip()
        data['9A_B2BReverse_Cess'] = b2b_rev_match.group(5).strip()
    else:
        data['9A_B2BReverse_Value'] = ""
        data['9A_B2BReverse_IGST'] = ""
        data['9A_B2BReverse_CGST'] = ""
        data['9A_B2BReverse_SGST'] = ""
        data['9A_B2BReverse_Cess'] = ""
    
    # B2CL
    b2cl_match = re.search(r'9A - Amendment to Inter-State supplies.*B2CL.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if b2cl_match:
        data['9A_B2CL_Value'] = b2cl_match.group(1).strip()
        data['9A_B2CL_IGST'] = b2cl_match.group(2).strip()
        data['9A_B2CL_Cess'] = b2cl_match.group(3).strip()
    else:
        data['9A_B2CL_Value'] = ""
        data['9A_B2CL_IGST'] = ""
        data['9A_B2CL_Cess'] = ""
    
    # Exports (EXPWP)
    expwp_match = re.search(r'9A - Amendment to Export supplies.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if expwp_match:
        data['9A_EXPWP_Value'] = expwp_match.group(1).strip()
        data['9A_EXPWP_IGST'] = expwp_match.group(2).strip()
        data['9A_EXPWP_Cess'] = expwp_match.group(3).strip()
    else:
        data['9A_EXPWP_Value'] = ""
        data['9A_EXPWP_IGST'] = ""
        data['9A_EXPWP_Cess'] = ""
    
    # Exports (EXPWOP)
    expwop_match = re.search(r'9A - Amendment to Export supplies.*- EXPWOP\s+\d+\s+Invoice\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if expwop_match:
        data['9A_EXPWOP_Value'] = expwop_match.group(1).strip()
    else:
        data['9A_EXPWOP_Value'] = ""
    
    # SEZ (SEZWP)
    sezwp_match = re.search(r'9A - Amendment to supplies made to SEZ.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if sezwp_match:
        data['9A_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['9A_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['9A_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['9A_SEZWP_Value'] = ""
        data['9A_SEZWP_IGST'] = ""
        data['9A_SEZWP_Cess'] = ""
    
    # SEZ (SEZWOP)
    sezwop_match = re.search(r'9A - Amendment to supplies made to SEZ.*- SEZWOP\s+\d+\s+Invoice\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if sezwop_match:
        data['9A_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['9A_SEZWOP_Value'] = ""
    # ADD after each 9A section — net diff extraction
    # (same pattern as 9A_B2BRegular_NetDiff already done for B2BRegular)

# B2CL net diff
    b2cl_net = re.search(
        r'9A - Amendment to Inter-State supplies.*?B2CL.*?\nNet differential amount.*?\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
            text, re.DOTALL)
    data['9A_B2CL_NetDiff_Value'] = b2cl_net.group(1).strip() if b2cl_net else ""
    data['9A_B2CL_NetDiff_IGST']  = b2cl_net.group(2).strip() if b2cl_net else ""
    data['9A_B2CL_NetDiff_Cess']  = b2cl_net.group(3).strip() if b2cl_net else ""

    # EXPWP/EXPWOP net diff (exports)
    exp_net = re.search(
        r'9A - Amendment to Export supplies.*?\nNet differential amount.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.DOTALL)
    data['9A_EXPWP_NetDiff_Value']  = exp_net.group(1).strip() if exp_net else ""
    data['9A_EXPWP_NetDiff_IGST']   = exp_net.group(2).strip() if exp_net else ""
    data['9A_EXPWOP_NetDiff_Value'] = ""  # EXPWOP = no payment so no IGST line

    # SEZWP net diff
    sez_net = re.search(
        r'9A - Amendment to supplies made to SEZ.*?\nNet differential amount.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.DOTALL)
    data['9A_SEZWP_NetDiff_Value'] = sez_net.group(1).strip() if sez_net else ""
    data['9A_SEZWP_NetDiff_IGST']  = sez_net.group(2).strip() if sez_net else ""
    data['9A_SEZWP_NetDiff_Cess']  = sez_net.group(3).strip() if sez_net else ""

    # DE net diff
    de_net = re.search(
        r'9A - Amendment to Deemed Exports.*?\nNet differential amount.*?\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.DOTALL)
    data['9A_DE_NetDiff_Value'] = de_net.group(1).strip() if de_net else ""
    data['9A_DE_NetDiff_IGST']  = de_net.group(2).strip() if de_net else ""
    data['9A_DE_NetDiff_CGST']  = de_net.group(3).strip() if de_net else ""
    data['9A_DE_NetDiff_SGST']  = de_net.group(4).strip() if de_net else ""
    data['9A_DE_NetDiff_Cess']  = de_net.group(5).strip() if de_net else ""
    # Deemed Exports
    de_match = re.search(r'9A - Amendment to Deemed Exports.*\nAmended amount - Total\s+\d+\s+Invoice\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if de_match:
        data['9A_DE_Value'] = de_match.group(1).strip()
        data['9A_DE_IGST'] = de_match.group(2).strip()
        data['9A_DE_CGST'] = de_match.group(3).strip()
        data['9A_DE_SGST'] = de_match.group(4).strip()
        data['9A_DE_Cess'] = de_match.group(5).strip()
    else:
        data['9A_DE_Value'] = ""
        data['9A_DE_IGST'] = ""
        data['9A_DE_CGST'] = ""
        data['9A_DE_SGST'] = ""
        data['9A_DE_Cess'] = ""
    
    return data


def extract_table_9b_cdnur_values(text):
    """Extract 9B CDNUR (Unregistered) — B2CL, EXPWP, EXPWOP."""
    data = {}
    cdnur_block_match = re.search(
        r'9B - Credit/Debit Notes \(Unregistered\).*?CDNUR(.*?)9C -',
        text, re.DOTALL | re.IGNORECASE
    )
    cdnur_block = cdnur_block_match.group(1) if cdnur_block_match else ""

    b2cl = re.search(r'- B2CL\s+\d+\s+Note\s+([\d,.-]+)\s+([\d,.-]+)\s+([\d,.-]+)', cdnur_block)
    if b2cl:
        data['9B_CDNUR_B2CL_Value'] = b2cl.group(1).strip()
        data['9B_CDNUR_B2CL_IGST']  = b2cl.group(2).strip()
        data['9B_CDNUR_B2CL_Cess']  = b2cl.group(3).strip()
    else:
        data['9B_CDNUR_B2CL_Value'] = data['9B_CDNUR_B2CL_IGST'] = data['9B_CDNUR_B2CL_Cess'] = ""

    expwp = re.search(r'- EXPWP\s+\d+\s+N?Note\s+([\d,.-]+)\s+([\d,.-]+)\s+([\d,.-]+)', cdnur_block)
    if expwp:
        data['9B_CDNUR_EXPWP_Value'] = expwp.group(1).strip()
        data['9B_CDNUR_EXPWP_IGST']  = expwp.group(2).strip()
        data['9B_CDNUR_EXPWP_Cess']  = expwp.group(3).strip()
    else:
        data['9B_CDNUR_EXPWP_Value'] = data['9B_CDNUR_EXPWP_IGST'] = data['9B_CDNUR_EXPWP_Cess'] = ""

    expwop = re.search(r'- EXPWOP\s+\d+\s+Note\s+([\d,.-]+)', cdnur_block)
    data['9B_CDNUR_EXPWOP_Value'] = expwop.group(1).strip() if expwop else ""

    return data

def extract_table_9b_registered_values(text):
    """Extract Table 9B - Credit/Debit Notes (Registered) – CDNR.
    Extracts each sub-category separately using schema keys that
    match gstr1_schema.json and gstr1_vs_3b.py expectations.
    """
    data = {}

    # ── 9B CDNR Total (Registered) ───────────────────────────────────────────
    total_match = re.search(
        r'9B - Credit/Debit Notes \(Registered\).*?'
        r'Total - Net off debit/credit notes.*?\d+\s+Note\s+'
        r'(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)',
        text, re.DOTALL)
    if total_match:
        data['9B_CDNR_Total_Value'] = total_match.group(1).strip()
        data['9B_CDNR_Total_IGST']  = total_match.group(2).strip()
        data['9B_CDNR_Total_CGST']  = total_match.group(3).strip()
        data['9B_CDNR_Total_SGST']  = total_match.group(4).strip()
        data['9B_CDNR_Total_Cess']  = total_match.group(5).strip()
    else:
        data['9B_CDNR_Total_Value'] = ""
        data['9B_CDNR_Total_IGST']  = ""
        data['9B_CDNR_Total_CGST']  = ""
        data['9B_CDNR_Total_SGST']  = ""
        data['9B_CDNR_Total_Cess']  = ""

    # ── 9B CDNR B2B Regular (nets into 4A) ───────────────────────────────────
    b2b_match = re.search(
        r'Credit / Debit notes issued to registered person.*?B2B Regular\s*\n'
        r'Net Total.*?Note\s+'
        r'(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)',
        text, re.DOTALL | re.IGNORECASE)
    if b2b_match:
        data['9B_CDNR_B2BRegular_Value'] = b2b_match.group(1).strip()
        data['9B_CDNR_B2BRegular_IGST']  = b2b_match.group(2).strip()
        data['9B_CDNR_B2BRegular_CGST']  = b2b_match.group(3).strip()
        data['9B_CDNR_B2BRegular_SGST']  = b2b_match.group(4).strip()
        data['9B_CDNR_B2BRegular_Cess']  = b2b_match.group(5).strip()
    else:
        data['9B_CDNR_B2BRegular_Value'] = ""
        data['9B_CDNR_B2BRegular_IGST']  = ""
        data['9B_CDNR_B2BRegular_CGST']  = ""
        data['9B_CDNR_B2BRegular_SGST']  = ""
        data['9B_CDNR_B2BRegular_Cess']  = ""

    # ── 9B CDNR SEZ (nets into 6B) ───────────────────────────────────────────
    sez_match = re.search(
        r'Credit / Debit notes issued to registered person.*?SEZWP/SEZWOP\s*\n'
        r'Net Total.*?Note\s+'
        r'(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)',
        text, re.DOTALL | re.IGNORECASE)
    if sez_match:
        data['9B_CDNR_SEZ_Value'] = sez_match.group(1).strip()
        data['9B_CDNR_SEZ_IGST']  = sez_match.group(2).strip()
        data['9B_CDNR_SEZ_Cess']  = sez_match.group(3).strip()
    else:
        data['9B_CDNR_SEZ_Value'] = ""
        data['9B_CDNR_SEZ_IGST']  = ""
        data['9B_CDNR_SEZ_Cess']  = ""

    # ── 9B CDNR DE (nets into 6C) ────────────────────────────────────────────
    de_match = re.search(
        r'Credit / Debit notes issued to registered person.*?table 6C.*?DE\s*\n'
        r'Net Total.*?Note\s+'
        r'(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)',
        text, re.DOTALL | re.IGNORECASE)
    if de_match:
        data['9B_CDNR_DE_Value'] = de_match.group(1).strip()
        data['9B_CDNR_DE_IGST']  = de_match.group(2).strip()
        data['9B_CDNR_DE_CGST']  = de_match.group(3).strip()
        data['9B_CDNR_DE_SGST']  = de_match.group(4).strip()
        data['9B_CDNR_DE_Cess']  = de_match.group(5).strip()
    else:
        data['9B_CDNR_DE_Value'] = ""
        data['9B_CDNR_DE_IGST']  = ""
        data['9B_CDNR_DE_CGST']  = ""
        data['9B_CDNR_DE_SGST']  = ""
        data['9B_CDNR_DE_Cess']  = ""

    # ── Backward-compat aliases (old keys some callers may still use) ─────────
    data['CDNR_Value'] = data['9B_CDNR_B2BRegular_Value']
    data['CDNR_IGST']  = data['9B_CDNR_B2BRegular_IGST']
    data['CDNR_CGST']  = data['9B_CDNR_B2BRegular_CGST']
    data['CDNR_SGST']  = data['9B_CDNR_B2BRegular_SGST']
    data['CDNR_Cess']  = data['9B_CDNR_B2BRegular_Cess']

    return data

def extract_table_9b_values(text):
    """Extract Table 9B - Credit/Debit Notes (Registered CDNR + Unregistered CDNUR)"""
    data = {}
    
    # === REGISTERED (CDNR) - B2B, SEZ, DE ===
    # Net Differential (most important)
    net_match = re.search(
        r'9B - Credit/Debit Notes \(Registered\).*?Net off debit/credit notes.*?Net Total.*?Note\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)',
        text, re.DOTALL | re.IGNORECASE
    )
    if net_match:
        data['9B_NetDiff_Value'] = safe_float(net_match.group(1))
        data['9B_NetDiff_IGST'] = safe_float(net_match.group(2))
        data['9B_NetDiff_CGST'] = safe_float(net_match.group(3))
        data['9B_NetDiff_SGST'] = safe_float(net_match.group(4))
        data['9B_NetDiff_Cess'] = safe_float(net_match.group(5))

    # B2B Regular CDNR
    b2b_match = re.search(
        r'B2B Regular.*?Net Total.*?Note\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)',
        text, re.DOTALL | re.IGNORECASE
    )
    if b2b_match:
        data['9B_CDNR_B2B_Value'] = safe_float(b2b_match.group(1))
        data['9B_CDNR_B2B_IGST'] = safe_float(b2b_match.group(2))
        data['9B_CDNR_B2B_CGST'] = safe_float(b2b_match.group(3))
        data['9B_CDNR_B2B_SGST'] = safe_float(b2b_match.group(4))
        data['9B_CDNR_B2B_Cess'] = safe_float(b2b_match.group(5))

    # SEZ CDNR
    sez_match = re.search(
        r'SEZWP/SEZWOP.*?Net Total.*?Note\s+([-\d,.]+)\s+([-\d,.]+)',
        text, re.DOTALL | re.IGNORECASE
    )
    if sez_match:
        data['9B_CDNR_SEZ_Value'] = safe_float(sez_match.group(1))
        data['9B_CDNR_SEZ_IGST'] = safe_float(sez_match.group(2))

    # DE CDNR
    de_match = re.search(
        r'table 6C.*?DE.*?Net Total.*?Note\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)',
        text, re.DOTALL | re.IGNORECASE
    )
    if de_match:
        data['9B_CDNR_DE_Value'] = safe_float(de_match.group(1))
        data['9B_CDNR_DE_IGST'] = safe_float(de_match.group(2))
        data['9B_CDNR_DE_CGST'] = safe_float(de_match.group(3))
        data['9B_CDNR_DE_SGST'] = safe_float(de_match.group(4))
        data['9B_CDNR_DE_Cess'] = safe_float(de_match.group(5))

    # === UNREGISTERED (CDNUR) - Keep for completeness ===
    b2cl_match = re.search(r'B2CL\s+\d+\s+Note\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)', text, re.DOTALL | re.IGNORECASE)
    if b2cl_match:
        data['9B_CDNUR_B2CL_Value'] = safe_float(b2cl_match.group(1))
        data['9B_CDNUR_B2CL_IGST'] = safe_float(b2cl_match.group(2))
        data['9B_CDNUR_B2CL_Cess'] = safe_float(b2cl_match.group(3))

    # Default all keys
    default_keys = [
        '9B_NetDiff_Value', '9B_NetDiff_IGST', '9B_NetDiff_CGST', '9B_NetDiff_SGST', '9B_NetDiff_Cess',
        '9B_CDNR_B2B_Value', '9B_CDNR_B2B_IGST', '9B_CDNR_B2B_CGST', '9B_CDNR_B2B_SGST', '9B_CDNR_B2B_Cess',
        '9B_CDNR_SEZ_Value', '9B_CDNR_SEZ_IGST', '9B_CDNR_DE_Value', '9B_CDNR_DE_IGST',
        '9B_CDNUR_B2CL_Value', '9B_CDNUR_B2CL_IGST', '9B_CDNUR_B2CL_Cess'
    ]
    for key in default_keys:
        data.setdefault(key, 0.0)

    return data

def extract_table_10_values(text):
    """Extract Table 10 - Amendment to B2C Supplies."""
    data = {}
    
    # Amended total
    match = re.search(r'10 - Amendment to taxable outward supplies.*B2C.*\nAmended amount - Total\s+\d+\s+Net Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if match:
        data['10_Value'] = match.group(1).strip()
        data['10_CGST'] = match.group(2).strip()
        data['10_SGST'] = match.group(3).strip()
        data['10_Cess'] = match.group(4).strip()
    else:
        data['10_Value'] = ""
        data['10_CGST'] = ""
        data['10_SGST'] = ""
        data['10_Cess'] = ""
    
    # Net differential (most important for reconciliation)
    net_match = re.search(
        r'10 - Amendment.*?Net differential amount.*?\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)',
        text, re.DOTALL
    )
    if net_match:
        data['10_NetDiff_Value'] = net_match.group(1).strip()
        data['10_NetDiff_IGST']  = net_match.group(2).strip()   # Often 0 for B2CS but keep
        data['10_NetDiff_CGST']  = net_match.group(3).strip()
        data['10_NetDiff_SGST']  = net_match.group(4).strip()
        data['10_NetDiff_Cess']  = net_match.group(5).strip()
    else:
        data['10_NetDiff_Value'] = ""
        data['10_NetDiff_IGST']  = ""
        data['10_NetDiff_CGST']  = ""
        data['10_NetDiff_SGST']  = ""
        data['10_NetDiff_Cess']  = ""
    
    return data

def extract_table_11_values(text):
    """Extract Table 11A and 11B - Advances and Adjustments."""
    data = {}

    # ── 11A(1), 11A(2) — Advances received ──────────────────────────────
    # Pattern: header line immediately followed by Total line
    # Fix: use line-by-line matching instead of DOTALL to avoid greedy overshoot
    match_11a = re.search(
        r'11A\(1\),\s*11A\(2\)\s*-\s*Advances received[^\n]*\n'
        r'Total\s+(\d+)\s+Net Value\s+'
        r'(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.IGNORECASE
    )
    if match_11a:
        data['11A_Records'] = match_11a.group(1).strip()
        data['11A_Value']   = match_11a.group(2).strip()
        data['11A_IGST']    = match_11a.group(3).strip()
        data['11A_CGST']    = match_11a.group(4).strip()
        data['11A_SGST']    = match_11a.group(5).strip()
        data['11A_Cess']    = match_11a.group(6).strip()
    else:
        data['11A_Records'] = ''
        data['11A_Value']   = ''
        data['11A_IGST']    = ''
        data['11A_CGST']    = ''
        data['11A_SGST']    = ''
        data['11A_Cess']    = ''

    # ── 11B(1), 11B(2) — Advances adjusted ──────────────────────────────
    match_11b = re.search(
        r'11B\(1\),\s*11B\(2\)\s*-\s*Advance amount[^\n]*\n'
        r'Total\s+(\d+)\s+Net Value\s+'
        r'(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.IGNORECASE
    )
    if match_11b:
        data['11B_Records'] = match_11b.group(1).strip()
        data['11B_Value']   = match_11b.group(2).strip()
        data['11B_IGST']    = match_11b.group(3).strip()
        data['11B_CGST']    = match_11b.group(4).strip()
        data['11B_SGST']    = match_11b.group(5).strip()
        data['11B_Cess']    = match_11b.group(6).strip()
    else:
        data['11B_Records'] = ''
        data['11B_Value']   = ''
        data['11B_IGST']    = ''
        data['11B_CGST']    = ''
        data['11B_SGST']    = ''
        data['11B_Cess']    = ''

    # ── 11A Amendment — Amendment to advances received ───────────────────
    # Fix: header may contain stray characters (e.g. "tableN 11A") — use [^\n]* to absorb
    # Fix: Total line has NO record count — format is "Total 0.00 0.00 ..."
    match_11a_amend = re.search(
        r'11A\s*-\s*Amendment to advances received[^\n]*\n'
        r'Amended amount\s*-\s*Total\s+\d+\s+Net Value\s+'
        r'(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\n'
        r'Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.IGNORECASE
    )
    if match_11a_amend:
        data['11A_Amend_Value']      = match_11a_amend.group(1).strip()
        data['11A_Amend_IGST']       = match_11a_amend.group(2).strip()
        data['11A_Amend_CGST']       = match_11a_amend.group(3).strip()
        data['11A_Amend_SGST']       = match_11a_amend.group(4).strip()
        data['11A_Amend_Cess']       = match_11a_amend.group(5).strip()
        data['11A_Amend_Net_Value']  = match_11a_amend.group(6).strip()
        data['11A_Amend_Net_IGST']   = match_11a_amend.group(7).strip()
        data['11A_Amend_Net_CGST']   = match_11a_amend.group(8).strip()
        data['11A_Amend_Net_SGST']   = match_11a_amend.group(9).strip()
        data['11A_Amend_Net_Cess']   = match_11a_amend.group(10).strip()
    else:
        for key in ['11A_Amend_Value','11A_Amend_IGST','11A_Amend_CGST','11A_Amend_SGST','11A_Amend_Cess',
                    '11A_Amend_Net_Value','11A_Amend_Net_IGST','11A_Amend_Net_CGST','11A_Amend_Net_SGST','11A_Amend_Net_Cess']:
            data[key] = ''

    # ── 11B Amendment — Amendment to advances adjusted ───────────────────
    match_11b_amend = re.search(
        r'11B\s*-\s*Amendment to advances adjusted[^\n]*\n'
        r'Amended amount\s*-\s*Total\s+\d+\s+Net Value\s+'
        r'(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\n'
        r'Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        text, re.IGNORECASE
    )
    if match_11b_amend:
        data['11B_Amend_Value']      = match_11b_amend.group(1).strip()
        data['11B_Amend_IGST']       = match_11b_amend.group(2).strip()
        data['11B_Amend_CGST']       = match_11b_amend.group(3).strip()
        data['11B_Amend_SGST']       = match_11b_amend.group(4).strip()
        data['11B_Amend_Cess']       = match_11b_amend.group(5).strip()
        data['11B_Amend_Net_Value']  = match_11b_amend.group(6).strip()
        data['11B_Amend_Net_IGST']   = match_11b_amend.group(7).strip()
        data['11B_Amend_Net_CGST']   = match_11b_amend.group(8).strip()
        data['11B_Amend_Net_SGST']   = match_11b_amend.group(9).strip()
        data['11B_Amend_Net_Cess']   = match_11b_amend.group(10).strip()
    else:
        for key in ['11B_Amend_Value','11B_Amend_IGST','11B_Amend_CGST','11B_Amend_SGST','11B_Amend_Cess',
                    '11B_Amend_Net_Value','11B_Amend_Net_IGST','11B_Amend_Net_CGST','11B_Amend_Net_SGST','11B_Amend_Net_Cess']:
            data[key] = ''

    return data

def extract_table_12_values(text):
    """Extract Table 12 - HSN-wise summary."""
    data = {}
    
    # Total
    total_match = re.search(
    r'12 - HSN-wise summary of outward supplies\s*\nTotal\s+\d+\s+NA\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.IGNORECASE)
    if total_match:
        data['12_Value'] = total_match.group(1).strip()
        data['12_IGST'] = total_match.group(2).strip()
        data['12_CGST'] = total_match.group(3).strip()
        data['12_SGST'] = total_match.group(4).strip()
        data['12_Cess'] = total_match.group(5).strip()
    else:
        data['12_Value'] = ""
        data['12_IGST'] = ""
        data['12_CGST'] = ""
        data['12_SGST'] = ""
        data['12_Cess'] = ""
    
    return data

def extract_table_13_values(text):
    data = {}
    match = re.search(r'13 - Documents issued.*?Net issued documents\s+(\d+)', text, re.DOTALL)
    if match:
        data['13_DocumentsIssued'] = match.group(1).strip()
    else:
        data['13_DocumentsIssued'] = ""
    # Table 13 only has a document count, no tax amount columns
    return data

def extract_table_14_values(text):
    """Extract Table 14 - E-Commerce Supplies."""
    data = {}
    
    # Total
    total_match = re.search(
    r'14 - Supplies made through E-Commerce Operators\s*\nTotal\s+\d+\s+Net Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
    text, re.DOTALL | re.IGNORECASE)
    
    if total_match:
        data['14_Value'] = total_match.group(1).strip()
        data['14_IGST']  = total_match.group(2).strip()  
        data['14_CGST']  = total_match.group(3).strip()
        data['14_SGST']  = total_match.group(4).strip()
        data['14_Cess']  = total_match.group(5).strip()
        
    else:
        data['14_Value'] = ""
        data['14_CGST'] = ""
        data['14_SGST'] = ""
        data['14_Cess'] = ""
    
    # Liable to collect tax u/s 52
    u52_match = re.search(r'14 - Supplies made through E-Commerce Operators.*\(a\) Liable to collect tax u/s 52\s+\d+\s+Net Value\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if u52_match:
        data['14_U52_Value'] = u52_match.group(1).strip()
        data['14_U52_CGST'] = u52_match.group(2).strip()
        data['14_U52_SGST'] = u52_match.group(3).strip()
        data['14_U52_Cess'] = u52_match.group(4).strip()
    else:
        data['14_U52_Value'] = ""
        data['14_U52_CGST'] = ""
        data['14_U52_SGST'] = ""
        data['14_U52_Cess'] = ""
    
    # Liable to pay tax u/s 9(5)
    u95_match = re.search(r'14 - Supplies made through E-Commerce Operators.*\(b\) Liable to pay tax u/s 9\(5\)\s+\d+\s+Net Value\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if u95_match:
        data['14_U95_Value'] = u95_match.group(1).strip()
        data['14_U95_CGST'] = u95_match.group(2).strip()
        data['14_U95_SGST'] = u95_match.group(3).strip()
        data['14_U95_Cess'] = u95_match.group(4).strip()
    else:
        data['14_U95_Value'] = ""
        data['14_U95_CGST'] = ""
        data['14_U95_SGST'] = ""
        data['14_U95_Cess'] = ""
    
    return data

def extract_table_14a_values(text):
    """Extract Table 14A - Amended E-Commerce Supplies."""
    data = {}
    
    # Total
    total_match = re.search(
    r'14A - Amended Supplies.*?Amended amount\s*[–-]\s*Total\s+\d+\s+Net Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL | re.IGNORECASE)
    if total_match:
        data['14A_Value'] = total_match.group(1).strip()
        data['14A_CGST'] = total_match.group(2).strip()
        data['14A_SGST'] = total_match.group(3).strip()
        data['14A_Cess'] = total_match.group(4).strip()
    else:
        data['14A_Value'] = ""
        data['14A_CGST'] = ""
        data['14A_SGST'] = ""
        data['14A_Cess'] = ""
    
    # Liable to collect tax u/s 52
    u52_match = re.search(r'14A - Amended Supplies made through E-Commerce Operators.*\(a\) Liable to collect tax u/s 52\s+\d+\s+Net Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if u52_match:
        data['14A_U52_Value'] = u52_match.group(1).strip()
        data['14A_U52_CGST'] = u52_match.group(2).strip()
        data['14A_U52_SGST'] = u52_match.group(3).strip()
        data['14A_U52_Cess'] = u52_match.group(4).strip()
    else:
        data['14A_U52_Value'] = ""
        data['14A_U52_CGST'] = ""
        data['14A_U52_SGST'] = ""
        data['14A_U52_Cess'] = ""
    
    # Liable to pay tax u/s 9(5)
    u95_match = re.search(r'14A - Amended Supplies made through E-Commerce Operators.*\(b\) Liable to pay tax u/s 9\(5\)\s+\d+\s+Net Value\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if u95_match:
        data['14A_U95_Value'] = u95_match.group(1).strip()
        data['14A_U95_CGST'] = u95_match.group(2).strip()
        data['14A_U95_SGST'] = u95_match.group(3).strip()
        data['14A_U95_Cess'] = u95_match.group(4).strip()
    else:
        data['14A_U95_Value'] = ""
        data['14A_U95_CGST'] = ""
        data['14A_U95_SGST'] = ""
        data['14A_U95_Cess'] = ""
    
    return data

def extract_table_15_values(text):
    """Extract Table 15 - Supplies U/s 9(5)."""
    data = {}
    
    # Total
    total_match = re.search(r'15 - Supplies U/s 9\(5\).*\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if total_match:
        data['15_Value'] = total_match.group(1).strip()
        data['15_IGST'] = total_match.group(2).strip()
        data['15_CGST'] = total_match.group(3).strip()
        data['15_SGST'] = total_match.group(4).strip()
        data['15_Cess'] = total_match.group(5).strip()
    else:
        data['15_Value'] = ""
        data['15_IGST'] = ""
        data['15_CGST'] = ""
        data['15_SGST'] = ""
        data['15_Cess'] = ""
    
    # Registered Recipients - Regular
    reg_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+Regular\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if reg_match:
        data['15_Regular_Value'] = reg_match.group(1).strip()
        data['15_Regular_IGST'] = reg_match.group(2).strip()
        data['15_Regular_CGST'] = reg_match.group(3).strip()
        data['15_Regular_SGST'] = reg_match.group(4).strip()
        data['15_Regular_Cess'] = reg_match.group(5).strip()
    else:
        data['15_Regular_Value'] = ""
        data['15_Regular_IGST'] = ""
        data['15_Regular_CGST'] = ""
        data['15_Regular_SGST'] = ""
        data['15_Regular_Cess'] = ""
    
    # Registered Recipients - DE
    de_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+DE\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if de_match:
        data['15_DE_Value'] = de_match.group(1).strip()
        data['15_DE_IGST'] = de_match.group(2).strip()
        data['15_DE_CGST'] = de_match.group(3).strip()
        data['15_DE_SGST'] = de_match.group(4).strip()
        data['15_DE_Cess'] = de_match.group(5).strip()
    else:
        data['15_DE_Value'] = ""
        data['15_DE_IGST'] = ""
        data['15_DE_CGST'] = ""
        data['15_DE_SGST'] = ""
        data['15_DE_Cess'] = ""
    
    # Registered Recipients - SEZWP
    sezwp_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+SEZWP\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if sezwp_match:
        data['15_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['15_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['15_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['15_SEZWP_Value'] = ""
        data['15_SEZWP_IGST'] = ""
        data['15_SEZWP_Cess'] = ""
    
    # Registered Recipients - SEZWOP
    sezwop_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+SEZWOP\s+\d+\s+Document\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if sezwop_match:
        data['15_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['15_SEZWOP_Value'] = ""
    
    # Unregistered Recipients
    unreg_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+For Unregistered Recipient\s+\d+\s+Net Value\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if unreg_match:
        data['15_Unreg_Value'] = unreg_match.group(1).strip()
        data['15_Unreg_IGST'] = unreg_match.group(2).strip()
        data['15_Unreg_CGST'] = unreg_match.group(3).strip()
        data['15_Unreg_SGST'] = unreg_match.group(4).strip()
        data['15_Unreg_Cess'] = unreg_match.group(5).strip()
    else:
        data['15_Unreg_Value'] = ""
        data['15_Unreg_IGST'] = ""
        data['15_Unreg_CGST'] = ""
        data['15_Unreg_SGST'] = ""
        data['15_Unreg_Cess'] = ""
    
    return data

def extract_table_15a_values(text):
    """Extract Table 15A - Amended Supplies U/s 9(5)."""
    data = {}
    
    # Registered Recipients - Total
    reg_total_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*\nAmended amount - Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)', text, re.DOTALL)
    if reg_total_match:
        data['15A_Reg_Value'] = reg_total_match.group(1).strip()
        data['15A_Reg_IGST'] = reg_total_match.group(2).strip()
        data['15A_Reg_CGST'] = reg_total_match.group(3).strip()
        data['15A_Reg_SGST'] = reg_total_match.group(4).strip()
        data['15A_Reg_Cess'] = reg_total_match.group(5).strip()
    else:
        data['15A_Reg_Value'] = ""
        data['15A_Reg_IGST'] = ""
        data['15A_Reg_CGST'] = ""
        data['15A_Reg_SGST'] = ""
        data['15A_Reg_Cess'] = ""
    
    # Registered Recipients - Regular
    reg_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+Regular\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if reg_match:
        data['15A_Regular_Value'] = reg_match.group(1).strip()
        data['15A_Regular_IGST'] = reg_match.group(2).strip()
        data['15A_Regular_CGST'] = reg_match.group(3).strip()
        data['15A_Regular_SGST'] = reg_match.group(4).strip()
        data['15A_Regular_Cess'] = reg_match.group(5).strip()
    else:
        data['15A_Regular_Value'] = ""
        data['15A_Regular_IGST'] = ""
        data['15A_Regular_CGST'] = ""
        data['15A_Regular_SGST'] = ""
        data['15A_Regular_Cess'] = ""
    
    # Registered Recipients - DE
    de_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+DE\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if de_match:
        data['15A_DE_Value'] = de_match.group(1).strip()
        data['15A_DE_IGST'] = de_match.group(2).strip()
        data['15A_DE_CGST'] = de_match.group(3).strip()
        data['15A_DE_SGST'] = de_match.group(4).strip()
        data['15A_DE_Cess'] = de_match.group(5).strip()
    else:
        data['15A_DE_Value'] = ""
        data['15A_DE_IGST'] = ""
        data['15A_DE_CGST'] = ""
        data['15A_DE_SGST'] = ""
        data['15A_DE_Cess'] = ""
    
    # Registered Recipients - SEZWP
    sezwp_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+SEZWP\s+\d+\s+Document\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if sezwp_match:
        data['15A_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['15A_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['15A_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['15A_SEZWP_Value'] = ""
        data['15A_SEZWP_IGST'] = ""
        data['15A_SEZWP_Cess'] = ""
    
    # Registered Recipients - SEZWOP
    sezwop_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+SEZWOP\s+\d+\s+Document\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if sezwop_match:
        data['15A_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['15A_SEZWOP_Value'] = ""
    
    # Unregistered Recipients
    unreg_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Unregistered Recipients.*\nAmended amount - Total\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)\s+(-?[\d,.]+|0.00)', text, re.DOTALL)
    if unreg_match:
        data['15A_Unreg_Value'] = unreg_match.group(1).strip()
        data['15A_Unreg_IGST'] = unreg_match.group(2).strip()
        data['15A_Unreg_CGST'] = unreg_match.group(3).strip()
        data['15A_Unreg_SGST'] = unreg_match.group(4).strip()
        data['15A_Unreg_Cess'] = unreg_match.group(5).strip()
    else:
        data['15A_Unreg_Value'] = ""
        data['15A_Unreg_IGST'] = ""
        data['15A_Unreg_CGST'] = ""
        data['15A_Unreg_SGST'] = ""
        data['15A_Unreg_Cess'] = ""
    
    return data

def extract_hsn_summaries(text):
    """Extract HSN-wise summaries (16-19) if present with enhanced patterns."""
    data = {}
    
    # HSN 16 - Multiple patterns
    hsn16_patterns = [
        r'16\s*-\s*HSN-wise\s+summary.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'16.*?HSN.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'16.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in hsn16_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['HSN16_Value'] = match.group(1).strip()
            data['HSN16_IGST'] = match.group(2).strip()
            data['HSN16_CGST'] = match.group(3).strip()
            data['HSN16_SGST'] = match.group(4).strip()
            data['HSN16_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted HSN16 values")
            break
    else:
        data['HSN16_Value'] = ""
        data['HSN16_IGST'] = ""
        data['HSN16_CGST'] = ""
        data['HSN16_SGST'] = ""
        data['HSN16_Cess'] = ""
    
    # HSN 17 - Multiple patterns
    hsn17_patterns = [
        r'17\s*-\s*HSN-wise\s+summary.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'17.*?HSN.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'17.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in hsn17_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['HSN17_Value'] = match.group(1).strip()
            data['HSN17_IGST'] = match.group(2).strip()
            data['HSN17_CGST'] = match.group(3).strip()
            data['HSN17_SGST'] = match.group(4).strip()
            data['HSN17_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted HSN17 values")
            break
    else:
        data['HSN17_Value'] = ""
        data['HSN17_IGST'] = ""
        data['HSN17_CGST'] = ""
        data['HSN17_SGST'] = ""
        data['HSN17_Cess'] = ""
    
    # HSN 18 - Multiple patterns
    hsn18_patterns = [
        r'18\s*-\s*HSN-wise\s+summary.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'18.*?HSN.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'18.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in hsn18_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['HSN18_Value'] = match.group(1).strip()
            data['HSN18_IGST'] = match.group(2).strip()
            data['HSN18_CGST'] = match.group(3).strip()
            data['HSN18_SGST'] = match.group(4).strip()
            data['HSN18_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted HSN18 values")
            break
    else:
        data['HSN18_Value'] = ""
        data['HSN18_IGST'] = ""
        data['HSN18_CGST'] = ""
        data['HSN18_SGST'] = ""
        data['HSN18_Cess'] = ""
    
    # HSN 19 - Multiple patterns
    hsn19_patterns = [
        r'19\s*-\s*HSN-wise\s+summary.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'19.*?HSN.*?\nTotal\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'19.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)'
    ]
    
    for pattern in hsn19_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['HSN19_Value'] = match.group(1).strip()
            data['HSN19_IGST'] = match.group(2).strip()
            data['HSN19_CGST'] = match.group(3).strip()
            data['HSN19_SGST'] = match.group(4).strip()
            data['HSN19_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted HSN19 values")
            break
    else:
        data['HSN19_Value'] = ""
        data['HSN19_IGST'] = ""
        data['HSN19_CGST'] = ""
        data['HSN19_SGST'] = ""
        data['HSN19_Cess'] = ""
    
    return data

def extract_summary_values(text):
    """Enhanced extraction for Summary (Page 2 Total) with multiple patterns."""
    data = {}
    
    # Summary total with multiple patterns
    summary_patterns = [
        r'Summary\s*\(Page\s*2\s*Total\)\s*(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'Summary.*?Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'Page\s*2\s*Total\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        r'Total Liability\s*\(Outward supplies[^)]+\)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['Summary_Value'] = match.group(1).strip()
            data['Summary_IGST'] = match.group(2).strip()
            data['Summary_CGST'] = match.group(3).strip()
            data['Summary_SGST'] = match.group(4).strip()
            data['Summary_Cess'] = match.group(5).strip()
            logger.info("Successfully extracted Summary values")
            break
    else:
        data['Summary_Value'] = ""
        data['Summary_IGST'] = ""
        data['Summary_CGST'] = ""
        data['Summary_SGST'] = ""
        data['Summary_Cess'] = ""
        logger.warning("Failed to extract Summary values")
    
    return data

def calculate_summary_statistics(data):
    """Calculate summary statistics and add to data."""
    summary_stats = {}
    
    # Calculate totals for major tables
    try:
        # Table 4A + 4B totals
        table_4a_value = safe_float(data.get('4A_Value', 0))
        table_4b_value = safe_float(data.get('4B_Value', 0))
        summary_stats['Total_B2B_Value'] = table_4a_value + table_4b_value
        
        # Table 6A + 6B + 6C totals
        table_6a_value = safe_float(data.get('6A_Value', 0))
        table_6b_value = safe_float(data.get('6B_Value', 0))
        table_6c_value = safe_float(data.get('6C_Value', 0))
        summary_stats['Total_Export_Value'] = table_6a_value + table_6b_value + table_6c_value
        
        # Table 7 + 8 totals
        table_7_value = safe_float(data.get('7_Value', 0))
        table_8_total = safe_float(data.get('8_Total', 0))
        summary_stats['Total_B2C_Value'] = table_7_value + table_8_total
        
        # Calculate total taxable supplies
        summary_stats['Total_Taxable_Supplies'] = (
            safe_float(data.get('4A_Value', 0)) +
            safe_float(data.get('4B_Value', 0)) +
            safe_float(data.get('5_Value', 0)) +
            safe_float(data.get('6A_Value', 0)) +
            safe_float(data.get('6B_Value', 0)) +
            safe_float(data.get('6C_Value', 0)) +
            safe_float(data.get('7_Value', 0)) +
            safe_float(data.get('14_Value', 0)) +
            safe_float(data.get('15_Value', 0))
        )
        
        # Calculate total tax amounts
        summary_stats['Total_IGST'] = (
            safe_float(data.get('4A_IGST', 0)) +
            safe_float(data.get('4B_IGST', 0)) +
            safe_float(data.get('5_IGST', 0)) +
            safe_float(data.get('6A_IGST', 0)) +
            safe_float(data.get('6B_IGST', 0)) +
            safe_float(data.get('6C_IGST', 0)) +
            safe_float(data.get('7_IGST', 0)) +
            safe_float(data.get('14_IGST', 0)) +
            safe_float(data.get('15_IGST', 0))
        )
        
        summary_stats['Total_CGST'] = (
            safe_float(data.get('4A_CGST', 0)) +
            safe_float(data.get('4B_CGST', 0)) +
            safe_float(data.get('6C_CGST', 0)) +
            safe_float(data.get('7_CGST', 0)) +
            safe_float(data.get('14_CGST', 0)) +
            safe_float(data.get('15_CGST', 0))
        )
        
        summary_stats['Total_SGST'] = (
            safe_float(data.get('4A_SGST', 0)) +
            safe_float(data.get('4B_SGST', 0)) +
            safe_float(data.get('6C_SGST', 0)) +
            safe_float(data.get('7_SGST', 0)) +
            safe_float(data.get('14_SGST', 0)) +
            safe_float(data.get('15_SGST', 0))
        )
        
        summary_stats['Total_Cess'] = (
            safe_float(data.get('4A_Cess', 0)) +
            safe_float(data.get('4B_Cess', 0)) +
            safe_float(data.get('5_Cess', 0)) +
            safe_float(data.get('6A_Cess', 0)) +
            safe_float(data.get('6B_Cess', 0)) +
            safe_float(data.get('6C_Cess', 0)) +
            safe_float(data.get('7_Cess', 0)) +
            safe_float(data.get('15_Cess', 0))
        )
        
        logger.info("Successfully calculated summary statistics")
        
    except Exception as e:
        logger.error(f"Error calculating summary statistics: {str(e)}")
        summary_stats['Total_B2B_Value'] = 0
        summary_stats['Total_Export_Value'] = 0
        summary_stats['Total_B2C_Value'] = 0
        summary_stats['Total_Taxable_Supplies'] = 0
        summary_stats['Total_IGST'] = 0
        summary_stats['Total_CGST'] = 0
        summary_stats['Total_SGST'] = 0
        summary_stats['Total_Cess'] = 0
    
    return summary_stats
def validate_extracted_data(data):
    """Perform comprehensive validation on extracted data."""
    try:
        validation_results = {}

        # Required fields validation
        required_fields = [
            'GSTIN', 'LegalName', 'ARN', 'ARNDate', 'TaxPeriod',
            'FinancialYear', 'VerificationDate', 'AuthorizedSignatory', 'Designation'
        ]
        for field in required_fields:
            if not data.get(field):
                validation_results[f'{field}_missing'] = True
                validation_results[f'{field}_validation'] = 'FAILED'
            else:
                validation_results[f'{field}_missing'] = False
                validation_results[f'{field}_validation'] = 'PASSED'

        # GSTIN format validation
        gstin = data.get('GSTIN', '')
        if gstin and len(gstin) == 15 and gstin.isalnum():
            validation_results['GSTIN_format'] = 'VALID'
        else:
            validation_results['GSTIN_format'] = 'INVALID'

        # ARN format validation
        arn = data.get('ARN', '')
        if arn and arn.isalnum():
            validation_results['ARN_format'] = 'VALID'
        else:
            validation_results['ARN_format'] = 'INVALID'

        # Date format validation
        date_fields = ['ARNDate', 'VerificationDate']
        for field in date_fields:
            date_value = data.get(field, '')
            if date_value and re.match(r'\d{2}/\d{2}/\d{4}', date_value):
                validation_results[f'{field}_format'] = 'VALID'
            else:
                validation_results[f'{field}_format'] = 'INVALID'

        # Tax period validation
        tax_period = data.get('TaxPeriod', '')
        if tax_period and re.match(r'[A-Za-z]+', tax_period):
            validation_results['TaxPeriod_format'] = 'VALID'
        else:
            validation_results['TaxPeriod_format'] = 'INVALID'

        # Financial year validation
        fy = data.get('FinancialYear', '')
        if fy and re.match(r'\d{4}-\d{2}', fy):
            validation_results['FinancialYear_format'] = 'VALID'
        else:
            validation_results['FinancialYear_format'] = 'INVALID'

        # Summary validation
        summary_value = safe_float(data.get('Summary_Value', 0))
        calculated_total = safe_float(data.get('Total_Taxable_Supplies', 0))
        if summary_value > 0 and calculated_total > 0:
            difference = abs(summary_value - calculated_total)
            if difference < 100:
                validation_results['Summary_consistency'] = 'PASSED'
            else:
                validation_results['Summary_consistency'] = 'FAILED'
                validation_results['Summary_difference'] = difference
        else:
            validation_results['Summary_consistency'] = 'NOT_AVAILABLE'

        # Overall validation score
        passed_validations = sum(1 for v in validation_results.values() if v in ('PASSED', 'VALID'))
        total_validations = len([v for v in validation_results.values() if isinstance(v, str) and v in ('PASSED', 'FAILED', 'VALID', 'INVALID')])
        if total_validations > 0:
            validation_score = (passed_validations / total_validations) * 100
            validation_results['Overall_Validation_Score'] = round(validation_score, 2)
            if validation_score >= 80:
                validation_results['Overall_Status'] = 'EXCELLENT'
            elif validation_score >= 60:
                validation_results['Overall_Status'] = 'GOOD'
            elif validation_score >= 40:
                validation_results['Overall_Status'] = 'FAIR'
            else:
                validation_results['Overall_Status'] = 'POOR'
        else:
            validation_results['Overall_Validation_Score'] = 0
            validation_results['Overall_Status'] = 'NOT_AVAILABLE'

        logger.info(f"Validation completed. Overall score: {validation_results.get('Overall_Validation_Score', 0)}%")
        return validation_results

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'Overall_Validation_Score': 0,
            'Overall_Status': 'VALIDATION_ERROR',
            '_validation_error': str(e)
        }

def process_directory(directory_path, output_file):
    """Process all PDF files in a directory and generate comprehensive output."""
    all_data = []
    
    try:
        # Get all PDF files in the directory
        pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory_path}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF file
        for pdf_file in pdf_files:
            pdf_path = os.path.join(directory_path, pdf_file)
            logger.info(f"Processing {pdf_file}...")
            
            try:
                data = extract_gstr1_data(pdf_path)
                all_data.append(data)
                logger.info(f"Successfully processed {pdf_file}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                error_data = {
                    'FileName': pdf_file,
                    'parsing_error': str(e),
                    'processing_status': 'FAILED'
                }
                all_data.append(error_data)
        
        # Create DataFrame and save to Excel
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Save to Excel with multiple sheets
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='GSTR1_Data', index=False)
                
                # Summary statistics sheet
                summary_columns = ['FileName','GSTIN','LegalName','TradeName','ARN','TaxPeriod','FinancialYear','Summary_Value','Summary_IGST','Summary_CGST','Summary_SGST','Summary_Cess','Total_B2B_Value','Total_Export_Value','Total_B2C_Value','Total_Taxable_Supplies','Total_IGST','Total_CGST','Total_SGST','Total_Cess','Overall_Validation_Score','Overall_Status','processing_status']

                available = [c for c in summary_columns if c in df.columns]

                summary_df = df[available].copy()
                summary_df.to_excel(writer, sheet_name='Summary_Statistics', index=False)
                
                # Validation results sheet
                validation_columns = [col for col in df.columns if 'validation' in col.lower() or 'missing' in col.lower()]
                if validation_columns:
                    validation_df = df[['FileName'] + validation_columns].copy()
                    validation_df.to_excel(writer, sheet_name='Validation_Results', index=False)
            
            logger.info(f"Successfully saved data to {output_file}")
            logger.info(f"Total files processed: {len(all_data)}")
            
            # Print summary
            successful_files = len([d for d in all_data if 'parsing_error' not in d])
            failed_files = len([d for d in all_data if 'parsing_error' in d])
            
            print(f"\n=== GSTR-1 Processing Summary ===")
            print(f"Total files: {len(all_data)}")
            print(f"Successful: {successful_files}")
            print(f"Failed: {failed_files}")
            print(f"Output saved to: {output_file}")
            
        else:
            logger.error("No data to save")
            
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {str(e)}")
        logger.error(traceback.format_exc())

def process_json_directory(directory_path, output_file):
    """Process all JSON files in a directory and generate comprehensive output."""
    from json_import import extract_gstr1_from_json, load_json_file

    all_data = []

    try:
        # Get all JSON files in the directory
        json_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.json')]

        if not json_files:
            logger.warning(f"No JSON files found in {directory_path}")
            return

        logger.info(f"Found {len(json_files)} JSON files to process")

        # Process each JSON file
        for json_file in json_files:
            json_path = os.path.join(directory_path, json_file)
            logger.info(f"Processing {json_file}...")

            try:
                json_data = load_json_file(json_path)
                data = extract_gstr1_from_json(json_data)
                data['FileName'] = json_file
                all_data.append(data)
                logger.info(f"Successfully processed {json_file}")

            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")
                error_data = {
                    'FileName': json_file,
                    'parsing_error': str(e),
                    'processing_status': 'FAILED'
                }
                all_data.append(error_data)

        # Create DataFrame and save to Excel
        if all_data:
            df = pd.DataFrame(all_data)

            # Save to Excel with multiple sheets
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='GSTR1_Data', index=False)

                # Summary statistics sheet
                summary_columns = ['FileName', 'GSTIN', 'LegalName', 'TaxPeriod', 'FinancialYear']
                numeric_columns = ['4A_Value', '4A_IGST', '4A_CGST', '4A_SGST', '4A_Cess',
                                 '5_Value', '5_IGST', '6A_Value', '6A_IGST', '7_Value']

                available_columns = [col for col in summary_columns + numeric_columns if col in df.columns]
                summary_df = df[available_columns].copy()
                summary_df.to_excel(writer, sheet_name='Summary_Statistics', index=False)

            logger.info(f"Successfully saved data to {output_file}")
            logger.info(f"Total files processed: {len(all_data)}")

            # Print summary
            successful_files = len([d for d in all_data if 'parsing_error' not in d])
            failed_files = len([d for d in all_data if 'parsing_error' in d])

            print(f"\n=== GSTR-1 JSON Processing Summary ===")
            print(f"Total files: {len(all_data)}")
            print(f"Successful: {successful_files}")
            print(f"Failed: {failed_files}")
            print(f"Output saved to: {output_file}")

        else:
            logger.error("No data to save")

    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """Main function to run the GSTR-1 extraction tool."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract GSTR-1 data from PDF or JSON files')
    parser.add_argument('--input', '-i', required=True, help='Input directory containing PDF or JSON files')
    parser.add_argument('--output', '-o', required=True, help='Output Excel file path')
    parser.add_argument('--format', '-f', choices=['pdf', 'json'], default='pdf', help='Input file format (pdf or json)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not os.path.exists(args.input):
        print(f"Error: Input directory '{args.input}' does not exist")
        return

    if not os.path.isdir(args.input):
        print(f"Error: '{args.input}' is not a directory")
        return

    print(f"Starting GSTR-1 extraction from: {args.input}")
    print(f"Input format: {args.format.upper()}")
    print(f"Output will be saved to: {args.output}")

    if args.format == 'pdf':
        process_directory(args.input, args.output)
    else:
        process_json_directory(args.input, args.output)

    print("GSTR-1 extraction completed!")

if __name__ == "__main__":
    main()