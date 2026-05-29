from pathlib import Path
import pandas as pd

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW = "INDICATORS_EN15804_A2_RAW"
ZIP_DIR = Path("data/eco_zip")

df = pd.read_excel(WB, sheet_name=RAW, dtype=str)
raw_uuids = set(df.get("dataset_uuid", pd.Series(dtype=str)).dropna().str.strip())

zip_uuids = set(p.stem for p in ZIP_DIR.glob("*.zip"))

print("RAW UUIDs:", len(raw_uuids))
print("ZIP UUIDs:", len(zip_uuids))
print("In ZIP but not in RAW:", len(zip_uuids - raw_uuids))
print("In RAW but not in ZIP:", len(raw_uuids - zip_uuids))

# Show a few examples to debug
print("Examples ZIP-not-RAW:", list(zip_uuids - raw_uuids)[:5])
print("Examples RAW-not-ZIP:", list(raw_uuids - zip_uuids)[:5])
