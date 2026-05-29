import zipfile, io, re, argparse
from pathlib import Path

ZIP_DIR = Path("data/eco_zip")
KEYS = ["gwp", "climate change", "global warming potential", "a1-a3", "a1 – a3", "a1–a3", "a1", "a2", "a3", "kg co2"]

def norm(s):
    return re.sub(r"\s+"," ", (s or "").lower().replace("–","-"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uuid", required=True)
    ap.add_argument("--zip", default=None, help="Optional explicit path to zip")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    p = Path(args.zip) if args.zip else ZIP_DIR / f"{args.uuid}.zip"
    if not p.exists():
        print(f"File not found: {p}")
        return

    data = p.read_bytes()
    if data[:4] != b"PK\x03\x04":
        print("Not a zip; try --zip with an XML file path")
        return

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if not n.lower().endswith(".xml"):
                continue
            t = z.read(n).decode("utf-8", "ignore")
            tnorm = norm(t)
            flags = {k: ("YES" if k in tnorm else "no") for k in KEYS}
            print(f"--- {n} ---", " ".join(f"{k}:{flags[k]}" for k in KEYS))
            if args.show and any(v == "YES" for v in flags.values()):
                for k in KEYS:
                    i = tnorm.find(k)
                    if i != -1:
                        start = max(0, i - 200); end = min(len(t), i + 200)
                        print(t[start:end])
                        break

if __name__ == "__main__":
    main()
