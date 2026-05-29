# eco_pv_to_excel.py
# Windows 11 + VS Code. Filters PV in-page, downloads ILCD ZIP/XML, parses, and appends to Excel.

import argparse, io, pathlib, re, time, zipfile
from urllib.parse import urlparse, parse_qs, unquote
import pandas as pd
from lxml import etree
from playwright.sync_api import sync_playwright

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
XML_SHEET = "ILCD_XML"

OUT_XML_DIR = pathlib.Path("data/eco_xml")
OUT_XML_DIR.mkdir(parents=True, exist_ok=True)

PV_TERMS = [
    "photovoltaic", "pv module", "solar module", "pv panel", "photovoltaik",
    "photovoltaikmodul", "solarmodul", "photovoltaic module"
]

def is_pv_text(txt: str) -> bool:
    t = (txt or "").lower()
    return any(k in t for k in PV_TERMS)

def extract_uuid_from_url(u: str) -> str | None:
    # handles portal proxy redirect → .../processes/<uuid>/zipexport
    try:
        q = parse_qs(urlparse(u).query)
        ru = unquote(q.get("redirect_uri", [""])[0])
        m = re.search(r"/processes/([0-9a-f-]{8,})/", ru, re.I)
        if m: return m.group(1)
        m2 = re.search(r"/([0-9a-f-]{8,})/(?:zipexport|download)", u, re.I)
        return m2.group(1) if m2 else None
    except Exception:
        return None

def save_zip_or_xml(eid: str | None, ctype: str, body: bytes) -> pathlib.Path | None:
    """Save XML (or first XML in ZIP) → return file path, else None."""
    name = (eid or f"epd_{int(time.time()*1000)}").strip()
    ctype = (ctype or "").lower()
    try:
        if "zip" in ctype or body[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
                if not xmls:
                    (OUT_XML_DIR / f"{name}.zip").write_bytes(body)
                    return None
                data = z.read(xmls[0])
                p = OUT_XML_DIR / f"{name}.xml"
                p.write_bytes(data)
                return p
        # treat as XML/text
        p = OUT_XML_DIR / f"{name}.xml"
        p.write_bytes(body)
        return p
    except Exception:
        # dump raw for inspection
        (OUT_XML_DIR / f"{name}.bin").write_bytes(body)
        return None

def parse_ilcd_min(xml_txt: str) -> dict:
    """Robust, schema-light parser. Captures core fields and a few indicators if present."""
    rec = {
        "dataset_uuid": "",
        "source": "ECO Platform",
        "name": "",
        "version": "",
        "manufacturer": "",
        "programme_operator": "",
        "declared_unit": "",
        "GWP_total_A1A3_per_DU_kgCO2e": None
    }
    try:
        root = etree.fromstring(xml_txt.encode("utf-8"))
    except Exception:
        return rec

    ns = root.nsmap
    # UUID / version / name
    for xp in ["//*[local-name()='UUID'][1]"]:
        v = root.xpath(f"string({xp})", namespaces=ns)
        if v: rec["dataset_uuid"] = v.strip(); break
    rec["version"] = root.xpath("string(//*[local-name()='dataSetInformation']/*[local-name()='version'][1])", namespaces=ns).strip()
    # name candidates
    for xp in [
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='baseName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='shortName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='name'][1]",
    ]:
        val = root.xpath(f"string({xp})", namespaces=ns).strip()
        if val:
            rec["name"] = val
            break
    # manufacturer / owner
    for xp in [
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='shortName'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='contactInformation']/*[local-name()='name'][1]"
    ]:
        val = root.xpath(f"string({xp})", namespaces=ns).strip()
        if val:
            rec["manufacturer"] = val
            break

    # programme operator (best-effort)
    po = root.xpath("string(//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'programme')][1])", namespaces=ns).strip()
    rec["programme_operator"] = po

    # declared unit (try unitName on reference flow)
    du = root.xpath("string(//*[local-name()='referenceToReferenceFlow']/@unitName)", namespaces=ns).strip()
    if not du:
        du = root.xpath("string(//*[local-name()='quantitativeReference']//*[local-name()='unitGroup'][1]/@name)", namespaces=ns).strip()
    rec["declared_unit"] = du

    # GWP A1-A3 (very heuristic)
    # Search for the first numeric value near a node mentioning GWP and A1-A3
    # (works for many ECO ILCD exports; your normalizer can refine later).
    # 1) Try epd-specific tags
    gwp = root.xpath("string(//*[contains(translate(.,'GWP','gwp'),'gwp')][1]/following::*/number()[1])", namespaces=ns)
    try:
        rec["GWP_total_A1A3_per_DU_kgCO2e"] = float(gwp)
    except Exception:
        rec["GWP_total_A1A3_per_DU_kgCO2e"] = None

    return rec

def is_pv_rec(rec: dict, xml_txt: str) -> bool:
    if is_pv_text(rec.get("name","")): return True
    if is_pv_text(rec.get("manufacturer","")): return False
    return is_pv_text(xml_txt)

