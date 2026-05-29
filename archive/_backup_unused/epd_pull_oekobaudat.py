#!/usr/bin/env python3
"""
epd_pull_oekobaudat.py

Pull PV-related processes from ÖKOBAUDAT (public Soda4LCA node), parse EN 15804(+A2)
LCIA indicators per module, and upsert the RAW sheet in your Excel.

Usage (PowerShell):
  python .\epd_pull_oekobaudat.py --out EPD_Hub_V3_PV_starter_enriched.xlsx --page-size 50 --max-pages 2
  python .\epd_pull_oekobaudat.py --out EPD_Hub_V3_PV_starter_enriched.xlsx --page-size 200 --max-pages 200 --sleep 0.25
  python .\epd_pull_oekobaudat.py --datastock OBD_2024_II --out EPD_Hub_V3_PV_starter_enriched.xlsx

No auth required for read access.
"""
import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

BASE = "https://www.oekobaudat.de/OEKOBAU.DAT/resource"
TIMEOUT = 40

# Indicator mapping: substring of indicator name (lower) -> (canonical code, unit)
NAME_MAP = [
    ("gwp total",      ("GWP_total", "kgCO2e")),
    ("gwp fossil",     ("GWP_fossil","kgCO2e")),
    ("gwp biogenic",   ("GWP_biogenic","kgCO2e")),
    ("gwp luluc",      ("GWP_luluc","kgCO2e")),
    ("odp",            ("ODP","kgCFC11e")),
    ("ap",             ("AP","molH+e")),
    ("ep freshwater",  ("EP_freshwater","kgPe")),
    ("ep marine",      ("EP_marine","kgNe")),
    ("ep terrestrial", ("EP_terrestrial","molNe")),
    ("pocp",           ("POCP","kgNMVOCe")),
    ("adp elements",   ("ADP_mm","kgSbe")),
    ("adp fossil",     ("ADP_fossil","MJ")),
    ("wdp",            ("WDP","m3w.e.")),
    ("pere",           ("PERE","MJ")),  ("perm",("PERM","MJ")),  ("pert",("PERT","MJ")),
    ("penre",          ("PENRE","MJ")), ("penrm",("PENRM","MJ")),("penrt",("PENRT","MJ")),
    ("sm",             ("SM","kg")),    ("rsf",("RSF","MJ")),     ("nrsf",("NRSF","MJ")),
    ("fw",             ("FW","m3")),
    ("hwd",            ("HWD","kg")),   ("nhwd",("NHWD","kg")),   ("rwd",("RWD","kg")),
    ("cru",            ("CRU","kg")),   ("mfr",("MFR","kg")),     ("mer",("MER","kg")),
    ("eee",            ("EEE","MJ")),   ("eet",("EET","MJ")),
]

DEFAULT_QUERIES = [
    "photovoltaic module", "pv module", "solar module", "photovoltaic panel", "pv panel",
    "photovoltaikmodul", "solarmodul", "module photovoltaïque", "panneau photovoltaïque",
    "módulo fotovoltaico", "panel fotovoltaico", "modulo fotovoltaico", "pannello fotovoltaico"
]

def canon_indicator(name: Optional[str]):
    n = (name or "").strip().lower()
    for sub, canon in NAME_MAP:
        if sub in n:
            return canon
    return None

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def get_json(sess: requests.Session, url: str, params: dict = None) -> dict:
    """GET and ensure JSON; save unexpected response to data/last_response_oekobaudat.txt"""
    r = sess.get(url, params=params or {}, timeout=TIMEOUT)
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "json" not in ctype:
        ensure_dir("data")
        with open("data/last_response_oekobaudat.txt", "wb") as f:
            f.write(r.content)
        raise RuntimeError(
            f"Non-JSON from {url} (status={r.status_code}, content-type={ctype}). "
            f"Saved to data/last_response_oekobaudat.txt"
        )
    return r.json()

