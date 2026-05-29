#!/usr/bin/env python3
"""
Compute BoP impacts from BOP_CATALOG + BOP_FACTORS + BOP_PROJECTS
using ÖKOBAUDAT indicators already stored in INDICATORS_EN15804_A2_RAW.
Writes BOP_IMPACTS.
"""
import math, pandas as pd

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
CAT = "BOP_CATALOG"
FAC = "BOP_FACTORS"
PROJ = "BOP_PROJECTS"
OUT = "BOP_IMPACTS"

# Minimal indicator set; extend as needed
INDICATORS = [
    ("GWP_total", "kgCO2e"),
    ("AP", "molH+e"),
    ("EP_marine", "kgNe"),
    ("POCP", "kgNMVOCe"),
    ("ADP_mm", "kgSbe"),
    ("ADP_fossil", "MJ"),
    ("WDP", "m3w.e."),
]

def pick_row_for_uuid(df_raw, uuid):
    hit = df_raw[df_raw["dataset_uuid"] == uuid]
    return hit.iloc[0] if len(hit) else None

def to_declared_qty(value_per_MWp, baseline_unit, declared_unit, project_MWp):
    qty = value_per_MWp * project_MWp  # linear scaling
    # Convert baseline unit to declared_unit if needed (simple cases)
    # If baseline and declared units match, return qty directly.
    if baseline_unit.lower() == declared_unit.lower():
        return qty
    # Common conversions: t↔kg, m3 of concrete -> t via density (approx; refine later)
    if baseline_unit.lower() == "kg/mwp" and declared_unit.lower() == "t":
        return qty / 1000.0
    if baseline_unit.lower() == "t/mwp" and declared_unit.lower() == "kg":
        return qty * 1000.0
    # Fallback: return qty (you can refine per item_code later)
    return qty

def main():
    df_raw = pd.read_excel(WB, sheet_name=RAW_SHEET)
    df_cat = pd.read_excel(WB, sheet_name=CAT)
    df_fac = pd.read_excel(WB, sheet_name=FAC)
    df_proj = pd.read_excel(WB, sheet_name=PROJ)

    out_rows = []
    for _, p in df_proj.iterrows():
        pid = p["project_id"]
        MWp = float(p["capacity_MWp"])
        # Iterate BoP items
        for _, c in df_cat.iterrows():
            item = c["item_code"]
            uuid = c["oekb_uuid"]
            decl_u = str(c["declared_unit"]).strip()
            # find factor row
            f = df_fac[df_fac["item_code"] == item]
            if f.empty:
                continue
            f = f.iloc[0]
            baseline = str(f["baseline_unit"]).strip()
            val_per_MWp = float(f["value_per_MWp"])
            # compute required quantity in declared units
            qty_declared = to_declared_qty(val_per_MWp, baseline, decl_u, MWp)

            raw = pick_row_for_uuid(df_raw, uuid)
            if raw is None:
                continue

            row = {
                "project_id": pid,
                "scope": item,
                "capacity_MWp": MWp,
            }
            # For each indicator, use A1–A3 per declared unit if present
            for code, unit in INDICATORS:
                col = f"{code}_A1-A3_per_DU_{unit}"
                if col not in raw:
                    # try alternative combined name (your harvest might have A1A3)
                    col = f"{code}_A1A3_per_DU_{unit}"
                v = raw.get(col)
                if pd.isna(v):
                    row[f"{code}_A1A3_per_project_{unit}"] = math.nan
                    row[f"{code}_A1A3_per_kWp_{unit}"] = math.nan
                else:
                    total = float(v) * qty_declared
                    row[f"{code}_A1A3_per_project_{unit}"] = total
                    row[f"{code}_A1A3_per_kWp_{unit}"] = total / (MWp * 1000.0)
            out_rows.append(row)

        # roll-up TOTAL per project
        if out_rows:
            import pandas as _pd
            tmp = _pd.DataFrame([r for r in out_rows if r["project_id"] == pid])
            total_row = {"project_id": pid, "scope": "TOTAL", "capacity_MWp": MWp}
            for code, unit in INDICATORS:
                colp = f"{code}_A1A3_per_project_{unit}"
                if colp in tmp:
                    s = _pd.to_numeric(tmp[colp], errors="coerce").sum()
                    total_row[colp] = s
                    total_row[f"{code}_A1A3_per_kWp_{unit}"] = s / (MWp * 1000.0)
            out_rows.append(total_row)

    df_out = pd.DataFrame(out_rows)
    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df_out.to_excel(w, sheet_name=OUT, index=False)
    print(f"✓ Wrote {len(df_out)} rows to {OUT}")

if __name__ == "__main__":
    main()
