# eco_pv_to_excel_click.py
# Clicks the per-row </> (fa-file-code) link, captures download or popup (portal-proxy zipexport),
# saves ILCD XML, parses minimal fields, appends ILCD_XML + INDICATORS_EN15804_A2_RAW in your workbook.

import argparse, io, pathlib, re, time, zipfile
from urllib.parse import urlparse, parse_qs, unquote
import pandas as pd
from lxml import etree
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
XML_SHEET = "ILCD_XML"
OUT_XML_DIR = pathlib.Path("data/eco_xml"); OUT_XML_DIR.mkdir(parents=True, exist_ok=True)

PV_TERMS = [
    "photovoltaic", "pv module", "solar module", "pv panel", "module pv",
    "photovoltaik", "photovoltaikmodul", "solarmodul"
]

def is_pv_text(t: str) -> bool:
    t = (t or "").lower()
    return any(k in t for k in PV_TERMS)

def extract_uuid_from_url(u: str) -> str | None:
    # Matches Environdec-style redirect: ...?redirect_uri=.../datastocks/<ds>/processes/<uuid>/zipexport?version=...
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
    """Save XML (or first XML in ZIP) → return path, else None."""
    name = (eid or f"epd_{int(time.time()*1000)}").strip()
    ctype = (ctype or "").lower()
    try:
        if "zip" in ctype or body[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                # Prefer likely ILCD process file
                cands = [n for n in z.namelist() if n.lower().endswith(".xml")]
                # Heuristic: prefer files in processes/ or named process.xml
                prio = sorted(cands, key=lambda n: (0 if "process" in n.lower() else 1, len(n)))
                target = prio[0] if prio else None
                if not target:
                    (OUT_XML_DIR / f"{name}.zip").write_bytes(body); return None
                data = z.read(target)
                p = OUT_XML_DIR / f"{name}.xml"; p.write_bytes(data); return p
        p = OUT_XML_DIR / f"{name}.xml"; p.write_bytes(body); return p
    except Exception:
        (OUT_XML_DIR / f"{name}.bin").write_bytes(body); return None

def parse_ilcd_min(xml_txt: str) -> dict:
    """Schema-light ILCD parse with namespace-agnostic XPath (no namespaces=...)."""
    rec = {
        "dataset_uuid": "",
        "source": "Environdec via ECO",
        "name": "",
        "version": "",
        "manufacturer": "",
        "programme_operator": "",
        "declared_unit": "",
        "GWP_total_A1A3_per_DU_kgCO2e": None,
    }
    try:
        parser = etree.XMLParser(recover=True, huge_tree=True)
        root = etree.fromstring(xml_txt.encode("utf-8"), parser=parser)
    except Exception:
        return rec

    # Helper: evaluate XPath without namespaces
    def s(xp: str) -> str:
        try:
            return root.xpath(f"string({xp})").strip()
        except Exception:
            return ""

    # Core fields (namespace-agnostic)
    rec["dataset_uuid"] = s("//*[local-name()='UUID'][1]")
    rec["version"] = s("//*[local-name()='dataSetInformation']/*[local-name()='version'][1]")

    for xp in [
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='baseName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='shortName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='name'][1]",
    ]:
        v = s(xp)
        if v:
            rec["name"] = v
            break

    for xp in [
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='shortName'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='contactInformation']/*[local-name()='name'][1]",
    ]:
        v = s(xp)
        if v:
            rec["manufacturer"] = v
            break

    rec["programme_operator"] = s("(//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'programme')])[1]")

    du = s("//*[local-name()='referenceToReferenceFlow'][1]/@unitName")
    if not du:
        du = s("//*[local-name()='quantitativeReference']//*[local-name()='unitGroup'][1]/@name")
    rec["declared_unit"] = du

    # Heuristic GWP A1–A3 grab: first numeric after a node mentioning 'GWP'
    try:
        # Find the first text node following any element whose text mentions 'gwp'
        val = root.xpath("string((//*[contains(translate(.,'GWP','gwp'),'gwp')])[1]/following::*/text()[normalize-space()][1])").strip()
        # Extract first number from that text
        import re as _re
        m = _re.search(r"-?\d+(?:[\.,]\d+)?", val)
        if m:
            rec["GWP_total_A1A3_per_DU_kgCO2e"] = float(m.group(0).replace(",", "."))
    except Exception:
        pass

    return rec


def is_pv(rec: dict, xml_txt: str) -> bool:
    if is_pv_text(rec.get("name", "")): return True
    return is_pv_text(xml_txt)

def ensure_workbook():
    try: pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception: pd.DataFrame().to_excel(WB, sheet_name=RAW_SHEET, index=False)
    try: pd.read_excel(WB, sheet_name=XML_SHEET)
    except Exception: pd.DataFrame(columns=["dataset_uuid","href","xml"]).to_excel(WB, sheet_name=XML_SHEET, index=False)

def existing_uuids() -> set:
    try:
        df = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
        return set(df["dataset_uuid"].dropna().astype(str).str.strip().tolist())
    except Exception:
        return set()

