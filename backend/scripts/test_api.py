import requests
import time

url = "http://127.0.0.1:8000/api/calculate"
data = {
    "base_irradiance": 1000,
    "ambient_temp_c": 25,
    "lifetime": 25,
    "avg_price_wp": 0.20,
    "project_size_mwp": 0.5,
    "scenario": "Utility Scale (Lowest LCOE)"
}

start = time.time()
response = requests.post(url, json=data)
end = time.time()

print(f"Status Code: {response.status_code}")
print(f"Time Taken: {end - start:.3f} seconds")

if response.status_code == 200:
    res_data = response.json()
    print(f"Returned {len(res_data.get('results', []))} top panels")
    if res_data.get('results'):
        print(f"Top panel: {res_data['results'][0]['Display_Name']}")
else:
    print(response.text)
