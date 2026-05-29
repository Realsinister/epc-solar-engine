# gwp_from_archives.py
# Scan data/eco_zip/*.zip (and any XML saved there) for EN 15804+A2 "Climate change/GWP" indicators and A1–A3.
# Write GWP_total_A1A3_per_DU_kgCO2e and declared_unit into RAW, then normalize.

import io, re, zipfile
from pathlib import Path
import pandas as pd
from lxml import etree

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
ZIP_DIR = Path("data/eco_zip")

# Common synonyms / locales
GWP_KEYS = [
    "climate change", "climate-change", "gwp", "gwp-total", "gwp ghg", "gwp-ghg",
    "global warming potential", "gwp100", "gwp 100", "gwp (100)"
]
UNIT_HINTS = ["kg co2", "kg co₂", "kg co2e", "kg co2-eq", "kg co₂-eq", "kg co2 eq", "kg co₂ eq"]
A_COMB_KEYS = ["a1-a3", "a1 – a3", "a1–a3", "a1 to a3", "modules a1-a3"]
A_KEYS = ["a1","a2","a3"]

def norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("–","-").replace("\u00a0"," ")
    s = re.sub(r"\s+"," ", s)
    return s

def find_declared_unit(text: str) -> str|None:
    t = norm(text)
    m = re.search(r"(declared unit|reference unit)[^:\n]*[:\s]\s*([a-z0-9²^/ .-]{1,30})", t, re.I)
    if m: return m.group(2).strip()
    # common PV DU fallbacks
    if "kwp" in t: return "kWp"
    if "m2" in t or "m²" in t: return "m2"
    if "piece" in t or "module" in t: return "piece"
    return None

def extract_gwp_a1a3(text: str):
    """Return (gwp, du_guess). Accept combined A1-A3 or sum of A1,A2,A3 in the vicinity of GWP synonyms."""
    t = norm(text)
    # narrow to sections mentioning GWP/Climate change
    if not any(k in t for k in GWP_KEYS):
        return None, None
    # 1) Combined A1-A3 near indicator
    m = re.search(r"(?:gwp|climate change|global warming potential)[^0-9a-z]{0,40}(?:a1-a3|a1 to a3|a1–a3)[^0-9]{0,30}(-?\d+(?:[.,]\d+)?)", t, re.I)
    if m:
        val = float(m.group(1).replace(",", "."))
        return val, find_declared_unit(t)
    # 2) Sum A1+A2+A3 near indicator
    vals = {}
    for mod in A_KEYS:
        mm = re.search(r"(?:gwp|climate change|global warming potential)[^0-9a-z]{0,40}"+mod+r"[^0-9]{0,20}(-?\d+(?:[.,]\d+)?)", t, re.I)
        if mm:
            vals[mod] = float(mm.group(1).replace(",", "."))
    if vals:
        return sum(vals.values()), find_declared_unit(t)
    # 3) Last resort: first number in the same line as GWP + unit hint
    m = re.search(r"(?:gwp|climate change)[^0-9]{0,40}(-?\d+(?:[.,]\d+)?).{0,15}(?:co2|co₂)", t, re.I)
    if m:
        return float(m.group(1).replace(",", ".")), find_declared_unit(t)
    return None, None

def all_xml_texts_from_path(p: Path) -> list[str]:
    data = p.read_bytes()
    texts = []
    if data[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    try:
                        x = z.read(name).decode("utf-8", errors="ignore")
                        texts.append(x)
                    except Exception:
                        continue
    else:
        # may actually be xml
        try:
            texts.append(data.decode("utf-8", errors="ignore"))
        except Exception:
            pass
    return texts

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")
    try:
        df_raw = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df_raw = pd.DataFrame()

    # Make index by dataset_uuid for quick update
    if "dataset_uuid" not in df_raw.columns:
        df_raw["dataset_uuid"] = None
    df_raw["dataset_uuid"] = df_raw["dataset_uuid"].astype(str).str.strip()
    idx = {str(df_raw.at[i,"dataset_uuid"]): i for i in df_raw.index}

    updates = 0
    for p in ZIP_DIR.glob("*.zip"):
        uid = p.stem
        texts = all_xml_texts_from_path(p)
        gwp_val = None
        du = None
        for t in texts:
            v, d = extract_gwp_a1a3(t)
            if v is not None:
                gwp_val = v
                du = du or find_declared_unit(t) or "piece"  # default to piece if absent
                break
        if gwp_val is None:
            continue
        # write back if present in RAW
        if uid in idx:
            i = idx[uid]
            # Only fill if empty
            if ("GWP_total_A1A3_per_DU_kgCO2e" not in df_raw.columns) or pd.isna(df_raw.at[i, "GWP_total_A1A3_per_DU_kgCO2e"]):
                df_raw.at[i, "GWP_total_A1A3_per_DU_kgCO2e"] = gwp_val
                updates += 1
            if ("declared_unit" not in df_raw.columns) or not str(df_raw.at[i,"declared_unit"]).strip():
                df_raw.at[i, "declared_unit"] = du or df_raw.at[i, "declared_unit"]

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ Updated RAW with GWP A1–A3 for {updates} datasets from archives in {ZIP_DIR}")

if __name__ == "__main__":
    main()
