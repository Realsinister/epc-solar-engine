#!/usr/bin/env python3
"""
Common helpers: indicator mapping, ILCD(+EPD) parser, Excel upsert.
"""
from __future__ import annotations
import os, re, json, math, xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Canonical indicators (extend as needed)
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
    ("pere",           ("PERE","MJ")), ("perm",("PERM","MJ")), ("pert",("PERT","MJ")),
    ("penre",          ("PENRE","MJ")),("penrm",("PENRM","MJ")),("penrt",("PENRT","MJ")),
    ("sm",             ("SM","kg")),   ("rsf",("RSF","MJ")),    ("nrsf",("NRSF","MJ")),
    ("fw",             ("FW","m3")),
    ("hwd",            ("HWD","kg")),  ("nhwd",("NHWD","kg")),  ("rwd",("RWD","kg")),
    ("cru",            ("CRU","kg")),  ("mfr",("MFR","kg")),    ("mer",("MER","kg")),
    ("eee",            ("EEE","MJ")),  ("eet",("EET","MJ")),
]

def canon_indicator(name: Optional[str]):
    n = (name or "").strip().lower()
    for sub, canon in NAME_MAP:
        if sub in n:
            return canon
    return None

def ensure_dir(p:str): os.makedirs(p, exist_ok=True)

def upsert_raw(xlsx_path: str, rows: List[Tuple[dict, Dict[str,float]]], sheet="INDICATORS_EN15804_A2_RAW") -> int:
    if not rows: return 0
    base_cols = ["manufacturer","model","declared_unit","Wp_module","Wp_per_m2","area_m2",
                 "year","PCR","programme_operator","dataset_uuid","version","source"]
    all_cols = set(base_cols)
    for r,ind in rows: all_cols |= set(ind.keys())
    cols = list(base_cols) + sorted([c for c in all_cols if c not in base_cols])
    try:
        df_old = pd.read_excel(xlsx_path, sheet_name=sheet)
    except Exception:
        df_old = pd.DataFrame(columns=cols)
    df_new = pd.DataFrame([{**r, **ind} for r,ind in rows], columns=cols)
    df = pd.concat([df_old, df_new], ignore_index=True)
    # de-dupe by (dataset_uuid, version, source) when present
    keep_cols = [c for c in ("dataset_uuid","version","source") if c in df.columns]
    if keep_cols:
        df = df.drop_duplicates(subset=keep_cols, keep="last")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=sheet, index=False)
    return len(df_new)

def parse_ilcd_epd(xml_text: str, programme_operator: str) -> Tuple[dict, Dict[str,float]]:
    """Best-effort ILCD(+EPD) parser: extract declared unit and LCIA results by module."""
    root = ET.fromstring(xml_text)

    def find_text(path_list):
        for p in path_list:
            el = root.find(p)
            if el is not None and (el.text or "").strip():
                return el.text.strip()
        return None

    rec = {
        "manufacturer": None, "model": None, "declared_unit": None,
        "Wp_module": None, "Wp_per_m2": None, "area_m2": None,
        "year": None, "PCR": None, "programme_operator": programme_operator,
        "dataset_uuid": None, "version": None, "source": programme_operator
    }

    # Typical ILCD name locations (varies by issuer)
    rec["model"] = find_text([
        ".//{*}name/{*}baseName",
        ".//{*}name/{*}name",
        ".//{*}dataSetInformation/{*}name/{*}baseName",
    ])

    # Declared unit – varies; try several hints
    rec["declared_unit"] = find_text([
        ".//{*}quantitativeReference/{*}referenceToReferenceFlow/{*}functionalUnit/{*}unitName",
        ".//{*}referenceToReferenceUnitGroup/{*}shortDescription",
        ".//{*}referenceToReferenceFlow/{*}shortDescription",
    ])

    indicators: Dict[str,float] = {}

    # Walk through any LCIA-like sections; look for indicator name + module + value
    for res in root.iter():
        tag = res.tag.lower()
        # quick gate: only look at nodes likely to hold a result
        if not any(k in tag for k in ("lcia", "result", "impact", "indicator", "module")):
            continue

        # try to read child fields
        iname = None
        module = None
        value  = None

        for child in list(res):
            ct = (getattr(child, "tag", "") or "").lower()
            txt = (child.text or "").strip() if child.text else None
            if not txt: continue
            if any(k in ct for k in ("indicatorname","indicator","impactcategory","impactname")):
                iname = txt
            elif "module" in ct:
                module = txt
            elif any(k in ct for k in ("meanvalue","result","value")):
                try: value = float(txt)
                except: pass

        if not (iname and module and isinstance(value, float)):
            continue

        canon = canon_indicator(iname)
        if not canon:
            continue
        code, unit = canon
        col = f"{code}_{module}_per_DU_{unit}"
        indicators[col] = value

    return rec, indicators
