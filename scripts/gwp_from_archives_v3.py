# gwp_from_archives_v3.py
# Extract GWP (Climate change) for A1–A3 from Environdec ILCD zips using XPath over EPD module results.
# Updates INDICATORS_EN15804_A2_RAW; treats "", whitespace, and 0.0 as missing.

from __future__ import annotations
import io, re, zipfile
from pathlib import Path
import pandas as pd
from lxml import etree

WB = "EPD_Hub_V3_PV_starter_enriched.xlsx"
RAW_SHEET = "INDICATORS_EN15804_A2_RAW"
ZIP_DIR = Path("data/eco_zip")

# Text heuristics (fallbacks)
GWP_KEYS = ["climate change","gwp","global warming potential","gwp-ghg","gwp total","gwp-total"]
A_COMB = ["a1-a3","a1 – a3","a1–a3","a1 to a3","modules a1-a3"]
A_SPLIT = ["a1","a2","a3"]

def norm(s: str) -> str:
    return re.sub(r"\s+"," ", (s or "").lower().replace("–","-").replace("\u00a0"," "))

def is_missing_number(x) -> bool:
    if x is None: return True
    s = str(x).strip()
    if s == "": return True
    try:
        v = float(s.replace(",", "."))
        return v == 0.0
    except:
        return True

def texts_from_zip(p: Path):
    b = p.read_bytes()
    if b[:4] != b"PK\x03\x04":
        # not a zip -> try direct XML/text
        try:
            yield b.decode("utf-8","ignore")
        except Exception:
            return
        return
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        for n in z.namelist():
            if n.lower().endswith(".xml"):
                yield z.read(n).decode("utf-8","ignore")

# ---------- EPD-aware XPath extractor ----------

def try_epd_xpath(root) -> tuple[float|None, str|None]:
    """
    Look for module 'A1-A3' (or split A1/A2/A3) and an indicator named 'Climate change' / 'GWP'.
    Return (value per declared unit in kg CO2e, declared_unit_guess) or (None, None).
    """
    # helper: case-insensitive contains(@name, 'x') using translate
    def ci_contains_name(x):
        return f"contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜÇÉÈÊÁÀÂÍÌÎÓÒÔÚÙÛ','abcdefghijklmnopqrstuvwxyzäöüçéèêáàâíìîóòôúùû'),'{x}')"

    # 1) Combined A1–A3 module block -> value element
    # Common structures:
    #   epd:module[@name='A1-A3']//epd:indicator[...]//epd:resultPerDeclaredUnit|epd:value|epd:meanValue
    # Use local-name() to avoid depending on exact epd namespace URI.
    xp_mod_comb = f"//*[local-name()='module' and ({' or '.join([ci_contains_name(x) for x in ['a1-a3','a1 – a3','a1–a3','a1 to a3']])})]"
    modules = root.xpath(xp_mod_comb)
    for m in modules:
        # find indicator nodes that look like climate change / gwp
        inds = m.xpath(".//*[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'climate change') or contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'gwp') or contains(translate(normalize-space(string(.)),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'climate change') or contains(translate(normalize-space(string(.)),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'global warming potential')]")
        for ind in inds:
            # candidate numeric holders under the indicator
            for xp in [
                ".//*[local-name()='resultPerDeclaredUnit']/text()",
                ".//*[local-name()='meanValue']/text()",
                ".//*[local-name()='result']/text()",
                ".//*[local-name()='value']/text()",
                "normalize-space(string(.))"  # last resort: text scrape
            ]:
                try:
                    s = ind.xpath(f"string({xp})") if "normalize-space" in xp else (ind.xpath(xp)[0] if ind.xpath(xp) else "")
                except Exception:
                    s = ""
                s = (s or "").strip()
                mnum = re.search(r"-?\d+(?:[.,]\d+)?", s)
                if mnum:
                    val = float(mnum.group(0).replace(",", "."))
                    du = guess_declared_unit(root) or guess_declared_unit_text(root) or None
                    return val, du

    # 2) Sum A1 + A2 + A3 (if combined is absent)
    vals = []
    for ak in ["a1","a2","a3"]:
        xp_mod = f"//*[local-name()='module' and {ci_contains_name(ak)}]"
        for m in root.xpath(xp_mod):
            inds = m.xpath(".//*[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'climate change') or contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'gwp') or contains(translate(normalize-space(string(.)),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'climate change') or contains(translate(normalize-space(string(.)),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'global warming potential')]")
            got = None
            for ind in inds:
                for xp in [
                    ".//*[local-name()='resultPerDeclaredUnit']/text()",
                    ".//*[local-name()='meanValue']/text()",
                    ".//*[local-name()='result']/text()",
                    ".//*[local-name()='value']/text()",
                    "normalize-space(string(.))"
                ]:
                    try:
                        s = ind.xpath(f"string({xp})") if "normalize-space" in xp else (ind.xpath(xp)[0] if ind.xpath(xp) else "")
                    except Exception:
                        s = ""
                    s = (s or "").strip()
                    mnum = re.search(r"-?\d+(?:[.,]\d+)?", s)
                    if mnum:
                        got = float(mnum.group(0).replace(",", "."))
                        break
                if got is not None: break
            if got is not None:
                vals.append(got)
    if vals:
        du = guess_declared_unit(root) or guess_declared_unit_text(root) or None
        return sum(vals), du

    return None, None