def list_datastocks(sess: requests.Session) -> List[dict]:
    """Return normalized datastocks: [{'uuid','name','shortName','root'}, ...]."""
    url = f"{BASE}/datastocks/"
    data = get_json(sess, url, params={"format": "JSON"})

    # Your probe showed {"dataStock":[{...}, ...]}
    items = []
    if isinstance(data, dict):
        if isinstance(data.get("dataStock"), list):
            items = data["dataStock"]
        else:
            # fallback variants
            for k in ("datastocks", "items", "children", "datastock", "data"):
                if k in data:
                    v = data[k]
                    items = v if isinstance(v, list) else [v]
                    break
            if not items:
                items = [data]
    elif isinstance(data, list):
        items = data

    norm = []
    for ds in items:
        if isinstance(ds, str):
            norm.append({"uuid": ds, "name": ds, "shortName": ds, "root": False})
            continue
        if not isinstance(ds, dict):
            continue
        uuid = ds.get("uuid") or ds.get("@uuid")
        short = ds.get("shortName") or ds.get("shortname") or ""
        # name can be a list of {value, lang}; prefer EN
        nm = ds.get("name")
        if isinstance(nm, list) and nm:
            val = next((n.get("value") for n in nm if (n.get("lang") or "").lower() == "en" and (n.get("value") or "").strip()), None)
            if not val:
                val = next((n.get("value") for n in nm if (n.get("value") or "").strip()), "")
            name = val or ""
        elif isinstance(nm, dict):
            name = nm.get("value") or ""
        elif isinstance(nm, str):
            name = nm
        else:
            name = ""
        display = name or short or (uuid or "")
        if uuid:
            norm.append({"uuid": uuid, "name": display, "shortName": short, "root": bool(ds.get("root"))})
    return norm

def pick_latest_datastock(items: List[dict], prefer_name_prefix: Optional[str] = "OBD_") -> dict:
    """Pick a recent-looking datastock by shortName/name heuristic (e.g., OBD_2025_I > OBD_2024_II)."""
    if not items:
        return {}

    def score(ds: dict):
        name = (ds.get("name") or "").strip()
        short = (ds.get("shortName") or "").strip()
        text = short or name

        # Extract year if present
        m_year = re.search(r"(20\d{2})", text)
        year = int(m_year.group(1)) if m_year else 0

        # Roman index I/II/III/IV
        m_rom = re.search(r"\b(I{1,4}|II|III|IV)\b", text)
        roman = (m_rom.group(1) if m_rom else "").upper()
        order = {"I": 1, "II": 2, "III": 3, "IV": 4}.get(roman, 0)

        pref = 1 if (prefer_name_prefix and text.startswith(prefer_name_prefix)) else 0
        root = 1 if ds.get("root") else 0
        return (pref, year, order, root, text)

    return sorted(items, key=score)[-1]

def list_processes_in_datastock(sess: requests.Session, ds_uuid: str,
                                query: Optional[str] = None,   # kept for signature, not used
                                compliance: Optional[str] = None,
                                page_size: int = 200,
                                start_index: int = 0) -> List[dict]:
    """Return a list of process stubs for a datastock page (no text search; just paging)."""
    url = f"{BASE}/datastocks/{ds_uuid}/processes/"
    params = {"format": "JSON", "pageSize": str(page_size), "startIndex": str(start_index)}
    if compliance:
        params["compliance"] = compliance

    data = get_json(sess, url, params=params)

    # Normalize common shapes
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("processes", "process", "items", "children", "data"):
            if k in data:
                v = data[k]
                return v if isinstance(v, list) else [v]
        # Fallback: some nodes return a dict that is already "one item"
        return [data]
    return []


def fetch_extended_process(sess: requests.Session, proc_uuid: str) -> dict:
    url = f"{BASE}/processes/{proc_uuid}"
    return get_json(sess, url, params={"format": "JSON", "view": "extended"})

