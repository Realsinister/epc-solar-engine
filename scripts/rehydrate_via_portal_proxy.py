# rehydrate_via_portal_proxy.py
# Download ECO zipexports using Playwright's browser request context (with stored login),
# via the portal-proxy URL. Saves to data/eco_zip/<uuid>.zip

from pathlib import Path
import pandas as pd
from urllib.parse import urlparse, parse_qs, quote
from playwright.sync_api import sync_playwright

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
OUT_DIR = Path("data/eco_zip")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PORTAL = "https://eco-portal.eco-platform.org/"
PROXY  = "https://portal-proxy.eco-platform.org"

def to_proxy(url: str) -> str:
    """Ensure we request via ECO's portal-proxy."""
    if not url:
        return ""
    if url.startswith(PROXY):
        return url
    return f"{PROXY}?redirect_uri={quote(url, safe='')}"

def uuid_from_any(url: str) -> str:
    import re
    m = re.search(r"/processes/([0-9a-f-]{8,})/", url, re.I)
    return m.group(1) if m else ""

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")
    try:
        df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
    except Exception:
        raise SystemExit(f"Sheet '{XML_SHEET}' not found in {WB}")

    rows = []
    for _, r in df.iterrows():
        href = (r.get("href") or "").strip()
        if not href:
            continue
        rows.append(href)

    if not rows:
        print("No href values in ILCD_XML; harvest first.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use saved login/session if available
        if Path("auth.json").exists():
            ctx = browser.new_context(storage_state="auth.json")
        else:
            ctx = browser.new_context()
        api = ctx.request

        ok = fail = 0
        for href in rows:
            proxy_url = to_proxy(href)
            uid = uuid_from_any(href) or uuid_from_any(proxy_url) or "unknown"
            out = OUT_DIR / f"{uid}.zip"

            # Always overwrite to be sure
            resp = api.get(
                proxy_url,
                headers={
                    "Referer": PORTAL,
                    "Accept": "application/zip, application/octet-stream, application/xml, */*",
                },
                timeout=120_000,
            )
            if not resp.ok:
                print(f"! {uid} -> HTTP {resp.status} {resp.url}")
                fail += 1
                continue

            body = resp.body()
            ctype = (resp.headers.get("content-type") or "").lower()
            # Save even if not a ZIP; later scripts handle 'not zip' gracefully
            out.write_bytes(body)
            print(f"+ {uid} {len(body)} bytes  ({ctype})")
            ok += 1

        browser.close()
        print(f"Done. downloaded={ok} failed={fail} -> {OUT_DIR}")

if __name__ == "__main__":
    main()
