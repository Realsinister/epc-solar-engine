# dedupe_ilcd_excel.py
# Removes duplicate rows by dataset_uuid from ILCD_XML and INDICATORS_EN15804_A2_RAW.

import pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
XML_SHEET = "ILCD_XML"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")

    # Read sheets (if missing, create empty frames)
    try:
        df_xml = pd.read_excel(WB, sheet_name=XML_SHEET, dtype=str)
    except Exception:
        df_xml = pd.DataFrame(columns=["dataset_uuid","href","xml"])

    try:
        df_raw = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df_raw = pd.DataFrame()

    # Normalize keys
    if "dataset_uuid" not in df_xml.columns:
        df_xml["dataset_uuid"] = None
    if "dataset_uuid" not in df_raw.columns:
        df_raw["dataset_uuid"] = None

    # Drop dups keeping the first occurrence
    before_xml = len(df_xml)
    before_raw = len(df_raw)
    df_xml = df_xml.drop_duplicates(subset=["dataset_uuid"], keep="first")
    df_raw = df_raw.drop_duplicates(subset=["dataset_uuid"], keep="first")

    # Write back
    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df_xml.to_excel(w, sheet_name=XML_SHEET, index=False)
        df_raw.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ ILCD_XML: {before_xml} → {len(df_xml)} (removed {before_xml - len(df_xml)})")
    print(f"✓ RAW     : {before_raw} → {len(df_raw)} (removed {before_raw - len(df_raw)})")

if __name__ == "__main__":
    main()
