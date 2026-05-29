# fill_gwp_per_module.py
#
# Compute GWP_total_A1A3_per_module_kgCO2e in INDICATORS_NORMALIZED
# from:
#   - GWP_total_A1A3_per_DU_kgCO2e
#   - declared_unit
#   - module_power_Wp
#   - module_area_m2

from pathlib import Path
import pandas as pd
import numpy as np

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
SHEET = "INDICATORS_NORMALIZED"

GWP_DU_COL = "GWP_total_A1A3_per_DU_kgCO2e"
UNIT_COL   = "declared_unit"
P_COL      = "module_power_Wp"
A_COL      = "module_area_m2"
GWP_MOD_COL = "GWP_total_A1A3_per_module_kgCO2e"


def norm_unit(u: str) -> str:
    if u is None or (isinstance(u, float) and np.isnan(u)):
        return ""
    s = str(u).strip().lower()
    # normalize a few variants
    s = s.replace("m²", "m2")
    s = s.replace("kwp", "kwp")
    return s


def is_number(x) -> bool:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return False
    try:
        float(str(x).replace(",", "."))
        return True
    except Exception:
        return False


def to_float(x) -> float | None:
    if not is_number(x):
        return None
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def main():
    path = Path(WB)
    if not path.exists():
        raise SystemExit(f"Workbook not found: {WB}")

    df = pd.read_excel(path, sheet_name=SHEET)

    # Check required columns
    for col in [GWP_DU_COL, UNIT_COL, P_COL, A_COL]:
        if col not in df.columns:
            raise SystemExit(f"Column '{col}' not found in sheet '{SHEET}'")

    # Ensure target column exists
    if GWP_MOD_COL not in df.columns:
        df[GWP_MOD_COL] = np.nan

    updated = 0
    total = len(df)

    for idx, row in df.iterrows():
        gwp_du = to_float(row[GWP_DU_COL])
        u = norm_unit(row[UNIT_COL])
        p_wp = to_float(row[P_COL])
        a_m2 = to_float(row[A_COL])

        if gwp_du is None:
            continue

        # Compute per module depending on declared unit
        gwp_mod = None

        if u in ("piece", "module"):
            gwp_mod = gwp_du
        elif u == "m2":
            if a_m2 and a_m2 > 0:
                gwp_mod = gwp_du * a_m2
        elif u == "kwp":
            if p_wp and p_wp > 0:
                gwp_mod = gwp_du * (p_wp / 1000.0)
        else:
            # unknown unit -> leave as NaN
            gwp_mod = None

        if gwp_mod is not None:
            df.at[idx, GWP_MOD_COL] = gwp_mod
            updated += 1

    print(f"Rows in INDICATORS_NORMALIZED: {total}")
    print(f"Rows with per-module GWP computed: {updated}")

    # Write back to workbook (replace sheet)
    with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=SHEET, index=False)

    print(f"Updated '{GWP_MOD_COL}' in sheet '{SHEET}' of {WB}")


if __name__ == "__main__":
    main()
