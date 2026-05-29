import argparse, pandas as pd
from pathlib import Path
import numpy as np

WB="EPD_Hub_V3_PV_starter_enriched.xlsx"
NORM="INDICATORS_NORMALIZED"

def explain(df, label):
    print(f"{label}: {len(df)}")

def backfill_per_kWp(row):
    # Prefer direct per_kWp
    v = row.get("GWP_total_A1A3_per_kWp_kgCO2e")
    if pd.notna(v): return v
    # Derive from per_m2 and area
    pm2 = row.get("GWP_total_A1A3_per_m2_kgCO2e")
    A   = row.get("module_area_m2")
    Wp  = row.get("module_power_Wp")
    if pd.notna(pm2) and pd.notna(A) and pd.notna(Wp) and Wp>0:
        return pm2 * A / (Wp/1000.0)
    # Derive from per_module and Wp
    pmod = row.get("GWP_total_A1A3_per_module_kgCO2e")
    if pd.notna(pmod) and pd.notna(Wp) and Wp>0:
        return pmod / (Wp/1000.0)
    return np.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wb", default=WB)
    ap.add_argument("--tech", default="", help="keyword in name, e.g. TOPCon, HJT, bifacial")
    ap.add_argument("--wp-min", type=float, default=0)
    ap.add_argument("--wp-max", type=float, default=1e9)
    ap.add_argument("--gwp-max", type=float, default=1e9, help="max GWP per kWp (kgCO2e)")
    ap.add_argument("--qty", type=int, default=1000, help="desired capacity in kWp (e.g., 5000 = 5 MW)")
    ap.add_argument("--out", default="selection.csv")
    ap.add_argument("--explain", action="store_true")
    args = ap.parse_args()

    df = pd.read_excel(args.wb, sheet_name=NORM)
    # Guard columns
    for c in ["name","manufacturer","module_power_Wp","module_area_m2",
              "GWP_total_A1A3_per_kWp_kgCO2e","GWP_total_A1A3_per_m2_kgCO2e",
              "GWP_total_A1A3_per_module_kgCO2e"]:
        if c not in df.columns: df[c] = pd.NA

    # Backfill per_kWp where possible
    df["gwp_per_kWp_calc"] = df.apply(backfill_per_kWp, axis=1)

    if args.explain: explain(df, "start")

    q = df.copy()

    # Tech keyword (optional)
    if args.tech:
        q = q[q["name"].astype(str).str.contains(args.tech, case=False, na=False)]
        if args.explain: explain(q, f'after tech="{args.tech}"')

    # Wp range
    q = q[(q["module_power_Wp"].fillna(-1) >= args.wp_min) & (q["module_power_Wp"].fillna(1e12) <= args.wp_max)]
    if args.explain: explain(q, f"after Wp {args.wp_min}..{args.wp_max}")

    # GWP per kWp (use backfilled column)
    q = q[(q["gwp_per_kWp_calc"].fillna(1e12) <= args.gwp_max)]
    if args.explain: explain(q, f"after gwp_per_kWp <= {args.gwp_max}")

    # Sort by GWP, then manufacturer/name
    q = q.sort_values(by=["gwp_per_kWp_calc","manufacturer","name"], na_position="last")

    if q.empty:
        print("No modules match filters.")
        # Show the first 10 rows with their calc fields to debug
        cols = ["manufacturer","name","module_power_Wp","module_area_m2",
                "GWP_total_A1A3_per_kWp_kgCO2e","GWP_total_A1A3_per_m2_kgCO2e",
                "GWP_total_A1A3_per_module_kgCO2e","gwp_per_kWp_calc"]
        print(df[cols].head(10))
        return

    # Greedy pack until reaching qty kWp
    target_Wp = args.qty * 1000.0
    picked = []
    total = 0.0
    for _, r in q.iterrows():
        if pd.isna(r["module_power_Wp"]): 
            continue
        picked.append(r)
        total += float(r["module_power_Wp"])
        if total >= target_Wp:
            break

    out = pd.DataFrame(picked)
    out.to_csv(args.out, index=False)
    print(f"✓ Picked {len(out)} modules, total ~{total/1000:.2f} kWp → {args.out}")

if __name__ == "__main__":
    main()
