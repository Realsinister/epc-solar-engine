# dump_one_process_xml.py
# Show the first 'process' XML inside a downloaded zip, for a given UUID.
from pathlib import Path
import argparse, io, zipfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uuid", required=True, help="dataset UUID (zip name without .zip)")
    args = ap.parse_args()

    zpath = Path("data/eco_zip") / f"{args.uuid}.zip"
    if not zpath.exists():
        print(f"Zip not found: {zpath}")
        return

    data = zpath.read_bytes()
    if data[:4] != b"PK\x03\x04":
        print("Not a zip (might be raw XML or HTML).")
        txt = data.decode("utf-8", "ignore")
        print(txt[:1200])
        return

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".xml")]
        # Prefer files with "process" in their name
        names.sort(key=lambda n: (0 if "process" in n.lower() else 1, len(n)))
        if not names:
            print("No XML files inside the zip.")
            return
        x = z.read(names[0]).decode("utf-8", "ignore")
        print(f"{names[0]} ::\n{x[:1200]}")

if __name__ == "__main__":
    main()
