import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from api import load_data_from_parquet, CalculationRequest
from src.pv_engine.engine import PVEngine

req = CalculationRequest(
    base_irradiance=1000,
    ambient_temp_c=25,
    lifetime=25,
    avg_price_wp=0.20,
    project_size_mwp=5.0,
    scenario="Utility Scale (Lowest LCOE)",
    cbam_tax_rate_eur_t=80,
    eol_recycling_rate_pct=85,
    system_topology="Fixed Tilt",
    ground_albedo=0.2
)

try:
    df = load_data_from_parquet(project_size_mwp=req.project_size_mwp, ground_albedo=req.ground_albedo)
    print(f"Loaded {len(df)} rows.")

    df_calc = PVEngine.calculate_metrics(
        df, 
        base_irradiance=req.base_irradiance,
        ambient_temp_c=req.ambient_temp_c,
        lifetime=req.lifetime,
        avg_price_wp=req.avg_price_wp,
        bos_cost_wp=req.bos_cost_wp,
        opex_annual=req.opex_annual,
        cbam_tax_rate_eur_t=req.cbam_tax_rate_eur_t,
        eol_recycling_rate_pct=req.eol_recycling_rate_pct,
        system_topology=req.system_topology,
        ground_albedo=req.ground_albedo,
        project_size_mwp=req.project_size_mwp
    )
    print("Metrics calculated successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
