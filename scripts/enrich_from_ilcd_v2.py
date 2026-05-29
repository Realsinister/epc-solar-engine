# enrich_from_ilcd_v2.py
# Re-parse ILCD_XML with namespace-agnostic XPath + text heuristics to fill:
# manufacturer, declared_unit, module_power_Wp, module_area_m2, GWP_total_A1A3_per_DU_kgCO2e
# Then merge into INDICATORS_EN15804_A2_RAW (update only missing/empty fields).

import re, math
import pandas as pd
from lxml import etree
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"

# Known vendors (helps manufacturer fallback from name/text)
VENDOR_PAT = re.compile(r"(?i)\b(astronergy|longi|longi|trinasolar|trina|jinko|ja\s*solar|canadian\s*solar|maxeon|rec|q\.?\s*cells|hanwha|risen|boviet|znshine|talesun|first\s*solar|seraphim|jnl|bisu|sunpower|win\s*win|clearline|viridian|solitek|maysun|vikram|bhel|waaree|adani)\b")

def _num(s):
    try: return float(str(s).replace(",", "."))
    except: return None

def _s(root, xp):
    try: return root.xpath(f"string({xp})").strip()
    except: return ""

def parse_ilcd_record(xml_txt: str) -> dict:
    """Return dict with enriched fields."""
    rec = {
        "dataset_uuid": "", "name": "", "version": "",
        "manufacturer": "", "declared_unit": "",
        "module_power_Wp": None, "module_area_m2": None,
        "GWP_total_A1A3_per_DU_kgCO2e": None
    }

    # Build an element tree and an all-text string for regex passes
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xml_txt.encode("utf-8"), parser=parser)
    except Exception:
        # As a last resort, regex on plain text only
        txt = xml_txt
        rec.update(extract_from_text(txt))
        return rec

    txt = etree.tostring(root, encoding="unicode", with_tail=False) or ""

    # --- UUID, version, name (prefer structured)
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
        # fallback to any <name> near top
        rec["name"] = _s(root, "(//*[local-name()='name'])[1]")

    # --- Manufacturer (several ILCD variants)
    for xp in [
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='shortName'][1]",
        "//*[local-name()='publicationAndOwnership']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='contactInformation']/*[local-name()='name'][1]",
        "//*[local-name()='adminInfo']//*[local-name()='dataSetOwner']/*[local-name()='name'][1]",
        "//*[local-name()='modellingAndValidation']//*[local-name()='intendedApplications'][1]"
    ]:
        v = _s(root, xp)
        if v:
            rec["manufacturer"] = v.strip()
            break
    if not rec["manufacturer"]:
        # Fallback from name/text via vendor list
        m = VENDOR_PAT.search((rec["name"] + " " + txt)[:5000])
        if m: rec["manufacturer"] = m.group(1).upper()

    # --- Declared unit (DU)
    du = _s(root, "//*[local-name()='referenceToReferenceFlow'][1]/@unitName")
    if not du:
        du = _s(root, "//*[local-name()='quantitativeReference']//*[local-name()='unitGroup'][1]/@name")
    if not du:
        # last-ditch from text
        m = re.search(r"(?i)\b(declared\s+unit|reference\s+unit)\b.*?:?\s*([A-Za-z0-9²^/ .-]+)", txt)
        if m: du = m.group(2).strip()
    rec["declared_unit"] = du

    # --- Power (Wp) & Area (m²): from name and full text
    p = None; A = None

    # From name (e.g., "MAXEON 3 ... 400 W")
    m_name = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", rec["name"], flags=re.I)
    if m_name:
        val = _num(m_name.group(1))
        if val and 200 <= val <= 800: p = val

    # From text: ranges like "400–415 W" -> take min
    if p is None:
        m = re.search(r"(\d{3,4})\s*(?:–|-|to)\s*(\d{3,4})\s*(?:Wp|W\b)", txt, flags=re.I)
        if m:
            v1, v2 = _num(m.group(1)), _num(m.group(2))
            if v1 and v2: p = min(v1, v2)

    if p is None:
        m = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", txt, flags=re.I)
        if m:
            val = _num(m.group(1))
            if val and 150 <= val <= 900: p = val

    # Area in m² or via mm dimensions
    mA = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b", txt, flags=re.I)
    if mA:
        val = _num(mA.group(1))
        if val and 0.5 <= val <= 3.5: A = round(val, 4)
    else:
        dims = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})\s*mm", txt, flags=re.I)
        if dims:
            try:
                L = float(dims.group(1)); W = float(dims.group(2))
                area = (L*W)/1_000_000.0
                if 0.5 <= area <= 3.5: A = round(area, 4)
            except: pass

    rec["module_power_Wp"] = p
    rec["module_area_m2"]  = A

    # --- GWP A1–A3 per declared unit
    # Try structured: find a result node mentioning both 'GWP' and phase A1..A3
    # When structure is unknown, fallback to text regex around 'A1-A3' or 'A1–A3'
    # 1) Structured-ish: any node whose string() contains 'A1'..'A3' and 'GWP' and a number
    val = ""
    try:
        val = root.xpath("string((//*[contains(translate(.,'GWP','gwp'),'gwp') and (contains(.,'A1-A3') or contains(.,'A1–A3') or contains(.,'A1 – A3'))])[1])").strip()
    except Exception:
        val = ""
    if not val:
        # 2) Text-wide regex
        m = re.search(r"(?is)gwp.*?(?:a1\s*[–-]\s*a3|a1a3|a1\s*to\s*a3).*?(-?\d+(?:[.,]\d+)?)", txt)
        if m: val = m.group(1)
    if val:
        try:
            rec["GWP_total_A1A3_per_DU_kgCO2e"] = float(str(val).replace(",", "."))
        except Exception:
            pass

    # Filter out bogus Wp=1.0 artifacts
    if rec["module_power_Wp"] is not None and rec["module_power_Wp"] < 50:
        rec["module_power_Wp"] = None

    return rec

