import sqlite3
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path("data/pv_epd.db")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for Manufacturers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            country TEXT
        )
    ''')
    
    # Table for EPD Data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS epd_data (
            epd_id TEXT PRIMARY KEY,
            manufacturer_id INTEGER,
            module_name TEXT,
            power_wp REAL,
            efficiency_pct REAL,
            gwp_total_a1_a3 REAL,
            functional_unit TEXT,
            registration_number TEXT,
            issue_date TEXT,
            valid_until TEXT,
            FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_epds_as_dataframe() -> pd.DataFrame:
    conn = get_connection()
    query = '''
        SELECT 
            m.name as manufacturer,
            e.module_name as name,
            e.power_wp,
            e.efficiency_pct as Efficiency_Pct,
            e.gwp_total_a1_a3 as GWP_total_A1A3_per_kWp_kgCO2e,
            'Environdec API' as source,
            1.0 as Uncertainty_SD,
            e.epd_id
        FROM epd_data e
        JOIN manufacturers m ON e.manufacturer_id = m.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
