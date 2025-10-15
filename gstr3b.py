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
import fitz  # PyMuPDF

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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helper functions
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
    """Remove watermarks by cropping the page"""
    # This is a simple example. Actual implementation might need adjustments based on the PDF
    # Get page dimensions
    width = page.width
    height = page.height
    
    # Define crop box (crop top and bottom margins where watermarks often appear)
    crop_box = (0, height * 0.05, width, height * 0.95)
    
    # Return cropped page
    return page.crop(crop_box)

def extract_text_with_watermark_handling(pdf_path):
    """Extract text from PDF with watermark handling"""
    all_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Try with watermark removal first
                try:
                    cleaned_page = remove_watermarks(page)
                    text = cleaned_page.extract_text()
                except:
                    # If watermark removal fails, use original page
                    text = page.extract_text()
                
                if text:
                    all_text += text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        logger.error(traceback.format_exc())
    
    return all_text

def extract_tables_from_pdf(pdf_path):
    """Extract all tables from PDF with watermark handling"""
    all_tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Try with watermark removal first
                try:
                    cleaned_page = remove_watermarks(page)
                    tables = cleaned_page.extract_tables()
                except:
                    # If watermark removal fails, use original page
                    tables = page.extract_tables()
                
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        logger.error(traceback.format_exc())
    
    return all_tables

def find_value_by_regex(text, pattern, default=""):
    """Find value using regex pattern with improved error handling"""
    try:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return default
    except re.error as e:
        # Log the regex error
        logger.error(f"Regex error with pattern '{pattern}': {str(e)}")
        return default

def extract_auth_signatory(text):
    """Extract authorized signatory and designation"""
    auth_info = {}
    
    # Try to find authorized signatory with improved pattern matching
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
    
    # Try to find designation with improved pattern matching
    designation_patterns = [
        r'Designation\s*/?\s*Status\s*:?\s*([^\r\n]+)',  # Modified this pattern
        r'Designation\s*:?\s*([^\r\n]+)',
        r'Status\s*:?\s*([^\r\n]+)'
    ]
    
    for pattern in designation_patterns:
        designation_match = re.search(pattern, text, re.IGNORECASE)
        if designation_match:
            # Remove "/Status" from the designation if present
            designation = designation_match.group(1).strip()
            designation = designation.replace('/Status', '').strip()
            auth_info['designation'] = designation
            logger.info(f"Found designation: {auth_info['designation']}")
            break
    
    return auth_info
    
def extract_verification_details(text):
    """Extract verification details such as date and place from text."""
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
                # Detect table 3.1
                if any(x in row_text for x in ["3.1 details of outward supplies", "outward taxable supplies"]):
                    section_3_1 = True
                    logger.info("Found table 3.1")
                if not section_3_1:
                    continue
                # Inward supplies liable to reverse charge (3.1(d))
                if "(d)" in row_text and "inward supplies" in row_text and "reverse charge" in row_text:
                    try:
                        outward_supplies['inward_reverse_charge_value'] = safe_float(row[1])
                        outward_supplies['inward_reverse_charge_igst'] = safe_float(row[2])
                        outward_supplies['inward_reverse_charge_cgst'] = safe_float(row[3])
                        outward_supplies['inward_reverse_charge_sgst'] = safe_float(row[4])
                        outward_supplies['inward_reverse_charge_cess'] = safe_float(row[5]) if len(row) > 5 else 0.0
                        logger.info(f"Extracted 3.1(d) reverse charge: {outward_supplies['inward_reverse_charge_value']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing 3.1(d) reverse charge: {str(e)}")
                # Other 3.1 rows (unchanged)...
                elif "outward taxable supplies (other than zero rated" in row_text:
                    try:
                        outward_supplies['outward_taxable_value'] = safe_float(row[1])
                        outward_supplies['outward_igst'] = safe_float(row[2])
                        outward_supplies['outward_cgst'] = safe_float(row[3])
                        outward_supplies['outward_sgst'] = safe_float(row[4])
                        outward_supplies['outward_cess'] = safe_float(row[5]) if len(row) > 5 else 0.0
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "zero rated" in row_text:
                    try:
                        outward_supplies['zero_rated_value'] = safe_float(row[1])
                        outward_supplies['zero_rated_igst'] = safe_float(row[2])
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "nil rated, exempted" in row_text:
                    try:
                        outward_supplies['nil_exempt_value'] = safe_float(row[1])
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "non-gst outward supplies" in row_text:
                    try:
                        outward_supplies['non_gst_value'] = safe_float(row[1])
                    except (ValueError, TypeError, IndexError):
                        pass
                # Stop at next section
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
                # Detect section 3.1.1
                if any(x in row_text for x in ["3.1.1", "section 9(5)", "supplies notified"]):
                    section_9_5_found = True
                    logger.info("Found section 3.1.1")
                    continue
                if not section_9_5_found:
                    continue
                # Row (i): Electronic commerce operator
                if "electronic commerce operator pays tax" in row_text:
                    try:
                        supplies_9_5['ecom_operator'] = {
                            'value': safe_float(row[1]),
                            'igst': safe_float(row[2]),
                            'cgst': safe_float(row[3]),
                            'sgst': safe_float(row[4]),
                            'cess': safe_float(row[5]) if len(row) > 5 else 0.0
                        }
                        logger.info(f"Extracted ecom operator: {supplies_9_5['ecom_operator']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing ecom operator: {str(e)}")
                # Row (ii): Registered person through ecom operator
                elif "through electronic commerce operator" in row_text:
                    try:
                        supplies_9_5['registered_person'] = {
                            'value': safe_float(row[1]),
                            'igst': safe_float(row[2]) if len(row) > 2 else 0.0,
                            'cgst': safe_float(row[3]) if len(row) > 3 else 0.0,
                            'sgst': safe_float(row[4]) if len(row) > 4 else 0.0,
                            'cess': safe_float(row[5]) if len(row) > 5 else 0.0
                        }
                        logger.info(f"Extracted registered person: {supplies_9_5['registered_person']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing registered person: {str(e)}")
                # Stop at next section
                elif any(x in row_text for x in ["3.2", "out of supplies"]):
                    break
    # Flatten for result
    flat_result = {}
    for key, sub_dict in supplies_9_5.items():
        for sub_key, value in sub_dict.items():
            flat_result[f"sec_9_5_{key}_{sub_key}"] = value
    return flat_result

def extract_interstate_supplies(tables):
    interstate_supplies = {}
    section_3_2_found = False
    for table in tables:
        for row in table:
            if row and len(row) > 1:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                logger.debug(f"Checking row: {row_text}")
                # Detect section 3.2
                if any(x in row_text for x in ["3.2", "inter-state supplies", "out of supplies"]):
                    section_3_2_found = True
                    logger.info("Found section 3.2")
                    continue
                if not section_3_2_found:
                    continue
                # Unregistered persons
                if "unregistered" in row_text:
                    try:
                        interstate_supplies['interstate_unreg_value'] = safe_float(row[1])
                        interstate_supplies['interstate_unreg_igst'] = safe_float(row[2])
                        logger.info(f"Extracted unregistered: {interstate_supplies['interstate_unreg_value']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing unregistered: {str(e)}")
                # Composition taxable persons
                elif "composition" in row_text:
                    try:
                        interstate_supplies['interstate_composition_value'] = safe_float(row[1])
                        interstate_supplies['interstate_composition_igst'] = safe_float(row[2])
                        logger.info(f"Extracted composition: {interstate_supplies['interstate_composition_value']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing composition: {str(e)}")
                # UIN holders
                elif "uin" in row_text:
                    try:
                        interstate_supplies['interstate_uin_value'] = safe_float(row[1])
                        interstate_supplies['interstate_uin_igst'] = safe_float(row[2])
                        logger.info(f"Extracted UIN: {interstate_supplies['interstate_uin_value']}")
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
                # Inward supplies liable to reverse charge (4(3))
                if "inward supplies" in row_text and "reverse charge" in row_text and "other than 1 & 2" in row_text:
                    try:
                        eligible_itc['reverse_charge_itc_igst'] = safe_float(row[1])
                        eligible_itc['reverse_charge_itc_cgst'] = safe_float(row[2])
                        eligible_itc['reverse_charge_itc_sgst'] = safe_float(row[3])
                        eligible_itc['reverse_charge_itc_cess'] = safe_float(row[4])
                        logger.info(f"Extracted 4(3) reverse charge: CGST={eligible_itc['reverse_charge_itc_cgst']}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing 4(3) reverse charge: {str(e)}")
                # Other ITC rows...
                elif "import of goods" in row_text:
                    try:
                        eligible_itc['import_goods_igst'] = safe_float(row[1])
                        eligible_itc['import_goods_cgst'] = safe_float(row[2])
                        eligible_itc['import_goods_sgst'] = safe_float(row[3])
                        eligible_itc['import_goods_cess'] = safe_float(row[4])
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "import of services" in row_text:
                    try:
                        eligible_itc['import_services_igst'] = safe_float(row[1])
                        eligible_itc['import_services_cgst'] = safe_float(row[2])
                        eligible_itc['import_services_sgst'] = safe_float(row[3])
                        eligible_itc['import_services_cess'] = safe_float(row[4])
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "inward supplies from isd" in row_text:
                    try:
                        eligible_itc['isd_igst'] = safe_float(row[1])
                        eligible_itc['isd_cgst'] = safe_float(row[2])
                        eligible_itc['isd_sgst'] = safe_float(row[3])
                        eligible_itc['isd_cess'] = safe_float(row[4])
                    except (ValueError, TypeError, IndexError):
                        pass
                elif "all other itc" in row_text:
                    try:
                        eligible_itc['other_itc_igst'] = safe_float(row[1])
                        eligible_itc['other_itc_cgst'] = safe_float(row[2])
                        eligible_itc['other_itc_sgst'] = safe_float(row[3])
                        eligible_itc['other_itc_cess'] = safe_float(row[4])
                    except (ValueError, TypeError, IndexError):
                        pass
                # Stop at ITC Reversed
                if "itc reversed" in row_text:
                    break
    return eligible_itc

