# epd_pdf_extract_climate_change.py
# Scan all PDFs in data/epd_manual and print lines containing
# "Climate change" / "GWP" so you can see A1–A3 values + units.

from pathlib import Path
import pdfplumber
import re

PDF_DIR = Path("data/epd_manual")

KEYWORDS = ["climate change", "global warming potential", "gwp"]
A13_HINTS = ["a1-a3", "a1 – a3", "a1–a3", "a1 to a3"]

# optional: rough number finder
NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?")


def main():
    if not PDF_DIR.exists():
        print(f"Folder not found: {PDF_DIR}")
        return

    pdfs = list(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}")
        return

    for pdf_path in pdfs:
        print("=" * 80)
        print(f"FILE: {pdf_path.name}")
        print("=" * 80)

        try:
            with pdfplumber.open(pdf_path) as doc:
                lines = []
                for page in doc.pages:
                    text = page.extract_text() or ""
                    # keep page number for orientation if needed later
                    for ln in text.splitlines():
                        lines.append(ln)

                for ln in lines:
                    low = ln.lower()
                    if any(k in low for k in KEYWORDS):
                        # focus on rows likely to include A1-A3 or modules
                        has_a13 = any(h in low for h in A13_HINTS)
                        nums = NUM_RE.findall(ln)
                        print("---")
                        print(ln)
                        print(f"  -> has A1-A3 hint: {has_a13}, numbers: {nums}")
        except Exception as e:
            print(f"!! Error reading {pdf_path.name}: {e}")


if __name__ == "__main__":
    main()