def canon_indicator_from_res(res: dict) -> Optional[Tuple[str, str]]:
    ind_name = res.get("indicatorName") or (res.get("impactCategory", {}) or {}).get("name") or (res.get("lciaMethod", {}) or {}).get("name")
    canon = canon_indicator(ind_name)
    return canon

def parse_process(proc: dict) -> Tuple[dict, Dict[str, float]]:
    """Parse extended process JSON to (record, indicators dict)."""
    rec = {
        "manufacturer": None, "model": None, "declared_unit": None,
        "Wp_module": None, "Wp_per_m2": None, "area_m2": None,
        "year": None, "PCR": None, "programme_operator": None,
        "dataset_uuid": None, "version": None
    }
    rec["dataset_uuid"] = proc.get("@uuid") or proc.get("uuid") or proc.get("sapi:uuid")
    rec["version"] = proc.get("@version") or proc.get("version")

    name = proc.get("name")
    if isinstance(name, dict):
        rec["model"] = name.get("#text") or (name.get("baseName", {}) or {}).get("#text")
    else:
        rec["model"] = name

    pub = proc.get("publication") or {}
    if isinstance(pub, dict):
        pubr = pub.get("publisher") or {}
        if isinstance(pubr, dict):
            rec["programme_operator"] = pubr.get("name") or rec["programme_operator"]
            rec["manufacturer"] = rec["manufacturer"] or pubr.get("name")

    ex = proc.get("exchanges") or {}
    exlist = ex.get("exchange", []) if isinstance(ex, dict) else ex
    ref = None
    if isinstance(exlist, list):
        for e in exlist:
            if e.get("@isReferenceFlow") == "true" or e.get("isReferenceFlow") is True:
                ref = e
                break
        if ref is None and exlist:
            ref = exlist[0]
    if isinstance(ref, dict):
        unit = ref.get("resultingFlowUnit") or ref.get("unit")
        if isinstance(unit, dict):
            rec["declared_unit"] = unit.get("name") or rec["declared_unit"]
        elif isinstance(unit, str):
            rec["declared_unit"] = unit

    indicators: Dict[str, float] = {}
    lcia = proc.get("LCIAResults") or proc.get("lciaResults") or {}
    llist = lcia.get("LCIAResult", []) if isinstance(lcia, dict) else lcia
    if not isinstance(llist, list):
        llist = [llist]
    for res in llist:
        module = res.get("module") or res.get("@module") or ""
        if not module:
            continue
        val = res.get("result") or res.get("meanValue") or res.get("value")
        try:
            valf = float(val)
        except Exception:
            continue
        canon = canon_indicator_from_res(res)
        if not canon:
            continue
        code, unit = canon
        col = f"{code}_{module}_per_DU_{unit}"
        indicators[col] = valf
    return rec, indicators

