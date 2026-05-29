from pydantic import BaseModel, Field
from typing import Dict

class ProjectDefaults(BaseModel):
    """
    Default technical and economic constants for the PV Engine.
    """
    irradiance_kwh_kwp_yr: float = 1000.0
    lifetime_years: int = 30
    temp_loss_pct: float = 10.0
    
    avg_price_wp_eur: float = 0.22
    bos_cost_wp_eur: float = 0.45
    opex_annual_eur_kwp: float = 15.0

class LocationPreset(BaseModel):
    yield_kwh: float
    temp_loss: float
    grid_mix: float # gCO2e/kWh

LOCATION_PRESETS: Dict[str, LocationPreset] = {
    "🇩🇪 Germany (Berlin)": LocationPreset(yield_kwh=1050, temp_loss=5.0, grid_mix=380),
    "🇪🇸 Spain (Seville)": LocationPreset(yield_kwh=1750, temp_loss=14.0, grid_mix=190),
    "🇺🇸 USA (Arizona)": LocationPreset(yield_kwh=1900, temp_loss=16.0, grid_mix=350),
    "🇨🇳 China (Shanghai)": LocationPreset(yield_kwh=1100, temp_loss=8.0, grid_mix=550),
    "🇸🇪 Sweden (Stockholm)": LocationPreset(yield_kwh=950, temp_loss=2.0, grid_mix=40),
}
