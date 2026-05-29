# eco_pv_environdec_direct.py
# Harvest ECO Portal search results, classify PV modules vs BOS, download Environdec zipexports,
# parse minimal ILCD, and append into Excel sheets:
#   - ILCD_XML (dataset_uuid, href, xml)
#   - INDICATORS_EN15804_A2_RAW (minimal indicators, manufacturer, DU...)
#   - BOS_CANDIDATES (non-module "Solar" hits like glass/cables/roof)
#
# Windows 11 + VS Code + PowerShell usage:
#   .\.venv\Scripts\Activate.ps1
#   pip install playwright requests pandas openpyxl lxml
#   playwright install
#   python .\eco_pv_environdec_direct.py --url "https://eco-portal.eco-platform.org/" --term "Solar" --max-pages 10

from __future__ import annotations
import argparse, io, time, zipfile, re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import requests
import pandas as pd
from lxml import etree
from playwright.sync_api import sync_playwright

# -------------------- Configuration --------------------

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
XML_SHEET = "ILCD_XML"
BOS_SHEET = "BOS_CANDIDATES"

OUT_XML_DIR = Path("data/eco_xml")
OUT_XML_DIR.mkdir(parents=True, exist_ok=True)

# PV module classification (name-based)
PV_PATTERNS = [
    r"\bphotovoltaic module\b", r"\bsolar module\b", r"\bpv module\b",
    r"\bbifacial\b.*\bmodule\b", r"\bmono(?:crystalline)?\b.*\bmodule\b",
    r"\bn-?\s*type\b.*\bmodule\b", r"\btopcon\b.*\bmodule\b", r"\bhjt\b.*\bmodule\b",
    r"\bPV16\b.*\bmodule\b", r"\bmodule\b.*\bphotovoltaic\b"
]
# BOS buckets for later BoP calculator (kept out of PV pipeline)
BOS_CATS = [
    (r"\bglass\b", "bos_glass"),
    (r"\bcable\b", "bos_cable"),
    (r"\broof|roofing|membrane|tile\b", "bos_roof"),
    (r"\bmounting|rack|rail|bracket|tracker\b", "bos_mount"),
]

UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Playwright/1.49",
    "Referer": "https://eco-portal.eco-platform.org/",
}

# -------------------- Helpers: classification --------------------

def is_pv_module(name: str) -> bool:
    n = (name or "").lower()
    return any(re.search(p, n) for p in PV_PATTERNS)

def bos_category(name: str) -> str | None:
    n = (name or "").lower()
    for pat, cat in BOS_CATS:
        if re.search(pat, n):
            return cat
    if "solar" in n:
        return "bos_other"
    return None

def dataset_uuid_from_href(href: str) -> str:
    m = re.search(r"/processes/([0-9a-f-]{8,})/", href, re.I)
    return m.group(1) if m else ""

# -------------------- Helpers: workbook --------------------

def ensure_workbook():
    if not Path(WB).exists():
        with pd.ExcelWriter(WB, engine="openpyxl", mode="w") as w:
            pd.DataFrame(columns=["dataset_uuid","href","xml"]).to_excel(w, sheet_name=XML_SHEET, index=False)
            pd.DataFrame().to_excel(w, sheet_name=RAW_SHEET, index=False)
    else:
        # make sure sheets exist
        try: pd.read_excel(WB, sheet_name=XML_SHEET)
        except Exception:
            with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="overlay") as w:
                pd.DataFrame(columns=["dataset_uuid","href","xml"]).to_excel(w, sheet_name=XML_SHEET, index=False)
        try: pd.read_excel(WB, sheet_name=RAW_SHEET)
        except Exception:
            with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="overlay") as w:
                pd.DataFrame().to_excel(w, sheet_name=RAW_SHEET, index=False)

def existing_uuids() -> set[str]:
    try:
        df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
        return set(df["dataset_uuid"].dropna().astype(str).str.strip().tolist())
    except Exception:
        return set()

# -------------------- Helpers: portal interaction --------------------

def fill_search(page, term: str):
    # robust search box detection
    sb = page.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
    if sb.count():
        sb.fill("")
        if term:
            sb.type(term, delay=10)
            sb.press("Enter")
        page.wait_for_timeout(800)

