import pandas as pd
import os

parquet_path = os.path.join("backend", "src", "pv_engine", "data", "pv_database_v2.parquet")
df = pd.read_parquet(parquet_path, filters=[('module_power_Wp', '<=', 450.0)])
print(f"Loaded {len(df)} rows with filter")
