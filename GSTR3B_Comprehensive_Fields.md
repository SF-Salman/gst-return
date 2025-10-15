# GSTR-3B Comprehensive Field Extraction Guide

## Overview
The enhanced GSTR-3B tool now captures ALL available information from GSTR-3B returns, providing comprehensive coverage of every field and table present in the return.

## Basic Information Fields

### 1. Registration Details
- **gstin**: GSTIN of the supplier
- **legal_name**: Legal name of the registered person
- **trade_name**: Trade name (if any)
- **period**: Tax period (month)
- **year**: Financial year
- **arn**: ARN (Acknowledgement Reference Number)
- **arn_date**: Date of ARN
- **arn_date_parsed**: Parsed ARN date

### 2. Authorized Signatory
- **authorized_signatory**: Name of authorized signatory
- **designation**: Designation/Status of signatory

### 3. Verification Details
- **verification_date**: Date of verification
- **place_of_signing**: Place of signing
- **digital_signature**: Digital signature details

## Table 3.1: Outward Supplies

### 3.1.1: Taxable Outward Supplies
- **outward_taxable_value**: Total taxable value
- **outward_igst**: IGST amount
- **outward_cgst**: CGST amount
- **outward_sgst**: SGST amount
- **outward_cess**: CESS amount

### 3.1.2: Zero Rated Supplies
- **zero_rated_value**: Zero rated supplies value
- **zero_rated_igst**: Zero rated IGST

### 3.1.3: Nil Rated/Exempted Supplies
- **nil_exempt_value**: Nil rated/exempted supplies value

### 3.1.4: Non-GST Supplies
- **non_gst_value**: Non-GST supplies value

### 3.1.5: Inward Supplies Liable to Reverse Charge
- **inward_reverse_charge_value**: Value of inward supplies liable to reverse charge
- **inward_reverse_charge_igst**: IGST on reverse charge supplies
- **inward_reverse_charge_cgst**: CGST on reverse charge supplies
- **inward_reverse_charge_sgst**: SGST on reverse charge supplies
- **inward_reverse_charge_cess**: CESS on reverse charge supplies

## Table 3.1.1: Supplies under Section 9(5)

### Electronic Commerce Operator
- **sec_9_5_ecom_operator_value**: Value of supplies where e-commerce operator pays tax
- **sec_9_5_ecom_operator_igst**: IGST amount
- **sec_9_5_ecom_operator_cgst**: CGST amount
- **sec_9_5_ecom_operator_sgst**: SGST amount
- **sec_9_5_ecom_operator_cess**: CESS amount

### Registered Person through E-commerce Operator
- **sec_9_5_registered_person_value**: Value of supplies through e-commerce operator
- **sec_9_5_registered_person_igst**: IGST amount
- **sec_9_5_registered_person_cgst**: CGST amount
- **sec_9_5_registered_person_sgst**: SGST amount
- **sec_9_5_registered_person_cess**: CESS amount

## Table 3.2: Inter-State Supplies

### Unregistered Persons
- **interstate_unreg_value**: Value of supplies to unregistered persons
- **interstate_unreg_igst**: IGST amount

### Composition Taxable Persons
- **interstate_composition_value**: Value of supplies to composition taxable persons
- **interstate_composition_igst**: IGST amount

### UIN Holders
- **interstate_uin_value**: Value of supplies to UIN holders
- **interstate_uin_igst**: IGST amount

## Table 4: ITC Available

### 4(A): ITC Available
- **import_goods_igst**: ITC on import of goods - IGST
- **import_goods_cgst**: ITC on import of goods - CGST
- **import_goods_sgst**: ITC on import of goods - SGST
- **import_goods_cess**: ITC on import of goods - CESS

- **import_services_igst**: ITC on import of services - IGST
- **import_services_cgst**: ITC on import of services - CGST
- **import_services_sgst**: ITC on import of services - SGST
- **import_services_cess**: ITC on import of services - CESS

- **reverse_charge_itc_igst**: ITC on inward supplies liable to reverse charge - IGST
- **reverse_charge_itc_cgst**: ITC on inward supplies liable to reverse charge - CGST
- **reverse_charge_itc_sgst**: ITC on inward supplies liable to reverse charge - SGST
- **reverse_charge_itc_cess**: ITC on inward supplies liable to reverse charge - CESS

