import pandas as pd
import numpy as np
from typing import Dict, Any

class BOSEngine:
    """
    Engine for Balance of System (BOS) modeling: Racking/Trackers, Cabling, 
    Step-up Transformers, and System Topologies.
    """

    PRESETS = {
        "Fixed Tilt": {
            "topology": "Fixed Tilt Ground Mount",
            "racking_gwp_kgco2e_per_kwp": 140.0,
            "racking_cost_eur_per_wp": 0.08,
            "bos_electrical_efficiency": 0.982, # 1.8% combined DC/AC wiring & trans losses
            "bos_electrical_gwp_kgco2e_per_kwp": 45.0,
            "yield_multiplier": 1.00
        },
        "Single-Axis Tracker": {
            "topology": "Single-Axis Tracker",
            "racking_gwp_kgco2e_per_kwp": 210.0, # Motorized steel & slewing drives
            "racking_cost_eur_per_wp": 0.14,
            "bos_electrical_efficiency": 0.980, # 2.0% wiring/trans losses
            "bos_electrical_gwp_kgco2e_per_kwp": 50.0,
            "yield_multiplier": 1.15 # +15% annual yield boost from tracking
        },
        "Rooftop Ballasted": {
            "topology": "Commercial Rooftop Ballasted",
            "racking_gwp_kgco2e_per_kwp": 110.0, # Lightweight aluminum & ballast blocks
            "racking_cost_eur_per_wp": 0.10,
            "bos_electrical_efficiency": 0.978, # 2.2% wiring losses
            "bos_electrical_gwp_kgco2e_per_kwp": 35.0,
            "yield_multiplier": 0.98
        }
    }

    @staticmethod
    def get_bos_performance(system_topology: str = "Fixed Tilt") -> Dict[str, Any]:
        """
        Retrieves the BOS carbon, cost, and efficiency specs based on system topology.
        """
        preset = BOSEngine.PRESETS.get(system_topology, BOSEngine.PRESETS["Fixed Tilt"])
        
        total_bos_gwp = preset["racking_gwp_kgco2e_per_kwp"] + preset["bos_electrical_gwp_kgco2e_per_kwp"]
        total_bos_capex = preset["racking_cost_eur_per_wp"]

        return {
            "topology": preset["topology"],
            "racking_gwp_kgco2e_per_kwp": preset["racking_gwp_kgco2e_per_kwp"],
            "electrical_gwp_kgco2e_per_kwp": preset["bos_electrical_gwp_kgco2e_per_kwp"],
            "total_bos_gwp_kgco2e_per_kwp": total_bos_gwp,
            "total_bos_capex_eur_per_wp": total_bos_capex,
            "bos_electrical_efficiency": preset["bos_electrical_efficiency"],
            "yield_multiplier": preset["yield_multiplier"]
        }
