# clean_unrealistic_values.py
import pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW = "INDICATORS_EN15804_A2_RAW"

def main():
    if not Path(WB).exists(): 
        print("Workbook not found"); return
    df = pd.read_excel(WB, sheet_name=RAW)
    if "module_power_Wp" not in df.columns:
        print("No module_power_Wp in RAW"); return
    bad = (df["module_power_Wp"].fillna(0) > 0) & (df["module_power_Wp"].fillna(0) < 50)
    n = bad.sum()
    df.loc[bad, "module_power_Wp"] = pd.NA
    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=RAW, index=False)
    print(f"✓ Cleared {n} unrealistic Wp values (<50)")

if __name__ == "__main__":
    main()