def pick_list_frame(page):
    # Find the frame that contains the bottom table with our anchors
    for f in page.frames:
        try:
            if f.locator("a:has(i.fa-file-code)").count() or f.locator("a[href*='zipexport']").count():
                return f
        except Exception:
            continue
    return page.main_frame

def scroll_all(frame):
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

def collect_anchors(frame):
    # Our exact case: <a ... href="...portal-proxy...zipexport..."><i class="fa-file-code"></i></a>
    scroll_all(frame)
    anchors = frame.locator("a:has(i.fa-file-code)")
    items = []
    try: n = anchors.count()
    except Exception: n = 0
    for i in range(n):
        a = anchors.nth(i)
        href = a.get_attribute("href")
        items.append((a, href))
    # Deduplicate by href
    seen, out = set(), []
    for a, h in items:
        key = h or f"elem-{id(a)}"
        if key in seen: continue
        seen.add(key); out.append((a, h))
    return out

def click_and_capture(frame, anchor, href: str, pause_ms:int=250):
    # 1) Native download path
    try:
        with frame.expect_download(timeout=8000) as dlev:
            anchor.scroll_into_view_if_needed()
            anchor.click(force=True, timeout=8000)
        dl = dlev.value
        # Save temp then read bytes
        tmp_path = OUT_XML_DIR / f"tmp_{int(time.time()*1000)}"
        dl.save_as(str(tmp_path))
        body = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        eid = extract_uuid_from_url(dl.url) or extract_uuid_from_url(href or "") or None
        frame.wait_for_timeout(pause_ms)
        return (eid, body, dl.url)
    except PWTimeout:
        pass
    except Exception:
        pass

    # 2) New tab response path
    try:
        with frame.expect_popup(timeout=8000) as pop:
            anchor.scroll_into_view_if_needed()
            anchor.click(force=True, timeout=8000)
        tab = pop.value
        tab.wait_for_load_state("domcontentloaded")
        resp = tab.wait_for_event("response", predicate=lambda r: "zipexport" in r.url.lower(), timeout=10000)
        body = resp.body()
        url = resp.url
        eid = extract_uuid_from_url(url) or extract_uuid_from_url(href or "") or None
        tab.close()
        frame.wait_for_timeout(pause_ms)
        return (eid, body, url)
    except PWTimeout:
        return (None, None, href or "")
    except Exception:
        return (None, None, href or "")

def paginate_next(frame) -> bool:
    # Common variants; we’ll add your exact one if needed
    for sel in [
        "button[aria-label='Next']", "a[aria-label='Next']",
        "button[aria-label*='Go to next page' i], a[aria-label*='Go to next page' i]",
        "a:has-text('»'), button:has-text('»'), a:has-text('>>'), button:has-text('>>')",
        "a.p-paginator-next, button.p-paginator-next"
    ]:
        try:
            b = frame.locator(sel).first
            if b.count() and b.is_enabled():
                b.click(); frame.wait_for_load_state("networkidle"); frame.wait_for_timeout(400)
                return True
        except Exception:
            continue
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="ECO page that shows the datasets list")
    ap.add_argument("--term", default="photovoltaic", help="typed into the table search box")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    ensure_workbook()
    done = existing_uuids()
    print(f"✓ Existing ILCD entries in Excel: {len(done)}")

    xml_rows, raw_rows = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth.json", accept_downloads=True)
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_load_state("networkidle")
        frame = pick_list_frame(page)

        # In-table PV filter
        try:
            sb = frame.locator("input[placeholder*='search' i], input[type='search'], input[aria-label*='search' i]").first
            if sb.count():
                sb.fill(""); sb.type(args.term); sb.press("Enter"); frame.wait_for_timeout(800)
        except Exception:
            pass

        for pnum in range(1, args.max_pages+1):
            frame.wait_for_load_state("networkidle")
            anchors = collect_anchors(frame)
            print(f"[page {pnum}] ILCD anchors: {len(anchors)}")

            for anchor, href in anchors:
                # Skip if we already have this UUID
                guess = extract_uuid_from_url(href or "")
                if guess and guess in done:
                    continue

                eid, body, final_url = click_and_capture(frame, anchor, href, int(args.sleep*1000))
                if body is None:
                    continue

                path = save_zip_or_xml(eid or guess, "", body)
                if not path:
                    continue

                xml_txt = path.read_text(encoding="utf-8", errors="ignore")
                rec = parse_ilcd_min(xml_txt)
                uuid = rec.get("dataset_uuid") or (eid or guess) or path.stem

                # Strong PV gate
                if not is_pv(rec, xml_txt):
                    continue
                if uuid in done:
                    continue

                xml_rows.append({"dataset_uuid": uuid, "href": final_url or (href or ""), "xml": xml_txt})
                rec["dataset_uuid"] = uuid
                raw_rows.append(rec)
                done.add(uuid)

            if not paginate_next(frame):
                print("[end] reached last page."); break

        browser.close()

    print(f"✓ New PV XML rows: {len(xml_rows)}; New RAW rows: {len(raw_rows)}")

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
        print("No new PV items matched; try --term \"solar module\" or increase --max-pages.")

if __name__ == "__main__":
    main()
