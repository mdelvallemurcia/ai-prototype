"""Minimal hand-built PDF bytes carrying real extractable text.

No PDF-authoring library is available as a dependency (reportlab/fpdf are not
installed and may not be added without approval — see CLAUDE.md). This raw PDF
syntax with a single text-show (Tj) operator is the smallest reliable way to
produce a PDF that PyPDFLoader can extract real text from for an E2E test.
"""

from __future__ import annotations

_HEADER = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R
   /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length """

_FOOTER = b"""
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""


def build_minimal_pdf(text_content: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 150 Td ({text_content}) Tj ET".encode("latin-1")
    body = str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n"
    return _HEADER + body + _FOOTER
