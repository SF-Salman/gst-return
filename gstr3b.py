import pandas as pd
import numpy as np
import pdfplumber
import re
import io
import os
import tempfile
from datetime import datetime
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import time
import traceback
import logging
import fitz  

def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def safe_float(value):
    try:
        return round(float(value), 2) if value and value != "-" else 0.0
    except (ValueError, TypeError):
        return 0.0

def clean_cell(val):
    if not val:
        return val
    s = str(val).strip()
    # Strip one or more leading watermark letters (e.g. F, I, L, E, D from "FILED")
    s = re.sub(r'^([A-Z]\n)+', '', s)
    # Rejoin numbers split by a newline after a decimal point e.g. "1438415.\n00"
    s = re.sub(r'\.\n(\d)', r'.\1', s)
    # Rejoin numbers split mid-digit e.g. "565960.0\n0"
    s = re.sub(r'(\d)\n(\d)', r'\1\2', s)
    s = re.sub(r'(\d)\n\.(\d)', r'\1.\2', s)
    return s

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_gstin(gstin):
    """Validate GSTIN format: 22AAAAA0000A1Z5"""
    if not gstin:
        return False
    pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9]$'
    return bool(re.match(pattern, gstin))

def parse_date(date_str):
    """Parse date from DD/MM/YYYY format"""
    try:
        if date_str:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        return None
    except ValueError:
        logger.error(f"Failed to parse date: {date_str}")
        return None

def remove_watermarks(page):
    width = page.width
    height = page.height
    crop_box = (0, height * 0.05, width, height * 0.95)
    return page.crop(crop_box)

def extract_text_with_watermark_handling(pdf_path):
    all_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    cleaned_page = remove_watermarks(page)
                    text = cleaned_page.extract_text()
                except:
                    text = page.extract_text()
                if text:
                    all_text += text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        logger.error(traceback.format_exc())
    return all_text

def extract_tables_from_pdf(pdf_path):
    all_tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    cleaned_page = remove_watermarks(page)
                    tables = cleaned_page.extract_tables()
                except:
                    tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        logger.error(traceback.format_exc())
    return all_tables

def find_value_by_regex(text, pattern, default=""):
    try:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return default
    except re.error as e:
        logger.error(f"Regex error with pattern '{pattern}': {str(e)}")
        return default

def extract_auth_signatory(text):
    auth_info = {}
    signatory_patterns = [
        r'Authorized\s+Signatory\s*:\s*([^\r\n]+)',
        r'Name\s+of\s+Authorised\s+Signatory\s*:?\s*([^\r\n]+)',
        r'Authorised\s+Signatory\s*:?\s*([^\r\n]+)',
        r'Authorized\s+Signatory\s*:?\s*([^\r\n]+)',
        r'Name\s+of\s+Authorized\s+Signatory\s*:?\s*([^\r\n]+)'
    ]
    for pattern in signatory_patterns:
        signatory_match = re.search(pattern, text, re.IGNORECASE)
        if signatory_match:
            auth_info['authorized_signatory'] = signatory_match.group(1).strip()
            logger.info(f"Found authorized signatory: {auth_info['authorized_signatory']}")
            break
    designation_patterns = [
        r'Designation\s*/?.\s*Status\s*:?\s*([^\r\n]+)',
        r'Designation\s*:?\s*([^\r\n]+)',
        r'Status\s*:?\s*([^\r\n]+)'
    ]
    for pattern in designation_patterns:
        designation_match = re.search(pattern, text, re.IGNORECASE)
        if designation_match:
            designation = designation_match.group(1).strip()
            designation = designation.replace('/Status', '').strip()
            auth_info['designation'] = designation
            logger.info(f"Found designation: {auth_info['designation']}")
            break
    return auth_info

def extract_verification_details(text):
    details = {}
    try:
        verification_date = find_value_by_regex(
            text,
            r'(?:Verification\s*Date|Date\s*of\s*Verification)\s*:?\s*(\d{2}/\d{2}/\d{4})',
            ''
        )
        if verification_date:
            details['verification_date'] = verification_date
    except Exception as e:
        logger.error(f"Error extracting verification date: {str(e)}")
    try:
        verification_place = find_value_by_regex(
            text,
            r'Place(?:\s*of\s*Verification)?\s*:?\s*([^\r\n]+)',
            ''
        )
        if verification_place:
            details['verification_place'] = verification_place.strip()
    except Exception as e:
        logger.error(f"Error extracting verification place: {str(e)}")
    return details

