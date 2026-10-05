"""Markdown reports -> PDF (tables + images), using Chrome's headless "print to PDF".

Usage: python docs/build_pdf.py        -> docs/report.pdf
Needs Google Chrome (path below; on Windows: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe).
"""
import os
import subprocess
import sys
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
REPORTS = ["report"]
CHROME = {
    "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "win32": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}.get(sys.platform, "google-chrome")

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10pt;
       line-height: 1.45; color: #222; }
h1 { font-size: 18pt; border-bottom: 2px solid #2a78d6; padding-bottom: 4px; }
h2 { font-size: 13.5pt; margin-top: 18px; border-bottom: 1px solid #ddd; padding-bottom: 2px; }
h3 { font-size: 11.5pt; }
h2, h3 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.5pt; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #eef3fa; }
tr:nth-child(even) td { background: #fafafa; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.5pt; background: #f3f3f1; padding: 0 3px; border-radius: 3px; }
pre { background: #f3f3f1; padding: 8px 10px; border-radius: 4px; font-size: 7.8pt; line-height: 1.35;
      white-space: pre; overflow: hidden; break-inside: avoid; }  /* keep ASCII diagrams intact */
pre code { background: none; padding: 0; }
img { max-width: 100%; break-inside: avoid; }
p:has(img) { break-inside: avoid; text-align: center; }
em { color: #555; }
"""


def build(name: str):
    md = (DOCS / f"{name}.md").read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html_path = DOCS / f".{name}.html"  # next to the .md so the relative image paths still work
    html_path.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{name}</title>"
                         f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    pdf = DOCS / f"{name}.pdf"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html_path.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html_path)
    print("wrote", pdf)


if __name__ == "__main__":
    for r in REPORTS:
        build(r)
