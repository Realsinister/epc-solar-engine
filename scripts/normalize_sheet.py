#!/usr/bin/env python3
"""
normalize_sheet.py — Normalize indicators from a chosen input sheet to per-module / per-m² / per-kWp.
Default in: PV_RAW  |  Default out: PV_NORMALIZED
"""
import argparse, math, pandas as pd

INDICATORS = [
    ("GWP_total", "kgCO2e"),
    ("GWP_fossil", "kgCO2e"),
    ("ODP", "kgCFC11e"),
    ("AP", "molH+e"),
    ("EP_freshwater", "kgPe"),
    ("EP_marine", "kgNe"),
    ("EP_terrestrial", "molNe"),
    ("POCP", "kgNMVOCe"),
    ("ADP_mm", "kgSbe"),
    ("ADP_fossil", "MJ"),
    ("WDP", "m3w.e."),
]

def norm_row(r, ind_base, unit):
    du = str(r.get("declared_unit") or "").strip().lower()
    val = r.get(f"{ind_base}_A1A3_per_DU_{unit}")
    if pd.isna(val): return math.nan, math.nan, math.nan
    wp   = r.get("Wp_module")
    wpm2 = r.get("Wp_per_m2")
    area = r.get("area_m2")
    per_module = per_m2 = per_kWp = math.nan
    if du in ("wp","watt-peak","wattpeak","watt peak"):
        per_module = (val * wp) if pd.notna(wp) else math.nan
        per_m2 = (val * wpm2) if pd.notna(wpm2) else (
            per_module / area if (pd.notna(per_module) and pd.notna(area)) else math.nan
        )
        per_kWp = val * 1000.0
    elif du in ("piece","module","unit","pcs"):
        per_module = val
        per_m2 = (val / area) if pd.notna(area) else math.nan
        per_kWp = (val * 1000.0 / wp) if pd.notna(wp) else math.nan
    return per_module, per_m2, per_kWp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default="EPD_Hub_V3_PV_starter_enriched.xlsx")
    ap.add_argument("--in-sheet", default="PV_RAW")
    ap.add_argument("--out-sheet", default="PV_NORMALIZED")
    args = ap.parse_args()

    df = pd.read_excel(args.workbook, sheet_name=args.in_sheet)
    if df.empty:
        print(f"Input sheet '{args.in_sheet}' is empty; run pv_filter.py first.")
        return

    keep = ["manufacturer","model","declared_unit","Wp_module","Wp_per_m2","area_m2",
        "year","PCR","programme_operator","dataset_uuid","version"]

# create any missing columns
for c in keep:
    if c not in df.columns:
        df[c] = pd.NA

out = df[keep].copy()


    for code, unit in INDICATORS:
        pm, pm2, pkwp = [], [], []
        for _, r in df.iterrows():
            a, b, c = norm_row(r, code, unit)
            pm.append(a); pm2.append(b); pkwp.append(c)
        out[f"{code}_A1A3_per_module_{unit}"] = pm
        out[f"{code}_A1A3_per_m2_{unit}"]     = pm2
        out[f"{code}_A1A3_per_kWp_{unit}"]    = pkwp

    with pd.ExcelWriter(args.workbook, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        out.to_excel(w, sheet_name=args.out_sheet, index=False)

    print(f"✓ Wrote '{args.out_sheet}' ({len(out)} rows) in {args.workbook}")

if __name__ == "__main__":
    main()
