# gwp_from_archives_v2.py
# Robustly extract GWP A1–A3 from data/eco_zip/*.zip (or XML) and update RAW.
# Treat "", whitespace, and 0/0.0 as missing so we actually fill values.

import io, re, zipfile
from pathlib import Path
import pandas as pd

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
ZIP_DIR = Path("data/eco_zip")

GWP_KEYS = ["climate change","gwp","global warming potential","gwp-ghg","gwp total","gwp-total"]
A_COMB = ["a1-a3","a1 – a3","a1–a3","a1 to a3","modules a1-a3"]
A_SPLIT = ["a1","a2","a3"]

def norm(s: str) -> str:
    return re.sub(r"\s+"," ", (s or "").lower().replace("–","-").replace("\u00a0"," "))

def find_declared_unit(t: str) -> str | None:
    if "kwp" in t: return "kWp"
    if "m2" in t or "m²" in t: return "m2"
    if "piece" in t or "module" in t: return "piece"
    m = re.search(r"(declared unit|reference unit)\W{0,10}([a-z0-9²/\- ]{1,24})", t, re.I)
    return m.group(2).strip() if m else None

def extract_gwp(text: str):
    """Return (gwp_value_float, declared_unit_guess or None)."""
    t = norm(text)
    if not any(k in t for k in GWP_KEYS):
        return None, None
    # Combined A1–A3
    m = re.search(r"(?:gwp|climate change|global warming potential)\W{0,40}(?:a1-a3|a1 to a3|a1–a3)\W{0,30}(-?\d+(?:[.,]\d+)?)", t, re.I)
    if m:
        return float(m.group(1).replace(",", ".")), find_declared_unit(t)
    # Split A1/A2/A3
    vals = {}
    for mod in A_SPLIT:
        mm = re.search(r"(?:gwp|climate change|global warming potential)\W{0,40}"+mod+r"\W{0,20}(-?\d+(?:[.,]\d+)?)", t, re.I)
        if mm:
            vals[mod] = float(mm.group(1).replace(",", "."))
    if vals:
        return sum(vals.values()), find_declared_unit(t)
    # Fallback: first number on same line as GWP + CO2 hint
    m = re.search(r"(?:gwp|climate change)[^0-9]{0,40}(-?\d+(?:[.,]\d+)?).{0,15}(?:co2|co₂)", t, re.I)
    if m:
        return float(m.group(1).replace(",", ".")), find_declared_unit(t)
    return None, None

def iterate_texts(p: Path):
    b = p.read_bytes()
    if b[:4] != b"PK\x03\x04":
        # not a zip -> try direct XML/text
        try:
            yield b.decode("utf-8","ignore")
        except Exception:
            return
        return
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        for n in z.namelist():
            if n.lower().endswith(".xml"):
                yield z.read(n).decode("utf-8","ignore")

def to_float(x):
    try: return float(str(x).strip().replace(",", "."))
    except: return None

def is_missing_number(x) -> bool:
    """Treat NaN, '', whitespace, and 0/0.0 as missing for GWP."""
    if x is None: return True
    s = str(x).strip()
    if s == "": return True
    try:
        v = float(s.replace(",", "."))
        return v == 0.0
    except:
        return True

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")
    try:
        df = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df = pd.DataFrame()

    if "dataset_uuid" not in df.columns:
        raise SystemExit("RAW sheet has no 'dataset_uuid' column.")

    df["dataset_uuid"] = df["dataset_uuid"].astype(str).str.strip()
    idx = {str(df.at[i,"dataset_uuid"]): i for i in df.index}

    updated = 0
    hits = []

    for p in ZIP_DIR.glob("*.zip"):
        uid = p.stem
        gwp = du = None
        for t in iterate_texts(p):
            gwp, du = extract_gwp(t)
            if gwp is not None:
                break
        if gwp is None:
            continue

        if uid in idx:
            i = idx[uid]
            # Update GWP if missing/blank/zero
            col = "GWP_total_A1A3_per_DU_kgCO2e"
            current = df.at[i, col] if col in df.columns else None
            if is_missing_number(current):
                df.at[i, col] = gwp
                updated += 1
                hits.append(uid)
            # Update declared_unit if empty
            if du:
                du_col = "declared_unit"
                cur_du = str(df.at[i, du_col]).strip() if du_col in df.columns and pd.notna(df.at[i, du_col]) else ""
                if cur_du == "":
                    df.at[i, du_col] = du

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ Updated RAW with GWP A1–A3 for {updated} datasets")
    if hits:
        print("Updated UUIDs (first 10):", hits[:10])

if __name__ == "__main__":
    main()
