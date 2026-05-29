# eco_ui_harvest_zip.py
import argparse, io, pathlib, re, zipfile
from urllib.parse import urlparse, parse_qs, unquote
from playwright.sync_api import sync_playwright

OUT_XML = pathlib.Path("data/eco_xml")
OUT_XML.mkdir(parents=True, exist_ok=True)

NEXT_SELS = [
    "button[aria-label='Next']", "a[aria-label='Next']",
    "button[aria-label*='Go to next page' i], a[aria-label*='Go to next page' i]",
    "button:has-text('Next'), a:has-text('Next'), a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
]

def js_scroll_all(page):
    # step-scroll to force lazy content & bottom bar to render
    page.evaluate("""
        async () => {
          const step = 600; let y = 0;
          while (y < document.body.scrollHeight) {
            window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
            y += step;
          }
          window.scrollTo(0, document.body.scrollHeight);
        }
    """)

def extract_uuid(href: str) -> str | None:
    # .../resource/processes/<uuid>/zipexport?version=...
    try:
        q = parse_qs(urlparse(href).query)
        ru = unquote(q.get("redirect_uri", [""])[0])
        m = re.search(r"/processes/([0-9a-f-]{8,})/", ru, re.I)
        return m.group(1) if m else None
    except Exception:
        return None

def save_as_xml(eid: str | None, ctype: str, body: bytes) -> int:
    ctype = (ctype or "").lower()
    if "zip" in ctype:
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
            if not xmls:
                (OUT_XML / f"{eid or 'epd'}.zip").write_bytes(body)
                return 0
            data = z.read(xmls[0])
            (OUT_XML / f"{eid or 'epd'}.xml").write_bytes(data)
            return 1
    (OUT_XML / f"{eid or 'epd'}.xml").write_bytes(body)
    return 1

def collect_links(page) -> list[str]:
    # Ensure the table is in DOM (bottom of page)
    js_scroll_all(page)
    hrefs = set()
    # 1) The exact pattern you showed: anchor that contains <i.fa-file-code>
    for i in range(page.locator("a:has(i.fa-file-code)").count()):
        h = page.locator("a:has(i.fa-file-code)").nth(i).get_attribute("href")
        if h: hrefs.add(h)
    # 2) Fallback: any anchor with zipexport
    for i in range(page.locator("a[href*='zipexport']").count()):
        h = page.locator("a[href*='zipexport']").nth(i).get_attribute("href")
        if h: hrefs.add(h)
    return sorted(hrefs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="ECO list page URL (datasets table)")
    ap.add_argument("--term", default="photovoltaic", help="optional table search term")
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    if not pathlib.Path("auth.json").exists():
        raise SystemExit("auth.json not found. Run eco_login_capture.py first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json")
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)

        # Optional: narrow to PV
        search = page.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
        if search.count():
            search.fill(""); search.type(args.term); search.press("Enter"); page.wait_for_timeout(700)

        total_xml = 0
        for pnum in range(1, args.max_pages + 1):
            page.wait_for_load_state("networkidle")
            links = collect_links(page)
            print(f"[page {pnum}] ILCD links found: {len(links)}")

            if not links and pnum == 1:
                # Dump page HTML for quick inspection if needed
                pathlib.Path("data/last_page.html").write_text(page.content(), encoding="utf-8")
                raise SystemExit("No ILCD links found. Inspect data/last_page.html to adjust selectors.")

            for href in links:
                try:
                    eid = extract_uuid(href) or "epd"
                    resp = ctx.request.get(href, timeout=60_000)
                    if not resp.ok:
                        print(f"  ! GET {resp.status} {href[:90]}…"); continue
                    saved = save_as_xml(eid, resp.headers.get("content-type",""), resp.body())
                    if saved: total_xml += 1
                    page.wait_for_timeout(int(args.sleep * 1000))
                except Exception as e:
                    print(f"  ! download failed: {e}")

            # Next page
            moved = False
            for sel in NEXT_SELS:
                nxt = page.locator(sel).first
                try:
                    if nxt.count() and nxt.is_enabled():
                        nxt.click(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(500)
                        moved = True; break
                except Exception:
                    continue
            if not moved:
                print("[end] pagination ended."); break

        browser.close()
        print(f"[done] saved {total_xml} XML files → {OUT_XML}")

if __name__ == "__main__":
    main()
