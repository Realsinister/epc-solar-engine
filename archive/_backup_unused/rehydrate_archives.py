# rehydrate_archives.py
# Re-download Environdec zipexport for each href in ILCD_XML and save full zip.
import re, time, requests, pandas as pd
from pathlib import Path
from urllib.parse import unquote, urlparse

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
OUT_DIR = Path("data/eco_zip")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Quick check for one UUID (replace <UUID>):
# import zipfile, io, re
# from pathlib import Path
# uid="<UUID>"
# p=Path("data/eco_zip")/f"{uid}.zip"
# data=p.read_bytes()
# with zipfile.ZipFile(io.BytesIO(data)) as z:
#     for n in z.namelist():
#         if n.lower().endswith(".xml"):
#             t=z.read(n).decode("utf-8","ignore")
#             if any(k in t.lower() for k in ["gwp","climate change","global warming potential","a1-a3","a1 – a3","a1–a3"]):
#                 print("HIT in", n); break
# print("Checked", p)


def uuid_from_href(href: str) -> str|None:
    try:
        # href is already a redirect_uri to Environdec; keep as-is
        m = re.search(r"/processes/([0-9a-f-]{8,})/", href, re.I)
        return m.group(1) if m else None
    except Exception:
        return None

def main():
    df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
    ok = 0; skip=0; fail=0
    for _, row in df.iterrows():
        href = (row.get("href") or "").strip()
        if not href:
            continue
        uid = (row.get("dataset_uuid") or "").strip() or uuid_from_href(href) or "unknown"
        out = OUT_DIR / f"{uid}.zip"
        if out.exists() and out.stat().st_size > 0:
            skip += 1
            continue
        try:
            r = requests.get(href, headers={
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer":"https://eco-portal.eco-platform.org/"
            }, timeout=90)
            if r.status_code != 200:
                fail += 1
                print(f"  ! GET {r.status_code} {uid}")
                continue
            # Save whatever we got; most will be ZIP, some direct XML
            out.write_bytes(r.content)
            ok += 1
            time.sleep(0.3)
        except Exception as e:
            fail += 1
            print(f"  ! ERR {uid}: {e}")
    print(f"Done. downloaded={ok} skipped={skip} failed={fail} -> {OUT_DIR}")
if __name__ == "__main__":
    main()
