# gwp_from_archives_v3_xpath.py
# Simple text-based extraction of GWP A1–A3 from ECO/Environdec ILCD archives.
# - Looks inside data/eco_zip/*.zip (or plain XML)
# - Searches for "GWP / Climate change" + "A1-A3" + a numeric value
# - Writes GWP_total_A1A3_per_DU_kgCO2e and declared_unit into RAW
# - Treats "", whitespace and 0 as missing (so it overwrites zeros)

from pathlib import Path
import io, zipfile, re
import pandas as pd

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
ZIP_DIR = Path("data/eco_zip")

GWP_HINTS = ["gwp", "climate change", "global warming potential", "gwp-ghg"]
A13_HINTS = ["a1-a3", "a1 – a3", "a1–a3", "a1 to a3"]
UNIT_HINTS = ["kg co2", "kg co₂", "kgco2", "kg co2e", "kgco2e"]

def norm(text: str) -> str:
    """Normalize text for easier searching."""
    return re.sub(r"\s+", " ", (text or "").lower().replace("–", "-").replace("\u00a0", " "))

def is_missing_number(x) -> bool:
    """Treat NaN, '', whitespace, and 0/0.0 as missing."""
    if x is None:
        return True
    s = str(x).strip()
    if s == "":
        return True
    try:
        v = float(s.replace(",", "."))
        return v == 0.0
    except Exception:
        return True

def to_float(s: str):
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None

def guess_unit(tnorm: str) -> str | None:
    """Very simple unit guess based on full text."""
    if "per kwp" in tnorm or "/kwp" in tnorm or "kwp" in tnorm:
        return "kWp"
    if "m2" in tnorm or "m²" in tnorm:
        return "m2"
    if "piece" in tnorm or "module" in tnorm:
        return "piece"
    # fallback: look for 'kg co2'
    if any(h in tnorm for h in UNIT_HINTS):
        return "kg CO2e"
    return None

def extract_gwp_a1a3_from_text(xml_text: str):
    """
    Heuristic:
    - Work on normalized text
    - Require at least one GWP hint and one A1–A3 hint
    - In a window around "a1-a3", grab the first number (supports exponent)
    """
    t = norm(xml_text)
    if not any(h in t for h in GWP_HINTS):
        return None, None

    # find the "A1-A3" position
    pos = -1
    for h in A13_HINTS:
        pos = t.find(h)
        if pos != -1:
            break
    if pos == -1:
        # no explicit A1-A3, can't reliably extract
        return None, None

    # look in a window around A1-A3
    start = max(0, pos - 160)
    end = min(len(t), pos + 220)
    window = t[start:end]

    # number pattern: supports simple floats and scientific notation
    m = re.search(r"(-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)", window)
    if not m:
        return None, None

    val = to_float(m.group(1))
    if val is None:
        return None, None

    du = guess_unit(t)
    return val, du

def iterate_xml_texts(zip_path: Path):
    """Yield decoded XML texts from a .zip or raw text file."""
    data = zip_path.read_bytes()
    # if not a zip, treat as single XML/text
    if data[:4] != b"PK\x03\x04":
        try:
            yield data.decode("utf-8", "ignore")
        except Exception:
            return
        return

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Prefer files with "process" in name
        names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        names.sort(key=lambda n: (0 if "process" in n.lower() else 1, len(n)))
        for name in names:
            try:
                txt = zf.read(name).decode("utf-8", "ignore")
                yield txt
            except Exception:
                continue

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")

    try:
        df = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df = pd.DataFrame()

    if "dataset_uuid" not in df.columns:
        raise SystemExit(f"Sheet '{RAW_SHEET}' has no 'dataset_uuid' column.")

    df["dataset_uuid"] = df["dataset_uuid"].astype(str).str.strip()
    idx = {str(df.at[i, "dataset_uuid"]): i for i in df.index}

    updated = 0
    touched = []

    for zp in ZIP_DIR.glob("*.zip"):
        uid = zp.stem
        gwp = unit = None

        for xml_text in iterate_xml_texts(zp):
            gwp, unit = extract_gwp_a1a3_from_text(xml_text)
            if gwp is not None:
                break

        if gwp is None:
            continue

        if uid not in idx:
            continue

        i = idx[uid]
        col = "GWP_total_A1A3_per_DU_kgCO2e"
        if col not in df.columns:
            df[col] = pd.NA

        current = df.at[i, col]
        if is_missing_number(current):
            df.at[i, col] = gwp
            updated += 1
            touched.append(uid)

        # declared_unit
        if unit:
            du_col = "declared_unit"
            if du_col not in df.columns:
                df[du_col] = ""
            cur_du = str(df.at[i, du_col]).strip() if pd.notna(df.at[i, du_col]) else ""
            if cur_du == "":
                df.at[i, du_col] = unit

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ Updated RAW with GWP A1–A3 for {updated} datasets")
    if touched:
        print("Sample updated UUIDs:", touched[:10])

if __name__ == "__main__":
    main()
