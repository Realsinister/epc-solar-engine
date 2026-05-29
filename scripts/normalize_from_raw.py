# normalize_from_raw.py
# Builds indicators 'per_m2', 'per_module', 'per_kWp' from RAW, using declared_unit + module_power_Wp + module_area_m2
import math, pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
OUT_SHEET = "INDICATORS_NORMALIZED"

def _num(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None

def classify_du(du: str):
    if not isinstance(du, str): 
        return "unknown"
    s = du.lower()
    if "kwp" in s or "k w p" in s:
        return "kwp"
    if "m2" in s or "m²" in s:
        return "m2"
    if "piece" in s or "pcs" in s or "unit" in s or "module" in s:
        return "piece"
    return "unknown"

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")

    try:
        df = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        raise SystemExit(f"Sheet '{RAW_SHEET}' not found in {WB}.")

    # Ensure required columns exist
    for col in ["GWP_total_A1A3_per_DU_kgCO2e", "declared_unit", "module_power_Wp", "module_area_m2"]:
        if col not in df.columns:
            df[col] = None

    out_rows = []
    for _, r in df.iterrows():
        uuid = str(r.get("dataset_uuid") or "").strip()
        gwp = _num(r.get("GWP_total_A1A3_per_DU_kgCO2e"))
        du  = r.get("declared_unit")
        Wp  = _num(r.get("module_power_Wp"))
        A   = _num(r.get("module_area_m2"))

        du_kind = classify_du(du)

        per_kwp = None
        per_m2 = None
        per_module = None

        if gwp is not None:
            if du_kind == "kwp":
                per_kwp = gwp
                if Wp and Wp > 0:
                    per_module = gwp * (Wp / 1000.0)
                # per_m2 not derivable without specific Wp/m²; leave None
            elif du_kind == "m2":
                per_m2 = gwp
                if A and A > 0:
                    per_module = gwp * A
                if Wp and Wp > 0:
                    per_kwp = gwp / (Wp / 1000.0)
            elif du_kind == "piece":
                per_module = gwp
                if Wp and Wp > 0:
                    per_kwp = gwp / (Wp / 1000.0)
                if A and A > 0:
                    per_m2 = gwp / A
            else:
                # Unknown DU: try to salvage if both Wp and A exist
                # Prefer expressing per_kWp if power known
                if Wp and Wp > 0:
                    per_kwp = gwp / (Wp / 1000.0)
                if A and A > 0:
                    per_m2 = gwp / A

        out_rows.append({
            "dataset_uuid": uuid,
            "name": r.get("name"),
            "manufacturer": r.get("manufacturer"),
            "declared_unit": du,
            "module_power_Wp": Wp,
            "module_area_m2": A,
            "GWP_total_A1A3_per_DU_kgCO2e": gwp,
            "GWP_total_A1A3_per_kWp_kgCO2e": per_kwp,
            "GWP_total_A1A3_per_m2_kgCO2e": per_m2,
            "GWP_total_A1A3_per_module_kgCO2e": per_module,
            "source": r.get("source"),
            "version": r.get("version"),
        })

    out = pd.DataFrame(out_rows)

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        out.to_excel(w, sheet_name=OUT_SHEET, index=False)

    print(f"✓ Wrote '{OUT_SHEET}' with {len(out)} rows in {WB}")

if __name__ == "__main__":
    main()
