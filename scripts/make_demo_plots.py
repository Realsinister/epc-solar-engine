import os, pandas as pd, matplotlib.pyplot as plt
WB="EPD_Hub_V3_PV_starter_enriched.xlsx"; SH="PV_SCORED"
df=pd.read_excel(WB, sheet_name=SH)
col=[c for c in df.columns if ("GWP_total" in c and "per_kWp" in c)][0]
os.makedirs("plots", exist_ok=True)

# Top-20 lowest GWP/kWp
d=df[["manufacturer","model",col]].dropna().sort_values(col).head(20)
plt.figure(figsize=(8,6)); plt.barh(d["model"].astype(str).str[:40], d[col])
plt.xlabel("kg CO₂e / kWp (A1–A3)"); plt.tight_layout()
plt.savefig("plots/top20_gwp_kWp.png", dpi=160)
print("Saved plots/top20_gwp_kWp.png")