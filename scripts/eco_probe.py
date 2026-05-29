import os, sys, requests, json, pathlib
BASE = os.getenv("ECO_BASE")
SEARCH = os.getenv("ECO_SEARCH_PATH")
GET = os.getenv("ECO_GET_PATH")
tok = os.getenv("ECO_BEARER_TOKEN")
cid, cs, tu = os.getenv("ECO_CLIENT_ID"), os.getenv("ECO_CLIENT_SECRET"), os.getenv("ECO_TOKEN_URL")

def bearer():
    if tok: return tok
    if cid and cs and tu:
        r = requests.post(tu, data={"grant_type":"client_credentials"}, auth=(cid, cs), timeout=40)
        r.raise_for_status()
        return r.json()["access_token"]
    raise SystemExit("No ECO_BEARER_TOKEN or client credentials set.")

def main():
    if not BASE or not SEARCH or not GET:
        raise SystemExit("Set ECO_BASE / ECO_SEARCH_PATH / ECO_GET_PATH.")

    b = bearer()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {b}", "Accept":"application/json"})
    u = f"{BASE}{SEARCH}"
    # 'q' vs 'term' fallback
    r = s.get(u, params={"q":"photovoltaic module","page":1,"pageSize":1}, timeout=40)
    if r.status_code == 400:
        r = s.get(u, params={"term":"photovoltaic module","page":1,"pageSize":1}, timeout=40)

    print("STATUS:", r.status_code)
    print("CTYPE:", r.headers.get("Content-Type"))
    body_path = pathlib.Path("data/last_response.txt")
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_text(r.text, encoding="utf-8")

    if "application/json" not in r.headers.get("Content-Type","").lower():
        print("Non-JSON body saved to", body_path)
        sys.exit(1)

    data = r.json()
    items = data.get("items") or data.get("results") or data.get("data") or []
    print("ITEMS:", len(items))
    if items:
        sample_id = (items[0].get("id") or items[0].get("uuid") or items[0].get("code"))
        print("SAMPLE_ID:", sample_id)
    else:
        print("No items for query—try broader terms or check permissions.")
if __name__ == "__main__":
    main()
