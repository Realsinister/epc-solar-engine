import pandas as pd, numpy as np

WB    = "EPD_Hub_V3_PV_starter_enriched.xlsx"
IN    = "INDICATORS_NORMALIZED"
OUT   = "PV_SCORED"

df = pd.read_excel(WB, sheet_name=IN)
gwp_cols = [c for c in df.columns if ("GWP_total" in c and "per_kWp" in c)]
assert gwp_cols, "No GWP_total per-kWp column found"
GWP = gwp_cols[0]

x = pd.to_numeric(df[GWP], errors="coerce")
q1, q3 = np.nanpercentile(x, [25, 75]) if x.notna().any() else (np.nan, np.nan)
# Rank (lower is better): score = 100 at 10th percentile, 0 at 90th
p = x.rank(pct=True, method="average")
score = (1 - p).clip(0,1) * 100

out = df.copy()
out["score_gwp_kWp_0to100"] = score.round(1)
out["note_score_method"] = "percentile-based, lower GWP per kWp = higher score"

with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
    out.to_excel(w, sheet_name=OUT, index=False)
print(f"Wrote {len(out)} rows -> {OUT}")