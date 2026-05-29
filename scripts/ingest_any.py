# ingest_any.py  — Windows-first ingestion from ILCD XML/ZIP and manufacturer PDFs
# Usage:
#   python .\ingest_any.py --incoming data\incoming --wb EPD_Hub_V3_PV_starter_enriched.xlsx
#   python .\ingest_any.py --incoming data\incoming --watch   (optional live watcher)

import argparse, hashlib, io, pathlib, re, time, zipfile, threading
from pathlib import Path
import pandas as pd
from lxml import etree
import fitz  # PyMuPDF
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAVE_WATCHDOG = True
except Exception:
    HAVE_WATCHDOG = False

WB_DEFAULT = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
XML_SHEET = "ILCD_XML"
NORM_SCRIPT = "normalize_from_raw.py"

PV_TERMS = ["photovoltaic","pv module","solar module","pv panel","photovoltaik","photovoltaikmodul","solarmodul"]

def is_pv_text(t: str) -> bool:
    if not isinstance(t, str): return False
    s = t.lower()
    return any(k in s for k in PV_TERMS)

def file_sha1(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_workbook(wb: Path):
    try:
        pd.read_excel(wb, sheet_name=RAW_SHEET)
    except Exception:
        pd.DataFrame().to_excel(wb, sheet_name=RAW_SHEET, index=False)
    try:
        pd.read_excel(wb, sheet_name=XML_SHEET, dtype=str)
    except Exception:
        pd.DataFrame(columns=["dataset_uuid","href","xml","source"]).to_excel(wb, sheet_name=XML_SHEET, index=False)

def read_existing_uuids(wb: Path) -> set[str]:
    try:
        df_xml = pd.read_excel(wb, sheet_name=XML_SHEET, dtype=str)
        return set(df_xml["dataset_uuid"].dropna().astype(str).str.strip().tolist())
    except Exception:
        return set()

# ----------- ILCD parsing (namespace-agnostic) -----------
def parse_ilcd_min(xml_txt: str, source_tag: str) -> dict:
    rec = {
        "dataset_uuid": "",
        "source": source_tag,
        "name": "",
        "version": "",
        "manufacturer": "",
        "programme_operator": "",
        "declared_unit": "",
        "GWP_total_A1A3_per_DU_kgCO2e": None
    }
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xml_txt.encode("utf-8"), parser=parser)
    except Exception:
        return rec

    def s(xp: str) -> str:
        try:
            return root.xpath(f"string({xp})").strip()
        except Exception:
            return ""

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

    # Heuristic for GWP
    try:
        val = root.xpath("string((//*[contains(translate(.,'GWP','gwp'),'gwp')])[1]/following::*/text()[normalize-space()][1])").strip()
        m = re.search(r"-?\d+(?:[\.,]\d+)?", val)
        if m:
            rec["GWP_total_A1A3_per_DU_kgCO2e"] = float(m.group(0).replace(",", "."))
    except Exception:
        pass

    return rec

def extract_xml_from_zip(blob: bytes) -> str | None:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
        xmls.sort(key=lambda n: (0 if "process" in n.lower() else 1, len(n)))
        if not xmls:
            return None
        return z.read(xmls[0]).decode("utf-8", errors="ignore")

# ----------- PDF parsing (specs only) -----------
def extract_text_from_pdf(p: Path) -> str:
    try:
        doc = fitz.open(p)
        text = []
        for page in doc:
            text.append(page.get_text("text"))
        return "\n".join(text)
    except Exception:
        return ""

def pdf_specs(text: str) -> dict:
    # Robust heuristics: Wp, area via m² or dimensions
    def _num(x):
        try: return float(str(x).replace(",", "."))
        except: return None

    rec = {
        "module_power_Wp": None,
        "module_area_m2": None,
        "manufacturer": None,
        "name": None
    }
    # Manufacturer guess from header/footer lines
    mname = re.search(r"(?i)\b(trina|longi|jinko|ja solar|canadian solar|hanwha|q\.?cells|risen|talesun|znshine|astronergy|boviet|first solar|rec)\b", text)
    if mname: rec["manufacturer"] = mname.group(0).strip().title()

    # Model name-like tokens (very heuristic)
    model = re.search(r"(?i)\b([A-Z]{1,3}[A-Z0-9\-]{4,})\b.*(module|panel)", text)
    if model: rec["name"] = model.group(1).strip()

    # Power
    kwp = [ _num(x) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:kWp|kW-?p|kWpeak)\b", text, flags=re.I) ]
    wp  = [ _num(x) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:Wp|W-?p)\b", text, flags=re.I) ]
    kwp = [ v*1000 for v in kwp if v is not None ]
    cand = [v for v in (wp + kwp) if v is not None]
    pv = [v for v in cand if 200 <= v <= 800]
    rec["module_power_Wp"] = (pv or cand or [None])[0]

    # Area (m²)
    m2 = [ _num(x) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b", text, flags=re.I) ]
    am = [v for v in m2 if 0.5 <= v <= 3.5]
    if am:
        typical = [v for v in am if 1.3 <= v <= 2.6]
        rec["module_area_m2"] = (typical or am)[0]
    else:
        dims = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})\s*mm", text, flags=re.I)
        if dims:
            try:
                L = float(dims.group(1)); W = float(dims.group(2))
                rec["module_area_m2"] = round((L*W)/1_000_000, 4)
            except: pass
    return rec

