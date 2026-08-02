#!/usr/bin/env python
"""Render docs/portfolio-report.md into docs/portfolio-report.pdf.

Build-time tooling only (markdown + xhtml2pdf are NOT runtime dependencies). Produces a clean,
print-ready PDF with a simple, professional style. Run:  python scripts/build_report_pdf.py
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "portfolio-report.md"
OUT = ROOT / "docs" / "portfolio-report.pdf"

CSS = """
@page { size: A4; margin: 2.0cm 1.8cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5px; color: #1a1f29;
       line-height: 1.5; }
h1 { font-size: 20px; color: #0C0F16; border-bottom: 2px solid #E7B24C; padding-bottom: 4px;
     margin-top: 6px; }
h2 { font-size: 14px; color: #1a2230; margin-top: 16px; border-bottom: 1px solid #d7dde6;
     padding-bottom: 2px; }
h3 { font-size: 12px; color: #2a3242; margin-top: 12px; }
p { margin: 6px 0; }
code { font-family: Courier, monospace; background: #f2f4f7; font-size: 9.5px; }
blockquote { border-left: 3px solid #E7B24C; margin: 8px 0; padding: 4px 10px;
             background: #fbf7ee; color: #3a3320; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5px; }
th, td { border: 1px solid #cdd4de; padding: 4px 6px; text-align: left; }
th { background: #eef1f5; }
ul, ol { margin: 6px 0 6px 4px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #d7dde6; margin: 14px 0; }
"""


def strip_front_matter(text: str) -> str:
    """Remove a leading YAML front-matter block (--- ... ---) if present."""
    if text.startswith("---"):
        return re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL)
    return text


def main() -> None:
    md_text = strip_front_matter(SRC.read_text())
    body = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "sane_lists", "toc"]
    )
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    with OUT.open("wb") as fh:
        result = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
    if result.err:
        raise SystemExit(f"PDF generation failed with {result.err} error(s)")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({size_kb:.0f} KiB)")


if __name__ == "__main__":
    main()
