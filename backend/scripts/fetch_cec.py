import requests
import os
import urllib3

urllib3.disable_warnings()

url = "https://solarequipment.energy.ca.gov/Home/DownloadtoExcel?filename=PVModuleList"
output_file = "cec_modules.xlsx"

print("Downloading CEC dataset...")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

response = requests.get(url, headers=headers, verify=False)
if response.status_code == 200:
    with open(output_file, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded successfully! File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
else:
    print(f"Failed to download. Status code: {response.status_code}")