- **isd_igst**: ITC from ISD - IGST
- **isd_cgst**: ITC from ISD - CGST
- **isd_sgst**: ITC from ISD - SGST
- **isd_cess**: ITC from ISD - CESS

- **other_itc_igst**: All other ITC - IGST
- **other_itc_cgst**: All other ITC - CGST
- **other_itc_sgst**: All other ITC - SGST
- **other_itc_cess**: All other ITC - CESS

### 4(B): ITC Reversed
- **rules_igst**: ITC reversed as per rules 38, 42 & 43 - IGST
- **rules_cgst**: ITC reversed as per rules 38, 42 & 43 - CGST
- **rules_sgst**: ITC reversed as per rules 38, 42 & 43 - SGST
- **rules_cess**: ITC reversed as per rules 38, 42 & 43 - CESS

- **others_igst**: ITC reversed - Others - IGST
- **others_cgst**: ITC reversed - Others - CGST
- **others_sgst**: ITC reversed - Others - SGST
- **others_cess**: ITC reversed - Others - CESS

### 4(C): Net ITC Available
- **net_itc_igst**: Net ITC available - IGST
- **net_itc_cgst**: Net ITC available - CGST
- **net_itc_sgst**: Net ITC available - SGST
- **net_itc_cess**: Net ITC available - CESS

### 4(D): Other Details
- **itc_reclaimed_igst**: ITC reclaimed - IGST
- **itc_reclaimed_cgst**: ITC reclaimed - CGST
- **itc_reclaimed_sgst**: ITC reclaimed - SGST
- **itc_reclaimed_cess**: ITC reclaimed - CESS

- **ineligible_itc_igst**: Ineligible ITC - IGST
- **ineligible_itc_cgst**: Ineligible ITC - CGST
- **ineligible_itc_sgst**: Ineligible ITC - SGST
- **ineligible_itc_cess**: Ineligible ITC - CESS

## Table 5: Exempt/Nil/Non-GST Inward Supplies

### Composition Scheme
- **composition_inter_state**: From supplier under composition scheme - Inter-state
- **composition_intra_state**: From supplier under composition scheme - Intra-state

### Non-GST Supply
- **non_gst_inter_state**: Non-GST supply - Inter-state
- **non_gst_intra_state**: Non-GST supply - Intra-state

### Nil Rated Supplies
- **nil_rated_inter_state**: Nil rated supplies - Inter-state
- **nil_rated_intra_state**: Nil rated supplies - Intra-state

### Exempted Supplies
- **exempted_inter_state**: Exempted supplies - Inter-state
- **exempted_intra_state**: Exempted supplies - Intra-state

## Table 5.1: Interest and Late Fee

### Interest Paid
- **interest_igst**: Interest paid - IGST
- **interest_cgst**: Interest paid - CGST
- **interest_sgst**: Interest paid - SGST
- **interest_cess**: Interest paid - CESS

### Late Fee
- **late_fee_igst**: Late fee - IGST
- **late_fee_cgst**: Late fee - CGST
- **late_fee_sgst**: Late fee - SGST
- **late_fee_cess**: Late fee - CESS

## Table 6.1: Payment of Tax

### Other than Reverse Charge

#### IGST
- **igst_payable**: IGST payable
- **igst_paid_itc_igst**: IGST paid through ITC - IGST
- **igst_paid_itc_cgst**: IGST paid through ITC - CGST
- **igst_paid_itc_sgst**: IGST paid through ITC - SGST
- **igst_paid_cash**: IGST paid in cash
- **igst_interest**: IGST interest
- **igst_late_fee**: IGST late fee

#### CGST
- **cgst_payable**: CGST payable
- **cgst_paid_itc_igst**: CGST paid through ITC - IGST
- **cgst_paid_itc_cgst**: CGST paid through ITC - CGST
- **cgst_paid_itc_sgst**: CGST paid through ITC - SGST
- **cgst_paid_cash**: CGST paid in cash
- **cgst_interest**: CGST interest
- **cgst_late_fee**: CGST late fee

#### SGST
- **sgst_payable**: SGST payable
- **sgst_paid_itc_igst**: SGST paid through ITC - IGST
- **sgst_paid_itc_cgst**: SGST paid through ITC - CGST
- **sgst_paid_itc_sgst**: SGST paid through ITC - SGST
- **sgst_paid_cash**: SGST paid in cash
- **sgst_interest**: SGST interest
- **sgst_late_fee**: SGST late fee

