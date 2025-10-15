import json
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_get(data: Dict, *keys, default=""):
    """Safely navigate nested dictionary with multiple keys."""
    try:
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, {})
            else:
                return default
        return result if result != {} else default
    except (KeyError, TypeError, AttributeError):
        return default

def safe_float(value):
    """Safely convert value to float."""
    try:
        if value and value != "-" and value != "":
            clean_value = str(value).replace(',', '')
            return round(float(clean_value), 2)
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def extract_gstr1_from_json(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract GSTR-1 data from JSON format.
    Supports both official GSTN JSON format and custom formats.
    """
    extracted_data = {}

    try:
        logger.info("Starting GSTR-1 JSON extraction")

        # Basic Information
        extracted_data['GSTIN'] = safe_get(json_data, 'gstin') or safe_get(json_data, 'GSTIN')
        extracted_data['LegalName'] = safe_get(json_data, 'legal_name') or safe_get(json_data, 'lgnm')
        extracted_data['TradeName'] = safe_get(json_data, 'trade_name') or safe_get(json_data, 'trdnm')
        extracted_data['ARN'] = safe_get(json_data, 'arn') or safe_get(json_data, 'ARN')
        extracted_data['ARNDate'] = safe_get(json_data, 'arn_date') or safe_get(json_data, 'arn_dt')
        extracted_data['TaxPeriod'] = safe_get(json_data, 'ret_period') or safe_get(json_data, 'tax_period')
        extracted_data['FinancialYear'] = safe_get(json_data, 'fy') or safe_get(json_data, 'financial_year')

        # Table 4A - B2B Regular
        b2b_data = safe_get(json_data, 'b2b', default=[])
        if b2b_data:
            extracted_data.update(extract_b2b_from_json(b2b_data))

        # Table 4B - B2B Reverse Charge
        b2ba_data = safe_get(json_data, 'b2ba', default=[])
        if b2ba_data:
            extracted_data.update(extract_b2ba_from_json(b2ba_data))

        # Table 5 - B2CL
        b2cl_data = safe_get(json_data, 'b2cl', default=[])
        if b2cl_data:
            extracted_data.update(extract_b2cl_from_json(b2cl_data))

        # Table 6A - Exports
        exp_data = safe_get(json_data, 'exp', default=[])
        if exp_data:
            extracted_data.update(extract_exp_from_json(exp_data))

        # Table 6B - SEZ Supplies
        sez_data = safe_get(json_data, 'sez', default=[])
        if sez_data:
            extracted_data.update(extract_sez_from_json(sez_data))

        # Table 6C - Deemed Exports
        de_data = safe_get(json_data, 'de', default=[])
        if de_data:
            extracted_data.update(extract_de_from_json(de_data))

        # Table 7 - B2CS
        b2cs_data = safe_get(json_data, 'b2cs', default=[])
        if b2cs_data:
            extracted_data.update(extract_b2cs_from_json(b2cs_data))

        # Table 8 - Nil Rated
        nil_data = safe_get(json_data, 'nil', default={})
        if nil_data:
            extracted_data.update(extract_nil_from_json(nil_data))

        # Table 9 - Credit/Debit Notes
        cdnr_data = safe_get(json_data, 'cdnr', default=[])
        if cdnr_data:
            extracted_data.update(extract_cdnr_from_json(cdnr_data))

        cdnur_data = safe_get(json_data, 'cdnur', default=[])
        if cdnur_data:
            extracted_data.update(extract_cdnur_from_json(cdnur_data))

        # Table 11 - Advances
        at_data = safe_get(json_data, 'at', default=[])
        if at_data:
            extracted_data.update(extract_at_from_json(at_data))

        # Table 12 - HSN Summary
        hsn_data = safe_get(json_data, 'hsn', default={})
        if hsn_data:
            extracted_data.update(extract_hsn_from_json(hsn_data))

        # Table 13 - Documents Issued
        doc_issue_data = safe_get(json_data, 'doc_issue', default={})
        if doc_issue_data:
            extracted_data.update(extract_doc_issue_from_json(doc_issue_data))

        logger.info(f"Successfully extracted {len(extracted_data)} fields from GSTR-1 JSON")

    except Exception as e:
        logger.error(f"Error extracting GSTR-1 from JSON: {str(e)}")
        extracted_data['parsing_error'] = str(e)

    return extracted_data

def extract_b2b_from_json(b2b_data):
    """Extract B2B invoice data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in b2b_data:
            invoices = safe_get(entry, 'inv', default=[])
            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cgst += safe_float(safe_get(itm_det, 'camt'))
                    total_sgst += safe_float(safe_get(itm_det, 'samt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting B2B data: {str(e)}")

    data['4A_Value'] = total_value
    data['4A_IGST'] = total_igst
    data['4A_CGST'] = total_cgst
    data['4A_SGST'] = total_sgst
    data['4A_Cess'] = total_cess

    return data

def extract_b2ba_from_json(b2ba_data):
    """Extract B2B amended invoice data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in b2ba_data:
            invoices = safe_get(entry, 'inv', default=[])
            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cgst += safe_float(safe_get(itm_det, 'camt'))
                    total_sgst += safe_float(safe_get(itm_det, 'samt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting B2BA data: {str(e)}")

    data['4B_Value'] = total_value
    data['4B_IGST'] = total_igst
    data['4B_CGST'] = total_cgst
    data['4B_SGST'] = total_sgst
    data['4B_Cess'] = total_cess

    return data

def extract_b2cl_from_json(b2cl_data):
    """Extract B2CL data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cess = 0.0

    try:
        for entry in b2cl_data:
            invoices = safe_get(entry, 'inv', default=[])
            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting B2CL data: {str(e)}")

    data['5_Value'] = total_value
    data['5_IGST'] = total_igst
    data['5_Cess'] = total_cess

    return data

def extract_exp_from_json(exp_data):
    """Extract export data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cess = 0.0
    expwp_value = 0.0
    expwp_igst = 0.0
    expwp_cess = 0.0
    expwop_value = 0.0

    try:
        for entry in exp_data:
            exp_typ = safe_get(entry, 'exp_typ')
            invoices = safe_get(entry, 'inv', default=[])

            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    value = safe_float(safe_get(itm_det, 'txval'))
                    igst = safe_float(safe_get(itm_det, 'iamt'))
                    cess = safe_float(safe_get(itm_det, 'csamt'))

                    total_value += value
                    total_igst += igst
                    total_cess += cess

                    if exp_typ == 'WPAY':
                        expwp_value += value
                        expwp_igst += igst
                        expwp_cess += cess
                    elif exp_typ == 'WOPAY':
                        expwop_value += value
    except Exception as e:
        logger.error(f"Error extracting export data: {str(e)}")

    data['6A_Value'] = total_value
    data['6A_IGST'] = total_igst
    data['6A_Cess'] = total_cess
    data['6A_EXPWP_Value'] = expwp_value
    data['6A_EXPWP_IGST'] = expwp_igst
    data['6A_EXPWP_Cess'] = expwp_cess
    data['6A_EXPWOP_Value'] = expwop_value

    return data

def extract_sez_from_json(sez_data):
    """Extract SEZ data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cess = 0.0

    try:
        for entry in sez_data:
            invoices = safe_get(entry, 'inv', default=[])
            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting SEZ data: {str(e)}")

    data['6B_Value'] = total_value
    data['6B_IGST'] = total_igst
    data['6B_Cess'] = total_cess

    return data

def extract_de_from_json(de_data):
    """Extract deemed export data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in de_data:
            invoices = safe_get(entry, 'inv', default=[])
            for invoice in invoices:
                items = safe_get(invoice, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cgst += safe_float(safe_get(itm_det, 'camt'))
                    total_sgst += safe_float(safe_get(itm_det, 'samt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting deemed export data: {str(e)}")

    data['6C_Value'] = total_value
    data['6C_IGST'] = total_igst
    data['6C_CGST'] = total_cgst
    data['6C_SGST'] = total_sgst
    data['6C_Cess'] = total_cess

    return data

def extract_b2cs_from_json(b2cs_data):
    """Extract B2CS data from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in b2cs_data:
            total_value += safe_float(safe_get(entry, 'txval'))
            total_igst += safe_float(safe_get(entry, 'iamt'))
            total_cgst += safe_float(safe_get(entry, 'camt'))
            total_sgst += safe_float(safe_get(entry, 'samt'))
            total_cess += safe_float(safe_get(entry, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting B2CS data: {str(e)}")

    data['7_Value'] = total_value
    data['7_IGST'] = total_igst
    data['7_CGST'] = total_cgst
    data['7_SGST'] = total_sgst
    data['7_Cess'] = total_cess

    return data

def extract_nil_from_json(nil_data):
    """Extract nil rated data from JSON."""
    data = {}

    try:
        inv_data = safe_get(nil_data, 'inv', default=[])
        total = 0.0
        nil_amt = 0.0
        expt_amt = 0.0
        ngsup_amt = 0.0

        for entry in inv_data:
            sply_ty = safe_get(entry, 'sply_ty')
            value = safe_float(safe_get(entry, 'expt_amt'))

            if sply_ty == 'NILRATED':
                nil_amt += value
            elif sply_ty == 'EXEMP':
                expt_amt += value
            elif sply_ty == 'NONGST':
                ngsup_amt += value

            total += value

        data['8_Total'] = total
        data['8_Nil'] = nil_amt
        data['8_Exempted'] = expt_amt
        data['8_NonGST'] = ngsup_amt
    except Exception as e:
        logger.error(f"Error extracting nil rated data: {str(e)}")

    return data

def extract_cdnr_from_json(cdnr_data):
    """Extract credit/debit notes (registered) from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in cdnr_data:
            notes = safe_get(entry, 'nt', default=[])
            for note in notes:
                items = safe_get(note, 'itms', default=[])
                for item in items:
                    itm_det = safe_get(item, 'itm_det', default={})
                    total_value += safe_float(safe_get(itm_det, 'txval'))
                    total_igst += safe_float(safe_get(itm_det, 'iamt'))
                    total_cgst += safe_float(safe_get(itm_det, 'camt'))
                    total_sgst += safe_float(safe_get(itm_det, 'samt'))
                    total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting CDNR data: {str(e)}")

    data['9C_Value'] = total_value
    data['9C_IGST'] = total_igst
    data['9C_CGST'] = total_cgst
    data['9C_SGST'] = total_sgst
    data['9C_Cess'] = total_cess

    return data

def extract_cdnur_from_json(cdnur_data):
    """Extract credit/debit notes (unregistered) from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cess = 0.0

    try:
        for entry in cdnur_data:
            items = safe_get(entry, 'itms', default=[])
            for item in items:
                itm_det = safe_get(item, 'itm_det', default={})
                total_value += safe_float(safe_get(itm_det, 'txval'))
                total_igst += safe_float(safe_get(itm_det, 'iamt'))
                total_cess += safe_float(safe_get(itm_det, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting CDNUR data: {str(e)}")

    data['9B_Value'] = total_value
    data['9B_IGST'] = total_igst
    data['9B_Cess'] = total_cess

    return data

def extract_at_from_json(at_data):
    """Extract advance tax data from JSON."""
    data = {}
    total_value = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        for entry in at_data:
            total_value += safe_float(safe_get(entry, 'ad_amt'))
            total_cgst += safe_float(safe_get(entry, 'camt'))
            total_sgst += safe_float(safe_get(entry, 'samt'))
            total_cess += safe_float(safe_get(entry, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting advance tax data: {str(e)}")

    data['11A_Value'] = total_value
    data['11A_CGST'] = total_cgst
    data['11A_SGST'] = total_sgst
    data['11A_Cess'] = total_cess

    return data

def extract_hsn_from_json(hsn_data):
    """Extract HSN summary from JSON."""
    data = {}
    total_value = 0.0
    total_igst = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_cess = 0.0

    try:
        data_list = safe_get(hsn_data, 'data', default=[])
        for entry in data_list:
            total_value += safe_float(safe_get(entry, 'txval'))
            total_igst += safe_float(safe_get(entry, 'iamt'))
            total_cgst += safe_float(safe_get(entry, 'camt'))
            total_sgst += safe_float(safe_get(entry, 'samt'))
            total_cess += safe_float(safe_get(entry, 'csamt'))
    except Exception as e:
        logger.error(f"Error extracting HSN data: {str(e)}")

    data['12_Value'] = total_value
    data['12_IGST'] = total_igst
    data['12_CGST'] = total_cgst
    data['12_SGST'] = total_sgst
    data['12_Cess'] = total_cess

    return data

def extract_doc_issue_from_json(doc_issue_data):
    """Extract document issue data from JSON."""
    data = {}

    try:
        doc_det = safe_get(doc_issue_data, 'doc_det', default=[])
        total_value = 0.0

        for entry in doc_det:
            total_value += safe_float(safe_get(entry, 'tot_num'))

        data['13_Value'] = total_value
    except Exception as e:
        logger.error(f"Error extracting document issue data: {str(e)}")

    return data

def extract_gstr3b_from_json(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract GSTR-3B data from JSON format.
    Supports both official GSTN JSON format and custom formats.
    """
    extracted_data = {}

    try:
        logger.info("Starting GSTR-3B JSON extraction")

        # Basic Information
        extracted_data['gstin'] = safe_get(json_data, 'gstin')
        extracted_data['legal_name'] = safe_get(json_data, 'legal_name') or safe_get(json_data, 'lgnm')
        extracted_data['trade_name'] = safe_get(json_data, 'trade_name') or safe_get(json_data, 'trdnm')
        extracted_data['period'] = safe_get(json_data, 'ret_period')
        extracted_data['year'] = safe_get(json_data, 'fy')
        extracted_data['arn'] = safe_get(json_data, 'arn')
        extracted_data['arn_date'] = safe_get(json_data, 'arn_dt')

        # Table 3.1 - Outward Supplies
        sup_details = safe_get(json_data, 'sup_details', default={})
        if sup_details:
            extracted_data.update(extract_3_1_from_json(sup_details))

        # Table 3.1.1 - Section 9(5) Supplies
        inter_sup = safe_get(json_data, 'inter_sup', default={})
        if inter_sup:
            extracted_data.update(extract_3_1_1_from_json(inter_sup))

        # Table 3.2 - Inter-State Supplies
        if inter_sup:
            extracted_data.update(extract_3_2_from_json(inter_sup))

        # Table 4 - ITC
        itc_elg = safe_get(json_data, 'itc_elg', default={})
        if itc_elg:
            extracted_data.update(extract_4_from_json(itc_elg))

        # Table 5 - Exempt Supplies
        inward_sup = safe_get(json_data, 'inward_sup', default={})
        if inward_sup:
            extracted_data.update(extract_5_from_json(inward_sup))

        # Table 5.1 - Interest and Late Fee
        intr_details = safe_get(json_data, 'intr_details', default={})
        if intr_details:
            extracted_data.update(extract_5_1_from_json(intr_details))

        # Table 6.1 - Payment of Tax
        tax_pmt = safe_get(json_data, 'tax_pmt', default={})
        if tax_pmt:
            extracted_data.update(extract_6_1_from_json(tax_pmt))

        logger.info(f"Successfully extracted {len(extracted_data)} fields from GSTR-3B JSON")

    except Exception as e:
        logger.error(f"Error extracting GSTR-3B from JSON: {str(e)}")
        extracted_data['parsing_error'] = str(e)

    return extracted_data

def extract_3_1_from_json(sup_details):
    """Extract Table 3.1 data from JSON."""
    data = {}

    try:
        osup_det = safe_get(sup_details, 'osup_det', default={})

        data['outward_taxable_value'] = safe_float(safe_get(osup_det, 'txval'))
        data['outward_igst'] = safe_float(safe_get(osup_det, 'iamt'))
        data['outward_cgst'] = safe_float(safe_get(osup_det, 'camt'))
        data['outward_sgst'] = safe_float(safe_get(osup_det, 'samt'))
        data['outward_cess'] = safe_float(safe_get(osup_det, 'csamt'))

        osup_zero = safe_get(sup_details, 'osup_zero', default={})
        data['zero_rated_value'] = safe_float(safe_get(osup_zero, 'txval'))
        data['zero_rated_igst'] = safe_float(safe_get(osup_zero, 'iamt'))

        osup_nil_exmp = safe_get(sup_details, 'osup_nil_exmp', default={})
        data['nil_exempt_value'] = safe_float(safe_get(osup_nil_exmp, 'txval'))

        osup_nongst = safe_get(sup_details, 'osup_nongst', default={})
        data['non_gst_value'] = safe_float(safe_get(osup_nongst, 'txval'))

        isup_rev = safe_get(sup_details, 'isup_rev', default={})
        data['inward_reverse_charge_value'] = safe_float(safe_get(isup_rev, 'txval'))
        data['inward_reverse_charge_igst'] = safe_float(safe_get(isup_rev, 'iamt'))
        data['inward_reverse_charge_cgst'] = safe_float(safe_get(isup_rev, 'camt'))
        data['inward_reverse_charge_sgst'] = safe_float(safe_get(isup_rev, 'samt'))
        data['inward_reverse_charge_cess'] = safe_float(safe_get(isup_rev, 'csamt'))

    except Exception as e:
        logger.error(f"Error extracting 3.1 data: {str(e)}")

    return data

def extract_3_1_1_from_json(inter_sup):
    """Extract Table 3.1.1 data from JSON."""
    data = {}

    try:
        unreg_details = safe_get(inter_sup, 'unreg_details', default=[])

        for entry in unreg_details:
            supply_type = safe_get(entry, 'supply_type')

            if supply_type == 'INTER':
                data['interstate_unreg_value'] = safe_float(safe_get(entry, 'txval'))
                data['interstate_unreg_igst'] = safe_float(safe_get(entry, 'iamt'))
            elif supply_type == 'INTRA':
                data['sec_9_5_ecom_operator_value'] = safe_float(safe_get(entry, 'txval'))
                data['sec_9_5_ecom_operator_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['sec_9_5_ecom_operator_sgst'] = safe_float(safe_get(entry, 'samt'))

        comp_details = safe_get(inter_sup, 'comp_details', default=[])
        for entry in comp_details:
            data['interstate_composition_value'] = safe_float(safe_get(entry, 'txval'))
            data['interstate_composition_igst'] = safe_float(safe_get(entry, 'iamt'))

        uin_details = safe_get(inter_sup, 'uin_details', default=[])
        for entry in uin_details:
            data['interstate_uin_value'] = safe_float(safe_get(entry, 'txval'))
            data['interstate_uin_igst'] = safe_float(safe_get(entry, 'iamt'))

    except Exception as e:
        logger.error(f"Error extracting 3.1.1 data: {str(e)}")

    return data

def extract_3_2_from_json(inter_sup):
    """Extract Table 3.2 data from JSON."""
    return {}

def extract_4_from_json(itc_elg):
    """Extract Table 4 (ITC) data from JSON."""
    data = {}

    try:
        itc_avl = safe_get(itc_elg, 'itc_avl', default=[])

        for entry in itc_avl:
            ty = safe_get(entry, 'ty')

            if ty == 'IMPG':
                data['import_goods_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['import_goods_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['import_goods_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['import_goods_cess'] = safe_float(safe_get(entry, 'csamt'))
            elif ty == 'IMPS':
                data['import_services_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['import_services_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['import_services_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['import_services_cess'] = safe_float(safe_get(entry, 'csamt'))
            elif ty == 'ISRC':
                data['reverse_charge_itc_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['reverse_charge_itc_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['reverse_charge_itc_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['reverse_charge_itc_cess'] = safe_float(safe_get(entry, 'csamt'))
            elif ty == 'ISD':
                data['isd_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['isd_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['isd_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['isd_cess'] = safe_float(safe_get(entry, 'csamt'))
            elif ty == 'OTH':
                data['other_itc_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['other_itc_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['other_itc_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['other_itc_cess'] = safe_float(safe_get(entry, 'csamt'))

        itc_rev = safe_get(itc_elg, 'itc_rev', default=[])
        for entry in itc_rev:
            ty = safe_get(entry, 'ty')

            if ty == 'RUL':
                data['rules_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['rules_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['rules_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['rules_cess'] = safe_float(safe_get(entry, 'csamt'))
            elif ty == 'OTH':
                data['others_igst'] = safe_float(safe_get(entry, 'iamt'))
                data['others_cgst'] = safe_float(safe_get(entry, 'camt'))
                data['others_sgst'] = safe_float(safe_get(entry, 'samt'))
                data['others_cess'] = safe_float(safe_get(entry, 'csamt'))

        itc_net = safe_get(itc_elg, 'itc_net', default={})
        data['net_itc_igst'] = safe_float(safe_get(itc_net, 'iamt'))
        data['net_itc_cgst'] = safe_float(safe_get(itc_net, 'camt'))
        data['net_itc_sgst'] = safe_float(safe_get(itc_net, 'samt'))
        data['net_itc_cess'] = safe_float(safe_get(itc_net, 'csamt'))

    except Exception as e:
        logger.error(f"Error extracting ITC data: {str(e)}")

    return data

def extract_5_from_json(inward_sup):
    """Extract Table 5 (Exempt Supplies) data from JSON."""
    data = {}

    try:
        isup_details = safe_get(inward_sup, 'isup_details', default=[])

        for entry in isup_details:
            ty = safe_get(entry, 'ty')

            if ty == 'GST':
                data['composition_inter_state'] = safe_float(safe_get(entry, 'inter'))
                data['composition_intra_state'] = safe_float(safe_get(entry, 'intra'))
            elif ty == 'NONGST':
                data['non_gst_inter_state'] = safe_float(safe_get(entry, 'inter'))
                data['non_gst_intra_state'] = safe_float(safe_get(entry, 'intra'))
            elif ty == 'NIL':
                data['nil_rated_inter_state'] = safe_float(safe_get(entry, 'inter'))
                data['nil_rated_intra_state'] = safe_float(safe_get(entry, 'intra'))
            elif ty == 'EXMP':
                data['exempted_inter_state'] = safe_float(safe_get(entry, 'inter'))
                data['exempted_intra_state'] = safe_float(safe_get(entry, 'intra'))

    except Exception as e:
        logger.error(f"Error extracting exempt supplies data: {str(e)}")

    return data

def extract_5_1_from_json(intr_details):
    """Extract Table 5.1 (Interest and Late Fee) data from JSON."""
    data = {}

    try:
        data['interest_igst'] = safe_float(safe_get(intr_details, 'intr_iamt'))
        data['interest_cgst'] = safe_float(safe_get(intr_details, 'intr_camt'))
        data['interest_sgst'] = safe_float(safe_get(intr_details, 'intr_samt'))
        data['interest_cess'] = safe_float(safe_get(intr_details, 'intr_csamt'))

        data['late_fee_igst'] = safe_float(safe_get(intr_details, 'fee_iamt'))
        data['late_fee_cgst'] = safe_float(safe_get(intr_details, 'fee_camt'))
        data['late_fee_sgst'] = safe_float(safe_get(intr_details, 'fee_samt'))

    except Exception as e:
        logger.error(f"Error extracting interest/late fee data: {str(e)}")

    return data

def extract_6_1_from_json(tax_pmt):
    """Extract Table 6.1 (Payment of Tax) data from JSON."""
    data = {}

    try:
        data['igst_payable'] = safe_float(safe_get(tax_pmt, 'tax_iamt'))
        data['cgst_payable'] = safe_float(safe_get(tax_pmt, 'tax_camt'))
        data['sgst_payable'] = safe_float(safe_get(tax_pmt, 'tax_samt'))
        data['cess_payable'] = safe_float(safe_get(tax_pmt, 'tax_csamt'))

        data['igst_paid_itc_igst'] = safe_float(safe_get(tax_pmt, 'itc_iamt'))
        data['cgst_paid_itc_cgst'] = safe_float(safe_get(tax_pmt, 'itc_camt'))
        data['sgst_paid_itc_sgst'] = safe_float(safe_get(tax_pmt, 'itc_samt'))

        data['igst_paid_cash'] = safe_float(safe_get(tax_pmt, 'cash_iamt'))
        data['cgst_paid_cash'] = safe_float(safe_get(tax_pmt, 'cash_camt'))
        data['sgst_paid_cash'] = safe_float(safe_get(tax_pmt, 'cash_samt'))
        data['cess_paid_cash'] = safe_float(safe_get(tax_pmt, 'cash_csamt'))

        data['igst_interest'] = safe_float(safe_get(tax_pmt, 'intr_iamt'))
        data['cgst_interest'] = safe_float(safe_get(tax_pmt, 'intr_camt'))
        data['sgst_interest'] = safe_float(safe_get(tax_pmt, 'intr_samt'))
        data['cess_interest'] = safe_float(safe_get(tax_pmt, 'intr_csamt'))

        data['igst_late_fee'] = safe_float(safe_get(tax_pmt, 'fee_iamt'))
        data['cgst_late_fee'] = safe_float(safe_get(tax_pmt, 'fee_camt'))
        data['sgst_late_fee'] = safe_float(safe_get(tax_pmt, 'fee_samt'))

    except Exception as e:
        logger.error(f"Error extracting payment of tax data: {str(e)}")

    return data

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        return {}
