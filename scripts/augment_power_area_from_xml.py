# augment_power_area_from_xml.py
# Reads ILCD_XML and INDICATORS_EN15804_A2_RAW from workbook,
# regex-extracts module power (Wp) and area (m²) from XML text,
# writes 'module_power_Wp' and 'module_area_m2' back into RAW sheet.

import re, math, pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
XML_SHEET = "ILCD_XML"

def _num(x: str):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None

def extract_power_area(xml: str):
    """Return (Wp, m2) using robust regex heuristics typical for PV EPDs."""
    if not isinstance(xml, str) or not xml:
        return (None, None)

    text = xml
    # 1) Power (kWp / Wp)
    kwp_vals = [ _num(m) for m in re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:kW[\-\s]*p|kWp|kW-?peak|kWpeak)\b', text, flags=re.I) ]
    wp_vals  = [ _num(m) for m in re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:Wp|W[\-\s]*p)\b', text, flags=re.I) ]

    # Convert kWp to Wp
    kwp_vals = [ v*1000.0 for v in kwp_vals if v is not None ]
    power_candidates = [ v for v in (wp_vals + kwp_vals) if v is not None ]

    # Prefer realistic module power range (200..800 Wp), else fallback to first available
    power_Wp = None
    ranged = [v for v in power_candidates if 200 <= v <= 8000]  # allow strings like 1,500 Wp (large kits)
    if ranged:
        # Prefer 200..800 first, otherwise take smallest >800 (kits)
        in_mod_range = [v for v in ranged if 200 <= v <= 800]
        power_Wp = (in_mod_range or [min(ranged)])[0]
    elif power_candidates:
        power_Wp = power_candidates[0]

    # 2) Area (m²)
    m2_vals = [ _num(m) for m in re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\b', text, flags=re.I) ]
    area_m2 = None
    ranged_a = [v for v in m2_vals if 0.5 <= v <= 3.5]
    if ranged_a:
        # Prefer 1.5..2.5 first (typical), else first within wide range
        typical = [v for v in ranged_a if 1.3 <= v <= 2.6]
        area_m2 = (typical or [ranged_a[0]])[0]

    # 3) Fallback: dimensions like "1722 x 1134 mm"
    dim = re.search(r'(\d{3,4})\s*[x×]\s*(\d{3,4})\s*mm', text, flags=re.I)
    if dim and not area_m2:
        try:
            L = float(dim.group(1)); W = float(dim.group(2))
            area_m2 = (L * W) / 1_000_000.0  # mm² → m²
        except Exception:
            pass

    return (round(power_Wp, 3) if power_Wp is not None else None,
            round(area_m2, 4) if area_m2 is not None else None)

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

    # Build mapping: uuid -> (Wp, m2)
    power_map = {}
    for _, row in df_xml.iterrows():
        uuid = str(row.get("dataset_uuid") or "").strip()
        xml  = row.get("xml") or ""
        if not uuid or not xml:
            continue
        Wp, A = extract_power_area(xml)
        if Wp is None and A is None:
            continue
        prev = power_map.get(uuid, (None, None))
        # prefer non-None and typical ranges
        new_Wp = Wp if (prev[0] is None or (Wp and 200 <= Wp <= 800)) else prev[0]
        new_A  = A  if (prev[1] is None or (A  and 0.5 <= A <= 3.5)) else prev[1]
        power_map[uuid] = (new_Wp or prev[0], new_A or prev[1])

    if df_raw.empty:
        print("No RAW sheet found; nothing to augment.")
        return

    # Ensure columns exist
    for col in ["module_power_Wp", "module_area_m2"]:
        if col not in df_raw.columns:
            df_raw[col] = None

    # Apply mapping to RAW
    updated = 0
    for i in range(len(df_raw)):
        uuid = str(df_raw.at[i, "dataset_uuid"]) if "dataset_uuid" in df_raw.columns else ""
        if not uuid: 
            continue
        if uuid in power_map:
            Wp, A = power_map[uuid]
            if Wp is not None: df_raw.at[i, "module_power_Wp"] = Wp
            if A  is not None: df_raw.at[i, "module_area_m2"] = A
            updated += 1

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ Updated {updated} rows with module_power_Wp / module_area_m2 in '{RAW_SHEET}'.")

if __name__ == "__main__":
    main()