def extract_from_text(txt: str) -> dict:
    """Very last resort if XML parsing fails."""
    out = {"manufacturer":"","declared_unit":"","module_power_Wp":None,"module_area_m2":None,"GWP_total_A1A3_per_DU_kgCO2e":None}
    # Try vendor & W, area, GWP
    m = VENDOR_PAT.search(txt[:5000]);  out["manufacturer"] = (m.group(1).upper() if m else "")
    m = re.search(r"(\d{3,4})\s*(?:Wp|W\b)", txt, flags=re.I)
    if m:
        v = _num(m.group(1))
        if v and 150 <= v <= 900: out["module_power_Wp"] = v
    mA = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b", txt, flags=re.I)
    if mA:
        v = _num(mA.group(1))
        if v and 0.5 <= v <= 3.5: out["module_area_m2"] = round(v, 4)
    m = re.search(r"(?is)gwp.*?(?:a1\s*[–-]\s*a3|a1a3|a1\s*to\s*a3).*?(-?\d+(?:[.,]\d+)?)", txt)
    if m:
        try: out["GWP_total_A1A3_per_DU_kgCO2e"] = float(m.group(1).replace(",", "."))
        except: pass
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

    keep_cols = set(df_raw.columns) | {
        "dataset_uuid","name","version","manufacturer","declared_unit",
        "module_power_Wp","module_area_m2","GWP_total_A1A3_per_DU_kgCO2e","source"
    }

    updates = []
    for _, row in df_xml.iterrows():
        uuid = str(row.get("dataset_uuid") or "").strip()
        xml  = row.get("xml") or ""
        if not uuid or not xml:
            continue
        rec = parse_ilcd_record(xml)
        rec["dataset_uuid"] = uuid
        rec["source"] = "Environdec via ECO"
        updates.append(rec)

    df_up = pd.DataFrame(updates)

    # Merge into RAW on dataset_uuid; fill only missing values
    if df_raw.empty:
        merged = df_up
    else:
        merged = df_raw.merge(df_up, on="dataset_uuid", how="outer", suffixes=("", "_new"))
        for c in ["name","version","manufacturer","declared_unit",
                  "module_power_Wp","module_area_m2","GWP_total_A1A3_per_DU_kgCO2e","source"]:
            old = c; new = f"{c}_new"
            if new in merged.columns:
                merged[old] = merged[old].combine_first(merged[new])
        # Drop *_new columns
        merged = merged[[c for c in merged.columns if not c.endswith("_new")]]

    # Write back
    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        merged[list(keep_cols & set(merged.columns))].to_excel(w, sheet_name=RAW_SHEET, index=False)

    print("✓ Enriched RAW from ILCD_XML (manufacturer, DU, Wp, area, GWP A1–A3). Now run normalize_from_raw.py")

if __name__ == "__main__":
    main()
