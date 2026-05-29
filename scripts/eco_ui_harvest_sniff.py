# eco_ui_harvest_sniff.py
import argparse, io, pathlib, re, zipfile, time
from urllib.parse import urlparse, parse_qs, unquote
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUT_DIR = pathlib.Path("data/eco_xml")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_uuid_from_url(u: str) -> str | None:
    # Handles portal-proxy redirect: ?redirect_uri=https%3A%2F%2F.../processes/<uuid>/zipexport?version=...
    try:
        q = parse_qs(urlparse(u).query)
        ru = unquote(q.get("redirect_uri", [""])[0])
        m = re.search(r"/processes/([0-9a-f-]{8,})/", ru, re.I)
        if m:
            return m.group(1)
        # Fallback: pick up uuid directly in URL if present
        m2 = re.search(r"/([0-9a-f-]{8,})/(?:zipexport|download)", u, re.I)
        return m2.group(1) if m2 else None
    except Exception:
        return None

def save_zip_or_xml(eid: str | None, ctype: str, body: bytes) -> bool:
    name = (eid or "epd").strip() or "epd"
    ctype = (ctype or "").lower()
    try:
        if "zip" in ctype or body[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
                if not xmls:
                    (OUT_DIR / f"{name}.zip").write_bytes(body)
                    return False
                data = z.read(xmls[0])
                (OUT_DIR / f"{name}.xml").write_bytes(data)
                return True
        # XML / text
        (OUT_DIR / f"{name}.xml").write_bytes(body)
        return True
    except Exception:
        # Save raw for inspection
        (OUT_DIR / f"{name}.bin").write_bytes(body)
        return False

def pick_list_frame(page):
    """Return the frame that holds the dataset table."""
    # Heuristics: look for a frame whose URL contains portal-proxy or 'portal' list.
    for f in page.frames:
        u = (f.url or "").lower()
        if "portal-proxy" in u or "eco-portal" in u or "list" in u or "dataset" in u:
            # Avoid the tiny localization/json frames
            try:
                if f.locator("a:has(i.fa-file-code)").count() or f.locator("a[href*='zipexport']").count():
                    return f
            except Exception:
                pass
    # As a fallback, return main frame
    return page.main_frame

def scroll_all(frame):
    frame.evaluate("""
        async () => {
          const step = 600; let y = 0;
          while (y < document.body.scrollHeight) {
            window.scrollTo(0, y);
            await new Promise(r => setTimeout(r, 120));
            y += step;
          }
          window.scrollTo(0, document.body.scrollHeight);
        }
    """)

def collect_zipexport_links(frame) -> list[str]:
    scroll_all(frame)
    hrefs = set()
    # anchors with the FontAwesome code-file icon
    loc1 = frame.locator("a:has(i.fa-file-code)")
    try:
        for i in range(loc1.count()):
            h = loc1.nth(i).get_attribute("href")
            if h:
                hrefs.add(h)
    except Exception:
        pass
    # fallback: any anchor with 'zipexport'
    loc2 = frame.locator("a[href*='zipexport']")
    try:
        for i in range(loc2.count()):
            h = loc2.nth(i).get_attribute("href")
            if h:
                hrefs.add(h)
    except Exception:
        pass
    return sorted(hrefs)

def click_all_icons(frame, pause_ms:int=200):
    # If needed, you can trigger network by clicking the icons too
    loc = frame.locator("a:has(i.fa-file-code)")
    try:
        n = loc.count()
    except Exception:
        n = 0
    for i in range(n):
        try:
            loc.nth(i).click(button="left", delay=20, force=True, timeout=3000)
            frame.wait_for_timeout(pause_ms)
        except Exception:
            continue

def next_page(frame) -> bool:
    candidates = [
        "button[aria-label='Next']",
        "a[aria-label='Next']",
        "button[aria-label*='Go to next page' i], a[aria-label*='Go to next page' i]",
        "a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
        "a.p-paginator-next, button.p-paginator-next"
    ]
    for sel in candidates:
        try:
            b = frame.locator(sel).first
            if b.count() and b.is_enabled():
                b.click()
                frame.wait_for_load_state("networkidle")
                frame.wait_for_timeout(400)
                return True
        except Exception:
            continue
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Top-level ECO page that contains the datasets list")
    ap.add_argument("--term", default="photovoltaic", help="Optional search term typed in the list's search box")
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    if not pathlib.Path("auth.json").exists():
        raise SystemExit("auth.json not found. Run eco_login_capture.py first.")

    saved_ids = set()
    total_saved = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json", accept_downloads=True)
        page = ctx.new_page()

        # Response sniffer: any request/response containing 'zipexport'
        def on_response(resp):
            url = resp.url.lower()
            if "zipexport" not in url:
                return
            try:
                body = resp.body()
                ctype = resp.headers.get("content-type", "")
                eid = extract_uuid_from_url(resp.url) or None
                if eid and eid in saved_ids:
                    return
                ok = save_zip_or_xml(eid, ctype, body)
                if ok and eid:
                    saved_ids.add(eid)
            except Exception:
                pass

        page.on("response", on_response)

        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_load_state("networkidle")

        frame = pick_list_frame(page)

        # Optional search filter
        try:
            search = frame.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
            if search.count():
                search.fill("")
                search.type(args.term)
                search.press("Enter")
                frame.wait_for_timeout(800)
        except Exception:
            pass

        for pnum in range(1, args.max_pages+1):
            frame.wait_for_load_state("networkidle")
            scroll_all(frame)

            # Collect links (for ctx.request fallback) and also click icons to trigger responses
            links = collect_zipexport_links(frame)
            print(f"[page {pnum}] zipexport links detected: {len(links)}")

            # Click all icons to ensure network requests fire (sniffer will save)
            click_all_icons(frame, int(args.sleep*1000))

            # Fallback: if sniffer didn’t see anything, fetch via context.request with same cookies
            before = len(saved_ids)
            for href in links:
                if extract_uuid_from_url(href) in saved_ids:
                    continue
                try:
                    r = ctx.request.get(href, timeout=60_000)
                    if not r.ok:
                        continue
                    eid = extract_uuid_from_url(href) or None
                    ok = save_zip_or_xml(eid, r.headers.get("content-type",""), r.body())
                    if ok and eid:
                        saved_ids.add(eid)
                        time.sleep(args.sleep)
                except Exception:
                    continue
            gained = len(saved_ids) - before
            print(f"  saved this page: {gained}")

            # Next page or stop
            if not next_page(frame):
                print("[end] pagination finished.")
                break

        browser.close()
        total = len(saved_ids)
        print(f"[done] saved {total} XML files to {OUT_DIR}")

if __name__ == "__main__":
    main()
