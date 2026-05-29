import requests
import json
import logging
from typing import List, Dict, Any
from pv_engine.database import get_connection

logger = logging.getLogger(__name__)

class EnvirondecClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        # Example endpoint structure for EPD International (Environdec)
        self.base_url = "https://api.environdec.com/api/v1" 
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key if self.api_key else "",
            "Accept": "application/json"
        }

    def fetch_pv_epds(self, search_query: str = "photovoltaic module") -> List[Dict[Any, Any]]:
        """
        Fetches Photovoltaic EPDs. In a real environment, this hits the API.
        For now, it returns a mock response until the exact Environdec API token is loaded.
        """
        url = f"{self.base_url}/epds"
        params = {
            "search": search_query,
            "productCategory": "UN CPC 461" # UN CPC for electrical equipment/solar panels typically
        }
        
        try:
            logger.info(f"Fetching EPDs from {url}")
            # If token is configured, uncomment the actual API call
            # if self.api_key:
            #     response = requests.get(url, headers=self.headers, params=params)
            #     response.raise_for_status()
            #     return self._parse_environdec_response(response.json())
            
            return self._mock_epd_data()
        except Exception as e:
            logger.error(f"Error fetching from Environdec: {e}")
            return []

    def _parse_environdec_response(self, raw_data: dict) -> List[Dict[Any, Any]]:
        # Parsing logic for actual Environdec JSON
        # This will be refined once live API payload is inspected
        pass

    def _mock_epd_data(self) -> List[Dict[Any, Any]]:
        return [
            {
                "epd_id": "S-P-01111",
                "manufacturer": "Jinko Solar",
                "module_name": "Tiger Neo N-type 72HL4",
                "power_wp": 580,
                "efficiency_pct": 22.5,
                "gwp_total_a1_a3": 410.5, # kgCO2e/kWp
                "functional_unit": "1 kWp",
                "registration_number": "S-P-01111",
                "issue_date": "2024-01-15",
                "valid_until": "2029-01-14"
            },
            {
                "epd_id": "S-P-02222",
                "manufacturer": "Trina Solar",
                "module_name": "Vertex N",
                "power_wp": 600,
                "efficiency_pct": 22.6,
                "gwp_total_a1_a3": 395.0,
                "functional_unit": "1 kWp",
                "registration_number": "S-P-02222",
                "issue_date": "2024-05-20",
                "valid_until": "2029-05-19"
            },
            {
                "epd_id": "S-P-03333",
                "manufacturer": "First Solar",
                "module_name": "Series 7 (Thin Film)",
                "power_wp": 540,
                "efficiency_pct": 19.3,
                "gwp_total_a1_a3": 210.0, # Lower carbon for thin-film
                "functional_unit": "1 kWp",
                "registration_number": "S-P-03333",
                "issue_date": "2023-11-10",
                "valid_until": "2028-11-09"
            }
        ]

    def sync_to_db(self, epd_list: List[Dict[Any, Any]]):
        conn = get_connection()
        cursor = conn.cursor()
        
        for epd in epd_list:
            cursor.execute('''
                INSERT OR IGNORE INTO manufacturers (name) VALUES (?)
            ''', (epd['manufacturer'],))
            
            cursor.execute('SELECT id FROM manufacturers WHERE name = ?', (epd['manufacturer'],))
            mfg_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT OR REPLACE INTO epd_data 
                (epd_id, manufacturer_id, module_name, power_wp, efficiency_pct, gwp_total_a1_a3, functional_unit, registration_number, issue_date, valid_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                epd['epd_id'], mfg_id, epd['module_name'], epd['power_wp'], epd['efficiency_pct'],
                epd['gwp_total_a1_a3'], epd['functional_unit'], epd['registration_number'],
                epd['issue_date'], epd['valid_until']
            ))
            
        conn.commit()
        conn.close()
        logger.info(f"Synced {len(epd_list)} EPDs to local database.")