def extract_itc_reversed(tables):
    """Extract data from ITC Reversed table (4.B)"""
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
                
                # As per rules
                if "As per rules" in row_text or "rules 38,42 & 43" in row_text:
                    try:
                        itc_reversed['rules_igst'] = float(row[1] or 0)
                        itc_reversed['rules_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        itc_reversed['rules_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        itc_reversed['rules_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Others
                elif "Others" in row_text:
                    try:
                        itc_reversed['others_igst'] = float(row[1] or 0)
                        itc_reversed['others_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        itc_reversed['others_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        itc_reversed['others_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Net ITC available
                elif "Net ITC available" in row_text or "C. Net ITC available" in row_text:
                    break
    
    return itc_reversed

def extract_net_itc(tables):
    """Extract data from Net ITC table (4.C)"""
    net_itc = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                if "Net ITC available" in row_text or "C. Net ITC available" in row_text:
                    try:
                        net_itc['net_itc_igst'] = float(row[1] or 0)
                        net_itc['net_itc_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        net_itc['net_itc_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        net_itc['net_itc_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                    break
    
    return net_itc

def extract_other_details(tables):
    """Extract data from Other Details table (4.D)"""
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
                
                # ITC reclaimed
                if "ITC reclaimed" in row_text:
                    try:
                        other_details['itc_reclaimed_igst'] = float(row[1] or 0)
                        other_details['itc_reclaimed_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        other_details['itc_reclaimed_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        other_details['itc_reclaimed_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Ineligible ITC
                elif "Ineligible ITC" in row_text:
                    try:
                        other_details['ineligible_itc_igst'] = float(row[1] or 0)
                        other_details['ineligible_itc_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        other_details['ineligible_itc_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        other_details['ineligible_itc_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                    break
    
    return other_details

def extract_exempt_supplies(tables):
    """Extract data from exempt supplies table (5)"""
    exempt_supplies = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 2:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                if "From a supplier under composition scheme" in row_text:
                    try:
                        exempt_supplies['composition_inter_state'] = float(row[1] or 0)
                        exempt_supplies['composition_intra_state'] = float(row[2] or 0) if len(row) > 2 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                
                elif "Non GST supply" in row_text:
                    try:
                        exempt_supplies['non_gst_inter_state'] = float(row[1] or 0)
                        exempt_supplies['non_gst_intra_state'] = float(row[2] or 0) if len(row) > 2 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
    
    return exempt_supplies

def extract_interest_late_fee(tables):
    """Extract data from interest and late fee table (5.1)"""
    interest_late_fee = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                if "Interest Paid" in row_text:
                    try:
                        interest_late_fee['interest_igst'] = float(row[1] or 0)
                        interest_late_fee['interest_cgst'] = float(row[2] or 0) if len(row) > 2 else 0
                        interest_late_fee['interest_sgst'] = float(row[3] or 0) if len(row) > 3 else 0
                        interest_late_fee['interest_cess'] = float(row[4] or 0) if len(row) > 4 else 0
                    except (ValueError, TypeError, IndexError):
                        pass
                
                elif "Late fee" in row_text:
                    try:
                        interest_late_fee['late_fee_igst'] = float(row[1] or 0) if row[1] and row[1] != "-" else 0
                        interest_late_fee['late_fee_cgst'] = float(row[2] or 0) if len(row) > 2 and row[2] and row[2] != "-" else 0
                        interest_late_fee['late_fee_sgst'] = float(row[3] or 0) if len(row) > 3 and row[3] and row[3] != "-" else 0
                    except (ValueError, TypeError, IndexError):
                        pass
    
    return interest_late_fee

def extract_payment_details(tables):
    payment_details = {
        'normal': {},
        'reverse_charge': {}
    }
    normal_section = False
    reverse_charge_section = False
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                logger.debug(f"Payment row: {row_text}")
                # Detect sections
                if "(a) other than reverse charge" in row_text:
                    normal_section = True
                    reverse_charge_section = False
                    continue
                if "(b) reverse charge" in row_text:
                    normal_section = False
                    reverse_charge_section = True
                    continue
                # Normal section
                if normal_section:
                    if "integrated tax" in row_text:
                        try:
                            payment_details['normal'].update({
                                'igst_payable': safe_float(row[1]),
                                'igst_paid_itc_igst': safe_float(row[2]),
                                'igst_paid_itc_cgst': safe_float(row[3]),
                                'igst_paid_itc_sgst': safe_float(row[4]),
                                'igst_paid_cash': safe_float(row[6]),
                                'igst_interest': safe_float(row[7]),
                                'igst_late_fee': safe_float(row[8]) if len(row) > 8 else 0.0
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal IGST: {str(e)}")
                    elif "central tax" in row_text:
                        try:
                            payment_details['normal'].update({
                                'cgst_payable': safe_float(row[1]),
                                'cgst_paid_itc_igst': safe_float(row[2]),
                                'cgst_paid_itc_cgst': safe_float(row[3]),
                                'cgst_paid_itc_sgst': safe_float(row[4]),
                                'cgst_paid_cash': safe_float(row[6]),
                                'cgst_interest': safe_float(row[7]),
                                'cgst_late_fee': safe_float(row[8]) if len(row) > 8 else 0.0
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal CGST: {str(e)}")
                    elif "state/ut tax" in row_text:
                        try:
                            payment_details['normal'].update({
                                'sgst_payable': safe_float(row[1]),
                                'sgst_paid_itc_igst': safe_float(row[2]),
                                'sgst_paid_itc_cgst': safe_float(row[3]),
                                'sgst_paid_itc_sgst': safe_float(row[4]),
                                'sgst_paid_cash': safe_float(row[6]),
                                'sgst_interest': safe_float(row[7]),
                                'sgst_late_fee': safe_float(row[8]) if len(row) > 8 else 0.0
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing normal SGST: {str(e)}")
                # Reverse charge section
                elif reverse_charge_section:
                    if "integrated tax" in row_text:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_igst_payable': safe_float(row[1]),
                                'rc_igst_paid_cash': safe_float(row[6])
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC IGST: {str(e)}")
                    elif "central tax" in row_text:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_cgst_payable': safe_float(row[1]),
                                'rc_cgst_paid_cash': safe_float(row[6])
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC CGST: {str(e)}")
                    elif "state/ut tax" in row_text:
                        try:
                            payment_details['reverse_charge'].update({
                                'rc_sgst_payable': safe_float(row[1]),
                                'rc_sgst_paid_cash': safe_float(row[6])
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.error(f"Error parsing RC SGST: {str(e)}")
    logger.info(f"Payment details extracted: {payment_details}")
    return payment_details

def extract_reverse_charge_supplies(tables):
    """Extract data from reverse charge supplies table (3)"""
    reverse_charge = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                # Look for the specific section
                if "Inward supplies liable to reverse charge" in row_text:
                    try:
                        # Extract values from the row
                        reverse_charge['value'] = float(row[1]) if row[1] and row[1] != "-" else None
                        reverse_charge['igst'] = float(row[2]) if len(row) > 2 and row[2] and row[2] != "-" else None
                        reverse_charge['cgst'] = float(row[3]) if len(row) > 3 and row[3] and row[3] != "-" else None
                        reverse_charge['sgst'] = float(row[4]) if len(row) > 4 and row[4] and row[4] != "-" else None
                        reverse_charge['cess'] = float(row[5]) if len(row) > 5 and row[5] and row[5] != "-" else None
                        logger.info(f"Found reverse charge supplies: {reverse_charge}")
                        return reverse_charge
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing reverse charge supplies: {str(e)}")
                        continue
    
    return reverse_charge

def extract_other_debit_entries(tables):
    """Extract data from other debit entries table (4)"""
    other_debit = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                # Look for the specific section
                if "Other Debit Entries" in row_text:
                    try:
                        # Extract values from the row
                        other_debit['value'] = float(row[1]) if row[1] and row[1] != "-" else None
                        other_debit['igst'] = float(row[2]) if len(row) > 2 and row[2] and row[2] != "-" else None
                        other_debit['cgst'] = float(row[3]) if len(row) > 3 and row[3] and row[3] != "-" else None
                        other_debit['sgst'] = float(row[4]) if len(row) > 4 and row[4] and row[4] != "-" else None
                        other_debit['cess'] = float(row[5]) if len(row) > 5 and row[5] and row[5] != "-" else None
                        logger.info(f"Found other debit entries: {other_debit}")
                        return other_debit
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing other debit entries: {str(e)}")
                        continue
    
    return other_debit

def extract_other_credit_entries(tables):
    """Extract data from other credit entries table (4)"""
    other_credit = {}
    
    for table in tables:
        for row in table:
            if row and len(row) > 3:
                row_text = ' '.join([str(cell) for cell in row if cell])
                
                # Look for the specific section
                if "Other Credit Entries" in row_text:
                    try:
                        # Extract values from the row
                        other_credit['value'] = float(row[1]) if row[1] and row[1] != "-" else None
                        other_credit['igst'] = float(row[2]) if len(row) > 2 and row[2] and row[2] != "-" else None
                        other_credit['cgst'] = float(row[3]) if len(row) > 3 and row[3] and row[3] != "-" else None
                        other_credit['sgst'] = float(row[4]) if len(row) > 4 and row[4] and row[4] != "-" else None
                        other_credit['cess'] = float(row[5]) if len(row) > 5 and row[5] and row[5] != "-" else None
                        logger.info(f"Found other credit entries: {other_credit}")
                        return other_credit
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Error parsing other credit entries: {str(e)}")
                        continue
    
    return other_credit

def parse_gstr3b(pdf_path):
    """Parse GSTR-3B from PDF and return structured data with comprehensive coverage"""
    result = {}
    
    try:
        # Extract all text from the PDF
        all_text = extract_text_with_watermark_handling(pdf_path)
        
        # Extract basic information using regex patterns with safer patterns
        # Use simple patterns and add more error handling
        try:
            result['gstin'] = find_value_by_regex(all_text, r'GSTIN of the supplier\s+(\S+)')
            logger.info(f"Extracted GSTIN: {result['gstin']}")
        except Exception as e:
            logger.error(f"Error extracting GSTIN: {str(e)}")
            result['gstin'] = ""
            
        try:
            # Modified pattern to avoid unbalanced parentheses issue
            result['legal_name'] = find_value_by_regex(all_text, r'Legal name of the registered person\s+([^\r\n]+)')
            logger.info(f"Extracted legal name: {result['legal_name']}")
        except Exception as e:
            logger.error(f"Error extracting legal name: {str(e)}")
            result['legal_name'] = ""
            
        try:
            # Modified pattern to avoid unbalanced parentheses issue
            result['trade_name'] = find_value_by_regex(all_text, r'Trade name, if any\s+([^\r\n]+)')
            logger.info(f"Extracted trade name: {result['trade_name']}")
        except Exception as e:
            logger.error(f"Error extracting trade name: {str(e)}")
            result['trade_name'] = ""
            
        try:
            auth_info = extract_auth_signatory(all_text)
            result.update(auth_info)
            logger.info(f"Extracted auth info: {auth_info}")
        except Exception as e:
            logger.error(f"Error extracting authorized signatory: {str(e)}")
        
        # Safer patterns for other fields
        result['period'] = find_value_by_regex(all_text, r'Period\s+(\w+)', '')
        result['year'] = find_value_by_regex(all_text, r'Year\s+(\d{4}-\d{2}|\d{4})', '')
        result['arn'] = find_value_by_regex(all_text, r'ARN\s+(\S+)', '')
        result['arn_date'] = find_value_by_regex(all_text, r'Date of ARN\s+(\d{2}/\d{2}/\d{4})', '')
        
        # Extract verification details
        try:
            verification_details = extract_verification_details(all_text)
            result.update(verification_details)
            logger.info(f"Extracted verification details: {verification_details}")
        except Exception as e:
            logger.error(f"Error extracting verification details: {str(e)}")
        
        # Validate GSTIN
        if result['gstin'] and not validate_gstin(result['gstin']):
            if 'validation_errors' not in result:
                result['validation_errors'] = []
            result['validation_errors'].append('Invalid GSTIN format')
        
        # Parse ARN date
        if result['arn_date']:
            result['arn_date_parsed'] = parse_date(result['arn_date'])
        
        # Extract tables from PDF
        tables = extract_tables_from_pdf(pdf_path)
        logger.info(f"Extracted {len(tables)} tables from PDF")
        
        # Extract data from various tables with error handling for each section
        try:
            outward_supplies = extract_outward_supplies(tables)
            result.update(outward_supplies)
            # Add logging to check what's in outward_supplies
            logger.info(f"Extracted outward supplies keys: {outward_supplies.keys()}")
        except Exception as e:
            logger.error(f"Error extracting outward supplies: {str(e)}")
        
        # Add these calls in parse_gstr3b function, after extracting outward supplies
        try:
            supplies_9_5 = extract_supplies_9_5(tables)
            result.update(supplies_9_5)
            logger.info(f"Extracted section 9(5) supplies keys: {supplies_9_5.keys()}")
        except Exception as e:
            logger.error(f"Error extracting supplies under section 9(5): {str(e)}")

        try:
            interstate_supplies = extract_interstate_supplies(tables)
            result.update(interstate_supplies)
            logger.info(f"Extracted interstate supplies keys: {interstate_supplies.keys()}")
        except Exception as e:
            logger.error(f"Error extracting interstate supplies: {str(e)}")
        
        try:
            eligible_itc = extract_eligible_itc(tables)
            result.update(eligible_itc)
            logger.info(f"Extracted eligible ITC keys: {eligible_itc.keys()}")
        except Exception as e:
            logger.error(f"Error extracting eligible ITC: {str(e)}")
        
        try:
            itc_reversed = extract_itc_reversed(tables)
            result.update(itc_reversed)
            logger.info(f"Extracted ITC reversed keys: {itc_reversed.keys()}")
        except Exception as e:
            logger.error(f"Error extracting ITC reversed: {str(e)}")
        
        try:
            net_itc = extract_net_itc(tables)
            result.update(net_itc)
            logger.info(f"Extracted net ITC keys: {net_itc.keys()}")
        except Exception as e:
            logger.error(f"Error extracting net ITC: {str(e)}")
        
        try:
            other_details = extract_other_details(tables)
            result.update(other_details)
            logger.info(f"Extracted other details keys: {other_details.keys()}")
        except Exception as e:
            logger.error(f"Error extracting other details: {str(e)}")
        
        try:
            exempt_supplies = extract_exempt_supplies(tables)
            result.update(exempt_supplies)
            logger.info(f"Extracted exempt supplies keys: {exempt_supplies.keys()}")
        except Exception as e:
            logger.error(f"Error extracting exempt supplies: {str(e)}")
        
        try:
            interest_late_fee = extract_interest_late_fee(tables)
            result.update(interest_late_fee)
            logger.info(f"Extracted interest and late fee keys: {interest_late_fee.keys()}")
        except Exception as e:
            logger.error(f"Error extracting interest and late fee: {str(e)}")
        
        try:
            payment_details = extract_payment_details(tables)
            
            # Add payment details
            for key, value in payment_details['normal'].items():
                result[key] = value
            
            for key, value in payment_details['reverse_charge'].items():
                result[key] = value
                
            logger.info(f"Extracted payment details keys: {list(payment_details['normal'].keys()) + list(payment_details['reverse_charge'].keys())}")
        except Exception as e:
            logger.error(f"Error extracting payment details: {str(e)}")
        
        # Extract additional fields for comprehensive coverage
        try:
            additional_fields = extract_additional_fields(tables)
            result.update(additional_fields)
            logger.info(f"Extracted additional fields keys: {additional_fields.keys()}")
        except Exception as e:
            logger.error(f"Error extracting additional fields: {str(e)}")
        
        try:
            hsn_summary = extract_hsn_summary(tables)
            result.update(hsn_summary)
            logger.info(f"Extracted HSN summary keys: {hsn_summary.keys()}")
        except Exception as e:
            logger.error(f"Error extracting HSN summary: {str(e)}")
        
        try:
            additional_tax = extract_additional_tax_details(tables)
            result.update(additional_tax)
            logger.info(f"Extracted additional tax details keys: {additional_tax.keys()}")
        except Exception as e:
            logger.error(f"Error extracting additional tax details: {str(e)}")
        
        # Extract reverse charge supplies and other debit/credit entries
        try:
            reverse_charge_supplies = extract_reverse_charge_supplies(tables)
            result.update(reverse_charge_supplies)
            logger.info(f"Extracted reverse charge supplies: {reverse_charge_supplies}")
        except Exception as e:
            logger.error(f"Error extracting reverse charge supplies: {str(e)}")
        
        try:
            other_debit_entries = extract_other_debit_entries(tables)
            result.update(other_debit_entries)
            logger.info(f"Extracted other debit entries: {other_debit_entries}")
        except Exception as e:
            logger.error(f"Error extracting other debit entries: {str(e)}")
        
        try:
            other_credit_entries = extract_other_credit_entries(tables)
            result.update(other_credit_entries)
            logger.info(f"Extracted other credit entries: {other_credit_entries}")
        except Exception as e:
            logger.error(f"Error extracting other credit entries: {str(e)}")
        
        # Log all keys in the final result
        logger.info(f"Final result keys: {result.keys()}")
        
        # Add summary statistics
        try:
            # Calculate totals for validation
            total_outward_value = sum([
                result.get('outward_taxable_value', 0),
                result.get('zero_rated_value', 0),
                result.get('nil_exempt_value', 0),
                result.get('non_gst_value', 0),
                result.get('inward_reverse_charge_value', 0)
            ])
            result['total_outward_supplies_value'] = total_outward_value
            
            # Calculate total ITC available
            total_itc_available = sum([
                result.get('import_goods_igst', 0),
                result.get('import_services_igst', 0),
                result.get('reverse_charge_itc_igst', 0),
                result.get('isd_igst', 0),
                result.get('other_itc_igst', 0)
            ])
            result['total_itc_available_igst'] = total_itc_available
            
            # Calculate total tax payable
            total_tax_payable = sum([
                result.get('igst_payable', 0),
                result.get('cgst_payable', 0),
                result.get('sgst_payable', 0)
            ])
            result['total_tax_payable'] = total_tax_payable
            
            logger.info(f"Calculated summary statistics: outward={total_outward_value}, ITC={total_itc_available}, tax={total_tax_payable}")
        except Exception as e:
            logger.error(f"Error calculating summary statistics: {str(e)}")
    
    except Exception as e:
        logger.error(f"Major error in parse_gstr3b: {str(e)}")
        logger.error(traceback.format_exc())
        # Add error information to result
        result['parsing_error'] = str(e)
    
    return result

def create_excel(parsed_data_list):
    """Create Excel file from parsed data"""
    # Create dataframe from parsed data
    df = pd.DataFrame(parsed_data_list)
    
    # Log the columns in the dataframe
    logger.info(f"DataFrame columns: {df.columns.tolist()}")
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Convert dataframe to Excel
        df.to_excel(writer, index=False, sheet_name='GSTR-3B Data')
        
        # Get the workbook and worksheet to modify
        workbook = writer.book
        worksheet = writer.sheets['GSTR-3B Data']
        
        # Add formulas if needed
        # Example: Total tax paid = Cash + ITC
        # worksheet['Z2'] = '=X2+Y2'  # Adjust column references as needed
    
    output.seek(0)
    return output



def parse_gstr3b_from_text(text):
    """
    Parse GSTR-3B data from text input and return a structured dictionary.
    
    Args:
        text (str): The text content of the GSTR-3B form
        
    Returns:
        dict: A dictionary containing the structured data
    """
    result = {}
    
    # Extract basic information
    try:
        # Extract month
        month_match = re.search(r'Month:\s*([^\n]+)', text)
        if month_match:
            result['Month'] = month_match.group(1).strip()
        
        # Extract GSTIN
        gstin_match = re.search(r'GSTIN:\s*([^\n]+)', text)
        if gstin_match:
            result['GSTIN'] = gstin_match.group(1).strip()
        
        # Extract Legal Name
        legal_name_match = re.search(r'Legal Name:\s*([^\n]+)', text)
        if legal_name_match:
            result['Legal Name'] = legal_name_match.group(1).strip()
        
        # Extract Trade Name
        trade_name_match = re.search(r'Trade Name:\s*([^\n]+)', text)
        if trade_name_match:
            result['Trade Name'] = trade_name_match.group(1).strip()
        
        # Extract ARN
        arn_match = re.search(r'ARN:\s*([^\n]+)', text)
        if arn_match:
            result['ARN'] = arn_match.group(1).strip()
        
        # Extract Date of ARN
        arn_date_match = re.search(r'Date of ARN:\s*([^\n]+)', text)
        if arn_date_match:
            result['Date of ARN'] = arn_date_match.group(1).strip()
        
        # Extract Authorized Signatory
        auth_signatory_match = re.search(r'Authorized Signatory:\s*([^\n]+)', text)
        if auth_signatory_match:
            result['Authorized Signatory'] = auth_signatory_match.group(1).strip()
        
        # Extract Designation (if available)
        designation_match = re.search(r'Designation:\s*([^\n]+)', text)
        if designation_match:
            result['Designation'] = designation_match.group(1).strip()
        
        # Extract Table 3.1: Outward supplies
        outward_supplies_section = re.search(r'Table 3\.1:(.*?)(?=Table 3\.2|$)', text, re.DOTALL)
        if outward_supplies_section:
            outward_text = outward_supplies_section.group(1)
            
            # Outward taxable supplies
            taxable_match = re.search(r'Outward taxable supplies:\s*([\d.]+)\s*\|\s*IGST:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', outward_text)
            if taxable_match:
                result['Outward Taxable Value'] = float(taxable_match.group(1))
                result['Outward IGST'] = float(taxable_match.group(2))
                result['Outward CGST'] = float(taxable_match.group(3))
                result['Outward SGST'] = float(taxable_match.group(4))
            
            # Zero rated supplies
            zero_rated_match = re.search(r'Zero rated:\s*([\d.]+)', outward_text)
            if zero_rated_match:
                result['Zero Rated Value'] = float(zero_rated_match.group(1))
            
            # Nil rated/exempted supplies
            nil_exempt_match = re.search(r'Nil rated/exempted:\s*([\d.]+)', outward_text)
            if nil_exempt_match:
                result['Nil Exempt Value'] = float(nil_exempt_match.group(1))
            
            # Reverse charge
            reverse_charge_match = re.search(r'Reverse charge:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', outward_text)
            if reverse_charge_match:
                result['Reverse Charge Value'] = float(reverse_charge_match.group(1))
                result['Reverse Charge IGST'] = float(reverse_charge_match.group(2))
                result['Reverse Charge CGST'] = float(reverse_charge_match.group(3))
            
            # Non-GST supplies
            non_gst_match = re.search(r'Non-GST:\s*([\d.]+)', outward_text)
            if non_gst_match:
                result['Non-GST Value'] = float(non_gst_match.group(1))
        
        # Extract Table 3.2: Inter-state supplies
        interstate_section = re.search(r'Table 3\.2 Inter-State Supplies:(.*?)(?=Table 4|$)', text, re.DOTALL)
        if interstate_section:
            interstate_text = interstate_section.group(1)
            
            # Unregistered persons
            unregistered_match = re.search(r'Unregistered:\s*([\d.]+)\s*\|\s*IGST:\s*([\d.]+)', interstate_text)
            if unregistered_match:
                result['Unregistered Value'] = float(unregistered_match.group(1))
                result['Unregistered IGST'] = float(unregistered_match.group(2))
            
            # Composition & UIN
            composition_match = re.search(r'Composition & UIN:\s*([\d.]+)', interstate_text)
            if composition_match:
                result['Composition Value'] = float(composition_match.group(1))
        
        # Extract Table 4: ITC Available
        itc_section = re.search(r'Table 4 - ITC Available:(.*?)(?=ITC Reversed|$)', text, re.DOTALL)
        if itc_section:
            itc_text = itc_section.group(1)
            
            # Reverse charge ITC
            reverse_charge_itc_match = re.search(r'Reverse charge:\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', itc_text)
            if reverse_charge_itc_match:
                result['Reverse Charge ITC CGST'] = float(reverse_charge_itc_match.group(1))
                result['Reverse Charge ITC SGST'] = float(reverse_charge_itc_match.group(2))
            
            # ISD ITC
            isd_itc_match = re.search(r'From ISD:\s*IGST:\s*([\d.]+)', itc_text)
            if isd_itc_match:
                result['ISD IGST'] = float(isd_itc_match.group(1))
            
            # All other ITC
            other_itc_match = re.search(r'All other ITC:\s*IGST:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', itc_text)
            if other_itc_match:
                result['Other ITC IGST'] = float(other_itc_match.group(1))
                result['Other ITC CGST'] = float(other_itc_match.group(2))
                result['Other ITC SGST'] = float(other_itc_match.group(3))
        
        # Extract ITC Reversed
        itc_reversed_section = re.search(r'ITC Reversed:(.*?)(?=Net ITC|$)', text, re.DOTALL)
        if itc_reversed_section:
            itc_reversed_text = itc_reversed_section.group(1)
            
            # Rule 38/42/43
            rule_itc_match = re.search(r'Rule 38/42/43:\s*IGST:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', itc_reversed_text)
            if rule_itc_match:
                result['ITC Reversed Rule IGST'] = float(rule_itc_match.group(1))
                result['ITC Reversed Rule CGST'] = float(rule_itc_match.group(2))
                result['ITC Reversed Rule SGST'] = float(rule_itc_match.group(3))
            
            # Others
            others_itc_match = re.search(r'Others:\s*IGST:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', itc_reversed_text)
            if others_itc_match:
                result['ITC Reversed Others IGST'] = float(others_itc_match.group(1))
                result['ITC Reversed Others CGST'] = float(others_itc_match.group(2))
                result['ITC Reversed Others SGST'] = float(others_itc_match.group(3))
        
        # Extract Net ITC
        net_itc_match = re.search(r'Net ITC:\s*IGST:\s*([\d.]+)\s*\|\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', text)
        if net_itc_match:
            result['Net ITC IGST'] = float(net_itc_match.group(1))
            result['Net ITC CGST'] = float(net_itc_match.group(2))
            result['Net ITC SGST'] = float(net_itc_match.group(3))
        
        # Extract ITC Reclaimed
        itc_reclaimed_match = re.search(r'ITC Reclaimed:\s*CGST:\s*([\d.]+)\s*\|\s*SGST:\s*([\d.]+)', text)
        if itc_reclaimed_match:
            result['ITC Reclaimed CGST'] = float(itc_reclaimed_match.group(1))
            result['ITC Reclaimed SGST'] = float(itc_reclaimed_match.group(2))
        
        # Extract Table 5: Exempt/Nil/Non-GST Inward Supplies
        exempt_section = re.search(r'Table 5 - Exempt/Nil/Non-GST Inward Supplies:(.*?)(?=Table 6\.1|$)', text, re.DOTALL)
        if exempt_section:
            exempt_text = exempt_section.group(1)
            
            # Check if all zero
            if 'All zero' in exempt_text:
                result['Exempt Supplies Value'] = 0.0
                result['Exempt Supplies IGST'] = 0.0
                result['Exempt Supplies CGST'] = 0.0
                result['Exempt Supplies SGST'] = 0.0
        
        # Extract Table 6.1: Payment of Tax
        payment_section = re.search(r'Table 6\.1 - Payment of Tax:(.*?)(?=Authorized Signatory|$)', text, re.DOTALL)
        if payment_section:
            payment_text = payment_section.group(1)
            
            # Other than RCM
            other_rcm_section = re.search(r'Other than RCM:(.*?)(?=RCM:|$)', payment_text, re.DOTALL)
            if other_rcm_section:
                other_rcm_text = other_rcm_section.group(1)
                
                # IGST
                igst_match = re.search(r'IGST:\s*([\d.]+)\s*via\s*ITC', other_rcm_text)
                if igst_match:
                    result['Payment - IGST - Payable'] = float(igst_match.group(1))
                    result['Payment - IGST - ITC IGST'] = float(igst_match.group(1))
                    result['Payment - IGST - ITC CGST'] = 0.0
                    result['Payment - IGST - ITC SGST'] = 0.0
                    result['Payment - IGST - Cash'] = 0.0
                
                # CGST
                cgst_match = re.search(r'CGST:\s*([\d.]+)\s*ITC\s*\+\s*([\d.]+)\s*cash', other_rcm_text)
                if cgst_match:
                    result['Payment - CGST - Payable'] = float(cgst_match.group(1)) + float(cgst_match.group(2))
                    result['Payment - CGST - ITC IGST'] = 0.0  # Assuming this is from CGST ITC
                    result['Payment - CGST - ITC CGST'] = float(cgst_match.group(1))
                    result['Payment - CGST - Cash'] = float(cgst_match.group(2))
                
                # SGST
                sgst_match = re.search(r'SGST:\s*([\d.]+)\s*ITC\s*\+\s*([\d.]+)\s*cash\s*\+\s*([\d.]+)\s*cash', other_rcm_text)
                if sgst_match:
                    result['Payment - SGST - Payable'] = float(sgst_match.group(1)) + float(sgst_match.group(2)) + float(sgst_match.group(3))
                    result['Payment - SGST - ITC IGST'] = 0.0  # Assuming this is from SGST ITC
                    result['Payment - SGST - ITC SGST'] = float(sgst_match.group(1))
                    result['Payment - SGST - Cash'] = float(sgst_match.group(2)) + float(sgst_match.group(3))
            
            # RCM
            rcm_section = re.search(r'RCM:(.*?)(?=Authorized Signatory|$)', payment_text, re.DOTALL)
            if rcm_section:
                rcm_text = rcm_section.group(1)
                
                # CGST
                rcm_cgst_match = re.search(r'CGST:\s*([\d.]+)\s*cash', rcm_text)
                if rcm_cgst_match:
                    result['RCM - CGST - Payable'] = float(rcm_cgst_match.group(1))
                    result['RCM - CGST - Cash'] = float(rcm_cgst_match.group(1))
                
                # SGST
                rcm_sgst_match = re.search(r'SGST:\s*([\d.]+)\s*cash', rcm_text)
                if rcm_sgst_match:
                    result['RCM - SGST - Payable'] = float(rcm_sgst_match.group(1))
                    result['RCM - SGST - Cash'] = float(rcm_sgst_match.group(1))
    
    except Exception as e:
        logger.error(f"Error parsing GSTR-3B text: {str(e)}")
        logger.error(traceback.format_exc())
    
    return result

def convert_to_excel_format(parsed_data, filename=None):
    """
    Convert parsed GSTR-3B data into the exact format required for the Excel file.
    
    Args:
        parsed_data (dict): The parsed GSTR-3B data
        filename (str, optional): The filename to include in the output
        
    Returns:
        dict: A dictionary in the format required for the Excel file
    """
    excel_data = {}
    
    # Basic information
    excel_data['File'] = filename if filename else ''
    excel_data['Month'] = parsed_data.get('Month', '')
    excel_data['GSTIN'] = parsed_data.get('GSTIN', '')
    excel_data['Legal Name'] = parsed_data.get('Legal Name', '')
    excel_data['Trade Name'] = parsed_data.get('Trade Name', '')
    excel_data['ARN'] = parsed_data.get('ARN', '')
    excel_data['Date of ARN'] = parsed_data.get('Date of ARN', '')
    excel_data['Authorized Signatory'] = parsed_data.get('Authorized Signatory', '')
    excel_data['Designation'] = parsed_data.get('Designation', '')
    
    # 3.1 Outward supplies
    excel_data['Outward Taxable Value'] = parsed_data.get('Outward Taxable Value', None)
    excel_data['Outward IGST'] = parsed_data.get('Outward IGST', None)
    excel_data['Outward CGST'] = parsed_data.get('Outward CGST', None)
    excel_data['Outward SGST'] = parsed_data.get('Outward SGST', None)
    excel_data['Outward Cess'] = parsed_data.get('Outward Cess', None)
    
    excel_data['Zero Rated Value'] = parsed_data.get('Zero Rated Value', None)
    excel_data['Zero Rated IGST'] = parsed_data.get('Zero Rated IGST', None)
    
    excel_data['Nil Exempt Value'] = parsed_data.get('Nil Exempt Value', None)
    
    excel_data['Reverse Charge Value'] = parsed_data.get('Reverse Charge Value', None)
    excel_data['Reverse Charge IGST'] = parsed_data.get('Reverse Charge IGST', None)
    excel_data['Reverse Charge CGST'] = parsed_data.get('Reverse Charge CGST', None)
    excel_data['Reverse Charge SGST'] = parsed_data.get('Reverse Charge SGST', None)
    excel_data['Reverse Charge Cess'] = parsed_data.get('Reverse Charge Cess', None)
    
    excel_data['Non-GST Value'] = parsed_data.get('Non-GST Value', None)
    
    # 3.2 Inter-state supplies
    excel_data['Unregistered Value'] = parsed_data.get('Unregistered Value', None)
    excel_data['Unregistered IGST'] = parsed_data.get('Unregistered IGST', None)
    
    excel_data['Composition Value'] = parsed_data.get('Composition Value', None)
    excel_data['Composition IGST'] = parsed_data.get('Composition IGST', None)
    
    excel_data['UIN Value'] = parsed_data.get('UIN Value', None)
    excel_data['UIN IGST'] = parsed_data.get('UIN IGST', None)
    
    # 4 ITC
    excel_data['Import Goods IGST'] = parsed_data.get('Import Goods IGST', None)
    excel_data['Import Goods CGST'] = parsed_data.get('Import Goods CGST', None)
    excel_data['Import Goods SGST'] = parsed_data.get('Import Goods SGST', None)
    excel_data['Import Goods Cess'] = parsed_data.get('Import Goods Cess', None)
    
    excel_data['Import Services IGST'] = parsed_data.get('Import Services IGST', None)
    excel_data['Import Services CGST'] = parsed_data.get('Import Services CGST', None)
    excel_data['Import Services SGST'] = parsed_data.get('Import Services SGST', None)
    excel_data['Import Services Cess'] = parsed_data.get('Import Services Cess', None)
    
    excel_data['Reverse Charge ITC IGST'] = parsed_data.get('Reverse Charge ITC IGST', None)
    excel_data['Reverse Charge ITC CGST'] = parsed_data.get('Reverse Charge ITC CGST', None)
    excel_data['Reverse Charge ITC SGST'] = parsed_data.get('Reverse Charge ITC SGST', None)
    excel_data['Reverse Charge ITC Cess'] = parsed_data.get('Reverse Charge ITC Cess', None)
    
    excel_data['ISD IGST'] = parsed_data.get('ISD IGST', None)
    excel_data['ISD CGST'] = parsed_data.get('ISD CGST', None)
    excel_data['ISD SGST'] = parsed_data.get('ISD SGST', None)
    excel_data['ISD Cess'] = parsed_data.get('ISD Cess', None)
    
    excel_data['Other ITC IGST'] = parsed_data.get('Other ITC IGST', None)
    excel_data['Other ITC CGST'] = parsed_data.get('Other ITC CGST', None)
    excel_data['Other ITC SGST'] = parsed_data.get('Other ITC SGST', None)
    excel_data['Other ITC Cess'] = parsed_data.get('Other ITC Cess', None)
    
    excel_data['ITC Reversed Rule IGST'] = parsed_data.get('ITC Reversed Rule IGST', None)
    excel_data['ITC Reversed Rule CGST'] = parsed_data.get('ITC Reversed Rule CGST', None)
    excel_data['ITC Reversed Rule SGST'] = parsed_data.get('ITC Reversed Rule SGST', None)
    excel_data['ITC Reversed Rule Cess'] = parsed_data.get('ITC Reversed Rule Cess', None)
    
    excel_data['ITC Reversed Others IGST'] = parsed_data.get('ITC Reversed Others IGST', None)
    excel_data['ITC Reversed Others CGST'] = parsed_data.get('ITC Reversed Others CGST', None)
    excel_data['ITC Reversed Others SGST'] = parsed_data.get('ITC Reversed Others SGST', None)
    excel_data['ITC Reversed Others Cess'] = parsed_data.get('ITC Reversed Others Cess', None)
    
    excel_data['Net ITC IGST'] = parsed_data.get('Net ITC IGST', None)
    excel_data['Net ITC CGST'] = parsed_data.get('Net ITC CGST', None)
    excel_data['Net ITC SGST'] = parsed_data.get('Net ITC SGST', None)
    excel_data['Net ITC Cess'] = parsed_data.get('Net ITC Cess', None)
    
    excel_data['ITC Reclaimed IGST'] = parsed_data.get('ITC Reclaimed IGST', None)
    excel_data['ITC Reclaimed CGST'] = parsed_data.get('ITC Reclaimed CGST', None)
    excel_data['ITC Reclaimed SGST'] = parsed_data.get('ITC Reclaimed SGST', None)
    excel_data['ITC Reclaimed Cess'] = parsed_data.get('ITC Reclaimed Cess', None)
    
    # 5 Exempt/Nil/Non-GST inward supplies
    excel_data['Exempt Supplies Value'] = parsed_data.get('Exempt Supplies Value', None)
    excel_data['Exempt Supplies IGST'] = parsed_data.get('Exempt Supplies IGST', None)
    excel_data['Exempt Supplies CGST'] = parsed_data.get('Exempt Supplies CGST', None)
    excel_data['Exempt Supplies SGST'] = parsed_data.get('Exempt Supplies SGST', None)
    excel_data['Exempt Supplies Cess'] = parsed_data.get('Exempt Supplies Cess', None)
    
    # 6.1 Payment of tax
    excel_data['Payment - IGST - Payable'] = parsed_data.get('Payment - IGST - Payable', None)
    excel_data['Payment - IGST - ITC IGST'] = parsed_data.get('Payment - IGST - ITC IGST', None)
    excel_data['Payment - IGST - ITC CGST'] = parsed_data.get('Payment - IGST - ITC CGST', None)
    excel_data['Payment - IGST - ITC SGST'] = parsed_data.get('Payment - IGST - ITC SGST', None)
    excel_data['Payment - IGST - Cash'] = parsed_data.get('Payment - IGST - Cash', None)
    excel_data['Payment - IGST - Interest'] = parsed_data.get('Payment - IGST - Interest', None)
    excel_data['Payment - IGST - Late Fee'] = parsed_data.get('Payment - IGST - Late Fee', None)
    
    excel_data['Payment - CGST - Payable'] = parsed_data.get('Payment - CGST - Payable', None)
    excel_data['Payment - CGST - ITC IGST'] = parsed_data.get('Payment - CGST - ITC IGST', None)
    excel_data['Payment - CGST - ITC CGST'] = parsed_data.get('Payment - CGST - ITC CGST', None)
    excel_data['Payment - CGST - ITC SGST'] = parsed_data.get('Payment - CGST - ITC SGST', None)
    excel_data['Payment - CGST - Cash'] = parsed_data.get('Payment - CGST - Cash', None)
    excel_data['Payment - CGST - Interest'] = parsed_data.get('Payment - CGST - Interest', None)
    excel_data['Payment - CGST - Late Fee'] = parsed_data.get('Payment - CGST - Late Fee', None)
    
    excel_data['Payment - SGST - Payable'] = parsed_data.get('Payment - SGST - Payable', None)
    excel_data['Payment - SGST - ITC IGST'] = parsed_data.get('Payment - SGST - ITC IGST', None)
    excel_data['Payment - SGST - ITC CGST'] = parsed_data.get('Payment - SGST - ITC CGST', None)
    excel_data['Payment - SGST - ITC SGST'] = parsed_data.get('Payment - SGST - ITC SGST', None)
    excel_data['Payment - SGST - Cash'] = parsed_data.get('Payment - SGST - Cash', None)
    excel_data['Payment - SGST - Interest'] = parsed_data.get('Payment - SGST - Interest', None)
    excel_data['Payment - SGST - Late Fee'] = parsed_data.get('Payment - SGST - Late Fee', None)
    
    excel_data['RCM - IGST - Payable'] = parsed_data.get('RCM - IGST - Payable', None)
    excel_data['RCM - IGST - Cash'] = parsed_data.get('RCM - IGST - Cash', None)
    
    excel_data['RCM - CGST - Payable'] = parsed_data.get('RCM - CGST - Payable', None)
    excel_data['RCM - CGST - Cash'] = parsed_data.get('RCM - CGST - Cash', None)
    
    excel_data['RCM - SGST - Payable'] = parsed_data.get('RCM - SGST - Payable', None)
    excel_data['RCM - SGST - Cash'] = parsed_data.get('RCM - SGST - Cash', None)
    
    # Add section 3.1.1 fields
    excel_data['Section_9_5_Value'] = parsed_data.get('sec_9_5_value', None)
    excel_data['Section_9_5_IGST'] = parsed_data.get('sec_9_5_igst', None)
    excel_data['Section_9_5_CGST'] = parsed_data.get('sec_9_5_cgst', None)
    excel_data['Section_9_5_SGST'] = parsed_data.get('sec_9_5_sgst', None)
    
    # Add section 3.2 fields
    excel_data['Interstate_Unreg_Value'] = parsed_data.get('interstate_unreg_value', None)
    excel_data['Interstate_Unreg_IGST'] = parsed_data.get('interstate_unreg_igst', None)
    excel_data['Interstate_Composition_Value'] = parsed_data.get('interstate_composition_value', None)
    excel_data['Interstate_Composition_IGST'] = parsed_data.get('interstate_composition_igst', None)
    excel_data['Interstate_UIN_Value'] = parsed_data.get('interstate_uin_value', None)
    excel_data['Interstate_UIN_IGST'] = parsed_data.get('interstate_uin_igst', None)
    
    # Add inward reverse charge fields
    excel_data['Inward_RC_Value'] = parsed_data.get('inward_reverse_charge_value', None)
    excel_data['Inward_RC_IGST'] = parsed_data.get('inward_reverse_charge_igst', None)
    excel_data['Inward_RC_CGST'] = parsed_data.get('inward_reverse_charge_cgst', None)
    excel_data['Inward_RC_SGST'] = parsed_data.get('inward_reverse_charge_sgst', None)
    excel_data['Inward_RC_Cess'] = parsed_data.get('inward_reverse_charge_cess', None)
    
    return excel_data

def process_gstr3b_text(text, filename=None):
    """
    Process GSTR-3B text and return the data in the required format.
    
    Args:
        text (str): The text content of the GSTR-3B form
        filename (str, optional): The filename to include in the output
        
    Returns:
        dict: A dictionary in the format required for the Excel file
    """
    # Parse the GSTR-3B text
    parsed_data = parse_gstr3b_from_text(text)
    
    # Convert to Excel format
    excel_data = convert_to_excel_format(parsed_data, filename)
    
    return excel_data


def extract_gstr1_data(pdf_path):
    """Extract structured data from a GSTR-1 PDF file."""
    data = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract all text content from the PDF
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            
            # Clean up repeated lines like IP Address and FINAL
            text = re.sub(r'IP Address:.*\n', '', text)
            text = re.sub(r'FINAL\n', '', text)
            
            # Extract header fields
            data['FileName'] = os.path.basename(pdf_path)
            data['GSTIN'] = extract_value(text, r'GSTIN\s*(.*)')
            data['LegalName'] = extract_value(text, r'Legal name of the registered person\s*(.*)')
            data['TradeName'] = extract_value(text, r'Trade name if any\s*(.*)')
            data['ARN'] = extract_value(text, r'ARN\s*(.*)')
            data['ARNDate'] = extract_value(text, r'ARN date\s*(.*)')
            data['TaxPeriod'] = extract_value(text, r'Tax period\s*(.*)')
            data['FinancialYear'] = extract_value(text, r'Financial year\s*(.*)')
            
            # Extract table-wise totals
            
            # 4A - B2B Regular
            data['4A_Value'] = extract_table_value(text, r'4A - Taxable outward supplies.*\nTotal.*Invoice\s*([\d,.]+)')
            data['4A_IGST'] = extract_table_value(text, r'4A - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*([\d,.]+)')
            data['4A_CGST'] = extract_table_value(text, r'4A - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['4A_SGST'] = extract_table_value(text, r'4A - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['4A_Cess'] = extract_table_value(text, r'4A - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # 4B - B2B Reverse charge
            data['4B_Value'] = extract_table_value(text, r'4B - Taxable outward supplies.*\nTotal.*Invoice\s*([\d,.]+)')
            data['4B_IGST'] = extract_table_value(text, r'4B - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*([\d,.]+)')
            data['4B_CGST'] = extract_table_value(text, r'4B - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['4B_SGST'] = extract_table_value(text, r'4B - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['4B_Cess'] = extract_table_value(text, r'4B - Taxable outward supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # 5 - B2CL (Large)
            data['5_Value'] = extract_table_value(text, r'5 - Taxable outward inter-state supplies.*\nTotal.*Invoice\s*([\d,.]+)')
            data['5_IGST'] = extract_table_value(text, r'5 - Taxable outward inter-state supplies.*\nTotal.*Invoice\s*[\d,.]+\s*([\d,.]+)')
            data['5_Cess'] = extract_table_value(text, r'5 - Taxable outward inter-state supplies.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # 6A - Exports
            table_6a_data = extract_table_6a_values(text)
            data.update(table_6a_data)
            
            # 6B - SEZ Supplies
            data['6B_Value'] = extract_table_value(text, r'6B - Supplies made to SEZ.*\nTotal.*Invoice\s*([\d,.]+)')
            data['6B_IGST'] = extract_table_value(text, r'6B - Supplies made to SEZ.*\nTotal.*Invoice\s*[\d,.]+\s*([\d,.]+)')
            data['6B_Cess'] = extract_table_value(text, r'6B - Supplies made to SEZ.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # 6C - Deemed Exports
            data['6C_Value'] = extract_table_value(text, r'6C - Deemed Exports.*\nTotal.*Invoice\s*([\d,.]+)')
            data['6C_IGST'] = extract_table_value(text, r'6C - Deemed Exports.*\nTotal.*Invoice\s*[\d,.]+\s*([\d,.]+)')
            data['6C_CGST'] = extract_table_value(text, r'6C - Deemed Exports.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['6C_SGST'] = extract_table_value(text, r'6C - Deemed Exports.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['6C_Cess'] = extract_table_value(text, r'6C - Deemed Exports.*\nTotal.*Invoice\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # 7 - B2CS (Others)
            table_7_data = extract_table_7_values(text)
            data.update(table_7_data)
            
            # 8 - Nil rated, exempted and non GST
            table_8_data = extract_table_8_values(text)
            data.update(table_8_data)
            
            # 9A - Amendments to Taxable Supplies
            table_9a_data = extract_table_9a_values(text)
            data.update(table_9a_data)
            
            # 9B - Credit/Debit Notes (Unregistered)
            table_9b_data = extract_table_9b_values(text)
            data.update(table_9b_data)
            
            # 9C - Amended Credit/Debit Notes
            table_9c_data = extract_table_9c_values(text)
            data.update(table_9c_data)
            
            # 10 - Amendment to B2C Supplies
            table_10_data = extract_table_10_values(text)
            data.update(table_10_data)
            
            # 11A and 11B - Advances and Adjustments
            table_11_data = extract_table_11_values(text)
            data.update(table_11_data)
            
            # 14 - E-Commerce Supplies
            table_14_data = extract_table_14_values(text)
            data.update(table_14_data)
            
            # 14A - Amended E-Commerce Supplies
            table_14a_data = extract_table_14a_values(text)
            data.update(table_14a_data)
            
            # 15 - Supplies U/s 9(5)
            table_15_data = extract_table_15_values(text)
            data.update(table_15_data)
            
            # 15A - Amended Supplies U/s 9(5)
            table_15a_data = extract_table_15a_values(text)
            data.update(table_15a_data)
            
            # 12 - HSN-wise summary 
            data['12_Value'] = extract_table_value(text, r'12 - HSN-wise summary.*\nTotal.*NA\s*([\d,.]+)')
            data['12_IGST'] = extract_table_value(text, r'12 - HSN-wise summary.*\nTotal.*NA\s*[\d,.]+\s*([\d,.]+)')
            data['12_CGST'] = extract_table_value(text, r'12 - HSN-wise summary.*\nTotal.*NA\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['12_SGST'] = extract_table_value(text, r'12 - HSN-wise summary.*\nTotal.*NA\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            data['12_Cess'] = extract_table_value(text, r'12 - HSN-wise summary.*\nTotal.*NA\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*[\d,.]+\s*([\d,.]+)')
            
            # Summary (Page 2 Total)
            summary_data = extract_summary_values(text)
            data.update(summary_data)
            
            # Verification details 
            data['VerificationDate'] = extract_value(text, r'Date:\s*(.*)')
            data['AuthorizedSignatory'] = extract_value(text, r'Name of Authorized Signatory\s*(.*)')
            data['Designation'] = extract_value(text, r'Designation/Status:\s*(.*)')
            
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        
    return data

def extract_value(text, pattern):
    """Extract a single value using regex pattern."""
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ""

def extract_table_value(text, pattern):
    """Extract table values using regex pattern."""
    match = re.search(pattern, text)
    if match:
        value = match.group(1).strip()
        return value if value else ""
    return ""

def extract_table_6a_values(text):
    """Improved extraction for Table 6A - Exports."""
    data = {}
    
    # Total exports
    total_match = re.search(r'6A – Exports.*?\nTotal\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if total_match:
        data['6A_Value'] = total_match.group(1).strip()
        data['6A_IGST'] = total_match.group(2).strip()
        data['6A_Cess'] = total_match.group(3).strip()
    else:
        data['6A_Value'] = ""
        data['6A_IGST'] = ""
        data['6A_Cess'] = ""
    
    # Export with payment
    expwp_match = re.search(r'- EXPWP\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text)
    if expwp_match:
        data['6A_EXPWP_Value'] = expwp_match.group(1).strip()
        data['6A_EXPWP_IGST'] = expwp_match.group(2).strip()
        data['6A_EXPWP_Cess'] = expwp_match.group(3).strip()
    else:
        data['6A_EXPWP_Value'] = ""
        data['6A_EXPWP_IGST'] = ""
        data['6A_EXPWP_Cess'] = ""
    
    # Export without payment
    expwop_match = re.search(r'- EXPWOP\s+\d+\s+Invoice\s+([\d,.]+)', text)
    if expwop_match:
        data['6A_EXPWOP_Value'] = expwop_match.group(1).strip()
    else:
        data['6A_EXPWOP_Value'] = ""
    
    return data

def extract_table_7_values(text):
    """Improved extraction for Table 7 - B2CS (Others)."""
    data = {}
    
    # Look for the pattern with more context
    b2cs_match = re.search(r'7-\s+Taxable\s+supplies.*?unregistered\s+persons.*?\n.*?\n.*?Total\s+\d+\s+Net\s+Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    
    if not b2cs_match:
        # Alternative pattern with fewer constraints
        b2cs_match = re.search(r'Total\s+\d+\s+Net\s+Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text)
    
    if b2cs_match:
        data['7_Value'] = b2cs_match.group(1).strip()
        data['7_IGST'] = b2cs_match.group(2).strip()
        data['7_CGST'] = b2cs_match.group(3).strip()
        data['7_SGST'] = b2cs_match.group(4).strip()
        data['7_Cess'] = b2cs_match.group(5).strip()
    else:
        data['7_Value'] = ""
        data['7_IGST'] = ""
        data['7_CGST'] = ""
        data['7_SGST'] = ""
        data['7_Cess'] = ""
    
    return data

def extract_table_8_values(text):
    """Improved extraction for Table 8 - Nil rated, exempted and non GST."""
    data = {}
    
    # Extract using looser patterns with better context
    total_match = re.search(r'8\s+-\s+Nil\s+rated.*?\nTotal\s+([\d,.]+)', text, re.DOTALL)
    if total_match:
        data['8_Total'] = total_match.group(1).strip()
    else:
        data['8_Total'] = ""
    
    # Extract Nil value
    nil_match = re.search(r'-\s+Nil\s+([\d,.]+)', text)
    if nil_match:
        data['8_Nil'] = nil_match.group(1).strip()
    else:
        data['8_Nil'] = ""
    
    # Extract Exempted value
    exempted_match = re.search(r'-\s+Exempted\s+([\d,.]+)', text)
    if exempted_match:
        data['8_Exempted'] = exempted_match.group(1).strip()
    else:
        data['8_Exempted'] = ""
    
    # Extract Non-GST value
    non_gst_match = re.search(r'-\s+Non-GST\s+([\d,.]+)', text)
    if non_gst_match:
        data['8_NonGST'] = non_gst_match.group(1).strip()
    else:
        data['8_NonGST'] = ""
    
    return data

def extract_table_9a_values(text):
    """Extract Table 9A - Amendments to Taxable Supplies."""
    data = {}
    
    # B2B Regular
    b2b_reg_match = re.search(r'9A - Amendment to taxable outward supplies.*B2B Regular.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    
    # B2B Reverse Charge
    b2b_rev_match = re.search(r'9A - Amendment to taxable outward supplies.*B2B Reverse charge.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    b2cl_match = re.search(r'9A - Amendment to Inter-State supplies.*B2CL.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if b2cl_match:
        data['9A_B2CL_Value'] = b2cl_match.group(1).strip()
        data['9A_B2CL_IGST'] = b2cl_match.group(2).strip()
        data['9A_B2CL_Cess'] = b2cl_match.group(3).strip()
    else:
        data['9A_B2CL_Value'] = ""
        data['9A_B2CL_IGST'] = ""
        data['9A_B2CL_Cess'] = ""
    
    # Exports (EXPWP)
    expwp_match = re.search(r'9A - Amendment to Export supplies.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if expwp_match:
        data['9A_EXPWP_Value'] = expwp_match.group(1).strip()
        data['9A_EXPWP_IGST'] = expwp_match.group(2).strip()
        data['9A_EXPWP_Cess'] = expwp_match.group(3).strip()
    else:
        data['9A_EXPWP_Value'] = ""
        data['9A_EXPWP_IGST'] = ""
        data['9A_EXPWP_Cess'] = ""
    
    # Exports (EXPWOP)
    expwop_match = re.search(r'9A - Amendment to Export supplies.*- EXPWOP\s+\d+\s+Invoice\s+([\d,.]+|0.00)', text)
    if expwop_match:
        data['9A_EXPWOP_Value'] = expwop_match.group(1).strip()
    else:
        data['9A_EXPWOP_Value'] = ""
    
    # SEZ (SEZWP)
    sezwp_match = re.search(r'9A - Amendment to supplies made to SEZ.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if sezwp_match:
        data['9A_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['9A_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['9A_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['9A_SEZWP_Value'] = ""
        data['9A_SEZWP_IGST'] = ""
        data['9A_SEZWP_Cess'] = ""
    
    # SEZ (SEZWOP)
    sezwop_match = re.search(r'9A - Amendment to supplies made to SEZ.*- SEZWOP\s+\d+\s+Invoice\s+([\d,.]+|0.00)', text)
    if sezwop_match:
        data['9A_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['9A_SEZWOP_Value'] = ""
    
    # Deemed Exports
    de_match = re.search(r'9A - Amendment to Deemed Exports.*\nAmended amount - Total\s+\d+\s+Invoice\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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

def extract_table_9b_values(text):
    """Extract Table 9B - Credit/Debit Notes (Unregistered)."""
    data = {}
    
    # Total
    total_match = re.search(r'9B - Credit/Debit Notes \(Unregistered\).*\nTotal - Net off debit/credit notes\s+\d+\s+Note\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if total_match:
        data['9B_Value'] = total_match.group(1).strip()
        data['9B_IGST'] = total_match.group(2).strip()
        data['9B_Cess'] = total_match.group(3).strip()
    else:
        data['9B_Value'] = ""
        data['9B_IGST'] = ""
        data['9B_Cess'] = ""
    
    # B2CL
    b2cl_match = re.search(r'9B - Credit/Debit Notes \(Unregistered\).*-\s+B2CL\s+\d+\s+Note\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if b2cl_match:
        data['9B_B2CL_Value'] = b2cl_match.group(1).strip()
        data['9B_B2CL_IGST'] = b2cl_match.group(2).strip()
        data['9B_B2CL_Cess'] = b2cl_match.group(3).strip()
    else:
        data['9B_B2CL_Value'] = ""
        data['9B_B2CL_IGST'] = ""
        data['9B_B2CL_Cess'] = ""
    
    # EXPWP
    expwp_match = re.search(r'9B - Credit/Debit Notes \(Unregistered\).*-\s+EXPWP\s+\d+\s+Note\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if expwp_match:
        data['9B_EXPWP_Value'] = expwp_match.group(1).strip()
        data['9B_EXPWP_IGST'] = expwp_match.group(2).strip()
        data['9B_EXPWP_Cess'] = expwp_match.group(3).strip()
    else:
        data['9B_EXPWP_Value'] = ""
        data['9B_EXPWP_IGST'] = ""
        data['9B_EXPWP_Cess'] = ""
    
    # EXPWOP
    expwop_match = re.search(r'9B - Credit/Debit Notes \(Unregistered\).*-\s+EXPWOP\s+\d+\s+Note\s+([\d,.]+|0.00)', text, re.DOTALL)
    if expwop_match:
        data['9B_EXPWOP_Value'] = expwop_match.group(1).strip()
    else:
        data['9B_EXPWOP_Value'] = ""
    
    return data

def extract_table_9c_values(text):
    """Extract Table 9C - Amended Credit/Debit Notes (Registered and Unregistered)."""
    data = {}
    
    # Registered (CDNRA)
    cdnra_match = re.search(r'9C - Amended Credit/Debit Notes \(Registered\).*\nAmended amount - Total\s+\d+\s+Note\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if cdnra_match:
        data['9C_Value'] = cdnra_match.group(1).strip()
        data['9C_IGST'] = cdnra_match.group(2).strip()
        data['9C_CGST'] = cdnra_match.group(3).strip()
        data['9C_SGST'] = cdnra_match.group(4).strip()
        data['9C_Cess'] = cdnra_match.group(5).strip()
    else:
        data['9C_Value'] = ""
        data['9C_IGST'] = ""
        data['9C_CGST'] = ""
        data['9C_SGST'] = ""
        data['9C_Cess'] = ""
    
    # Unregistered (CDNURA) - B2CL
    cdnura_b2cl_match = re.search(r'9C - Amended Credit/Debit Notes \(Unregistered\).*B2CL\s+\d+\s+Note\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if cdnura_b2cl_match:
        data['9C_B2CL_Value'] = cdnura_b2cl_match.group(1).strip()
        data['9C_B2CL_IGST'] = cdnura_b2cl_match.group(2).strip()
        data['9C_B2CL_Cess'] = cdnura_b2cl_match.group(3).strip()
    else:
        data['9C_B2CL_Value'] = ""
        data['9C_B2CL_IGST'] = ""
        data['9C_B2CL_Cess'] = ""
    
    # Unregistered (CDNURA) - EXPWP
    cdnura_expwp_match = re.search(r'9C - Amended Credit/Debit Notes \(Unregistered\).*EXPWP\s+\d+\s+Note\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if cdnura_expwp_match:
        data['9C_EXPWP_Value'] = cdnura_expwp_match.group(1).strip()
        data['9C_EXPWP_IGST'] = cdnura_expwp_match.group(2).strip()
        data['9C_EXPWP_Cess'] = cdnura_expwp_match.group(3).strip()
    else:
        data['9C_EXPWP_Value'] = ""
        data['9C_EXPWP_IGST'] = ""
        data['9C_EXPWP_Cess'] = ""
    
    # Unregistered (CDNURA) - EXPWOP
    cdnura_expwop_match = re.search(r'9C - Amended Credit/Debit Notes \(Unregistered\).*EXPWOP\s+\d+\s+Note\s+([\d,.]+|0.00)', text, re.DOTALL)
    if cdnura_expwop_match:
        data['9C_EXPWOP_Value'] = cdnura_expwop_match.group(1).strip()
    else:
        data['9C_EXPWOP_Value'] = ""
    
    return data

def extract_table_10_values(text):
    """Extract Table 10 - Amendment to B2C Supplies."""
    data = {}
    
    match = re.search(r'10 - Amendment to taxable outward supplies.*B2C.*\nAmended amount - Total\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    
    return data

def extract_table_11_values(text):
    """Extract Table 11A and 11B - Advances and Adjustments."""
    data = {}
    
    # 11A
    match_11a = re.search(r'11A\(1\), 11A\(2\).*\nTotal\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if match_11a:
        data['11A_Value'] = match_11a.group(1).strip()
        data['11A_CGST'] = match_11a.group(2).strip()
        data['11A_SGST'] = match_11a.group(3).strip()
        data['11A_Cess'] = match_11a.group(4).strip()
    else:
        data['11A_Value'] = ""
        data['11A_CGST'] = ""
        data['11A_SGST'] = ""
        data['11A_Cess'] = ""
    
    # 11B
    match_11b = re.search(r'11B\(1\), 11B\(2\).*\nTotal\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if match_11b:
        data['11B_Value'] = match_11b.group(1).strip()
        data['11B_CGST'] = match_11b.group(2).strip()
        data['11B_SGST'] = match_11b.group(3).strip()
        data['11B_Cess'] = match_11b.group(4).strip()
    else:
        data['11B_Value'] = ""
        data['11B_CGST'] = ""
        data['11B_SGST'] = ""
        data['11B_Cess'] = ""
    
    return data

def extract_table_14_values(text):
    """Extract Table 14 - E-Commerce Supplies."""
    data = {}
    
    # Total
    total_match = re.search(r'14 - Supplies made through E-Commerce Operators.*\nTotal\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if total_match:
        data['14_Value'] = total_match.group(1).strip()
        data['14_CGST'] = total_match.group(2).strip()
        data['14_SGST'] = total_match.group(3).strip()
        data['14_Cess'] = total_match.group(4).strip()
    else:
        data['14_Value'] = ""
        data['14_CGST'] = ""
        data['14_SGST'] = ""
        data['14_Cess'] = ""
    
    # Liable to collect tax u/s 52
    u52_match = re.search(r'14 - Supplies made through E-Commerce Operators.*\(a\) Liable to collect tax u/s 52\s+\d+\s+Net Value\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    u95_match = re.search(r'14 - Supplies made through E-Commerce Operators.*\(b\) Liable to pay tax u/s 9\(5\)\s+\d+\s+Net Value\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    total_match = re.search(r'14A - Amended Supplies made through E-Commerce Operators.*\nAmended amount - Total\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    u52_match = re.search(r'14A - Amended Supplies made through E-Commerce Operators.*\(a\) Liable to collect tax u/s 52\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    u95_match = re.search(r'14A - Amended Supplies made through E-Commerce Operators.*\(b\) Liable to pay tax u/s 9\(5\)\s+\d+\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    total_match = re.search(r'15 - Supplies U/s 9\(5\).*\nTotal\s+\d+\s+Document/Not Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    reg_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+Regular\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    de_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+DE\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    sezwp_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+SEZWP\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if sezwp_match:
        data['15_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['15_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['15_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['15_SEZWP_Value'] = ""
        data['15_SEZWP_IGST'] = ""
        data['15_SEZWP_Cess'] = ""
    
    # Registered Recipients - SEZWOP
    sezwop_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+SEZWOP\s+\d+\s+Document\s+([\d,.]+|0.00)', text, re.DOTALL)
    if sezwop_match:
        data['15_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['15_SEZWOP_Value'] = ""
    
    # Unregistered Recipients
    unreg_match = re.search(r'15 - Supplies U/s 9\(5\).*-\s+For Unregistered Recipient\s+\d+\s+Net Value\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    reg_total_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*\nAmended amount - Total\s+\d+\s+Document\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
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
    reg_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+Regular\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    de_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+DE\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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
    sezwp_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+SEZWP\s+\d+\s+Document\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
    if sezwp_match:
        data['15A_SEZWP_Value'] = sezwp_match.group(1).strip()
        data['15A_SEZWP_IGST'] = sezwp_match.group(2).strip()
        data['15A_SEZWP_Cess'] = sezwp_match.group(3).strip()
    else:
        data['15A_SEZWP_Value'] = ""
        data['15A_SEZWP_IGST'] = ""
        data['15A_SEZWP_Cess'] = ""
    
    # Registered Recipients - SEZWOP
    sezwop_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Registered Recipients.*-\s+SEZWOP\s+\d+\s+Document\s+([\d,.]+|0.00)', text, re.DOTALL)
    if sezwop_match:
        data['15A_SEZWOP_Value'] = sezwop_match.group(1).strip()
    else:
        data['15A_SEZWOP_Value'] = ""
    
    # Unregistered Recipients
    unreg_match = re.search(r'15A \(i\) - Amended Supplies U/s 9\(5\) - For Unregistered Recipients.*\nAmended amount - Total\s+\d+\s+Net Value\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)\s+([\d,.]+|0.00)', text, re.DOTALL)
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

def extract_summary_values(text):
    """Extract Summary (Page 2 Total)."""
    data = {}
    
    match = re.search(r'Total\s+5\s+Net Value\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    if match:
        data['Summary_Value'] = match.group(1).strip()
        data['Summary_IGST'] = match.group(2).strip()
        data['Summary_CGST'] = match.group(3).strip()
        data['Summary_SGST'] = match.group(4).strip()
        data['Summary_Cess'] = match.group(5).strip()
    else:
        data['Summary_Value'] = ""
        data['Summary_IGST'] = ""
        data['Summary_CGST'] = ""
        data['Summary_SGST'] = ""
        data['Summary_Cess'] = ""
    
    return data
