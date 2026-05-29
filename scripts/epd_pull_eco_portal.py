
#!/usr/bin/env python3
"""
epd_pull_eco_portal.py

Pull digital PV EPDs from ECO Platform (soda4LCA) and auto-fill INDICATORS_EN15804_A2_RAW
in your master Excel.

Usage:
  python epd_pull_eco_portal.py --token YOUR_TOKEN \
    --out pv_master.xlsx \
    --query "photovoltaic module" \
    --min-valid-until 2022 \
    --page-size 50

You can re-run this to append new rows. It will de-duplicate on (dataset_uuid, version).

Docs referenced:
- ECO Portal API Quickstart: https://data.eco-platform.org/static/doc/ECO_Portal_API_-_Quickstart_Guide.pdf
- soda4LCA REST API overview: https://bitbucket.org/okusche/soda4lca/src/7.x-branch/Doc/src/Service_API/Service_API.md
- EN 15804+A2 indicators (see programme guidance / IES GPI 5 and One Click LCA help articles)

Author: your_name
License: MIT
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

ECO_PORTAL_SEARCH = "https://data.eco-platform.org/resource/processes"
DEFAULT_TIMEOUT = 30

# ---- Indicator mapping helpers -------------------------------------------------
# Strategy:
# 1) Try to use human-readable indicator names in extended JSON (if present).
# 2) Fallback to UUID mapping (fill these as you learn the UUIDs used on nodes).
#
# Fill these dictionaries gradually; this script handles partial coverage gracefully.

# Normalize indicator display names (contains) -> canonical code & unit suffix
NAME_CONTAINS_TO_CANON = [
    # (substring lower, canonical code, canonical unit suffix, notes)
    ("gwp total",      "GWP_total",      "kgCO2e", "EN 15804+A2 total"),
    ("gwp fossil",     "GWP_fossil",     "kgCO2e", ""),
    ("gwp biogenic",   "GWP_biogenic",   "kgCO2e", ""),
    ("gwp luluc",      "GWP_luluc",      "kgCO2e", "land use & land-use change"),
    ("odp",            "ODP",            "kgCFC11e", ""),
    ("ap",             "AP",             "molH+e", ""),
    ("ep freshwater",  "EP_freshwater",  "kgPe", ""),
    ("ep marine",      "EP_marine",      "kgNe", ""),
    ("ep terrestrial", "EP_terrestrial", "molNe", ""),
    ("pocp",           "POCP",           "kgNMVOCe", ""),
    ("adp elements",   "ADP_mm",         "kgSbe", "minerals & metals"),
    ("adp fossil",     "ADP_fossil",     "MJ", ""),
    ("wdp",            "WDP",            "m3w.e.", "water deprivation (world eq)"),
    # resource use
    ("pere",           "PERE",           "MJ", ""),
    ("perm",           "PERM",           "MJ", ""),
    ("pert",           "PERT",           "MJ", ""),
    ("penre",          "PENRE",          "MJ", ""),
    ("penrm",          "PENRM",          "MJ", ""),
    ("penrt",          "PENRT",          "MJ", ""),
    ("sm",             "SM",             "kg", ""),
    ("rsf",            "RSF",            "MJ", ""),
    ("nrsf",           "NRSF",           "MJ", ""),
    ("fw",             "FW",             "m3", ""),
    # waste
    ("hwd",            "HWD",            "kg", ""),
    ("nhwd",           "NHWD",           "kg", ""),
    ("rwd",            "RWD",            "kg", ""),
    # output flows
    ("cru",            "CRU",            "kg", ""),
    ("mfr",            "MFR",            "kg", ""),
    ("mer",            "MER",            "kg", ""),
    ("eee",            "EEE",            "MJ", ""),
    ("eet",            "EET",            "MJ", ""),
]

# Fallback UUIDs for indicators (example/placeholder).
# Fill as needed if your node does not include readable indicator names.
UUID_TO_CANON = {
    # "fb774615-0575-45de-9a89-1ded92f19770": ("GWP_total", "kgCO2e"),  # example only
    # Add more as you encounter them...
}

# Legal EN 15804 modules we will parse (others are kept but less used)
VALID_MODULES = {
    "A1", "A2", "A3", "A1-A3", "A4", "A5",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7",
    "C1", "C2", "C3", "C4", "D"
}

@dataclass
class EPDRecord:
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    declared_unit: Optional[str] = None
    Wp_module: Optional[float] = None
    Wp_per_m2: Optional[float] = None
    area_m2: Optional[float] = None
    year: Optional[int] = None
    PCR: Optional[str] = None
    programme_operator: Optional[str] = None
    dataset_uuid: Optional[str] = None
    version: Optional[str] = None
    # dynamic indicator fields will be added in a dict
    indicators: Dict[str, float] = field(default_factory=dict)

def _lower(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def _canon_indicator(name: Optional[str], uuid: Optional[str]) -> Optional[Tuple[str, str]]:
    """Return (canonical_code, unit_suffix) if we can recognize the indicator."""
    n = _lower(name)
    if n:
        for sub, code, unit, _note in NAME_CONTAINS_TO_CANON:
            if sub in n:
                return (code, unit)
    if uuid and uuid in UUID_TO_CANON:
        return UUID_TO_CANON[uuid]
    return None

def _safe_get(d: dict, path: List[str]):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

class EcoPortalClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.headers.update({"Accept": "application/json"})

    def search_pv_processes(self, query: str, min_valid_until: int = 2022,
                            page_size: int = 100, max_pages: int = 50) -> List[dict]:
        """Search ECO Portal for candidate PV EPD processes. Returns list of entries with xlink:href."""
        results = []
        start_idx = 0
        pages = 0
        while pages < max_pages:
            params = {
                "search": "true",
                "distributed": "true",
                "virtual": "true",
                "metaDataOnly": "false",
                "validUntil": str(min_valid_until),
                "format": "JSON",
                "pageSize": str(page_size),
                "startIndex": str(start_idx),
                "name": query,
            }
            r = self.session.get(ECO_PORTAL_SEARCH, params=params, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 403:
                raise RuntimeError("Forbidden (403): check your ECO token.")
            r.raise_for_status()
            data = r.json()

            # soda4LCA list JSON can vary: try common keys
            items = []
            if isinstance(data, dict):
                # try keys like "processes", "items", "children"
                for k in ("processes", "items", "children"):
                    if k in data and isinstance(data[k], list):
                        items = data[k]
                        break
                if not items and "process" in data:
                    items = data["process"] if isinstance(data["process"], list) else [data["process"]]
            elif isinstance(data, list):
                items = data
            else:
                items = []

            if not items:
                break

            results.extend(items)

            # pagination: soda4LCA usually gives "total" / we compute our own offset
            got = len(items)
            if got < page_size:
                break
            start_idx += got
            pages += 1

        return results

    def fetch_extended_json(self, href: str) -> dict:
        """
        Follow the xlink:href to the node and request extended JSON.
        Example:
          https://epdnorway.lca-data.com/resource/processes/<uuid>?version=...&format=JSON&view=extended
        """
        # If href already has query, just add/override
        if "?" in href:
            url = href + "&format=JSON&view=extended"
        else:
            url = href + "?format=JSON&view=extended"
        r = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()

def parse_extended_process(proc_json: dict) -> EPDRecord:
    """Parse one process JSON (extended view) into EPDRecord + indicators dict."""
    rec = EPDRecord()
    # UUID, version
    rec.dataset_uuid = _safe_get(proc_json, ["@uuid"]) or _safe_get(proc_json, ["uuid"]) or _safe_get(proc_json, ["sapi:uuid"])
    rec.version = _safe_get(proc_json, ["@version"]) or _safe_get(proc_json, ["version"])

    # Try to get basic info
    # Manufacturer/Operator often under "modellingAndValidation" -> "dataGenerator" or "publication" -> "publisher"
    rec.manufacturer = (
        _safe_get(proc_json, ["publication", "publisher", "name", "#text"]) or
        _safe_get(proc_json, ["publication", "publisher", "name"]) or
        _safe_get(proc_json, ["processInformation", "referenceToPrimaryDataSet", "contact", "name"]) or
        _safe_get(proc_json, ["contact", "name"])
    )

    # Product name / model: often the "processName" or product flow name
    rec.model = (
        _safe_get(proc_json, ["name", "#text"]) or
        _safe_get(proc_json, ["name"]) or
        _safe_get(proc_json, ["processInformation", "dataSetInformation", "name", "baseName", "#text"])
    )

    # Declared unit: from product flow and resultingFlowAmount (extended JSON). Also unit name if available.
    # The reference exchange is often under "exchanges" with referenceToFlowDataSet and an attribute "isReferenceFlow"
    # Extended JSON usually provides "resultingFlowAmount" on the reference exchange.
    exchanges = _safe_get(proc_json, ["exchanges"]) or []
    if isinstance(exchanges, dict):
        exchanges = exchanges.get("exchange", [])
    ref_ex = None
    if isinstance(exchanges, list):
        for ex in exchanges:
            if ex.get("@isReferenceFlow") == "true" or ex.get("isReferenceFlow") is True:
                ref_ex = ex
                break
    if ref_ex is None and exchanges:
        ref_ex = exchanges[0]  # fallback: take first

    if isinstance(ref_ex, dict):
        rec.declared_unit = (
            _safe_get(ref_ex, ["resultingFlowUnit", "name"]) or
            _safe_get(ref_ex, ["referenceToFlowProperty", "common:shortDescription", "#text"]) or
            _safe_get(ref_ex, ["unit", "name"])
        )
        val = ref_ex.get("resultingFlowAmount") or ref_ex.get("meanAmount")
        try:
            declared_amount = float(val) if val is not None else None
        except Exception:
            declared_amount = None

        # Try to infer Wp or piece from names (heuristic)
        unit_name_lower = _lower(rec.declared_unit)
        if unit_name_lower in ("wp", "watt-peak", "wattpeak", "watt peak"):
            # keep Wp declared unit
            pass
        elif unit_name_lower in ("piece", "unit", "pcs", "module"):
            rec.declared_unit = "piece"
        # PV-specific: some nodes encode declared unit via product flow properties; keep flexible.

    # Dimensions & Wp/m2 may be embedded as material properties or in "other" sections; here we set placeholders.
    # You can extend this to parse MatML in product flow if present.
    rec.Wp_module = None
    rec.Wp_per_m2 = None
    rec.area_m2 = None

    # Year / PCR / Programme operator (best-effort)
    rec.year = None
    rec.PCR = _safe_get(proc_json, ["processInfo", "pcr", "name"]) or _safe_get(proc_json, ["pcr", "name"])
    rec.programme_operator = _safe_get(proc_json, ["publication", "publisher", "name"]) or rec.manufacturer

    # Parse LCIA results per module (A1, A2, A3, A1-A3, ...)
    # Extended JSON typically exposes an array "LCIAResults" with entries that include:
    # - "impactMethod" or "lciaMethod" (may be an object)
    # - "impactCategory" / "indicatorName"
    # - "module" (A1, A2, A1-A3, etc.)
    # - "result" value & unit
    lcia = _safe_get(proc_json, ["LCIAResults"]) or _safe_get(proc_json, ["lciaResults"]) or []
    # Soda4LCA JSON can be dict or list
    if isinstance(lcia, dict):
        lcia = lcia.get("LCIAResult", []) or lcia.get("lciaResult", [])
    if not isinstance(lcia, list):
        lcia = [lcia]

    for res in lcia:
        # Extract fields in a tolerant way
        module = res.get("module") or res.get("@module") or ""
        module = module if module in VALID_MODULES else module
        indicator_uuid = (
            _safe_get(res, ["referenceToLCIAMethod", "@refObjectId"]) or
            _safe_get(res, ["referenceToLCIAMethod", "refObjectId"]) or
            res.get("indicatorUUID")
        )
        indicator_name = (
            _safe_get(res, ["lciaMethod", "name"]) or
            _safe_get(res, ["impactCategory", "name"]) or
            res.get("indicatorName")
        )
        value = res.get("result") or _safe_get(res, ["meanValue"]) or res.get("value")
        unit = (
            _safe_get(res, ["unit", "name"]) or
            _safe_get(res, ["referenceToUnitGroup", "name"]) or
            res.get("unitName")
        )
        try:
            valf = float(value) if value is not None else None
        except Exception:
            valf = None
        if not module or valf is None:
            continue

        canon = _canon_indicator(indicator_name, indicator_uuid)
        if not canon:
            continue  # skip unknown indicators; you can expand mappings

        code, unit_sfx = canon
        # prefer canonical unit suffix if unit is compatible; otherwise keep unit text
        unit_out = unit_sfx or (unit or "unit")
        col = f"{code}_{module}_per_DU_{unit_out}"
        rec.indicators[col] = valf

    return rec

def records_to_dataframe(records: List[EPDRecord]) -> pd.DataFrame:
    base_cols = [
        "manufacturer", "model", "declared_unit", "Wp_module", "Wp_per_m2",
        "area_m2", "year", "PCR", "programme_operator", "dataset_uuid", "version"
    ]
    # Collect all indicator columns seen
    ind_cols = sorted({k for r in records for k in r.indicators.keys()})
    rows = []
    for r in records:
        row = {c: getattr(r, c) for c in base_cols}
        for k in ind_cols:
            row[k] = r.indicators.get(k)
        rows.append(row)
    return pd.DataFrame(rows, columns=base_cols + ind_cols)

def upsert_raw_sheet(xlsx_path: str, df_new: pd.DataFrame, sheet_name="INDICATORS_EN15804_A2_RAW") -> None:
    """Append new rows; de-duplicate by (dataset_uuid, version)."""
    try:
        existing = pd.read_excel(xlsx_path, sheet_name=sheet_name)
    except Exception:
        existing = pd.DataFrame()

    if not existing.empty:
        combined = pd.concat([existing, df_new], ignore_index=True)
    else:
        combined = df_new.copy()

    # Drop duplicates
    if "dataset_uuid" in combined.columns and "version" in combined.columns:
        combined = combined.drop_duplicates(subset=["dataset_uuid", "version"], keep="last")

    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        combined.to_excel(writer, sheet_name=sheet_name, index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True, help="Bearer token for ECO Portal API")
    ap.add_argument("--out", required=True, help="Path to your Excel (e.g., pv_master.xlsx)")
    ap.add_argument("--query", default="photovoltaic module", help="Search query for ECO Portal")
    ap.add_argument("--min-valid-until", type=int, default=2022, help="Filter by validUntil (>=)")
    ap.add_argument("--page-size", type=int, default=100, help="API page size")
    ap.add_argument("--max-pages", type=int, default=20, help="Max pages to fetch")
    args = ap.parse_args()

    client = EcoPortalClient(args.token)

    print(f"[eco] searching: '{args.query}' …")
    items = client.search_pv_processes(
        query=args.query,
        min_valid_until=args.min_valid_until,
        page_size=args.page_size,
        max_pages=args.max_pages,
    )
    print(f"[eco] candidates: {len(items)}")

    records: List[EPDRecord] = []
    seen_hrefs = set()

    for it in items:
        # Try to get the node link (xlink:href). JSON often encodes it under '@xlink:href' or 'xlink:href'
        href = None
        for k in ("@xlink:href", "xlink:href", "href", "link"):
            if isinstance(it, dict) and k in it:
                href = it[k]
                break
        # Some list responses place link in 'self' or 'sapi:href'
        if not href and isinstance(it, dict):
            href = it.get("self") or it.get("sapi:href")

        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        try:
            proc = client.fetch_extended_json(href)
        except requests.HTTPError as e:
            print(f"[warn] skip {href} HTTP {e.response.status_code}")
            continue
        except Exception as e:
            print(f"[warn] skip {href}: {e}")
            continue

        try:
            rec = parse_extended_process(proc)
        except Exception as e:
            print(f"[warn] parse failed for {href}: {e}")
            continue

        # Heuristic: keep only likely PV modules (model/name contains 'photovoltaic' or 'module' or 'PV')
        name_blob = " ".join([str(rec.model or ""), str(rec.manufacturer or "")]).lower()
        if not any(s in name_blob for s in ("photovoltaic", "pv module", "module", "pv-module", "pv panel")):
            # soft filter; you can relax this
            pass

        records.append(rec)

    if not records:
        print("[eco] no records parsed. Try adjusting --query or check token/permissions.")
        sys.exit(2)

    df = records_to_dataframe(records)
    print(f"[eco] parsed rows: {len(df)}; columns: {len(df.columns)}")

    upsert_raw_sheet(args.out, df, sheet_name="INDICATORS_EN15804_A2_RAW")
    print(f"[eco] wrote/updated sheet 'INDICATORS_EN15804_A2_RAW' in {args.out}")
    print("[ok] Next: use your normalization workbook logic to compute per-module/per-m²/per-kWp.")

if __name__ == "__main__":
    main()