def extract_outward_supplies(tables):
    outward_supplies = {}
    section_3_1 = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if any(x in row_text for x in ["3.1 details of outward supplies", "outward taxable supplies"]):
                    section_3_1 = True
                    logger.info("Found table 3.1")
                if not section_3_1:
                    continue
                # Inward supplies liable to reverse charge (3.1(d))
                # Apply clean_cell to strip watermark artifacts before parsing
                if "(d)" in row_text and "inward supplies" in row_text and "reverse charge" in row_text:
                    try:
                        outward_supplies['inward_reverse_charge_value'] = safe_float(clean_cell(row[1]))
                        outward_supplies['inward_reverse_charge_igst']  = safe_float(clean_cell(row[2]))
                        outward_supplies['inward_reverse_charge_cgst']  = safe_float(clean_cell(row[3]))
                        outward_supplies['inward_reverse_charge_sgst']  = safe_float(clean_cell(row[4]))
                        outward_supplies['inward_reverse_charge_cess']  = safe_float(clean_cell(row[5])) if len(row) > 5 else 0.0
                        logger.info(f"Extracted 3.1(d) reverse charge: {outward_supplies['inward_reverse_charge_value']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing 3.1(d) reverse charge: {str(e)}")
                elif "outward taxable supplies (other than zero rated" in row_text:
                    try:
                        outward_supplies['outward_taxable_value'] = safe_float(clean_cell(row[1]))
                        outward_supplies['outward_igst']          = safe_float(clean_cell(row[2]))
                        outward_supplies['outward_cgst']          = safe_float(clean_cell(row[3]))
                        outward_supplies['outward_sgst']          = safe_float(clean_cell(row[4]))
                        outward_supplies['outward_cess']          = safe_float(clean_cell(row[5])) if len(row) > 5 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "zero rated" in row_text:
                    try:
                        outward_supplies['zero_rated_value'] = safe_float(clean_cell(row[1]))
                        outward_supplies['zero_rated_igst']  = safe_float(clean_cell(row[2]))
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "nil rated, exempted" in row_text:
                    try:
                        outward_supplies['nil_exempt_value'] = safe_float(clean_cell(row[1]))
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "non-gst outward supplies" in row_text:
                    try:
                        outward_supplies['non_gst_value'] = safe_float(clean_cell(row[1]))
                    except (ValueError, TypeError, IndexError):
                        pass
                if "3.1.1" in row_text or "3.2" in row_text:
                    section_3_1 = False
    return outward_supplies

def extract_supplies_9_5(tables):
    supplies_9_5 = {
        'ecom_operator': {},
        'registered_person': {}
    }
    section_9_5_found = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if any(x in row_text for x in ["3.1.1", "section 9(5)", "supplies notified"]):
                    section_9_5_found = True
                    logger.info("Found section 3.1.1")
                    continue
                if not section_9_5_found:
                    continue
                if "electronic commerce operator pays tax" in row_text:
                    try:
                        supplies_9_5['ecom_operator'] = {
                            'value': safe_float(clean_cell(row[1])),
                            'igst':  safe_float(clean_cell(row[2])),
                            'cgst':  safe_float(clean_cell(row[3])),
                            'sgst':  safe_float(clean_cell(row[4])),
                            'cess':  safe_float(clean_cell(row[5])) if len(row) > 5 else 0.0
                        }
                        logger.info(f"Extracted ecom operator: {supplies_9_5['ecom_operator']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing ecom operator: {str(e)}")
                elif "through electronic commerce operator" in row_text:
                    try:
                        supplies_9_5['registered_person'] = {
                            'value': safe_float(clean_cell(row[1])),
                            'igst':  safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0,
                            'cgst':  safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                            'sgst':  safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0,
                            'cess':  safe_float(clean_cell(row[5])) if len(row) > 5 else 0.0
                        }
                        logger.info(f"Extracted registered person: {supplies_9_5['registered_person']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing registered person: {str(e)}")
                elif any(x in row_text for x in ["3.2", "out of supplies"]):
                    break
    flat_result = {}
    for key, sub_dict in supplies_9_5.items():
        for sub_key, value in sub_dict.items():
            flat_result[f"sec_9_5_{key}_{sub_key}"] = value
    return flat_result

def extract_interstate_supplies(tables):
    """Extract Table 3.2 - inter-state supplies made to unregistered/composition/UIN."""
    interstate_supplies = {}
    for table in tables:
        for row in table:
            if row and len(row) > 1:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if "unregistered" in row_text:
                    try:
                        interstate_supplies['interstate_unreg_value'] = safe_float(clean_cell(row[1]))
                        interstate_supplies['interstate_unreg_igst']  = safe_float(clean_cell(row[2]))
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing unregistered: {str(e)}")
                elif "composition" in row_text and "taxable" in row_text:
                    # NOTE: matching on bare "composition" also caught Table 5's
                    # "From a supplier under composition scheme..." row (which
                    # appears later in the table list and silently overwrote
                    # this value with 0.00). "composition taxable" is specific
                    # to this Table 3.2 row.
                    try:
                        interstate_supplies['interstate_composition_value'] = safe_float(clean_cell(row[1]))
                        interstate_supplies['interstate_composition_igst']  = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing composition: {str(e)}")
                elif "uin" in row_text:
                    try:
                        interstate_supplies['interstate_uin_value'] = safe_float(clean_cell(row[1]))
                        interstate_supplies['interstate_uin_igst']  = safe_float(clean_cell(row[2]))
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing UIN: {str(e)}")
    return interstate_supplies

