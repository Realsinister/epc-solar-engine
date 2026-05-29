#!/usr/bin/env python3
"""
pv_filter.py — Extract PV-module rows from INDICATORS_EN15804_A2_RAW using
both Excel fields and saved ÖKOBAUDAT JSON (data/oekobaudat_raw/*.json).
Writes a new sheet: PV_RAW
"""
import argparse, json, os, re
import pandas as pd

WORKBOOK = "EPD_Hub_V3_PV_starter_enriched.xlsx"
IN_SHEET = "INDICATORS_EN15804_A2_RAW"
OUT_SHEET = "PV_RAW"
JSON_DIR = "data/oekobaudat_raw"

PV_TOKENS = [
    "photovoltaic", "pv", "solar module", "pv module", "photovoltaikmodul",
    "solarmodul", "pv-modul", "pv panel", "photovoltaic panel", "panneau photovoltaïque",
    "panel fotovoltaico", "modulo fotovoltaico", "pannello fotovoltaico"
]

def text_hit(text: str) -> bool:
    if not text: return False
    t = text.lower()
    # require a bit more than bare "pv" to avoid false positives
    if any(tok in t for tok in ("photovoltaic", "solar module", "pv module", "photovoltaikmodul", "solarmodul", "pv-modul", "pv panel")):
        return True
    # allow "pv" if near module/panel
    if "pv" in t and any(k in t for k in ("module","panel","modul","panneau","pannello","modulo")):
        return True
    return False

def load_json(uuid: str, json_dir: str):
    if not isinstance(uuid, str) or not uuid: return {}
    p = os.path.join(json_dir, f"{uuid}.json")
    if not os.path.isfile(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def flatten_for_search(obj):
    """Collect strings from likely places to search for PV semantics."""
    bag = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                bag.extend(flatten_for_search(v))
            else:
                if isinstance(v, str):
                    bag.append(v)
    elif isinstance(obj, list):
        for it in obj:
            bag.extend(flatten_for_search(it))
    return " | ".join(bag)

def json_hit(jd: dict) -> bool:
    if not jd: return False
    blob = " ".join([
        flatten_for_search(jd.get("name")),
        flatten_for_search(jd.get("synonyms")),
        flatten_for_search(jd.get("classification")),
        flatten_for_search(jd.get("tags")),
        flatten_for_search(jd.get("generalComment")),
        flatten_for_search(jd.get("technology")),
        flatten_for_search(jd.get("product")),
        flatten_for_search(jd.get("LCIAResults")),
    ]).lower()
    return text_hit(blob)

def pick_reason(row, jd) -> str:
    reasons = []
    model = str(row.get("model") or "")
    manuf = str(row.get("manufacturer") or "")
    unit = str(row.get("declared_unit") or "")
    if text_hit(model): reasons.append("model")
    if text_hit(manuf): reasons.append("manufacturer")
    if text_hit(unit): reasons.append("declared_unit")
    if json_hit(jd): reasons.append("json")
    return ",".join(sorted(set(reasons))) or "none"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default=WORKBOOK)
    ap.add_argument("--in-sheet", default=IN_SHEET)
    ap.add_argument("--json-dir", default=JSON_DIR)
    ap.add_argument("--out-sheet", default=OUT_SHEET)
    ap.add_argument("--sample", type=int, default=0, help="Optional: save a CSV sample of first N PV rows")
    args = ap.parse_args()

    df = pd.read_excel(args.workbook, sheet_name=args.in_sheet)
    if df.empty:
        print("Input sheet is empty; nothing to filter.")
        return

    hits = []
    for _, r in df.iterrows():
        model = str(r.get("model") or "")
        manuf = str(r.get("manufacturer") or "")
        unit = str(r.get("declared_unit") or "")
        uuid = str(r.get("dataset_uuid") or "")

        # quick text heuristic first
        likely = text_hit(model) or text_hit(manuf) or text_hit(unit)

        # then JSON-backed check
        jd = load_json(uuid, args.json_dir)
        likely = likely or json_hit(jd)

        if likely:
            reason = pick_reason(r, jd)
            out = dict(r)
            out["pv_match_reason"] = reason
            hits.append(out)

    pv = pd.DataFrame(hits, columns=list(df.columns) + ["pv_match_reason"])
    with pd.ExcelWriter(args.workbook, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        pv.to_excel(w, sheet_name=args.out_sheet, index=False)

    print(f"✓ PV rows: {len(pv)} -> wrote sheet '{args.out_sheet}' in {args.workbook}")
    if args.sample and len(pv) > 0:
        pv.head(args.sample).to_csv("PV_sample.csv", index=False, encoding="utf-8")
        print("  sample -> PV_sample.csv")

if __name__ == "__main__":
    main()