# ----------- Excel I/O -----------
def append_excel(wb: Path, xml_rows: list[dict], raw_rows: list[dict]):
    try:
        df_xml_old = pd.read_excel(wb, sheet_name=XML_SHEET, dtype=str)
    except Exception:
        df_xml_old = pd.DataFrame(columns=["dataset_uuid","href","xml","source"])
    try:
        df_raw_old = pd.read_excel(wb, sheet_name=RAW_SHEET)
    except Exception:
        df_raw_old = pd.DataFrame()

    df_xml = pd.concat([df_xml_old, pd.DataFrame(xml_rows)], ignore_index=True)
    df_raw = pd.concat([df_raw_old, pd.DataFrame(raw_rows)], ignore_index=True)

    # Deduplicate by dataset_uuid where available
    if "dataset_uuid" in df_xml.columns:
        df_xml = df_xml.drop_duplicates(subset=["dataset_uuid"], keep="first")
    if "dataset_uuid" in df_raw.columns:
        df_raw = df_raw.drop_duplicates(subset=["dataset_uuid"], keep="first")

    with pd.ExcelWriter(wb, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df_xml.to_excel(w, sheet_name=XML_SHEET, index=False)
        df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

# ----------- Main ingestion -----------
def ingest_file(p: Path, wb: Path):
    ensure_workbook(wb)
    xml_rows, raw_rows = [], []

    if p.suffix.lower() == ".xml":
        xml_txt = p.read_text(encoding="utf-8", errors="ignore")
        rec = parse_ilcd_min(xml_txt, "Manual ILCD")
        if not rec["dataset_uuid"]:
            # fallback: hash as pseudo-ID
            rec["dataset_uuid"] = file_sha1(p)
        # PV gate (try to avoid junk)
        if not (is_pv_text(rec["name"]) or is_pv_text(xml_txt)):
            return 0, 0
        xml_rows.append({"dataset_uuid": rec["dataset_uuid"], "href": str(p), "xml": xml_txt, "source": "Manual ILCD"})
        raw_rows.append(rec)
        append_excel(wb, xml_rows, raw_rows)
        return 1, 1

    if p.suffix.lower() == ".zip":
        try:
            xml_txt = extract_xml_from_zip(p.read_bytes())
        except Exception:
            xml_txt = None
        if not xml_txt:
            return 0, 0
        rec = parse_ilcd_min(xml_txt, "Manual ILCD (ZIP)")
        if not rec["dataset_uuid"]:
            rec["dataset_uuid"] = file_sha1(p)
        if not (is_pv_text(rec["name"]) or is_pv_text(xml_txt)):
            return 0, 0
        xml_rows.append({"dataset_uuid": rec["dataset_uuid"], "href": str(p), "xml": xml_txt, "source": "Manual ILCD (ZIP)"})
        raw_rows.append(rec)
        append_excel(wb, xml_rows, raw_rows)
        return 1, 1

    if p.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(p)
        specs = pdf_specs(text)
        # Build a minimal RAW row; no ILCD XML here
        uuid = file_sha1(p)
        name = specs["name"] or p.stem
        manuf = specs["manufacturer"] or ""
        if not (is_pv_text(name) or "module" in name.lower() or is_pv_text(text)):
            # still allow PDFs because name detection is rough
            pass
        raw = {
            "dataset_uuid": uuid,
            "source": "Manufacturer PDF",
            "name": name,
            "version": "",
            "manufacturer": manuf,
            "programme_operator": "",
            "declared_unit": "piece",
            "GWP_total_A1A3_per_DU_kgCO2e": None,
            "module_power_Wp": specs["module_power_Wp"],
            "module_area_m2": specs["module_area_m2"],
            "pdf_path": str(p)
        }
        append_excel(wb, [], [raw])
        return 0, 1

    return 0, 0

def bulk_ingest(incoming: Path, wb: Path):
    xml_ct = raw_ct = 0
    for ext in ("*.xml","*.zip","*.pdf"):
        for p in incoming.glob(ext):
            a,b = ingest_file(p, wb)
            xml_ct += a; raw_ct += b
    print(f"✓ Ingested: {xml_ct} ILCDs, {raw_ct} RAW rows")

# Optional: watch folder for new files
class _Handler(FileSystemEventHandler):
    def __init__(self, incoming: Path, wb: Path):
        self.incoming=incoming; self.wb=wb
    def on_created(self, event):
        if event.is_directory: return
        p = Path(event.src_path)
        if p.suffix.lower() in (".xml",".zip",".pdf"):
            # small delay to allow write completion
            time.sleep(0.5)
            try:
                a,b = ingest_file(p, self.wb)
                print(f"[watch] {p.name}: +{a} ILCD, +{b} RAW")
            except Exception as e:
                print(f"[watch] {p.name}: ERROR {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming", default="data\\incoming")
    ap.add_argument("--wb", default=WB_DEFAULT)
    ap.add_argument("--watch", action="store_true")
    args = ap.parse_args()

    incoming = Path(args.incoming); incoming.mkdir(parents=True, exist_ok=True)
    wb = Path(args.wb)
    ensure_workbook(wb)

    bulk_ingest(incoming, wb)

    if args.watch:
        if not HAVE_WATCHDOG:
            print("watchdog not installed; run: pip install watchdog")
            return
        obs = Observer()
        obs.schedule(_Handler(incoming, wb), str(incoming), recursive=False)
        obs.start()
        print(f"[watch] Monitoring {incoming} for .pdf/.xml/.zip (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            obs.stop()
        obs.join()

if __name__ == "__main__":
    main()
