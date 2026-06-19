import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from api import load_data_from_parquet

try:
    df1 = load_data_from_parquet(project_size_mwp=0.5, ground_albedo=0.2)
    print(f"Albedo=0.2, Size < 1.0MW (power <= 450W): {len(df1)} rows")
    
    df2 = load_data_from_parquet(project_size_mwp=5.0, ground_albedo=0.2)
    print(f"Albedo=0.2, Size 5.0MW (no power filter): {len(df2)} rows")
    
    df3 = load_data_from_parquet(project_size_mwp=15.0, ground_albedo=0.2)
    print(f"Albedo=0.2, Size 15.0MW (power >= 400W): {len(df3)} rows")

except Exception as e:
    print(f"Error: {e}")
