import pandas as pd
import numpy as np
import uuid
import os

print("Loading CEC Database...")
df_raw = pd.read_excel('cec_modules.xlsx', header=16)

print(f"Loaded {len(df_raw)} raw rows.")

# 1. Clean Data
df = df_raw.dropna(subset=['Manufacturer', 'Model Number', 'Nameplate Pmax', 'A_c', 'Technology']).copy()

# 2. Map to EPC Solar Schema
print("Mapping to EPC schema...")
df['dataset_uuid'] = [str(uuid.uuid4()) for _ in range(len(df))]
df['manufacturer'] = df['Manufacturer'].astype(str)
df['name'] = df['Model Number'].astype(str)
df['Display_Name'] = df['manufacturer'] + " - " + df['name']
df['module_power_Wp'] = pd.to_numeric(df['Nameplate Pmax'], errors='coerce')
df['module_area_m2'] = pd.to_numeric(df['A_c'], errors='coerce')

# Drop invalid power/area
df = df.dropna(subset=['module_power_Wp', 'module_area_m2'])
df = df[df['module_area_m2'] > 0]

# Calculate Efficiency
df['Efficiency_Pct'] = (df['module_power_Wp'] / (df['module_area_m2'] * 1000)) * 100

# 3. Detect Bifaciality
print("Detecting Bifaciality...")
def is_bifacial(row):
    desc = str(row.get('Description', '')).lower()
    notes = str(row.get('Notes', '')).lower()
    tech = str(row.get('Technology', '')).lower()
    return any(x in desc or x in notes or x in tech for x in ['bifacial', 'glass-glass', 'dual glass'])

df['Is_Bifacial'] = df.apply(is_bifacial, axis=1)

# 4. LCA Proxy Engine (Predictive GWP)
print("Running LCA Proxy Engine...")
def calculate_proxy_gwp(row):
    # Base footprint assumption: 550 kgCO2e per kWp for a standard Mono-Si in standard grid
    base_gwp_per_kwp = 550.0 
    
    tech = str(row['Technology']).lower()
    if 'multi' in tech or 'poly' in tech:
        base_gwp_per_kwp -= 50 # Poly-Si is less energy intensive
    elif 'thin' in tech or 'cdte' in tech or 'cigs' in tech:
        base_gwp_per_kwp -= 150 # Thin film is significantly lower
    elif 'mono' in tech:
        base_gwp_per_kwp += 50 # High efficiency mono-PERC/TOPCon
        
    if row['Is_Bifacial']:
        base_gwp_per_kwp *= 1.15 # Glass-glass penalty (+15% weight)
        
    # GWP_total_A1A3_per_DU_kgCO2e (DU = 1 Wp)
    gwp_per_wp = base_gwp_per_kwp / 1000.0
    return gwp_per_wp

df['GWP_total_A1A3_per_DU_kgCO2e'] = df.apply(calculate_proxy_gwp, axis=1)
df['GWP_total_A1A3_per_kWp_kgCO2e'] = df['GWP_total_A1A3_per_DU_kgCO2e'] * 1000
df['GWP_total_A1A3_per_m2_kgCO2e'] = df['GWP_total_A1A3_per_DU_kgCO2e'] * df['module_power_Wp'] / df['module_area_m2']
df['GWP_total_A1A3_per_module_kgCO2e'] = df['GWP_total_A1A3_per_DU_kgCO2e'] * df['module_power_Wp']

# Default missing attributes
df['avg_price_wp'] = 0.18 # Market average generic
df['declared_unit'] = 'Wp'
df['source'] = 'Proxy (CEC Data)'
df['version'] = 1.0
df['Panel_Temp_Coef'] = -0.35 # Generic mono-crystalline temp coefficient
df['Warranty_Years'] = 25 # Generic industry standard
df['Weight_t_kWp'] = 0.055 # Approximate 55 kg per kWp
df['Annual_Degradation_Pct'] = 0.45 # Standard degradation


# Define Size Category for extreme fast filtering
def size_category(wp):
    if wp < 400: return 'Residential'
    if wp <= 500: return 'Commercial'
    return 'Utility'
df['Size_Category'] = df['module_power_Wp'].apply(size_category)

# Filter final columns
final_cols = [
    'dataset_uuid', 'name', 'manufacturer', 'declared_unit', 'module_power_Wp', 'module_area_m2',
    'GWP_total_A1A3_per_DU_kgCO2e', 'GWP_total_A1A3_per_kWp_kgCO2e', 'GWP_total_A1A3_per_m2_kgCO2e',
    'GWP_total_A1A3_per_module_kgCO2e', 'source', 'version', 'Display_Name', 'Efficiency_Pct',
    'avg_price_wp', 'Is_Bifacial', 'Size_Category', 'Panel_Temp_Coef', 'Warranty_Years', 'Weight_t_kWp', 'Annual_Degradation_Pct'
]
df_final = df[final_cols]

# 5. Export Partitioned Parquet
out_dir = os.path.join('backend', 'src', 'pv_engine', 'data', 'pv_database_v2.parquet')
print(f"Exporting {len(df_final)} rows to partitioned Parquet at {out_dir}...")
df_final.to_parquet(out_dir, partition_cols=['Is_Bifacial', 'Size_Category'], index=False)
print("Complete!")