def guess_declared_unit(root) -> str|None:
    # Try common ILCD/EPD places where DU appears (piece/kWp/m2)
    try:
        du = root.xpath("string(//*[local-name()='quantitativeReference']//*[local-name()='unitGroup']/@name)")
        du = du.strip()
        if du: return du
    except Exception:
        pass
    try:
        du = root.xpath("string(//*[local-name()='referenceToReferenceFlow']/@unitName)")
        du = du.strip()
        if du: return du
    except Exception:
        pass
    return None

def guess_declared_unit_text(root) -> str|None:
    t = norm(etree.tostring(root, encoding="unicode", with_tail=False))
    if "kwp" in t: return "kWp"
    if "m2" in t or "m²" in t: return "m2"
    if "piece" in t or "module" in t: return "piece"
    return None

# ---------- Fallback: text heuristics if EPD blocks aren't present ----------

def extract_gwp_text(text: str):
    t = norm(text)
    if not any(k in t for k in GWP_KEYS): return None, None
    m = re.search(r"(?:gwp|climate change|global warming potential)\W{0,40}(?:a1-a3|a1 to a3|a1–a3)\W{0,30}(-?\d+(?:[.,]\d+)?)", t, re.I)
    if m: return float(m.group(1).replace(",", ".")), None
    vals = {}
    for mod in A_SPLIT:
        mm = re.search(r"(?:gwp|climate change|global warming potential)\W{0,40}"+mod+r"\W{0,20}(-?\d+(?:[.,]\d+)?)", t, re.I)
        if mm: vals[mod] = float(mm.group(1).replace(",", "."))
    if vals: return sum(vals.values()), None
    m = re.search(r"(?:gwp|climate change)[^0-9]{0,40}(-?\d+(?:[.,]\d+)?).{0,15}(?:co2|co₂)", t, re.I)
    if m: return float(m.group(1).replace(",", ".")), None
    return None, None

# ---------- Main ----------

def main():
    if not Path(WB).exists():
        raise SystemExit(f"{WB} not found.")
    try:
        df = pd.read_excel(WB, sheet_name=RAW_SHEET)
    except Exception:
        df = pd.DataFrame()

    if "dataset_uuid" not in df.columns:
        raise SystemExit("RAW sheet has no 'dataset_uuid' column.")

    # normalize types
    df["dataset_uuid"] = df["dataset_uuid"].astype(str).str.strip()
    idx = {str(df.at[i,"dataset_uuid"]): i for i in df.index}

    updated = 0
    hits = []

    for p in ZIP_DIR.glob("*.zip"):
        uid = p.stem

        gwp_val = None
        du_guess = None

        for text in texts_from_zip(p):
            # First: structured EPD extraction
            try:
                root = etree.fromstring(text.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
                gwp_val, du_guess = try_epd_xpath(root)
                if gwp_val is not None:
                    break
            except Exception:
                pass

            # Fallback: text heuristics
            gwp_val, du_guess2 = extract_gwp_text(text)
            if gwp_val is not None:
                du_guess = du_guess or du_guess2
                break

        if gwp_val is None:
            continue

        if uid in idx:
            i = idx[uid]
            col = "GWP_total_A1A3_per_DU_kgCO2e"
            cur = df.at[i, col] if col in df.columns else None
            if is_missing_number(cur):
                df.at[i, col] = gwp_val
                updated += 1
                hits.append(uid)
            # declared_unit: only fill if empty
            du_col = "declared_unit"
            if du_guess:
                cur_du = str(df.at[i, du_col]).strip() if du_col in df.columns and pd.notna(df.at[i, du_col]) else ""
                if cur_du == "":
                    df.at[i, du_col] = du_guess

    with pd.ExcelWriter(WB, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=RAW_SHEET, index=False)

    print(f"✓ Updated RAW with GWP A1–A3 for {updated} datasets")
    if hits:
        print("Updated UUIDs (first 10):", hits[:10])

if __name__ == "__main__":
    main()
