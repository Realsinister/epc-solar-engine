import requests
import json
import time

payload = {
    "base_irradiance": 1000,
    "ambient_temp_c": 25,
    "lifetime": 25,
    "avg_price_wp": 0.2,
    "project_size_mwp": 5.0,
    "scenario": "Utility Scale (Lowest LCOE)",
    "cbam_tax_rate_eur_t": 80,
    "eol_recycling_rate_pct": 85,
    "system_topology": "Fixed Tilt",
    "ground_albedo": 0.2
}

start = time.time()
response = requests.post("http://127.0.0.1:8000/api/calculate", json=payload)
end = time.time()

print(f"Status Code: {response.status_code}")
print(f"Time Taken: {end - start:.3f} seconds")

if response.status_code == 200:
    data = response.json()
    results = data.get("results", [])
    print(f"Returned {len(results)} top panels")
    if results:
        print(f"Top panel: {results[0].get('Display_Name')}")
else:
    print("Error:", response.text)
