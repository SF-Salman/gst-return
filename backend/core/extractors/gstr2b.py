"""
GSTR-2B extractor.

GSTR-2B is the static auto-drafted ITC statement generated monthly by the
GSTN portal. Unlike 2A (which updates in real time), 2B is locked on the
cut-off date and is the basis for ITC claims.

The JSON structure downloaded from the GSTN portal is identical to GSTR-2A.
The only difference is the source tag ("2B" instead of "2A") so this file
is a dedicated extractor that outputs InvoiceRecord with source="2B".

Supported sections from the GSTN 2B JSON:
  - b2b   : B2B invoices (regular)
  - b2ba  : B2B amended invoices
  - cdnr  : Credit/Debit notes (registered)
  - cdnra : Credit/Debit notes amended (registered)
  - impg  : Import of goods (bill of entry)
  - impgsez: Import of goods from SEZ
"""

from backend.core.models import InvoiceRecord
from backend.utils import safe_float, safe_get
import logging

logger = logging.getLogger(__name__)


def extract_2b(data: dict) -> list[InvoiceRecord]:
    """
    Parse a GSTN GSTR-2B JSON payload and return a list of InvoiceRecord dicts.

    Args:
        data: The parsed JSON dict from the GSTN portal 2B download.
              Top-level key is usually "data" containing "docdata".

    Returns:
        List of InvoiceRecord with source="2B".
    """
    records: list[InvoiceRecord] = []

    # GSTN wraps everything under data -> docdata
    # Some portal downloads have the docdata at the top level
    doc = safe_get(data, "data", "docdata") or safe_get(data, "docdata") or data

    # ── B2B invoices ────────────────────────────────────────────────────────
    for supplier in safe_get(doc, "b2b") or []:
        gstin = supplier.get("ctin", "")
        for inv in supplier.get("inv") or []:
            cgst = sgst = igst = 0.0
            for item in inv.get("itms") or []:
                detail = item.get("itm_det", {})
                cgst += safe_float(detail.get("camt", 0))
                sgst += safe_float(detail.get("samt", 0))
                igst += safe_float(detail.get("iamt", 0))
            records.append(InvoiceRecord(
                gstin=gstin,
                invoice_no=inv.get("inum", ""),
                invoice_date=inv.get("dt", ""),
                taxable_value=safe_float(inv.get("val", 0)),
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                source="2B"
            ))

    # ── B2B amended invoices ─────────────────────────────────────────────────
    for supplier in safe_get(doc, "b2ba") or []:
        gstin = supplier.get("ctin", "")
        for inv in supplier.get("inv") or []:
            cgst = sgst = igst = 0.0
            for item in inv.get("itms") or []:
                detail = item.get("itm_det", {})
                cgst += safe_float(detail.get("camt", 0))
                sgst += safe_float(detail.get("samt", 0))
                igst += safe_float(detail.get("iamt", 0))
            records.append(InvoiceRecord(
                gstin=gstin,
                invoice_no=inv.get("inum", ""),
                invoice_date=inv.get("dt", ""),
                taxable_value=safe_float(inv.get("val", 0)),
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                source="2B"
            ))

    # ── Credit/Debit notes (registered) ─────────────────────────────────────
    for supplier in safe_get(doc, "cdnr") or []:
        gstin = supplier.get("ctin", "")
        for note in supplier.get("nt") or []:
            cgst = sgst = igst = 0.0
            for item in note.get("itms") or []:
                detail = item.get("itm_det", {})
                cgst += safe_float(detail.get("camt", 0))
                sgst += safe_float(detail.get("samt", 0))
                igst += safe_float(detail.get("iamt", 0))
            records.append(InvoiceRecord(
                gstin=gstin,
                invoice_no=note.get("nt_num", ""),
                invoice_date=note.get("dt", ""),
                taxable_value=safe_float(note.get("val", 0)),
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                source="2B"
            ))

    # ── Import of goods (bill of entry) ─────────────────────────────────────
    for boe in safe_get(doc, "impg") or []:
        records.append(InvoiceRecord(
            gstin="",                               # imports have no supplier GSTIN
            invoice_no=str(boe.get("boe_num", "")),
            invoice_date=boe.get("boe_dt", ""),
            taxable_value=safe_float(boe.get("txval", 0)),
            cgst=0.0,
            sgst=0.0,
            igst=safe_float(boe.get("iamt", 0)),
            source="2B"
        ))

    # ── Import of goods from SEZ ─────────────────────────────────────────────
    for boe in safe_get(doc, "impgsez") or []:
        gstin = boe.get("sgstin", "")              # SEZ supplier GSTIN
        records.append(InvoiceRecord(
            gstin=gstin,
            invoice_no=str(boe.get("boe_num", "")),
            invoice_date=boe.get("boe_dt", ""),
            taxable_value=safe_float(boe.get("txval", 0)),
            cgst=0.0,
            sgst=0.0,
            igst=safe_float(boe.get("iamt", 0)),
            source="2B"
        ))

    logger.info(f"Extracted {len(records)} records from GSTR-2B JSON")
    return records
