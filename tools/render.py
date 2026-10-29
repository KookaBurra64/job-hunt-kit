"""Shared by build_cv.py and build_letter.py.

After a docx is saved: render it to PDF next to it with LibreOffice, count the
pages with pypdf, warn if over the limit. Without LibreOffice it says so and
does nothing else, so the builders still work on a machine without it.
LibreOffice is free: https://www.libreoffice.org/download/ (see START-HERE.md).
"""
import os, shutil, subprocess

CANDIDATES = [
    shutil.which('soffice'),
    r'C:\Program Files\LibreOffice\program\soffice.exe',
    r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
]


def soffice():
    return next((c for c in CANDIDATES if c and os.path.exists(c)), None)


def to_pdf(docx_path):
    """Returns (pdf_path, pages) or None when LibreOffice is absent."""
    exe = soffice()
    if not exe:
        print('no LibreOffice: PDF and page count skipped (install LibreOffice to get them, see START-HERE.md)')
        return None
    docx_path = os.path.abspath(docx_path)
    outdir = os.path.dirname(docx_path)
    subprocess.run([exe, '--headless', '--convert-to', 'pdf', '--outdir', outdir, docx_path],
                   check=True, capture_output=True, timeout=180)
    pdf = os.path.splitext(docx_path)[0] + '.pdf'
    pages = None
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(pdf).pages)
    except Exception as e:  # noqa: BLE001
        print('page count failed:', e)
    return pdf, pages


def report(docx_path, max_pages=1):
    """Prints the PDF path and page count. Returns 1 if over max_pages, else 0."""
    r = to_pdf(docx_path)
    if not r:
        return 0
    pdf, pages = r
    print('pdf', pdf, 'pages', pages)
    if pages and pages > max_pages:
        print(f'WARNING: {pages} pages, limit {max_pages}. Cut before sending.')
        return 1
    return 0
