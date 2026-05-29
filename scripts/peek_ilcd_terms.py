# peek_ilcd_terms.py
import pandas as pd, re
from pathlib import Path
WB="EPD_Hub_V3_PV_starter_enriched.xlsx"
df=pd.read_excel(WB, sheet_name="ILCD_XML", dtype=str)
for i,row in df.head(5).iterrows():
    xml=row.get("xml") or ""
    t=re.sub(r"\s+"," ",xml)[:4000]
    print(f"--- {i} ---")
    for key in ["GWP","Climate change","A1-A3","A1 – A3","A1","A2","A3","kg CO2"]:
        print(key, ("YES" if key.lower() in t.lower() else "no"))
