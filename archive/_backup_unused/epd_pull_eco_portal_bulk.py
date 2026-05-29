# epd_pull_eco_portal_bulk.py
# Bulk wrapper around ECO Portal to fetch MANY PV module EPDs, save raw JSON,
# and upsert your INDICATORS_EN15804_A2_RAW sheet.

import argparse, os, time, json, math
import pandas as pd
import requests

SEARCH_URL = "https://data.eco-platform.org/resource/processes"
EXT_QS = "format=JSON&view=extended"
TIMEOUT = 30

# Broad PV search phrases (you can add more later)
DEFAULT_QUERIES = [
    "photovoltaic module", "pv module", "solar module", "photovoltaic panel", "pv panel",
    "photovoltaikmodul", "module photovoltaïque", "módulo fotovoltaico", "modulo fotovoltaico"
]

# Simple indicator name → canonical (extend over time)
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
VALID_MODULES = {"A1","A2","A3","A1-A3","A4","A5","B1","B2","B3","B4","B5","B6","B7","C1","C2","C3","C4","D"}

def canon_indicator(name: str):
    n = (name or "").strip().lower()
    for sub, canon in NAME_MAP:
        if sub in n:
            return canon
    return None

def ensure_dir(p): 
    os.makedirs(p, exist_ok=True)

def search(client, query, min_valid_until, page_size, max_pages):
    results = []
    start = 0
    pages = 0
    while pages < max_pages:
        params = {
            "search":"true","distributed":"true","virtual":"true","metaDataOnly":"false",
            "validUntil": str(min_valid_until),"format":"JSON","pageSize":str(page_size),
            "startIndex": str(start),"name": query
        }
        r = client.get(SEARCH_URL, params=params, timeout=TIMEOUT)
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "json" not in ctype:
            # write the unexpected body for inspection and fail clearly
            open("data/last_response.txt","wb").write(r.content)
            raise RuntimeError(
                f"Non-JSON response: status={r.status_code}, "
                f"content-type={ctype}. Body saved to data/last_response.txt"
            )
        data = r.json()
        items = []
        if isinstance(data, dict):
            for k in ("processes","items","children","process"):
                if k in data:
                    v = data[k]; items = v if isinstance(v, list) else [v]; break
        elif isinstance(data, list):
            items = data
        if not items: break
        results.extend(items)
        got = len(items)
        if got < page_size: break
        start += got; pages += 1
    return results



def fetch_extended(client, href):
    url = href + ("&" if "?" in href else "?") + EXT_QS
    r = client.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def parse_record(proc):
    rec = {
        "manufacturer": None, "model": None, "declared_unit": None,
        "Wp_module": None, "Wp_per_m2": None, "area_m2": None,
        "year": None, "PCR": None, "programme_operator": None,
        "dataset_uuid": None, "version": None
    }
    # ids
    rec["dataset_uuid"] = proc.get("@uuid") or proc.get("uuid") or proc.get("sapi:uuid")
    rec["version"] = proc.get("@version") or proc.get("version")

    # names
    rec["model"] = (proc.get("name", {}) if isinstance(proc.get("name"), dict) else proc.get("name"))
    pub = proc.get("publication", {})
    if isinstance(pub, dict):
        pub_name = pub.get("publisher", {})
        if isinstance(pub_name, dict):
            rec["programme_operator"] = pub_name.get("name") or rec["programme_operator"]
            rec["manufacturer"] = rec["manufacturer"] or pub_name.get("name")

    # reference exchange
    exchanges = proc.get("exchanges") or {}
    exlist = exchanges.get("exchange", []) if isinstance(exchanges, dict) else exchanges
    ref = None
    for ex in (exlist or []):
        if ex.get("@isReferenceFlow") == "true" or ex.get("isReferenceFlow") is True:
            ref = ex; break
    if not ref and exlist: ref = exlist[0]
    if isinstance(ref, dict):
        u = ref.get("resultingFlowUnit", {})
        rec["declared_unit"] = (u.get("name") if isinstance(u, dict) else u) or ref.get("unit",{}).get("name")

    # indicators
    out = {}
    lcia = proc.get("LCIAResults") or proc.get("lciaResults") or {}
    llist = lcia.get("LCIAResult", []) if isinstance(lcia, dict) else lcia
    if not isinstance(llist, list): llist = [llist]
    for res in llist:
        module = res.get("module") or res.get("@module") or ""
        if not module: continue
        ind_name = (res.get("indicatorName") or 
                    (res.get("impactCategory",{}) or {}).get("name") or 
                    (res.get("lciaMethod",{}) or {}).get("name"))
        if not ind_name:  # Skip if no indicator name found
            continue
        val = res.get("result") or res.get("meanValue") or res.get("value")
        try: valf = float(val)
        except: continue
        canon = canon_indicator(ind_name)
        if not canon: continue
        code, unit = canon
        col = f"{code}_{module}_per_DU_{unit}"
        out[col] = valf
    return rec, out

