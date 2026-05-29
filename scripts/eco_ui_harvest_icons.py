# eco_ui_harvest_icons.py
import re, argparse, pathlib
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUT_DIR = pathlib.Path("data/eco_xml")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ICON_PARENT_SELECTORS = [
    "a:has(i.fa-file-code)",      # link that contains the file-code icon
    "button:has(i.fa-file-code)", # button that contains it
]
ICON_SELECTORS_RAW = [
    "i.fa-file-code",             # raw icon; we will find its clickable ancestor
]

NEXT_SELECTORS = [
    "button[aria-label='Next']",
    "a[aria-label='Next']",
    "button[aria-label*='Go to next page' i], a[aria-label*='Go to next page' i]",
    "button:has-text('Next'), a:has-text('Next'), a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
]

def guess_id(url:str, filename:str)->str:
    q = parse_qs(urlparse(url).query)
    for k in ("id","uuid","code"):
        if k in q and q[k]: return q[k][0]
    m = re.search(r"/([0-9a-f-]{8,})[\./]", url, flags=re.I)
    if m: return m.group(1)
    m = re.search(r"([0-9a-f-]{8,})", filename or "", flags=re.I)
    return m.group(1) if m else (filename or "epd")

def click_and_capture(page, clickable, sleep_ms:int) -> int:
    """Click a single clickable control and capture XML via download or popup; return 1 if saved."""
    # Try native download
    try:
        with page.expect_download(timeout=7000) as dl_info:
            clickable.click(force=True, timeout=7000)
        dl = dl_info.value
        eid = guess_id(dl.url, dl.suggested_filename or "epd.xml")
        dl.save_as(str(OUT_DIR / f"{eid}.xml"))
        page.wait_for_timeout(sleep_ms)
        return 1
    except PWTimeout:
        pass
    except Exception:
        pass

    # Fallback: some portals open XML in a new tab
    try:
        with page.expect_popup(timeout=5000) as pop_info:
            clickable.click(force=True, timeout=5000)
        pop = pop_info.value
        pop.wait_for_load_state("domcontentloaded")
        # Get raw XML text from the new tab
        xml = pop.evaluate("() => (new XMLSerializer()).serializeToString(document)")
        eid = guess_id(pop.url, "epd.xml")
        (OUT_DIR / f"{eid}.xml").write_text(xml, encoding="utf-8", errors="ignore")
        pop.close()
        page.wait_for_timeout(sleep_ms)
        return 1
    except PWTimeout:
        return 0
    except Exception:
        return 0

def download_all_on_page(page, sleep_ms:int) -> int:
    saved = 0
    # 1) Direct parents containing the icon
    for sel in ICON_PARENT_SELECTORS:
        loc = page.locator(sel)
        cnt = 0
        try: cnt = loc.count()
        except Exception: cnt = 0
        for i in range(cnt):
            el = loc.nth(i)
            if not el.is_visible(): continue
            saved += click_and_capture(page, el, sleep_ms)

    # 2) Raw <i.fa-file-code> → climb to a/button ancestor
    raw_icons = page.locator(ICON_SELECTORS_RAW[0])
    try: n = raw_icons.count()
    except Exception: n = 0
    for i in range(n):
        icon = raw_icons.nth(i)
        if not icon.is_visible(): continue
        parent = icon.locator("xpath=ancestor::a[1]")
        if not parent.count():
            parent = icon.locator("xpath=ancestor::button[1]")
        if parent.count() and parent.first.is_visible():
            saved += click_and_capture(page, parent.first, sleep_ms)
    return saved

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="ECO list page URL (datasets table)")
    ap.add_argument("--term", default="photovoltaic", help="search term to filter table")
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    if not pathlib.Path("auth.json").exists():
        raise SystemExit("auth.json not found. Run eco_login_capture.py first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json", accept_downloads=True)
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)

        # Optional filter to narrow to PV terms
        search = page.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
        if search.count():
            search.fill("")
            search.type(args.term)
            search.press("Enter")
            page.wait_for_timeout(800)

        total = 0
        for pnum in range(1, args.max_pages+1):
            print(f"[page {pnum}] scanning for ILCD icons…")
            got = download_all_on_page(page, int(args.sleep*1000))
            print(f"  downloads this page: {got}")
            total += got

            # Next page
            moved = False
            for sel in NEXT_SELECTORS:
                nxt = page.locator(sel).first
                try:
                    if nxt.count() and nxt.is_enabled():
                        nxt.click()
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(500)
                        moved = True
                        break
                except Exception:
                    continue
            if not moved:
                print("[end] no next page or end reached.")
                break

        browser.close()
        print(f"[done] downloaded {total} XML files → {OUT_DIR}")

if __name__ == "__main__":
    main()
