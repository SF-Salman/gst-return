import pdfplumber
import re

def detect_form_type(pdf_path: str) -> str:
    """
    Read only page 1 and return 'GSTR1', 'GSTR3B', 'GSTR2B', or 'UNKNOWN'.
    Signatures confirmed against real portal-generated PDFs:
      GSTR-1  → starts with "FORM GSTR-1"
      GSTR-3B → starts with "Form GSTR-3B"
      GSTR-2B → "GSTR-2B" or "Auto-drafted ITC Statement" (placeholder - update when you have a sample)
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return "UNKNOWN"
            text = pdf.pages[0].extract_text() or ""
        text_lower = text.lower()

        # GSTR-3B check first ("Form GSTR-3B" with capital F, lowercase 'orm')
        if "form gstr-3b" in text_lower:
            return "GSTR3B"

        # GSTR-1 ("FORM GSTR-1" all caps)
        if "form gstr-1" in text_lower:
            return "GSTR1"

        # GSTR-2B placeholder — update signatures once you have a real 2B PDF
        if "gstr-2b" in text_lower or "auto-drafted itc statement" in text_lower:
            return "GSTR2B"

        return "UNKNOWN"

    except Exception:
        return "UNKNOWN"