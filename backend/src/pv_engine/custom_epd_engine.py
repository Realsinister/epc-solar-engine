import pandas as pd
import numpy as np
import io
import json
import uuid
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

class CustomEPDEngine:
    """
    Decoupled engine for parsing, validating, and managing custom vendor EPD & datasheet imports (.csv, .xlsx).
    Ensures zero mutation of the baseline parquet database.
    """
    
    COLUMN_MAPPINGS = {
        'manufacturer': ['manufacturer', 'brand', 'make', 'company', 'vendor', 'supplier'],
        'name': ['name', 'model', 'model_name', 'module', 'type', 'part_number', 'model_number'],
        'module_power_Wp': ['module_power_wp', 'power', 'power_wp', 'pmax', 'wattage', 'watts', 'wattage_wp', 'wp', 'power_w'],
        'efficiency_pct': ['efficiency_pct', 'efficiency', 'eff', 'module_efficiency', 'eff_%', 'efficiency_%', 'eff_pct'],
        'carbon_intensity_mean': ['carbon_intensity_mean', 'carbon', 'lca_carbon', 'gwp', 'gwp_a1a3', 'carbon_gco2_kwh', 'co2_intensity', 'gwp_per_kwp'],
        'estimated_price_wp': ['estimated_price_wp', 'price_wp', 'price', 'cost_wp', 'price_per_wp', 'cost_per_wp', 'price_eur_wp', 'cost_eur_wp'],
        'temp_coeff_pmax': ['temp_coeff_pmax', 'temp_coef', 'temp_coefficient', 'gamma', 'pmax_temp_coef', 'pmax_temp_coefficient'],
        'bifaciality': ['bifaciality', 'bifacial_factor', 'bifaciality_factor']
    }

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "sim_history.db")
        else:
            self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initializes SQLite schema for storing user custom datasets."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_datasets (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    module_count INTEGER NOT NULL,
                    data_json TEXT NOT NULL
                )
            ''')
            conn.commit()

    @staticmethod
    def parse_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parses CSV or Excel bytes into a Pandas DataFrame."""
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            return pd.read_excel(io.BytesIO(file_bytes))
        elif file_ext == '.csv':
            # Try reading with standard comma delimiter, fallback to semicolon
            try:
                return pd.read_csv(io.BytesIO(file_bytes))
            except Exception:
                return pd.read_csv(io.BytesIO(file_bytes), sep=';')
        else:
            raise ValueError(f"Unsupported file format '{file_ext}'. Please upload a .csv or .xlsx file.")

    @classmethod
    def validate_and_normalize(cls, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Standardizes column headers and fills defaults for missing metrics.
        Returns (processed_df, warning_messages).
        """
        if df.empty:
            raise ValueError("Uploaded file is empty.")
            
        warnings = []
        df_norm = df.copy()
        
        # Lowercase and strip existing column names for matching
        original_cols = list(df_norm.columns)
        clean_col_map = {col: str(col).strip().lower().replace(' ', '_') for col in original_cols}
        df_norm.rename(columns=clean_col_map, inplace=True)
        
        mapped_df = pd.DataFrame()
        
        # Match columns against canonical names
        for canonical, aliases in cls.COLUMN_MAPPINGS.items():
            found_col = None
            for alias in aliases:
                if alias in df_norm.columns:
                    found_col = alias
                    break
            
            if found_col:
                mapped_df[canonical] = df_norm[found_col]
            else:
                # Assign intelligent default if missing
                if canonical == 'manufacturer':
                    mapped_df[canonical] = 'Custom Vendor'
                    warnings.append("Missing 'Manufacturer' column — defaulted to 'Custom Vendor'.")
                elif canonical == 'name':
                    mapped_df[canonical] = [f"Module-{i+1}" for i in range(len(df_norm))]
                    warnings.append("Missing 'Name' column — generated default module names.")
                elif canonical == 'module_power_Wp':
                    raise ValueError("Critical metric 'Power (Wp)' column not found in uploaded dataset.")
                elif canonical == 'efficiency_pct':
                    mapped_df[canonical] = 21.0
                    warnings.append("Missing 'Efficiency' column — defaulted to 21.0%.")
                elif canonical == 'carbon_intensity_mean':
                    mapped_df[canonical] = 550.0
                    warnings.append("Missing 'LCA Carbon Footprint' column — defaulted to baseline 550 gCO2e/kWh.")
                elif canonical == 'estimated_price_wp':
                    mapped_df[canonical] = 0.18
                    warnings.append("Missing 'Price/Wp' column — defaulted to €0.18/Wp.")
                elif canonical == 'temp_coeff_pmax':
                    mapped_df[canonical] = -0.35
                elif canonical == 'bifaciality':
                    mapped_df[canonical] = 0.70

        # Type conversion and bounds checking
        mapped_df['module_power_Wp'] = pd.to_numeric(mapped_df['module_power_Wp'], errors='coerce').fillna(500.0)
        mapped_df['efficiency_pct'] = pd.to_numeric(mapped_df['efficiency_pct'], errors='coerce').fillna(21.0)
        mapped_df['carbon_intensity_mean'] = pd.to_numeric(mapped_df['carbon_intensity_mean'], errors='coerce').fillna(550.0)
        mapped_df['estimated_price_wp'] = pd.to_numeric(mapped_df['estimated_price_wp'], errors='coerce').fillna(0.18)
        mapped_df['temp_coeff_pmax'] = pd.to_numeric(mapped_df['temp_coeff_pmax'], errors='coerce').fillna(-0.35)
        mapped_df['bifaciality'] = pd.to_numeric(mapped_df['bifaciality'], errors='coerce').fillna(0.70)
        
        # Enforce physical efficiency bounds (14.0% <= Efficiency <= 24.5%)
        mapped_df['efficiency_pct'] = mapped_df['efficiency_pct'].clip(lower=14.0, upper=24.5)
        
        # Generate dataset_uuid for engine tracking
        mapped_df['dataset_uuid'] = [f"custom-{uuid.uuid4().hex[:8]}" for _ in range(len(mapped_df))]
        mapped_df['dataset_type'] = 'custom'
        mapped_df['Display_Name'] = mapped_df['manufacturer'].astype(str) + " " + mapped_df['name'].astype(str)
        mapped_df['Panel_Temp_Coef'] = mapped_df['temp_coeff_pmax']
        mapped_df['Estimated_Price_Wp'] = mapped_df['estimated_price_wp']
        mapped_df['Carbon_Intensity_Mean'] = mapped_df['carbon_intensity_mean']
        mapped_df['GWP_total_A1A3_per_kWp_kgCO2e'] = mapped_df['carbon_intensity_mean']
        mapped_df['Efficiency_Pct'] = mapped_df['efficiency_pct']
        mapped_df['module_power_Wp'] = mapped_df['module_power_Wp']
        mapped_df['Weight_t_kWp'] = 0.05 # Default weight 50kg/kWp
        mapped_df['Is_Bifacial'] = mapped_df['bifaciality'] > 0
        mapped_df['Annual_Degradation_Pct'] = 0.50 # Standard default degradation 0.5%
        
        return mapped_df, list(set(warnings))

    def save_custom_dataset(self, filename: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Saves a normalized custom dataset to SQLite."""
        dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"
        records = df.to_dict(orient='records')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO custom_datasets (id, filename, timestamp, module_count, data_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (dataset_id, filename, timestamp, len(df), json.dumps(records)))
            conn.commit()
            
        return {
            "id": dataset_id,
            "filename": filename,
            "timestamp": timestamp,
            "module_count": len(df)
        }

    def get_custom_dataset(self, dataset_id: Any) -> pd.DataFrame:
        """Retrieves a custom dataset by ID."""
        if isinstance(dataset_id, dict):
            dataset_id = dataset_id.get('id', '')
        dataset_id = str(dataset_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data_json FROM custom_datasets WHERE id = ?', (dataset_id,))
            row = cursor.fetchone()
            if not row:
                return pd.DataFrame()
            records = json.loads(row[0])
            return pd.DataFrame(records)

    def list_custom_datasets(self) -> List[Dict[str, Any]]:
        """Lists metadata of all uploaded custom datasets."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, filename, timestamp, module_count FROM custom_datasets ORDER BY timestamp DESC')
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_custom_dataset(self, dataset_id: str) -> bool:
        """Deletes a custom dataset by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM custom_datasets WHERE id = ?', (dataset_id,))
            conn.commit()
            return cursor.rowcount > 0

# Singleton instance
custom_epd_engine = CustomEPDEngine()
