import os
from detector import detect_form_type

def parse_gst_return(pdf_path: str) -> dict:
    """
    Auto-detect form type and route to the correct parser.
    Always returns a dict with at minimum:
      - form_type   : 'GSTR1' | 'GSTR3B' | 'GSTR2B' | 'UNKNOWN'
      - source_file : filename only (no path)
    """
    form_type = detect_form_type(pdf_path)

    if form_type == "GSTR3B":
        from gstr3b import parse_gstr3b
        result = parse_gstr3b(pdf_path)

    elif form_type == "GSTR1":
        from gstr1 import extract_gstr1_data
        result = extract_gstr1_data(pdf_path)

    elif form_type == "GSTR2B":
        # Wire in when you have the real file + parser ready
        result = {"_extraction_warnings": "GSTR2B parser not yet implemented"}

    else:
        result = {
            "_extraction_warnings": f"Could not identify form type for: {os.path.basename(pdf_path)}"
        }

    # Always tag with these two so batch.py can route correctly
    result["form_type"] = form_type
    result["source_file"] = os.path.basename(pdf_path)
    return result