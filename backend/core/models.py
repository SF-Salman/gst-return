from typing import TypedDict, Literal

class InvoiceRecord(TypedDict):
    gstin: str
    invoice_no: str
    invoice_date: str
    taxable_value: float
    cgst: float
    sgst: float
    igst: float
    source: Literal["GSTR-1", "2A", "2B", "PR"]