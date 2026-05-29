# rehydrate_archives_force.py
import time, requests, pandas as pd
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
OUT_DIR = Path("data/eco_zip")
OUT_DIR.mkdir(parents=True, exist_ok=True)

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://eco-portal.eco-platform.org/",
    "Accept": "application/zip, application/xml, */*",
}

def main():
    df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
    ok = 0; fail = 0
    for _, row in df.iterrows():
        href = (row.get("href") or "").strip()
        if not href:
            continue
        # extract redirect_uri and dataset_uuid
        try:
            ru = unquote(parse_qs(urlparse(href).query).get("redirect_uri", [""])[0])
        except Exception:
            continue
        uid = (row.get("dataset_uuid") or "").strip() or "unknown"
        out = OUT_DIR / f"{uid}.zip"
        try:
            r = requests.get(ru, headers=HDR, timeout=120, allow_redirects=True)
            if r.status_code != 200:
                print(f"! GET {r.status_code} {uid}")
                fail += 1; continue
            out.write_bytes(r.content)  # overwrite always
            ok += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"! ERR {uid}: {e}")
            fail += 1
    print(f"Done. downloaded={ok} failed={fail} -> {OUT_DIR}")

if __name__ == "__main__":
    main()