def collect_candidates(page):
    """Return list of dicts {href, name} for all visible 'download XML' icons on the page."""
    items = []
    icons = page.locator("a[target='_blank'] i.fa-file-code")
    cnt = icons.count()
    for i in range(cnt):
        icon = icons.nth(i)
        href = icon.evaluate("el => el.closest('a')?.href || ''")
        if not href:
            continue
        # name: first column text in same row
        name = icon.evaluate("""
            el => {
              const tr = el.closest('tr');
              if (tr) {
                const a = tr.querySelector('td:first-child a');
                if (a && a.textContent) return a.textContent.trim();
                const td = tr.querySelector('td:first-child');
                if (td && td.textContent) return td.textContent.trim();
              }
              return '';
            }
        """)
        items.append({"href": href, "name": name})
    return items

def paginate_next(page) -> bool:
    """PrimeNG paginator: numeric next; else try »/>> or 'Next' buttons."""
    try:
        pages = page.locator(".p-paginator .p-paginator-pages button.p-paginator-page")
        cnt = pages.count()
        if cnt:
            # pick the highlighted; default 0
            active_idx = 0
            for i in range(cnt):
                cls = (pages.nth(i).get_attribute("class") or "").lower()
                aria = (pages.nth(i).get_attribute("aria-current") or "").lower()
                if "p-highlight" in cls or aria == "page":
                    active_idx = i
                    break
            nxt = active_idx + 1
            if nxt < cnt:
                pages.nth(nxt).click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(400)
                return True
    except Exception:
        pass
    # Fallback arrows
    for sel in [
        "a.p-paginator-next, button.p-paginator-next",
        "button[aria-label='Next']", "a[aria-label='Next']",
        "a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
    ]:
        try:
            b = page.locator(sel).first
            if b.count() and b.is_enabled():
                b.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(400)
                return True
        except Exception:
            continue
    return False

# -------------------- Helpers: download + parse --------------------

def extract_redirect_and_uuid(href: str) -> tuple[str | None, str | None]:
    # ECO link form: https://portal-proxy.eco-platform.org?redirect_uri=ENCODED(…/processes/<uuid>/zipexport?... )
    try:
        q = parse_qs(urlparse(href).query)
        ru = unquote(q.get("redirect_uri", [""])[0])
        m = re.search(r"/processes/([0-9a-f-]{8,})/", ru, re.I)
        return ru, (m.group(1) if m else None)
    except Exception:
        return None, None

def download_environdec(ru: str) -> tuple[bytes | None, str]:
    try:
        r = requests.get(ru, headers=UA_HEADERS, timeout=90)
        if r.status_code != 200:
            return None, f"GET {r.status_code}"
        return r.content, r.headers.get("Content-Type", "")
    except Exception as e:
        return None, f"ERR {e}"

def save_zip_or_xml(eid: str | None, ctype: str, body: bytes) -> Path | None:
    """Save first process XML from the zip (or raw XML). Return .xml path or None."""
    name = (eid or f"epd_{int(time.time()*1000)}").strip()
    ctype = (ctype or "").lower()
    try:
        if body[:4] == b"PK\x03\x04" or "zip" in ctype:
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
                xmls.sort(key=lambda n: (0 if "process" in n.lower() else 1, len(n)))
                if not xmls:
                    (OUT_XML_DIR / f"{name}.zip").write_bytes(body)
                    return None
                data = z.read(xmls[0])
                p = OUT_XML_DIR / f"{name}.xml"
                p.write_bytes(data)
                return p
        # direct XML
        p = OUT_XML_DIR / f"{name}.xml"
        p.write_bytes(body)
        return p
    except Exception:
        (OUT_XML_DIR / f"{name}.bin").write_bytes(body)
        return None

def parse_ilcd_min(xml_txt: str) -> dict:
    """Namespace-agnostic, minimal ILCD parse."""
    rec = {
        "dataset_uuid": "",
        "source": "Environdec via ECO",
        "name": "",
        "version": "",
        "manufacturer": "",
        "declared_unit": "",
        "GWP_total_A1A3_per_DU_kgCO2e": None,
    }
    try:
        root = etree.fromstring(xml_txt.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    except Exception:
        return rec

    s = lambda xp: (root.xpath(f"string({xp})") or "").strip()

    rec["dataset_uuid"] = s("//*[local-name()='UUID'][1]")
    rec["version"]      = s("//*[local-name()='dataSetInformation']/*[local-name()='version'][1]")

    for xp in [
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='baseName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='shortName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='name'][1]",
        "(//*[local-name()='name'])[1]",
    ]:
        v = s(xp)
        if v:
            rec["name"] = v; break

    for xp in [
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='shortName'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='contactInformation']/*[local-name()='name'][1]",
    ]:
        v = s(xp)
        if v:
            rec["manufacturer"] = v; break

    du = s("//*[local-name()='referenceToReferenceFlow'][1]/@unitName")
    if not du:
        du = s("//*[local-name()='quantitativeReference']//*[local-name()='unitGroup'][1]/@name")
    rec["declared_unit"] = du

    # Light heuristic for A1–A3 GWP (works when present in process XML)
    try:
        val = root.xpath("string((//*[contains(translate(.,'GWP','gwp'),'gwp')])[1]/following::*/text()[normalize-space()][1])").strip()
        m = re.search(r"-?\d+(?:[.,]\d+)?", val)
        if m:
            rec["GWP_total_A1A3_per_DU_kgCO2e"] = float(m.group(0).replace(",", "."))
    except Exception:
        pass

    return rec