#### CESS
- **cess_payable**: CESS payable
- **cess_paid_itc_igst**: CESS paid through ITC - IGST
- **cess_paid_itc_cgst**: CESS paid through ITC - CGST
- **cess_paid_itc_sgst**: CESS paid through ITC - SGST
- **cess_paid_cash**: CESS paid in cash
- **cess_interest**: CESS interest
- **cess_late_fee**: CESS late fee

### Reverse Charge

#### IGST
- **rc_igst_payable**: RC IGST payable
- **rc_igst_paid_cash**: RC IGST paid in cash

#### CGST
- **rc_cgst_payable**: RC CGST payable
- **rc_cgst_paid_cash**: RC CGST paid in cash

#### SGST
- **rc_sgst_payable**: RC SGST payable
- **rc_sgst_paid_cash**: RC SGST paid in cash

#### CESS
- **rc_cess_payable**: RC CESS payable
- **rc_cess_paid_cash**: RC CESS paid in cash

## Additional Fields

### Late Fee Details
- **late_fee_details_igst**: Late fee details - IGST
- **late_fee_details_cgst**: Late fee details - CGST
- **late_fee_details_sgst**: Late fee details - SGST
- **late_fee_details_cess**: Late fee details - CESS

### Interest Details
- **interest_details_igst**: Interest details - IGST
- **interest_details_cgst**: Interest details - CGST
- **interest_details_sgst**: Interest details - SGST
- **interest_details_cess**: Interest details - CESS

### Refund Claimed
- **refund_claimed_igst**: Refund claimed - IGST
- **refund_claimed_cgst**: Refund claimed - CGST
- **refund_claimed_sgst**: Refund claimed - SGST
- **refund_claimed_cess**: Refund claimed - CESS

## HSN Summary
- **hsn_total_value**: HSN summary total value
- **hsn_total_igst**: HSN summary total IGST
- **hsn_total_cgst**: HSN summary total CGST
- **hsn_total_sgst**: HSN summary total SGST
- **hsn_total_cess**: HSN summary total CESS

## Additional Tax Details

### TDS Details
- **tds_value**: TDS value
- **tds_igst**: TDS IGST
- **tds_cgst**: TDS CGST
- **tds_sgst**: TDS SGST

### TCS Details
- **tcs_value**: TCS value
- **tcs_igst**: TCS IGST
- **tcs_cgst**: TCS CGST
- **tcs_sgst**: TCS SGST

## Reverse Charge Supplies
- **value**: Reverse charge supplies value
- **igst**: Reverse charge supplies IGST
- **cgst**: Reverse charge supplies CGST
- **sgst**: Reverse charge supplies SGST
- **cess**: Reverse charge supplies CESS

## Other Debit/Credit Entries
- **value**: Other debit/credit entries value
- **igst**: Other debit/credit entries IGST
- **cgst**: Other debit/credit entries CGST
- **sgst**: Other debit/credit entries SGST
- **cess**: Other debit/credit entries CESS

## Summary Statistics (Calculated)
- **total_outward_supplies_value**: Total outward supplies value
- **total_itc_available_igst**: Total ITC available IGST
- **total_tax_payable**: Total tax payable

## Validation and Error Fields
- **validation_errors**: List of validation errors
- **parsing_error**: Any major parsing errors

## File Information
- **filename**: Name of the uploaded file

## Usage Notes

1. **Comprehensive Coverage**: This tool extracts ALL available fields from GSTR-3B returns, ensuring no information is missed.

2. **Pattern Matching**: Uses multiple pattern variations to handle different PDF formats and layouts.

3. **Error Handling**: Comprehensive error handling ensures the tool continues processing even if some fields fail to extract.

4. **Summary Calculations**: Automatically calculates totals and summary statistics for validation purposes.

5. **Logging**: Detailed logging for debugging and verification of extracted data.

6. **Excel Export**: All extracted data is exported to Excel format for easy analysis and reporting.

## Field Mapping

The tool maps all extracted fields to standard column names in the Excel output, making it easy to:
- Compare data across different periods
- Perform data analysis
- Generate reports
- Validate GST returns
- Audit compliance

This comprehensive extraction ensures that users have access to every piece of information available in their GSTR-3B returns, enabling better compliance management and business decision-making.
