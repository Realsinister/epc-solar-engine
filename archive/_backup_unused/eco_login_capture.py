# eco_login_capture.py
from playwright.sync_api import sync_playwright
import argparse
from urllib.parse import urlparse

def validate_url(u: str) -> str:
    p = urlparse(u)
    if not (p.scheme in ("http", "https") and p.netloc):
        raise SystemExit(f"Invalid URL: {u!r}. https://eco-portal.eco-platform.org/")
    return u

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="https://eco-portal.eco-platform.org/)")
    args = ap.parse_args()
    url = validate_url(args.url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        # Use 'domcontentloaded' to avoid waiting forever on live dashboards
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        print("\n1) Log in normally in the opened window.")
        print("2) Wait until the dataset table is visible and can scroll/page.")
        input("3) When ready, return here and press ENTER to save your session... ")
        ctx.storage_state(path="auth.json")
        print("Saved login state to auth.json")
        browser.close()

if __name__ == "__main__":
    main()