# -------------------- Main --------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="ECO list page")
    ap.add_argument("--term", default="photovoltaic", help="search text to type in the table filter")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    ensure_workbook()
    done = existing_uuids()
    print(f"✓ Existing ILCD entries in Excel: {len(done)}")

    xml_rows, raw_rows, bos_rows = [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json")  # reuse login if needed
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_load_state("networkidle")
        fill_search(page, args.term)

        for page_num in range(1, args.max_pages + 1):
            page.wait_for_load_state("networkidle")
            items = collect_candidates(page)
            print(f"[page {page_num}] candidate ILCD links: {len(items)}")

            for it in items:
                href, name = it["href"], it["name"]
                ru, guess_uuid = extract_redirect_and_uuid(href)
                if not ru:
                    continue
                if guess_uuid and guess_uuid in done:
                    continue

                # Classify by product name in the row
                if not is_pv_module(name):
                    cat = bos_category(name)
                    if cat:
                        bos_rows.append({
                            "dataset_uuid": dataset_uuid_from_href(href),
                            "name": name,
                            "category": cat,
                            "href": href
                        })
                    continue  # skip BOS in PV pipeline

                body, ctype = download_environdec(ru)
                if body is None:
                    continue

                path = save_zip_or_xml(guess_uuid, ctype, body)
                if not path:    # no XML found in archive
                    continue

                xml_txt = path.read_text(encoding="utf-8", errors="ignore")
                rec = parse_ilcd_min(xml_txt)
                uuid = rec.get("dataset_uuid") or guess_uuid or path.stem

                if uuid in done:
                    continue

                # Store PV rows
                xml_rows.append({"dataset_uuid": uuid, "href": ru, "xml": xml_txt})
                rec["dataset_uuid"] = uuid
                raw_rows.append(rec)
                done.add(uuid)
                time.sleep(args.sleep)

            if not paginate_next(page):
                print("[end] no more pages.")
                break

        browser.close()

    print(f"✓ New PV XML rows: {len(xml_rows)}; New RAW rows: {len(raw_rows)}")

    # Write sheets
    if xml_rows or raw_rows:
        try: df_xml_old = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
        except Exception: df_xml_old = pd.DataFrame(columns=["dataset_uuid","href","xml"])
        try: df_raw_old = pd.read_excel(WB, sheet_name=RAW_SHEET)
        except Exception: df_raw_old = pd.DataFrame()

        df_xml = pd.concat([df_xml_old, pd.DataFrame(xml_rows)], ignore_index=True)
        df_raw = pd.concat([df_raw_old, pd.DataFrame(raw_rows)], ignore_index=True)

        with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
            df_xml.to_excel(w, sheet_name=XML_SHEET, index=False)
            df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

        print(f"✓ Appended to {WB}: '{XML_SHEET}' and '{RAW_SHEET}' updated.")
    else:
        print("No new PV items matched; try a broader --term or increase --max-pages.")

    # BOS list (always safe to write; keeps BoP items out of PV pipeline)
    if bos_rows:
        try: bos_old = pd.read_excel(WB, sheet_name=BOS_SHEET, dtype=str)
        except Exception: bos_old = pd.DataFrame()
        bos_out = pd.concat([bos_old, pd.DataFrame(bos_rows)], ignore_index=True)
        if "dataset_uuid" in bos_out.columns:
            bos_out = bos_out.drop_duplicates(subset=["dataset_uuid"], keep="first")
        with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
            bos_out.to_excel(w, sheet_name=BOS_SHEET, index=False)
        print(f"✓ Wrote/updated {BOS_SHEET}: {len(bos_out)} rows")

if __name__ == "__main__":
    main()
