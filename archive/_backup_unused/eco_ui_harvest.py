# eco_ui_harvest.py (safe)
import re, argparse, pathlib
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

OUT_DIR = pathlib.Path("data/eco_xml")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- PASTE YOUR LOCATOR BELOW AS A *LAMBDA* ----
# Example: lambda page: page.get_by_role("link", name="ILCD")
USER_LOCATOR = lambda page: page.locator(".export-dl-icons > a").first.click()  
# <-- replace None with:  lambda page: page.get_by_role("link", name="ILCD")

def default_locators():
    locs = []
    if USER_LOCATOR is not None:
        locs.append(USER_LOCATOR)  # must be: lambda page: <returns a Locator>
    # generic fallbacks
    locs += [
        lambda page: page.locator("a[href*='ilcd' i], a[href$='.xml' i], a[download]"),
        lambda page: page.locator("a[title*='ilcd' i], a[title*='xml' i]"),
        lambda page: page.locator("button[aria-label*='ILCD' i], button:has-text('ILCD')"),
        lambda page: page.locator("button[aria-label*='XML' i],  button:has-text('XML')"),
        lambda page: page.locator("[data-testid*='ilcd' i], [data-testid*='xml' i]"),
    ]
    return locs

def guess_id(url:str, filename:str)->str:
    from urllib.parse import urlparse, parse_qs
    q = parse_qs(urlparse(url).query)
    for k in ("id","uuid","code"):
        if k in q and q[k]: return q[k][0]
    m = re.search(r"/([0-9a-f-]{8,})[\./]", url, flags=re.I)
    if m: return m.group(1)
    m = re.search(r"([0-9a-f-]{8,})", filename, flags=re.I)
    return m.group(1) if m else filename

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="ECO list page URL")
    ap.add_argument("--term", default="photovoltaic")
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    if not pathlib.Path("auth.json").exists():
        raise SystemExit("auth.json not found. Run eco_login_capture.py first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json")
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)

        # Optional: filter table
        search = page.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
        if search.count():
            search.fill("")
            search.type(args.term)
            search.press("Enter")
            page.wait_for_timeout(700)

        total = 0
        for pnum in range(1, args.max_pages+1):
            found = 0
            for maker in default_locators():
                if not callable(maker):
                    continue
                cand = None
                try:
                    cand = maker(page)
                except Exception:
                    continue
                # Guard: skip anything that isn't a Locator
                if cand is None or not hasattr(cand, "count"):
                    continue
                try:
                    count = cand.count()
                except Exception:
                    continue
                if count == 0:
                    continue

                for i in range(count):
                    el = cand.nth(i)
                    if not el.is_visible():
                        continue
                    try:
                        with page.expect_download() as dl_info:
                            el.click(force=True, timeout=10000)
                        dl = dl_info.value
                        url = dl.url
                        fname = dl.suggested_filename or "epd.xml"
                        eid = guess_id(url, fname)
                        dl.save_as(str(OUT_DIR / f"{eid}.xml"))
                        total += 1
                        found += 1
                        if args.sleep: page.wait_for_timeout(int(args.sleep*1000))
                    except Exception:
                        continue
                if found:
                    break  # this locator worked on this page

            if not found:
                # Try details page fallback (common pattern)
                row_link = page.locator("a[href*='detail' i], a[title*='detail' i], a:has-text('Detail'), a:has-text('Details')").first
                if row_link.count():
                    with page.expect_popup() as pop:
                        row_link.click()
                    detail = pop.value
                    detail.wait_for_load_state("domcontentloaded")
                    got = False
                    for maker in default_locators():
                        try:
                            cand2 = maker(detail)
                        except Exception:
                            continue
                        if cand2 is None or not hasattr(cand2, "count"):
                            continue
                        if cand2.count():
                            el = cand2.first
                            try:
                                with detail.expect_download() as dl_info:
                                    el.click(force=True, timeout=10000)
                                dl = dl_info.value
                                url = dl.url
                                fname = dl.suggested_filename or "epd.xml"
                                eid = guess_id(url, fname)
                                dl.save_as(str(OUT_DIR / f"{eid}.xml"))
                                total += 1
                                got = True
                                break
                            except Exception:
                                pass
                    detail.close()
                    if not got and pnum == 1 and USER_LOCATOR is None:
                        raise SystemExit("No ILCD/XML found. Use `python -m playwright codegen <URL>` and paste the *lambda* locator into USER_LOCATOR.")
                else:
                    if pnum == 1 and USER_LOCATOR is None:
                        raise SystemExit("No ILCD/XML found. Use codegen once and paste the *lambda* locator into USER_LOCATOR.")

            # Next page
            next_btn = page.locator(
                "button[aria-label='Next'], a[aria-label='Next'], "
                "button[aria-label='Go to next page'], a[aria-label='Go to next page'], "
                "button:has-text('Next'), a:has-text('Next')"
            ).first
            if next_btn.count() and next_btn.is_enabled():
                next_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(400)
            else:
                break

        print(f"[done] downloaded {total} ILCD/XML files → {OUT_DIR}")
        browser.close()

if __name__ == "__main__":
    main()