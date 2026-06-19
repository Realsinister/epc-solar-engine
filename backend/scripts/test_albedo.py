import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from api import load_data_from_parquet

try:
    df = load_data_from_parquet(project_size_mwp=0.5, ground_albedo=0.2)
    print(f"Loaded {len(df)} rows with albedo=0.2")
except Exception as e:
    import traceback
    traceback.print_exc()
