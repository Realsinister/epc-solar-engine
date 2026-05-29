# enrich_from_ilcd_v3.py
# Robust ILCD+EPD enrichment: manufacturer, declared_unit, module_power_Wp, module_area_m2,
# GWP_total_A1A3_per_DU_kgCO2e (handles "GWP"/"Climate change", A1–A3 combined or A1/A2/A3 split)

import re, pandas as pd
from lxml import etree
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"

VENDOR_PAT = re.compile(
    r"(?i)\b(astronergy|longi|trina|jinko|ja\s*solar|canadian\s*solar|maxeon|rec|q\.?\s*cells|hanwha|risen|boviet|znshine|talesun|first\s*solar|seraphim|solitek|clearline|viridian|maysun|vikram|adani|waaree)\b"
)

def _num(x):
    try: return float(str(x).replace(",", "."))
    except: return None

def _s(root, xp):
    try: return root.xpath(f"string({xp})").strip()
    except Exception: return ""

def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def parse_gwp_a1a3(txt: str):
    """Find GWP A1–A3 as single value, else sum A1+A2+A3 near GWP/Climate change keywords."""
    if not txt: return None
    t = _strip_ws(txt).replace("–", "-").replace("\u00A0", " ")
    # Combined A1-A3 near GWP/Climate change
    m = re.search(r"(?:gwp|climate\s*change)[^0-9a-z]{0,40}(?:a1\s*-\s*a3|a1a3|a1\s*to\s*a3|modules?\s*a1\s*-\s*a3)[^0-9]{0,30}(-?\d+(?:[.,]\d+)?)", t, re.I)
    if m:
        return _num(m.group(1))
    # Separate A1/A2/A3 near GWP
    vals = {}
    for mod in ("A1","A2","A3"):
        mm = re.search(r"(?:gwp|climate\s*change)[^0-9a-z]{0,40}"+mod+r"[^0-9]{0,20}(-?\d+(?:[.,]\d+)?)", t, re.I)
        if mm: vals[mod] = _num(mm.group(1))
    if any(v is not None for v in vals.values()):
        return sum(v for v in (vals.get("A1"), vals.get("A2"), vals.get("A3")) if v is not None)
    # Fallback: first number after “GWP … production stage”
    m = re.search(r"(?:gwp|climate\s*change)[^0-9]{0,40}(?:production\s*stage|manufacturing)[^0-9]{0,20}(-?\d+(?:[.,]\d+)?)", t, re.I)
    if m:
        return _num(m.group(1))
    return None