def extract_eligible_itc(tables):
    eligible_itc = {}
    itc_section = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if "itc available" in row_text or "a. itc available" in row_text:
                    itc_section = True
                    logger.info("Found ITC Available section")
                    continue
                if not itc_section:
                    continue
                if "inward supplies" in row_text and "reverse charge" in row_text and "other than 1 & 2" in row_text:
                    try:
                        eligible_itc['reverse_charge_itc_igst'] = safe_float(clean_cell(row[1]))
                        eligible_itc['reverse_charge_itc_cgst'] = safe_float(clean_cell(row[2]))
                        eligible_itc['reverse_charge_itc_sgst'] = safe_float(clean_cell(row[3]))
                        eligible_itc['reverse_charge_itc_cess'] = safe_float(clean_cell(row[4]))
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing 4(3) reverse charge: {str(e)}")
                elif "import of goods" in row_text:
                    try:
                        eligible_itc['import_goods_igst'] = safe_float(clean_cell(row[1]))
                        eligible_itc['import_goods_cgst'] = safe_float(clean_cell(row[2]))
                        eligible_itc['import_goods_sgst'] = safe_float(clean_cell(row[3]))
                        eligible_itc['import_goods_cess'] = safe_float(clean_cell(row[4]))
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "import of services" in row_text:
                    try:
                        eligible_itc['import_services_igst'] = safe_float(clean_cell(row[1]))
                        eligible_itc['import_services_cgst'] = safe_float(clean_cell(row[2]))
                        eligible_itc['import_services_sgst'] = safe_float(clean_cell(row[3]))
                        eligible_itc['import_services_cess'] = safe_float(clean_cell(row[4]))
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "inward supplies from isd" in row_text:
                    try:
                        eligible_itc['isd_igst'] = safe_float(clean_cell(row[1]))
                        eligible_itc['isd_cgst'] = safe_float(clean_cell(row[2]))
                        eligible_itc['isd_sgst'] = safe_float(clean_cell(row[3]))
                        eligible_itc['isd_cess'] = safe_float(clean_cell(row[4]))
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "all other itc" in row_text:
                    try:
                        eligible_itc['other_itc_igst'] = safe_float(clean_cell(row[1]))
                        eligible_itc['other_itc_cgst'] = safe_float(clean_cell(row[2]))
                        eligible_itc['other_itc_sgst'] = safe_float(clean_cell(row[3]))
                        eligible_itc['other_itc_cess'] = safe_float(clean_cell(row[4]))
                    except (ValueError, TypeError, IndexError):
                        pass
                if "itc reversed" in row_text:
                    return eligible_itc
    return eligible_itc
def extract_isd_itc_fallback(all_text):
    """
    Fallback for Table 4A(4) — Inward supplies from ISD.
    pdfplumber's extract_tables() unreliably splits this row because the
    "FILED" watermark sits directly in front of "(4)" in the source PDF,
    corrupting the column boundaries pdfplumber detects for this row only.
    Anchoring on "(4)" in the plain extracted text (unaffected by table-grid
    corruption) is far more reliable — same approach as the 3.1(d) fix above.
    """
    isd = {}
    match = re.search(
        r'\(4\)\s*Inward\s+supplies\s+from\s+ISD\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)',
        all_text, re.IGNORECASE
    )
    if match:
        isd['isd_igst'] = safe_float(clean_cell(match.group(1)))
        isd['isd_cgst'] = safe_float(clean_cell(match.group(2)))
        isd['isd_sgst'] = safe_float(clean_cell(match.group(3)))
        isd['isd_cess'] = safe_float(clean_cell(match.group(4)))
        logger.info(f"Extracted ISD via text fallback: {isd}")
    else:
        logger.warning("ISD text fallback also failed to match")
    return isd