def upsert_raw(xlsx_path: str, rows: List[Tuple[dict, Dict[str, float]]]) -> int:
    if not rows:
        return 0
    base_cols = ["manufacturer", "model", "declared_unit", "Wp_module", "Wp_per_m2", "area_m2",
                 "year", "PCR", "programme_operator", "dataset_uuid", "version"]
    all_cols = set(base_cols)
    for r, ind in rows:
        all_cols |= set(ind.keys())
    cols = base_cols + sorted([c for c in all_cols if c not in base_cols])
    try:
        df_old = pd.read_excel(xlsx_path, sheet_name="INDICATORS_EN15804_A2_RAW")
    except Exception:
        df_old = pd.DataFrame(columns=cols)
    df_new = pd.DataFrame([{**r, **ind} for r, ind in rows], columns=cols)
    df = pd.concat([df_old, df_new], ignore_index=True)
    if "dataset_uuid" in df.columns and "version" in df.columns:
        df = df.drop_duplicates(subset=["dataset_uuid", "version"], keep="last")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name="INDICATORS_EN15804_A2_RAW", index=False)
    return len(df_new)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="EPD_Hub_V3_PV_starter_enriched.xlsx", help="Path to master Excel")
    ap.add_argument("--datastock", default=None, help="Datastock UUID or name/shortName prefix (e.g., OBD_2025_I)")
    ap.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES, help="Search terms")
    ap.add_argument("--compliance", default=None, help="Optional compliance UUID to filter EN 15804 variants")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--save-json", default="data/oekobaudat_raw")
    args = ap.parse_args()

    os.makedirs(args.save_json, exist_ok=True)
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})

    # Datastock selection
    ds_items = list_datastocks(s)
    target_ds = None

    if args.datastock:
        # exact UUID
        for ds in ds_items:
            if ds.get("uuid") and ds["uuid"].strip().lower() == args.datastock.strip().lower():
                target_ds = ds
                break
        # by name/shortName prefix
        if not target_ds:
            pref = args.datastock.strip().lower()
            for ds in ds_items:
                nm = (ds.get("name") or "").strip().lower()
                sm = (ds.get("shortName") or "").strip().lower()
                if nm.startswith(pref) or sm.startswith(pref):
                    target_ds = ds
                    break

    if not target_ds:
        target_ds = pick_latest_datastock(ds_items)

    if not target_ds:
        print("No datastock found. Check connectivity or ÖKOBAUDAT availability.")
        sys.exit(2)

    ds_uuid = target_ds["uuid"]
    ds_name = target_ds.get("name") or target_ds.get("shortName") or ds_uuid
    print(f"[datastock] {ds_name} ({ds_uuid})")

        # 2) Harvest
    ensure_dir(args.save_json)
    seen = set()
    rows: List[Tuple[dict, Dict[str, float]]] = []
    total = 0

    start = 0
    pages = 0
    while pages < args.max_pages:
        try:
            items = list_processes_in_datastock(
                s, ds_uuid, compliance=args.compliance,
                page_size=args.page_size, start_index=start
            )
        except RuntimeError as e:
            print(f"  [warn] {e}")
            break
        if not items:
            break

        for it in items:
            href = None
            for k in ("@xlink:href","xlink:href","href","self","sapi:href"):
                if isinstance(it, dict) and it.get(k):
                    href = it[k]; break
            proc_uuid = None
            if href:
                m = re.search(r"/processes/([0-9a-f-]+)", href, flags=re.I)
                if m: proc_uuid = m.group(1)
            if not proc_uuid and isinstance(it, dict):
                proc_uuid = it.get("@uuid") or it.get("uuid")
            if not proc_uuid or proc_uuid in seen:
                continue
            seen.add(proc_uuid)

            try:
                proc = fetch_extended_process(s, proc_uuid)
            except RuntimeError as e:
                print(f"    [warn] {e}")
                continue

            with open(os.path.join(args.save_json, f"{proc_uuid}.json"), "w", encoding="utf-8") as f:
                json.dump(proc, f, ensure_ascii=False)

            rec, ind = parse_process(proc)

            # Loose PV filter AFTER we have full text (model/manufacturer)
            blob = f"{(rec.get('model') or '')} {(rec.get('manufacturer') or '')}".lower()
            if not any(t in blob for t in ("photovoltaic","pv module","pv-modul","pv panel","solar module","photovoltaikmodul","solarmodul")):
                # keep anyway, or uncomment next line to drop non-PV early
                # continue
                pass

            rows.append((rec, ind))
            total += 1

        got = len(items)
        if got < args.page_size:
            break
        start += got
        pages += 1
        if args.sleep:
            time.sleep(args.sleep)


    added = upsert_raw(args.out, rows)
    print(f"[done] scanned ~{total} processes, appended {added} rows to INDICATORS_EN15804_A2_RAW in {args.out}")
    print("  Next: python normalize_from_raw.py")

if __name__ == "__main__":
    main()