def parse_ilcd_record(xml_txt: str) -> dict:
    rec = {
        "dataset_uuid": "", "name": "", "version": "",
        "manufacturer": "", "declared_unit": "",
        "module_power_Wp": None, "module_area_m2": None,
        "GWP_total_A1A3_per_DU_kgCO2e": None
    }

    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xml_txt.encode("utf-8"), parser=parser)
    except Exception:
        # text-only heuristics (rare)
        txt = xml_txt
        return {**rec, **parse_text_fields("", txt)}

    txt = etree.tostring(root, encoding="unicode", with_tail=False) or ""
    # UUID / version / name
    rec["dataset_uuid"] = _s(root, "//*[local-name()='UUID'][1]")
    rec["version"]      = _s(root, "//*[local-name()='dataSetInformation']/*[local-name()='version'][1]")
    for xp in [
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='baseName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='shortName'][1]",
        "//*[local-name()='dataSetInformation']//*[local-name()='name']/*[local-name()='name'][1]",
    ]:
        v = _s(root, xp)
        if v: rec["name"] = v; break
    if not rec["name"]:
        rec["name"] = _s(root, "(//*[local-name()='name'])[1]")

    # Manufacturer (several ILCD/EPD patterns)
    for xp in [
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='shortName'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='adminInfo']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='contactInformation']/*[local-name()='name'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='owner']/*[local-name()='name'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='owner'][1]",
    ]:
        v = _s(root, xp)
        if v:
            rec["manufacturer"] = _strip_ws(v)
            break
    if not rec["manufacturer"]:
        m = VENDOR_PAT.search((rec["name"] + " " + txt)[:6000])
        if m: rec["manufacturer"] = m.group(1).upper()

    # Declared unit
    du = _s(root, "//*[local-name()='referenceToReferenceFlow'][1]/@unitName")
    if not du:
        du = _s(root, "//*[local-name()='quantitativeReference']//*[local-name()='unitGroup'][1]/@name")
    if not du:
        m = re.search(r"(?i)\b(declared\s+unit|reference\s+unit)\b.*?:?\s*([A-Za-z0-9²^/ .-]+)", txt)
        if m: du = _strip_ws(m.group(2))
    rec["declared_unit"] = du

    # Power (Wp) & Area (m²)
    p = None; A = None
    m_name = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", rec["name"], flags=re.I)
    if m_name:
        v = _num(m_name.group(1))
        if v and 200 <= v <= 900: p = v
    if p is None:
        m = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", txt, flags=re.I)
        if m:
            v = _num(m.group(1))
            if v and 150 <= v <= 900: p = v
    mA = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b", txt, flags=re.I)
    if mA:
        v = _num(mA.group(1))
        if v and 0.5 <= v <= 3.5: A = round(v, 4)
    else:
        dims = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})\s*mm", txt, flags=re.I)
        if dims:
            try:
                L = float(dims.group(1)); W = float(dims.group(2))
                area = (L*W)/1_000_000.0
                if 0.5 <= area <= 3.5: A = round(area, 4)
            except: pass
    if p is not None and p < 50: p = None  # kill artifacts (1.0 etc.)
    rec["module_power_Wp"] = p
    rec["module_area_m2"]  = A

    # GWP A1–A3
    rec["GWP_total_A1A3_per_DU_kgCO2e"] = parse_gwp_a1a3(txt)

    return rec

def parse_text_fields(name: str, txt: str) -> dict:
    out = {"manufacturer":"", "declared_unit":"", "module_power_Wp":None, "module_area_m2":None, "GWP_total_A1A3_per_DU_kgCO2e":None}
    if not name:
        m = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", txt, flags=re.I)
        if m:
            v = _num(m.group(1))
            if v and 150 <= v <= 900: out["module_power_Wp"] = v
    mA = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b", txt, flags=re.I)
    if mA:
        v = _num(mA.group(1))
        if v and 0.5 <= v <= 3.5: out["module_area_m2"] = round(v, 4)
    m = VENDOR_PAT.search((name + " " + txt)[:6000]);  out["manufacturer"] = (m.group(1).upper() if m else "")
    out["GWP_total_A1A3_per_DU_kgCO2e"] = parse_gwp_a1a3(txt)
    return out

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")

    try:
        df_xml = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
    except Exception:
        raise SystemExit(f"Sheet '{XML_SHEET}' not found in {WB}.")

    try:
        df_raw = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df_raw = pd.DataFrame()

    updates = []
    for _, row in df_xml.iterrows():
        uuid = str(row.get("dataset_uuid") or "").strip()
        xml  = row.get("xml") or ""
        if not uuid or not xml: 
            continue
        rec = parse_ilcd_record(xml)
        rec["dataset_uuid"] = uuid
        updates.append(rec)

    df_up = pd.DataFrame(updates)

    if df_raw.empty:
        merged = df_up
    else:
        merged = df_raw.merge(df_up, on="dataset_uuid", how="outer", suffixes=("", "_new"))
        for c in ["name","version","manufacturer","declared_unit","module_power_Wp","module_area_m2","GWP_total_A1A3_per_DU_kgCO2e"]:
            new = f"{c}_new"
            if new in merged.columns:
                # fill only if missing/NaN/empty
                merged[c] = merged[c].where(merged[c].notna() & (merged[c]!=""), merged[new])
        # drop helper cols
        merged = merged[[col for col in merged.columns if not col.endswith("_new")]]

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        merged.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print("✓ Enriched RAW from ILCD_XML (v3). Now run normalize_from_raw.py")

if __name__ == "__main__":
    main()
