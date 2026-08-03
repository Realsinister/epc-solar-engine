import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Tuple

INVERTER_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "inverter_database.parquet")

class InverterEngine:
    """
    Engine for Solar Inverter database lookup, Auto-Pairing, DC/AC clipping loss, 
    and Embodied Carbon ($GWP_{inverter}$) calculations.
    """

    @staticmethod
    def load_database() -> pd.DataFrame:
        if not os.path.exists(INVERTER_DB_PATH):
            return pd.DataFrame()
        return pd.read_parquet(INVERTER_DB_PATH)

    @staticmethod
    def auto_pair_inverter(project_size_mwp: float) -> Dict[str, Any]:
        """
        Auto-pairs the optimal inverter model based on plant scale.
        - Utility Scale (>= 20 MWp): Central or Ultra-High String Inverter
        - Commercial & Industrial (1 MWp - 20 MWp): High-Cap String Inverter
        - SME / Commercial (< 1 MWp): Standard String Inverter
        """
        df = InverterEngine.load_database()
        if df.empty:
            return {}

        if project_size_mwp >= 20.0:
            match = df[df['inverter_id'] == 'sungrow_sg350hx']
        elif project_size_mwp >= 1.0:
            match = df[df['inverter_id'] == 'huawei_sun2000_330']
        else:
            match = df[df['inverter_id'] == 'sma_sunny_150']

        if match.empty:
            return df.iloc[0].to_dict()
        return match.iloc[0].to_dict()

    @staticmethod
    def calculate_inverter_performance(
        inverter: Dict[str, Any], 
        target_dc_ac_ratio: float = 1.25
    ) -> Dict[str, Any]:
        """
        Calculates efficiency, DC/AC clipping losses, and inverter embodied carbon.
        """
        euro_eff = float(inverter.get('euro_efficiency_pct', 98.5)) / 100.0
        cec_eff = float(inverter.get('cec_efficiency_pct', 98.8)) / 100.0
        gwp_per_kw = float(inverter.get('gwp_per_kw_kgco2e', 35.0))
        price_per_kw = float(inverter.get('price_eur_kw', 40.0))

        # Clipping Loss Model: Empirically, for ILR > 1.30, losses scale non-linearly
        # ILR = DC Capacity / AC Capacity
        ilr = target_dc_ac_ratio
        if ilr > 1.30:
            clipping_loss_pct = (ilr - 1.30) * 8.5 # % loss of annual yield
        else:
            clipping_loss_pct = 0.0

        # Inverter carbon per kWp of DC capacity:
        # Since AC_capacity = DC_capacity / ILR, Inverter_kW = 1 / ILR
        gwp_inverter_per_kwp_kgco2e = gwp_per_kw / ilr
        price_inverter_per_wp_eur = (price_per_kw / 1000.0) / ilr

        return {
            'inverter_id': inverter.get('inverter_id'),
            'inverter_name': f"{inverter.get('manufacturer')} {inverter.get('model_name')}",
            'euro_efficiency': euro_eff,
            'cec_efficiency': cec_eff,
            'ilr_dc_ac_ratio': ilr,
            'clipping_loss_pct': clipping_loss_pct,
            'inverter_gwp_kgco2e_per_kwp': gwp_inverter_per_kwp_kgco2e,
            'inverter_capex_eur_per_wp': price_inverter_per_wp_eur,
            'lifespan_years': int(inverter.get('lifespan_years', 15))
        }
