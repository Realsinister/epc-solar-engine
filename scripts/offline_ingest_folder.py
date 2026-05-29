#!/usr/bin/env python3
"""
offline_ingest_folder.py — Parse all ILCD(+EPD) XMLs in data/offline_samples/
and append to INDICATORS_EN15804_A2_RAW for demo purposes.
"""
import glob, os
from epd_common import parse_ilcd_epd, upsert_raw, ensure_dir

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
SRC = "data/offline_samples"

def main():
    ensure_dir(SRC)
    rows = []
    for p in glob.glob(os.path.join(SRC, "*.xml")):
        try:
            xml = open(p, "r", encoding="utf-8").read()
        except:
            continue
        rec, ind = parse_ilcd_epd(xml, programme_operator="OFFLINE_SAMPLE")
        rec["dataset_uuid"] = rec.get("dataset_uuid") or os.path.splitext(os.path.basename(p))[0]
        rows.append((rec, ind))
    added = upsert_raw(WB, rows)
    print(f"[offline] processed {len(rows)} files, appended {added} rows to RAW in {WB}")

if __name__ == "__main__":
    main()