def extract_itc_reversed(tables):
    itc_reversed = {}
    itc_reversed_section = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "ITC Reversed" in row_text or "B. ITC Reversed" in row_text:
                    itc_reversed_section = True
                    continue
                if not itc_reversed_section:
                    continue
                if "As per rules" in row_text or "rules 38,42 & 43" in row_text:
                    try:
                        itc_reversed['rules_igst'] = safe_float(clean_cell(row[1]))
                        itc_reversed['rules_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        itc_reversed['rules_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        itc_reversed['rules_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "Others" in row_text:
                    try:
                        itc_reversed['others_igst'] = safe_float(clean_cell(row[1]))
                        itc_reversed['others_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        itc_reversed['others_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        itc_reversed['others_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "Net ITC available" in row_text or "C. Net ITC available" in row_text:
                    break
    return itc_reversed

def extract_net_itc(tables):
    net_itc = {}
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "Net ITC available" in row_text or "C. Net ITC available" in row_text:
                    try:
                        net_itc['net_itc_igst'] = safe_float(clean_cell(row[1]))
                        net_itc['net_itc_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        net_itc['net_itc_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        net_itc['net_itc_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                    break
    return net_itc

def extract_other_details(tables):
    other_details = {}
    other_details_section = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "(D) Other Details" in row_text:
                    other_details_section = True
                    continue
                if not other_details_section:
                    continue
                if "ITC reclaimed" in row_text:
                    try:
                        other_details['itc_reclaimed_igst'] = safe_float(clean_cell(row[1]))
                        other_details['itc_reclaimed_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        other_details['itc_reclaimed_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        other_details['itc_reclaimed_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "Ineligible ITC" in row_text:
                    try:
                        other_details['ineligible_itc_igst'] = safe_float(clean_cell(row[1]))
                        other_details['ineligible_itc_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        other_details['ineligible_itc_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        other_details['ineligible_itc_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                    break
    return other_details

def extract_exempt_supplies(tables):
    exempt_supplies = {}
    for table in tables:
        for row in table:
            if row and len(row) > 2:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "From a supplier under composition scheme" in row_text:
                    try:
                        exempt_supplies['composition_inter_state'] = safe_float(clean_cell(row[1]))
                        exempt_supplies['composition_intra_state'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "Non GST supply" in row_text:
                    try:
                        exempt_supplies['non_gst_inter_state'] = safe_float(clean_cell(row[1]))
                        exempt_supplies['non_gst_intra_state'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
    return exempt_supplies

def extract_interest_late_fee(tables):
    interest_late_fee = {}
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "Interest Paid" in row_text:
                    try:
                        interest_late_fee['interest_igst'] = safe_float(clean_cell(row[1]))
                        interest_late_fee['interest_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        interest_late_fee['interest_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                        interest_late_fee['interest_cess'] = safe_float(clean_cell(row[4])) if len(row) > 4 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "Late fee" in row_text:
                    try:
                        interest_late_fee['late_fee_igst'] = safe_float(clean_cell(row[1])) if row[1] and row[1] != "-" else 0.0
                        interest_late_fee['late_fee_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 and row[2] and row[2] != "-" else 0.0
                        interest_late_fee['late_fee_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 and row[3] and row[3] != "-" else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
    return interest_late_fee

def extract_payment_details(tables):
    """
    Extract Table 6.1 Payment of Tax.

    Government form column order (11 columns, 0-indexed):
      0  Description
      1  Tax payable
      2  Adjustment of negative liability of previous tax period
      3  Net Tax Payable
      4  ITC paid — Integrated tax
      5  ITC paid — Central tax
      6  ITC paid — State/UT tax
      7  ITC paid — Cess
      8  Tax paid in cash
      9  Interest paid in cash
      10 Late fee paid in cash
    """

    payment_details = {
        'normal': {},
        'reverse_charge': {}
    }

    normal_section = False
    reverse_charge_section = False

    for table in tables:
        for row in table:

            if row and len(row) > 3:

                # Skip split header
                if row[0] in ('Descripti', 'on'):
                    continue

                row_text = ' '.join(
                    [str(cell) for cell in row if cell]
                ).lower()

                logger.debug(f"Payment row: {row_text}")

                # Section detection
                if "(a) other than reverse charge" in row_text:
                    normal_section = True
                    reverse_charge_section = False
                    continue

                if "(b) reverse charge" in row_text:
                    normal_section = False
                    reverse_charge_section = True
                    continue

                # ======================
                # NORMAL SECTION
                # ======================

                if normal_section:

                    if "integrated" in row_text and len(row) > 4:
                        try:
                            payment_details['normal'].update({
                                'igst_payable': safe_float(clean_cell(row[1])),
                                'igst_adjustment': safe_float(clean_cell(row[2])),
                                'igst_net_payable': safe_float(clean_cell(row[3])),
                                'igst_paid_itc_igst': safe_float(clean_cell(row[4])),
                                'igst_paid_itc_cgst': safe_float(clean_cell(row[5])),
                                'igst_paid_itc_sgst': safe_float(clean_cell(row[6])),
                                'igst_paid_itc_cess': safe_float(clean_cell(row[7])),
                                'igst_paid_cash': safe_float(clean_cell(row[8])),
                                'igst_interest': safe_float(clean_cell(row[9])) if len(row) > 9 else 0.0,
                                'igst_late_fee': safe_float(clean_cell(row[10])) if len(row) > 10 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal IGST: {str(e)}")

                    elif "central" in row_text and len(row) > 4:
                        try:
                            payment_details['normal'].update({
                                'cgst_payable': safe_float(clean_cell(row[1])),
                                'cgst_adjustment': safe_float(clean_cell(row[2])),
                                'cgst_net_payable': safe_float(clean_cell(row[3])),
                                'cgst_paid_itc_igst': safe_float(clean_cell(row[4])),
                                'cgst_paid_itc_cgst': safe_float(clean_cell(row[5])),
                                'cgst_paid_itc_sgst': safe_float(clean_cell(row[6])),
                                'cgst_paid_itc_cess': safe_float(clean_cell(row[7])),
                                'cgst_paid_cash': safe_float(clean_cell(row[8])),
                                'cgst_interest': safe_float(clean_cell(row[9])) if len(row) > 9 else 0.0,
                                'cgst_late_fee': safe_float(clean_cell(row[10])) if len(row) > 10 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal CGST: {str(e)}")

                    elif "state" in row_text and len(row) > 4:
                        try:
                            payment_details['normal'].update({
                                'sgst_payable': safe_float(clean_cell(row[1])),
                                'sgst_adjustment': safe_float(clean_cell(row[2])),
                                'sgst_net_payable': safe_float(clean_cell(row[3])),
                                'sgst_paid_itc_igst': safe_float(clean_cell(row[4])),
                                'sgst_paid_itc_cgst': safe_float(clean_cell(row[5])),
                                'sgst_paid_itc_sgst': safe_float(clean_cell(row[6])),
                                'sgst_paid_itc_cess': safe_float(clean_cell(row[7])),
                                'sgst_paid_cash': safe_float(clean_cell(row[8])),
                                'sgst_interest': safe_float(clean_cell(row[9])) if len(row) > 9 else 0.0,
                                'sgst_late_fee': safe_float(clean_cell(row[10])) if len(row) > 10 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal SGST: {str(e)}")

                    elif "cess" in row_text and len(row) > 4:
                        try:
                            payment_details['normal'].update({
                                'cess_payable': safe_float(clean_cell(row[1])),
                                'cess_adjustment': safe_float(clean_cell(row[2])),
                                'cess_net_payable': safe_float(clean_cell(row[3])),
                                'cess_paid_itc_igst': safe_float(clean_cell(row[4])),
                                'cess_paid_itc_cgst': safe_float(clean_cell(row[5])),
                                'cess_paid_itc_sgst': safe_float(clean_cell(row[6])),
                                'cess_paid_itc_cess': safe_float(clean_cell(row[7])),
                                'cess_paid_cash': safe_float(clean_cell(row[8])),
                                'cess_interest': safe_float(clean_cell(row[9])) if len(row) > 9 else 0.0,
                                'cess_late_fee': safe_float(clean_cell(row[10])) if len(row) > 10 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal Cess: {str(e)}")

                # ======================
                # REVERSE CHARGE SECTION
                # ======================

                elif reverse_charge_section:

                    if "integrated" in row_text and len(row) > 8:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_igst_payable': safe_float(clean_cell(row[1])),
                                'rc_igst_net_payable': safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                                'rc_igst_paid_cash': safe_float(clean_cell(row[8])) if len(row) > 8 else safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC IGST: {str(e)}")

                    elif "central" in row_text and len(row) > 8:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_cgst_payable': safe_float(clean_cell(row[1])),
                                'rc_cgst_net_payable': safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                                'rc_cgst_paid_cash': safe_float(clean_cell(row[8])) if len(row) > 8 else safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC CGST: {str(e)}")

                    elif "state" in row_text and len(row) > 8:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_sgst_payable': safe_float(clean_cell(row[1])),
                                'rc_sgst_net_payable': safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                                'rc_sgst_paid_cash': safe_float(clean_cell(row[8])) if len(row) > 8 else safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC SGST: {str(e)}")

                    elif "cess" in row_text and len(row) > 8:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_cess_payable': safe_float(clean_cell(row[1])),
                                'rc_cess_net_payable': safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                                'rc_cess_paid_cash': safe_float(clean_cell(row[8])) if len(row) > 8 else safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0,
                            })

                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC Cess: {str(e)}")

    logger.info(f"Payment details extracted: {payment_details}")
    return payment_details

def extract_reverse_charge_supplies(tables):
    """Extract Table 3.1(d) - Inward supplies (liable to reverse charge)."""
    reverse_charge = {}
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                # NOTE: matching on the bare phrase "Inward supplies liable to
                # reverse charge" also matched Table 4A(3)'s ITC row --
                # "(3) Inward supplies liable to reverse charge (other than 1 &
                # 2 above)" -- since Table 3.1(d)'s actual text has
                # parentheses ("Inward supplies (liable to reverse charge)")
                # that don't match the phrase, extraction silently fell
                # through to the wrong (ITC) row. Anchor on the "(d)" prefix,
                # which is unique to Table 3.1(d), and exclude the ITC row
                # explicitly as a second safeguard.
                if (row[0] and str(row[0]).strip().startswith("(d)")
                        and "reverse charge" in row_text.lower()
                        and "other than 1 & 2 above" not in row_text.lower()):
                    try:                        
                        reverse_charge['inward_reverse_charge_value'] = safe_float(clean_cell(row[1])) if row[1] and row[1] != "-" else 0.0
                        reverse_charge['inward_reverse_charge_igst']  = safe_float(clean_cell(row[2])) if len(row) > 2 and row[2] and row[2] != "-" else 0.0
                        reverse_charge['inward_reverse_charge_cgst']  = safe_float(clean_cell(row[3])) if len(row) > 3 and row[3] and row[3] != "-" else 0.0
                        reverse_charge['inward_reverse_charge_sgst']  = safe_float(clean_cell(row[4])) if len(row) > 4 and row[4] and row[4] != "-" else 0.0
                        reverse_charge['inward_reverse_charge_cess']  = safe_float(clean_cell(row[5])) if len(row) > 5 and row[5] and row[5] != "-" else 0.0
                        logger.info(f"Found reverse charge supplies: {reverse_charge}")
                        # Add schema-compatible aliases for the Reverse Charge Supplies sheet
                        reverse_charge['reverse_charge_supplies_value'] = reverse_charge.get('inward_reverse_charge_value', 0.0)
                        reverse_charge['reverse_charge_supplies_igst']  = reverse_charge.get('inward_reverse_charge_igst',  0.0)
                        reverse_charge['reverse_charge_supplies_cgst']  = reverse_charge.get('inward_reverse_charge_cgst',  0.0)
                        reverse_charge['reverse_charge_supplies_sgst']  = reverse_charge.get('inward_reverse_charge_sgst',  0.0)
                        reverse_charge['reverse_charge_supplies_cess']  = reverse_charge.get('inward_reverse_charge_cess',  0.0)
                        return reverse_charge
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing reverse charge supplies: {str(e)}")
                        continue
    return reverse_charge

def extract_other_debit_entries(tables):
    other_debit = {}
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "Other Debit Entries" in row_text:
                    try:
                        other_debit['value'] = safe_float(clean_cell(row[1])) if row[1] and row[1] != "-" else None
                        other_debit['igst']  = safe_float(clean_cell(row[2])) if len(row) > 2 and row[2] and row[2] != "-" else None
                        other_debit['cgst']  = safe_float(clean_cell(row[3])) if len(row) > 3 and row[3] and row[3] != "-" else None
                        other_debit['sgst']  = safe_float(clean_cell(row[4])) if len(row) > 4 and row[4] and row[4] != "-" else None
                        other_debit['cess']  = safe_float(clean_cell(row[5])) if len(row) > 5 and row[5] and row[5] != "-" else None
                        return other_debit
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing other debit entries: {str(e)}")
                        continue
    return other_debit

def extract_other_credit_entries(tables):
    other_credit = {}
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                if "Other Credit Entries" in row_text:
                    try:
                        other_credit['value'] = safe_float(clean_cell(row[1])) if row[1] and row[1] != "-" else None
                        other_credit['igst']  = safe_float(clean_cell(row[2])) if len(row) > 2 and row[2] and row[2] != "-" else None
                        other_credit['cgst']  = safe_float(clean_cell(row[3])) if len(row) > 3 and row[3] and row[3] != "-" else None
                        other_credit['sgst']  = safe_float(clean_cell(row[4])) if len(row) > 4 and row[4] and row[4] != "-" else None
                        other_credit['cess']  = safe_float(clean_cell(row[5])) if len(row) > 5 and row[5] and row[5] != "-" else None
                        return other_credit
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing other credit entries: {str(e)}")
                        continue
    return other_credit

def extract_additional_fields(tables):
    """Stub for additional fields — returns empty dict; extend as needed."""
    return {}

def extract_hsn_summary(tables):
    """Extract HSN summary table if present."""
    hsn = {}
    hsn_section = False
    for table in tables:
        for row in table:
            if row and len(row) > 2:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if "hsn" in row_text and ("summary" in row_text or "hsn/sac" in row_text):
                    hsn_section = True
                    continue
                if not hsn_section:
                    continue
                # Stop at next major section
                if any(x in row_text for x in ["tds", "tcs", "verification", "authorized"]):
                    break
    return hsn

def extract_additional_tax_details(tables):
    """Extract TDS/TCS details if present."""
    tax_details = {}
    for table in tables:
        for row in table:
            if row and len(row) > 2:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                if "tds" in row_text and "deducted" in row_text:
                    try:
                        tax_details['tds_igst'] = safe_float(clean_cell(row[1]))
                        tax_details['tds_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        tax_details['tds_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "tcs" in row_text and "collected" in row_text:
                    try:
                        tax_details['tcs_igst'] = safe_float(clean_cell(row[1]))
                        tax_details['tcs_cgst'] = safe_float(clean_cell(row[2])) if len(row) > 2 else 0.0
                        tax_details['tcs_sgst'] = safe_float(clean_cell(row[3])) if len(row) > 3 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
    return tax_details

def parse_gstr3b(pdf_path):
    """Parse GSTR-3B from PDF and return structured data."""
    result = {}
    try:
        all_text = extract_text_with_watermark_handling(pdf_path)

        try:
            result['gstin'] = find_value_by_regex(all_text, r'GSTIN of the supplier\s+(\S+)')
            logger.info(f"Extracted GSTIN: {result['gstin']}")
        except Exception as e:
            logger.error(f"Error extracting GSTIN: {str(e)}")
            result['gstin'] = ""

        try:
            result['legal_name'] = find_value_by_regex(all_text, r'Legal name of the registered person\s+([^\r\n]+)')
        except Exception as e:
            result['legal_name'] = ""

        try:
            result['trade_name'] = find_value_by_regex(all_text, r'Trade name, if any\s+([^\r\n]+)')
        except Exception as e:
            result['trade_name'] = ""

        try:
            auth_info = extract_auth_signatory(all_text)
            result.update(auth_info)
        except Exception as e:
            logger.error(f"Error extracting authorized signatory: {str(e)}")

        result['period']   = find_value_by_regex(all_text, r'Period\s+(\w+)', '')
        result['year']     = find_value_by_regex(all_text, r'Year\s+(\d{4}-\d{2}|\d{4})', '')
        result['arn']      = find_value_by_regex(all_text, r'ARN\s+(\S+)', '')
        result['arn_date'] = find_value_by_regex(all_text, r'Date of ARN\s+(\d{2}/\d{2}/\d{4})', '')

        try:
            verification_details = extract_verification_details(all_text)
            result.update(verification_details)
        except Exception as e:
            logger.error(f"Error extracting verification details: {str(e)}")

        if result['gstin'] and not validate_gstin(result['gstin']):
            if 'validation_errors' not in result:
                result['validation_errors'] = []
            result['validation_errors'].append('Invalid GSTIN format')

        if result['arn_date']:
            result['arn_date_parsed'] = parse_date(result['arn_date'])

        tables = extract_tables_from_pdf(pdf_path)
        logger.info(f"Extracted {len(tables)} tables from PDF")

        try:
            outward_supplies = extract_outward_supplies(tables)
            result.update(outward_supplies)
            # Add schema aliases for Reverse Charge Supplies sheet
            result['reverse_charge_supplies_value'] = outward_supplies.get('inward_reverse_charge_value', 0.0)
            result['reverse_charge_supplies_igst']  = outward_supplies.get('inward_reverse_charge_igst',  0.0)
            result['reverse_charge_supplies_cgst']  = outward_supplies.get('inward_reverse_charge_cgst',  0.0)
            result['reverse_charge_supplies_sgst']  = outward_supplies.get('inward_reverse_charge_sgst',  0.0)
            result['reverse_charge_supplies_cess']  = outward_supplies.get('inward_reverse_charge_cess',  0.0)
        except Exception as e:
            logger.error(f"Error extracting outward supplies: {str(e)}")

        try:
            supplies_9_5 = extract_supplies_9_5(tables)
            result.update(supplies_9_5)
        except Exception as e:
            logger.error(f"Error extracting supplies under section 9(5): {str(e)}")

        try:
            interstate_supplies = extract_interstate_supplies(tables)
            result.update(interstate_supplies)
        except Exception as e:
            logger.error(f"Error extracting interstate supplies: {str(e)}")

        try:
            eligible_itc = extract_eligible_itc(tables)
            result.update(eligible_itc)
        except Exception as e:
            logger.error(f"Error extracting eligible ITC: {str(e)}")

        # Fallback: table-based ISD extraction is unreliable due to the
        # "FILED" watermark corrupting this row's column boundaries.
        if not result.get('isd_igst') and not result.get('isd_cgst') and not result.get('isd_sgst'):
            try:
                isd_fallback = extract_isd_itc_fallback(all_text)
                for k, v in isd_fallback.items():
                    result[k] = v
            except Exception as e:
                logger.error(f"Error in ISD fallback extraction: {str(e)}")

        try:
            itc_reversed = extract_itc_reversed(tables)
            result.update(itc_reversed)
        except Exception as e:
            logger.error(f"Error extracting ITC reversed: {str(e)}")

        try:
            net_itc = extract_net_itc(tables)
            result.update(net_itc)
        except Exception as e:
            logger.error(f"Error extracting net ITC: {str(e)}")

        try:
            other_details = extract_other_details(tables)
            result.update(other_details)
        except Exception as e:
            logger.error(f"Error extracting other details: {str(e)}")

        try:
            exempt_supplies = extract_exempt_supplies(tables)
            result.update(exempt_supplies)
        except Exception as e:
            logger.error(f"Error extracting exempt supplies: {str(e)}")

        try:
            interest_late_fee = extract_interest_late_fee(tables)
            result.update(interest_late_fee)
        except Exception as e:
            logger.error(f"Error extracting interest and late fee: {str(e)}")

        try:
            payment_details = extract_payment_details(tables)
            for key, value in payment_details['normal'].items():
                result[key] = value
            for key, value in payment_details['reverse_charge'].items():
                result[key] = value
        except Exception as e:
            logger.error(f"Error extracting payment details: {str(e)}")

        result['igst_net_payable'] = result.get('igst_net_payable', 0.0) + result.get('rc_igst_net_payable', 0.0)
        result['cgst_net_payable'] = result.get('cgst_net_payable', 0.0) + result.get('rc_cgst_net_payable', 0.0)
        result['sgst_net_payable'] = result.get('sgst_net_payable', 0.0) + result.get('rc_sgst_net_payable', 0.0)
        # NOTE: previously these lines overwrote igst_paid_cash / cgst_paid_cash
        # / sgst_paid_cash (the "Other than Reverse Charge" 6.1(A) values) by
        # adding the reverse-charge 6.1(B) amounts into them. That corrupted
        # the "Other than Reverse Charge" sheet's cash figures (they should
        # only reflect 6.1(A)). The combined total is kept under separate
        # total_* keys for anything that needs the grand total instead.
        result['total_igst_paid_cash'] = result.get('igst_paid_cash', 0.0) + result.get('rc_igst_paid_cash', 0.0)
        result['total_cgst_paid_cash'] = result.get('cgst_paid_cash', 0.0) + result.get('rc_cgst_paid_cash', 0.0)
        result['total_sgst_paid_cash'] = result.get('sgst_paid_cash', 0.0) + result.get('rc_sgst_paid_cash', 0.0)

        try:
            additional_fields = extract_additional_fields(tables)
            result.update(additional_fields)
        except Exception as e:
            logger.error(f"Error extracting additional fields: {str(e)}")

        try:
            hsn_summary = extract_hsn_summary(tables)
            result.update(hsn_summary)
        except Exception as e:
            logger.error(f"Error extracting HSN summary: {str(e)}")

        try:
            additional_tax = extract_additional_tax_details(tables)
            result.update(additional_tax)
        except Exception as e:
            logger.error(f"Error extracting additional tax details: {str(e)}")

        try:
            reverse_charge_supplies = extract_reverse_charge_supplies(tables)
            result.update(reverse_charge_supplies)
        except Exception as e:
            logger.error(f"Error extracting reverse charge supplies: {str(e)}")

        try:
            other_debit_entries = extract_other_debit_entries(tables)
            result.update(other_debit_entries)
        except Exception as e:
            logger.error(f"Error extracting other debit entries: {str(e)}")

        try:
            other_credit_entries = extract_other_credit_entries(tables)
            result.update(other_credit_entries)
        except Exception as e:
            logger.error(f"Error extracting other credit entries: {str(e)}")

        # Summary statistics
        try:
            result['total_outward_supplies_value'] = sum([
                result.get('outward_taxable_value', 0),
                result.get('zero_rated_value', 0),
                result.get('nil_exempt_value', 0),
                result.get('non_gst_value', 0)
                # NOTE: this field is documented as excluding inward reverse
                # charge value, but previously included
                # inward_reverse_charge_value in the sum anyway, inflating
                # the total by the full Table 3.1(d) amount.
            ])
            result['total_itc_available_igst'] = sum([
                result.get('import_goods_igst', 0),
                result.get('import_services_igst', 0),
                result.get('reverse_charge_itc_igst', 0),
                result.get('isd_igst', 0),
                result.get('other_itc_igst', 0)
            ])
            result['total_tax_payable'] = sum([
                result.get('igst_payable', 0),
                result.get('cgst_payable', 0),
                result.get('sgst_payable', 0),
                # NOTE: this field is documented as "sum of payable column in
                # Table 6.1(A) and 6.1(B)" but previously only summed IGST/
                # CGST/SGST, silently dropping both the reverse-charge (6.1B)
                # payable amounts and the Cess payable row entirely.
                result.get('cess_payable', 0),
                result.get('rc_igst_payable', 0),
                result.get('rc_cgst_payable', 0),
                result.get('rc_sgst_payable', 0),
                result.get('rc_cess_payable', 0),
            ])
        except Exception as e:
            logger.error(f"Error calculating summary statistics: {str(e)}")

    except Exception as e:
        logger.error(f"Major error in parse_gstr3b: {str(e)}")
        logger.error(traceback.format_exc())
        result['parsing_error'] = str(e)
        # Check which sections were actually found
        expected_keys = [
            'outward_taxable_value', 'itc_igst_available', 'igst_payable'
            # add more key field names that should always be present
        ]
        missing = [k for k in expected_keys if k not in result or result[k] == 0.0]
        if missing:
            result['_extraction_warnings'] = f"Possibly missing: {missing}"
            result['total_outward_supplies_value'] = sum([
                result.get('outward_taxable_value', 0),
                result.get('zero_rated_value', 0),
                result.get('nil_exempt_value', 0),
                result.get('non_gst_value', 0)
            ])
            result['total_itc_available_igst'] = sum([
                result.get('import_goods_igst', 0),
                result.get('import_services_igst', 0),
                result.get('reverse_charge_itc_igst', 0),
                result.get('isd_igst', 0),
                result.get('other_itc_igst', 0)
            ])
            result['total_tax_payable'] = sum([
                result.get('igst_payable', 0),
                result.get('cgst_payable', 0),
                result.get('sgst_payable', 0),
                result.get('cess_payable', 0),
                result.get('rc_igst_payable', 0),
                result.get('rc_cgst_payable', 0),
                result.get('rc_sgst_payable', 0),
                result.get('rc_cess_payable', 0),
            ])

    return result

def create_excel(parsed_data_list):
    df = pd.DataFrame(parsed_data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GSTR-3B Data')
    output.seek(0)
    return output
