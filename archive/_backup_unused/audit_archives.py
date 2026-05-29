# audit_archives.py


import io, zipfile, re
from pathlib import Path


DIR = Path("data/eco_zip")

def norm(s): return re.sub(r"\s+"," ", (s or "").lower().replace("–","-"))

def main():
    if not DIR.exists():
        print("Missing data/eco_zip"); return
    zips = list(DIR.glob("*.zip"))
    print(f"files: {len(zips)}")
    hit = miss = notzip = 0
    for p in zips:
        b = p.read_bytes()
        if b[:4] != b"PK\x03\x04":
            notzip += 1
            t = norm(b.decode("utf-8","ignore"))
            has = any(k in t for k in ["gwp","climate change","global warming potential","a1-a3","a1–a3"])
            print(f"- {p.name}  (not zip)  keywords={'YES' if has else 'no'}  size={len(b)}")
            miss += (0 if has else 1); hit += (1 if has else 0)
            continue
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".xml")]
            k = False
            for n in names:
                t = norm(z.read(n).decode("utf-8","ignore"))
                if any(x in t for x in ["gwp","climate change","global warming potential","a1-a3","a1–a3"]):
                    k = True; break
            print(f"- {p.name}  xmls={len(names)}  keywords={'YES' if k else 'no'}")
            if k: hit += 1
            else: miss += 1
    print(f"summary: hit={hit} miss={miss} notzip={notzip}")
if __name__ == "__main__":
    main()
