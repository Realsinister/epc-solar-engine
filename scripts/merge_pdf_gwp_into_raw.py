"""
merge_pdf_gwp_into_raw.py

Merge GWP A1–A3 values from solar_database.csv into
INDICATORS_EN15804_A2_RAW of EPD_Hub_V3_PV_starter_enriched.xlsx.

Matching is done by module name (case- and whitespace-insensitive).
"""

from pathlib import Path
import pandas as pd

# ---------- CONFIG: adjust here if your filenames / column names differ ----------

BASE = Path(__file__).resolve().parent

XLSX_PATH = BASE / "EPD_Hub_V3_PV_starter_enriched.xlsx"   # change if needed
CSV_PATH  = BASE / "solar_database.csv"                    # your CSV with GWP values
OUT_PATH  = BASE / "EPD_Hub_V3_PV_starter_enriched_with_pdf_gwp.xlsx"

RAW_SHEET_NAME = "INDICATORS_EN15804_A2_RAW"

# These must match the column names in solar_database.csv
# If your CSV has different headers, change these three strings accordingly.
CSV_NAME_COL = "name"                      # e.g. 'name' or 'module_name' or 'product_name'
CSV_GWP_COL  = "GWP_total_A1A3_kgCO2e"     # e.g. 'GWP_total_A1A3_kgCO2e' (adjust to your header)
CSV_UNIT_COL = "declared_unit"             # e.g. 'unit' or 'declared_unit'

# These are the RAW sheet columns we update
RAW_GWP_COL  = "GWP_total_A1A3_per_DU_kgCO2e"
RAW_UNIT_COL = "declared_unit"

# ---------- helper ----------

def norm_name(s):
    """Normalize names: lowercase, collapse whitespace."""
    if pd.isna(s):
        return ""
    return " ".join(str(s).strip().lower().split())

# ---------- main ----------

def main():
    if not XLSX_PATH.exists():
        raise SystemExit(f"Excel file not found: {XLSX_PATH}")
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV file not found: {CSV_PATH}")

    print(f"Using Excel: {XLSX_PATH.name}")
    print(f"Using CSV   : {CSV_PATH.name}")

    # Load CSV
    df_csv = pd.read_csv(CSV_PATH)

    # Sanity check for required CSV columns
    for col in [CSV_NAME_COL, CSV_GWP_COL, CSV_UNIT_COL]:
        if col not in df_csv.columns:
            raise SystemExit(
                f"CSV column '{col}' not found. "
                f"Available columns: {list(df_csv.columns)}"
            )

    # Normalize names in CSV
    df_csv["name_key"] = df_csv[CSV_NAME_COL].map(norm_name)

    # Keep only rows with a numeric GWP
    df_csv = df_csv[~df_csv[CSV_GWP_COL].isna()].copy()

    print(f"Rows in CSV with non-null GWP: {len(df_csv)}")

    # Load RAW sheet
    df_raw = pd.read_excel(XLSX_PATH, sheet_name=RAW_SHEET_NAME)

    if "name" not in df_raw.columns:
        raise SystemExit(f"RAW sheet '{RAW_SHEET_NAME}' has no 'name' column.")

    # Normalize names in RAW
    df_raw["name_key"] = df_raw["name"].map(norm_name)

    # Ensure target columns exist
    if RAW_GWP_COL not in df_raw.columns:
        df_raw[RAW_GWP_COL] = pd.NA
    if RAW_UNIT_COL not in df_raw.columns:
        df_raw[RAW_UNIT_COL] = pd.NA

    # Build a mapping from name_key -> (gwp, unit)
    csv_map = {}
    for _, row in df_csv.iterrows():
        key = row["name_key"]
        gwp_val = row[CSV_GWP_COL]
        unit_val = row[CSV_UNIT_COL]
        if key and pd.notna(gwp_val):
            # if duplicate names exist, later rows overwrite earlier ones
            csv_map[key] = (gwp_val, unit_val)

    print(f"Unique name keys in CSV map: {len(csv_map)}")

    # Apply mapping to RAW
    updated = 0
    total = len(df_raw)
    for idx, row in df_raw.iterrows():
        key = row["name_key"]
        if not key:
            continue
        if key not in csv_map:
            continue

        gwp_val, unit_val = csv_map[key]

        # Only overwrite if value is missing or zero
        current = df_raw.at[idx, RAW_GWP_COL]
        should_update = False
        if pd.isna(current):
            should_update = True
        else:
            try:
                v = float(str(current).replace(",", "."))
                if v == 0.0:
                    should_update = True
            except Exception:
                should_update = True

        if should_update:
            df_raw.at[idx, RAW_GWP_COL] = gwp_val
            if pd.notna(unit_val) and str(unit_val).strip() != "":
                df_raw.at[idx, RAW_UNIT_COL] = unit_val
            updated += 1

    print(f"Total RAW rows           : {total}")
    print(f"Rows updated from CSV    : {updated}")

    # Drop helper column
    df_raw = df_raw.drop(columns=["name_key"])

    # Write new workbook: copy all sheets, replace RAW
    xls = pd.ExcelFile(XLSX_PATH)
    with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
        for sheet in xls.sheet_names:
            if sheet == RAW_SHEET_NAME:
                df_raw.to_excel(writer, sheet_name=sheet, index=False)
            else:
                pd.read_excel(XLSX_PATH, sheet_name=sheet).to_excel(
                    writer, sheet_name=sheet, index=False
                )

    print(f"\nWrote updated workbook to: {OUT_PATH.name}")
    print("Now use this file as your master for further steps.")

if __name__ == "__main__":
    main()
