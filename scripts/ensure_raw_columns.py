import pandas as pd

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
SHEET = "INDICATORS_EN15804_A2_RAW"

# Add any columns your normalizer expects; include 'version'
REQUIRED = [
    "manufacturer","model","declared_unit","Wp_module","Wp_per_m2","area_m2",
    "year","PCR","programme_operator","dataset_uuid","version"
]

df = pd.read_excel(WB, sheet_name=SHEET)
for c in REQUIRED:
    if c not in df.columns:
        df[c] = pd.NA

with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
    df.to_excel(w, sheet_name=SHEET, index=False)

print("RAW sheet ensured with required columns:", REQUIRED)