def ensure_workbook():
    try:
        pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        pd.DataFrame().to_excel(WB, sheet_name=RAW_SHEET, index=False)
    try:
        pd.read_excel(WB, sheet_name=XML_SHEET)
    except Exception:
        pd.DataFrame(columns=["dataset_uuid","href","xml"]).to_excel(WB, sheet_name=XML_SHEET, index=False)

def read_existing_uuids():
    try:
        df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
        return set((df["dataset_uuid"].dropna().astype(str).str.strip().tolist()))
    except Exception:
        return set()

def js_scroll_all(frame):
    frame.evaluate("""
        async () => {
          const step = 600; let y = 0;
          while (y < document.body.scrollHeight) {
            window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
            y += step;
          }
          window.scrollTo(0, document.body.scrollHeight);
        }
    """)

def pick_list_frame(page):
    # Prefer frame that has our anchors
    for f in page.frames:
        try:
            if f.locator("a:has(i.fa-file-code)").count() or f.locator("a[href*='zipexport']").count():
                return f
        except Exception:
            continue
    return page.main_frame

def collect_pv_links(frame) -> list[str]:
    js_scroll_all(frame)
    hrefs = set()
    # anchors with code icon
    loc = frame.locator("a:has(i.fa-file-code)")
    try:
        n = loc.count()
    except Exception:
        n = 0
    for i in range(n):
        h = loc.nth(i).get_attribute("href")
        if h: hrefs.add(h)
    # any anchor with zipexport
    loc2 = frame.locator("a[href*='zipexport']")
    try:
        m = loc2.count()
    except Exception:
        m = 0
    for i in range(m):
        h = loc2.nth(i).get_attribute("href")
        if h: hrefs.add(h)
    return sorted(hrefs)

def paginate_next(frame) -> bool:
    candidates = [
        "button[aria-label='Next']", "a[aria-label='Next']",
        "button[aria-label*='Go to next page' i], a[aria-label*='Go to next page' i]",
        "a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
        "a.p-paginator-next, button.p-paginator-next"
    ]
    for sel in candidates:
        b = frame.locator(sel).first
        try:
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
    ap.add_argument("--url", required=True, help="ECO portal page that shows the datasets table")
    ap.add_argument("--term", default="photovoltaic", help="term typed into the table search box")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    ensure_workbook()
    existing = read_existing_uuids()
    print(f"✓ Existing ILCD entries in Excel: {len(existing)}")

    new_xml_rows = []
    new_raw_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json")
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_load_state("networkidle")

        frame = pick_list_frame(page)

        # Filter to PV in-page
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
            js_scroll_all(frame)
            links = collect_pv_links(frame)
            print(f"[page {pnum}] candidate ILCD links: {len(links)}")

            for href in links:
                try:
                    uuid_guess = extract_uuid_from_url(href)
                    if uuid_guess and uuid_guess in existing:
                        continue
                    resp = ctx.request.get(href, timeout=60_000)
                    if not resp.ok:
                        print(f"  ! GET {resp.status}")
                        continue
                    path = save_zip_or_xml(uuid_guess, resp.headers.get("content-type",""), resp.body())
                    if not path:
                        continue
                    xml_txt = path.read_text(encoding="utf-8", errors="ignore")
                    rec = parse_ilcd_min(xml_txt)

                    # prefer XML's own UUID
                    uuid = rec.get("dataset_uuid") or uuid_guess or path.stem
                    if uuid in existing:
                        continue

                    # PV filter (double gate: table filter + content check)
                    if not is_pv_rec(rec, xml_txt):
                        continue

                    # record to Excel buffers
                    new_xml_rows.append({"dataset_uuid": uuid, "href": href, "xml": xml_txt})
                    rec["dataset_uuid"] = uuid
                    new_raw_rows.append(rec)
                    existing.add(uuid)

                    time.sleep(args.sleep)
                except Exception as e:
                    print(f"  ! failed: {e}")
                    continue

            if not paginate_next(frame):
                print("[end] reached last page.")
                break

        browser.close()

    # Append to Excel
    print(f"✓ New PV XML rows: {len(new_xml_rows)}; New RAW rows: {len(new_raw_rows)}")

    if new_xml_rows or new_raw_rows:
        try:
            df_xml_old = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
        except Exception:
            df_xml_old = pd.DataFrame(columns=["dataset_uuid","href","xml"])
        try:
            df_raw_old = pd.read_excel(WB, sheet_name=RAW_SHEET)
        except Exception:
            df_raw_old = pd.DataFrame()

        df_xml = pd.concat([df_xml_old, pd.DataFrame(new_xml_rows)], ignore_index=True)
        df_raw = pd.concat([df_raw_old, pd.DataFrame(new_raw_rows)], ignore_index=True)

        with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
            df_xml.to_excel(w, sheet_name=XML_SHEET, index=False)
            df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

        print(f"✓ Appended to {WB}: sheets '{XML_SHEET}' and '{RAW_SHEET}' updated.")
    else:
        print("No new PV items matched; expand search term or pages.")

if __name__ == "__main__":
    main()
