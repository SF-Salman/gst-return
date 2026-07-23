"""
Core backend package for GST extractor logic.

Modules here should not import or depend on Streamlit.
"""
from .gstr1_vs_3b import reconcile_gstr1_vs_gstr3b, generate_excel_report