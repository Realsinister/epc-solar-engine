import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any, List

class HistoryDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Store in the data directory by default
            db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "sim_history.db")
        else:
            self.db_path = db_path
        
        self.init_db()

    def init_db(self):
        """Initializes the database schema with privacy in mind."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Privacy measure: We deliberately avoid capturing user IPs, sessions, or PII.
            # We strictly log the non-sensitive technical parameters and mathematical outputs.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sim_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    project_size_mwp REAL NOT NULL,
                    location_or_yield TEXT NOT NULL,
                    winner_mfg TEXT,
                    winner_name TEXT,
                    winner_suitability REAL,
                    inputs_json TEXT NOT NULL,
                    results_json TEXT NOT NULL
                )
            ''')
            conn.commit()

    def log_simulation(self, request_data: Dict[str, Any], results_data: List[Dict[str, Any]], weights: Dict[str, float]) -> str:
        """Logs a simulation run to the database."""
        sim_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        scenario = request_data.get("scenario", "Unknown")
        project_size = request_data.get("project_size_mwp", 0.0)
        loc_yield = str(request_data.get("base_irradiance", "Unknown"))
        
        # Determine the winner from the results (assuming sorted by rank or passing the top one)
        if results_data and len(results_data) > 0:
            winner = results_data[0]
            winner_mfg = winner.get("manufacturer", "Unknown")
            winner_name = winner.get("name", "Unknown")
            winner_suitability = winner.get("Suitability_Index", 0.0)
        else:
            winner_mfg = None
            winner_name = None
            winner_suitability = None
            
        # Serialize payloads (anonymized/technical data only)
        inputs_json = json.dumps(request_data)
        
        # For storage efficiency and privacy, we only store the top 5 results in the log, not all 20,000+ modules
        results_subset = results_data[:5] if results_data else []
        results_json = json.dumps({
            "weights": weights,
            "top_modules": results_subset
        })

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sim_logs (
                    id, timestamp, scenario, project_size_mwp, location_or_yield,
                    winner_mfg, winner_name, winner_suitability, inputs_json, results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sim_id, timestamp, scenario, project_size, loc_yield,
                winner_mfg, winner_name, winner_suitability, inputs_json, results_json
            ))
            conn.commit()
            
        return sim_id

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves a summary of past simulations."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Select everything except the massive JSON blobs for the summary view
            cursor.execute('''
                SELECT id, timestamp, scenario, project_size_mwp, location_or_yield,
                       winner_mfg, winner_name, winner_suitability, inputs_json, results_json
                FROM sim_logs
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                data = dict(row)
                data["inputs"] = json.loads(data["inputs_json"])
                data["results"] = json.loads(data["results_json"])
                del data["inputs_json"]
                del data["results_json"]
                history.append(data)
                
            return history

    def get_simulation(self, sim_id: str) -> Dict[str, Any]:
        """Retrieves the full details of a specific simulation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sim_logs WHERE id = ?', (sim_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            data = dict(row)
            data["inputs"] = json.loads(data["inputs_json"])
            data["results"] = json.loads(data["results_json"])
            del data["inputs_json"]
            del data["results_json"]
            
            return data

# Singleton instance
history_db = HistoryDatabase()