def upsert_raw(xlsx_path, rows):
    if not rows: return 0
    base_cols = ["manufacturer","model","declared_unit","Wp_module","Wp_per_m2","area_m2",
                 "year","PCR","programme_operator","dataset_uuid","version"]
    all_cols = set(base_cols)
    for _rec, ind in rows:
        all_cols |= set(ind.keys())
    cols = base_cols + sorted([c for c in all_cols if c not in base_cols])

    try:
        df_old = pd.read_excel(xlsx_path, sheet_name="INDICATORS_EN15804_A2_RAW")
    except Exception:
        df_old = pd.DataFrame(columns=cols)

    df_new = pd.DataFrame([{**r, **ind} for r, ind in rows], columns=cols)
    df = pd.concat([df_old, df_new], ignore_index=True)
    if "dataset_uuid" in df.columns and "version" in df.columns:
        df = df.drop_duplicates(subset=["dataset_uuid","version"], keep="last")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name="INDICATORS_EN15804_A2_RAW", index=False)
    return len(df_new)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--out", default="EPD_Hub_V3_PV_starter_enriched.xlsx")
    ap.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    ap.add_argument("--min-valid-until", type=int, default=2020)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--save-json", default="data/raw")  # raw cache
    args = ap.parse_args()

    os.makedirs(args.save_json, exist_ok=True)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {args.token}", "Accept":"application/json"})
    seen = set()
    rows = []

    for q in args.queries:
        print(f"[search] {q}")
        items = search(s, q, args.min_valid_until, args.page_size, args.max_pages)
        print(f"  -> {len(items)} items")
        for it in items:
            href = None
            for k in ("@xlink:href","xlink:href","href","self","sapi:href"):
                if isinstance(it, dict) and it.get(k):
                    href = it[k]; break
            if not href or href in seen: continue
            seen.add(href)
            try:
                proc = fetch_extended(s, href)
            except requests.HTTPError as e:
                print(f"  warn {e}")
                continue
            # save raw
            uid = proc.get("@uuid") or proc.get("uuid") or str(abs(hash(href)))
            with open(os.path.join(args.save_json, f"{uid}.json"), "w", encoding="utf-8") as f:
                json.dump(proc, f, ensure_ascii=False)

            # parse
            rec, ind = parse_record(proc)
            # coarse PV filter
            name_blob = f"{rec.get('model') or ''} {rec.get('manufacturer') or ''}".lower()
            if not any(s in name_blob for s in ("photovoltaic","pv module","module","pv panel","solar module","photovoltaikmodul")):
                pass  # keep loose; ECO metadata varies
            rows.append((rec, ind))
            time.sleep(args.sleep)

    added = upsert_raw(args.out, rows)
    print(f"[done] appended {added} rows to INDICATORS_EN15804_A2_RAW in {args.out}")

if __name__ == "__main__":
    main()
