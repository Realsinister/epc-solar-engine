import os, json, pandas as pd
WB   = "EPD_Hub_V3_PV_starter_enriched.xlsx"
SHEET= "PV_SCORED"

df = pd.read_excel(WB, sheet_name=SHEET)
gwp_cols = [c for c in df.columns if ("GWP_total" in c and "per_kWp" in c)]
GWP = gwp_cols[0]

keep = ["manufacturer","model","declared_unit","dataset_uuid","version",
        GWP, "score_gwp_kWp_0to100"]
df = df[keep].dropna(subset=[GWP])

os.makedirs("web_public", exist_ok=True)
with open("web_public/pv_catalog.json","w",encoding="utf-8") as f:
    json.dump(df.to_dict(orient="records"), f, ensure_ascii=False)
print("web_public/pv_catalog.json written:", len(df))