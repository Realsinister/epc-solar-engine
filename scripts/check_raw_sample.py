# check_raw_sample.py
import pandas as pd
from pathlib import Path

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
SHEET = "INDICATORS_EN15804_A2_RAW"

if not Path(WB).exists():
    raise SystemExit(f"{WB} not found in current folder.")

try:
    df = pd.read_excel(WB, sheet_name=SHEET, dtype=str)
except Exception as e:
    raise SystemExit(f"Cannot read sheet '{SHEET}': {e}")

print("RAW rows:", len(df))
if "dataset_uuid" not in df.columns:
    print("Column 'dataset_uuid' is missing in RAW.")
else:
    uu = df["dataset_uuid"].dropna().astype(str).str.strip()
    print("non-empty UUIDs:", uu.shape[0])
    print("sample UUIDs:", uu.head(10).tolist())
