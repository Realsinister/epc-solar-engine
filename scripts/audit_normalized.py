import pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
S = "INDICATORS_NORMALIZED"

df = pd.read_excel(WB, sheet_name=S)
print("rows:", len(df))
for c in ["name","manufacturer","module_power_Wp","module_area_m2",
          "GWP_total_A1A3_per_kWp_kgCO2e","GWP_total_A1A3_per_m2_kgCO2e",
          "GWP_total_A1A3_per_module_kgCO2e"]:
    print(f"non-null {c}:", df[c].notna().sum() if c in df.columns else 0)

print("\nTop 10 by presence of power:")
print(df[df["module_power_Wp"].notna()][["manufacturer","name","module_power_Wp"]].head(10))
