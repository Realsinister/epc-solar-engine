#!/usr/bin/env python3
"""
scan_oekobaudat_for_pv.py
Sample each ÖKOBAUDAT datastock, inspect a limited number of processes,
and count PV-related matches inside the extended JSON.

Outputs a CSV 'oekobaudat_pv_scan.csv' and a console summary sorted by PV hits.
"""

import os, re, time, csv, sys
from typing import List, Dict, Optional, Tuple
import requests

BASE = "https://www.oekobaudat.de/OEKOBAU.DAT/resource"
TIMEOUT = 40

# PV tokens (extend if needed)
PV_TOKENS = [
    "photovoltaic", "pv module", "pv-modul", "pv panel",
    "solar module", "solarmodul", "photovoltaikmodul",
    "module photovoltaïque", "panneau photovoltaïque",
    "panel fotovoltaico", "modulo fotovoltaico", "pannello fotovoltaico"
]

def get_json(sess: requests.Session, url: str, params: dict = None) -> dict:
    r = sess.get(url, params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_datastocks(sess: requests.Session) -> List[dict]:
    data = get_json(sess, f"{BASE}/datastocks/", params={"format": "JSON"})
    items = []
    if isinstance(data, dict) and isinstance(data.get("dataStock"), list):
        items = data["dataStock"]
    elif isinstance(data, dict):
        for k in ("datastocks","items","children","datastock","data"):
            if k in data:
                v = data[k]
                items = v if isinstance(v, list) else [v]
                break
        if not items:
            items = [data]
    elif isinstance(data, list):
        items = data

    out = []
    for ds in items:
        if isinstance(ds, dict):
            uuid = ds.get("uuid") or ds.get("@uuid")
            short = ds.get("shortName") or ds.get("shortname") or ""
            name = ""
            nm = ds.get("name")
            if isinstance(nm, list) and nm:
                # prefer EN name if present
                val = next((n.get("value") for n in nm if (n.get("lang") or "").lower()=="en" and (n.get("value") or "").strip()), None)
                if not val:
                    val = next((n.get("value") for n in nm if (n.get("value") or "").strip()), "")
                name = val or ""
            elif isinstance(nm, dict):
                name = nm.get("value") or ""
            elif isinstance(nm, str):
                name = nm
            display = name or short or (uuid or "")
            if uuid:
                out.append({"uuid": uuid, "name": display, "shortName": short})
    return out

def list_processes(sess: requests.Session, ds_uuid: str, page_size: int, start_index: int) -> List[dict]:
    data = get_json(sess, f"{BASE}/datastocks/{ds_uuid}/processes/", params={
        "format": "JSON", "pageSize": str(page_size), "startIndex": str(start_index)
    })
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("data","processes","items","children","process"):
            if k in data:
                v = data[k]
                return v if isinstance(v, list) else [v]
        return [data]
    return []

def fetch_extended(sess: requests.Session, proc_uuid: str) -> dict:
    return get_json(sess, f"{BASE}/processes/{proc_uuid}", params={"format": "JSON", "view": "extended"})

def text_hit(text: str) -> bool:
    t = (text or "").lower()
    if any(tok in t for tok in PV_TOKENS):
        return True
    if "pv" in t and any(k in t for k in ("module","panel","modul","panneau","pannello","modulo")):
        return True
    return False

def flatten(obj) -> str:
    bag = []
    if isinstance(obj, dict):
        for _, v in obj.items():
            if isinstance(v, (dict, list)):
                bag.append(flatten(v))
            elif isinstance(v, str):
                bag.append(v)
    elif isinstance(obj, list):
        for it in obj:
            bag.append(flatten(it))
    return " ".join(bag)

def json_hit(jd: dict) -> bool:
    blob = " ".join([
        flatten(jd.get("name")),
        flatten(jd.get("synonyms")),
        flatten(jd.get("classification")),
        flatten(jd.get("tags")),
        flatten(jd.get("generalComment")),
        flatten(jd.get("technology")),
        flatten(jd.get("product")),
        flatten(jd.get("LCIAResults")),
    ]).lower()
    return text_hit(blob)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-pages", type=int, default=2, help="pages per datastock")
    ap.add_argument("--page-size", type=int, default=50, help="items per page")
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    s = requests.Session()
    s.headers.update({"Accept": "application/json"})

    stocks = list_datastocks(s)
    rows = []
    for ds in stocks:
        ds_uuid = ds["uuid"]
        ds_name = ds.get("name") or ds.get("shortName") or ds_uuid
        pv_hits = total = 0
        seen = set()

        for p in range(args.sample_pages):
            items = list_processes(s, ds_uuid, args.page_size, p*args.page_size)
            if not items:
                break
            for it in items:
                href = None
                if isinstance(it, dict):
                    for k in ("@xlink:href","xlink:href","href","self","sapi:href"):
                        if it.get(k):
                            href = it[k]; break
                puid = None
                if href:
                    m = re.search(r"/processes/([0-9a-f-]+)", href, flags=re.I)
                    if m: puid = m.group(1)
                if not puid and isinstance(it, dict):
                    puid = it.get("@uuid") or it.get("uuid")
                if not puid or puid in seen:
                    continue
                seen.add(puid)
                try:
                    jd = fetch_extended(s, puid)
                except Exception:
                    continue
                total += 1
                if json_hit(jd):
                    pv_hits += 1
                time.sleep(args.sleep)

        rows.append((ds_uuid, ds_name, total, pv_hits))
        print(f"[scan] {ds_name} ({ds_uuid}) -> sampled {total}, PV hits {pv_hits}")

    # Save CSV
    rows.sort(key=lambda x: x[3], reverse=True)
    with open("oekobaudat_pv_scan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["datastock_uuid","datastock_name","sampled","pv_hits"])
        w.writerows(rows)

    # Console summary
    print("\nTop datastocks by PV hits (sampled):")
    for r in rows[:12]:
        print(f"  {r[1]} ({r[0]})  sampled={r[2]}  pv_hits={r[3]}")

if __name__ == "__main__":
    main()
