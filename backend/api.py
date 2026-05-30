import os
import sys
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file securely
load_dotenv()

# Add src to path so we can import our engine
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from pv_engine.engine import PVEngine
from pv_engine.financial_model import ExecutiveFinancialModel

app = FastAPI(title="EPC Solar Engine Premium API")

# Allow CORS for local development with Electron/Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to desktop app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for caching data
MASTER_DF = None

def load_data():
    global MASTER_DF
    if MASTER_DF is None:
        wb = os.path.join(os.path.dirname(__file__), "data", "EPD_Hub_V3_PV_master_curated_v1.xlsx")
        try:
            df = pd.read_excel(wb, sheet_name="INDICATORS_NORMALIZED")
            df = PVEngine.process_dataframe(df)
            MASTER_DF = PVEngine.validate_data(df)
        except Exception as e:
            print(f"Error loading master dataset: {e}")
            MASTER_DF = pd.DataFrame()
    return MASTER_DF

class CalculationRequest(BaseModel):
    base_irradiance: float
    ambient_temp_c: float
    lifetime: int
    avg_price_wp: float
    bos_cost_wp: float
    opex_annual: float
    cbam_tax_rate_eur_t: float
    eol_recycling_rate_pct: float
    transport_distance_km: float
    scenario: str
    project_size_mwp: float = 50.0
    ppa_rate_eur_mwh: float = 45.0
    discount_rate_pct: float = 5.0

@app.on_event("startup")
def startup_event():
    # Verify API key is loaded discreetly from .env
    api_key = os.getenv("ENVIRONDEC_API_KEY")
    if api_key:
        print("Environdec API Key loaded securely.")
    load_data()

@app.get("/")
def read_root():
    return {"status": "EPC Solar Engine Premium API is running"}

@app.get("/api/modules")
def get_modules():
    df = load_data()
    # Replace NaN with None for JSON serialization
    return df.replace({np.nan: None}).to_dict(orient="records")

@app.post("/api/calculate")
def calculate_leaderboard(request: CalculationRequest):
    df = load_data()
    if df.empty:
        raise HTTPException(status_code=500, detail="Database not loaded")

    df_calc = PVEngine.calculate_metrics(
        df, 
        base_irradiance=request.base_irradiance,
        ambient_temp_c=request.ambient_temp_c,
        lifetime=request.lifetime,
        avg_price_wp=request.avg_price_wp,
        bos_cost_wp=request.bos_cost_wp,
        opex_annual=request.opex_annual,
        cbam_tax_rate_eur_t=request.cbam_tax_rate_eur_t,
        eol_recycling_rate_pct=request.eol_recycling_rate_pct,
        transport_distance_km=request.transport_distance_km
    )

    df_calc, weights = PVEngine.normalize_scores(df_calc, request.scenario)
    df_calc = PVEngine.calculate_topsis(df_calc, request.scenario)

    top_panels = df_calc.head(50).replace({np.nan: None}).to_dict(orient="records")
    return {
        "weights": {"eco": weights[0], "cost": weights[1], "tech": weights[2]},
        "results": top_panels
    }

@app.post("/api/analyze/{dataset_uuid}")
def analyze_module(dataset_uuid: str, request: CalculationRequest):
    df = load_data()
    if df.empty:
        raise HTTPException(status_code=500, detail="Database not loaded")
        
    module_row = df[df['dataset_uuid'] == dataset_uuid]
    if module_row.empty:
        raise HTTPException(status_code=404, detail="Module not found")
        
    df_calc = PVEngine.calculate_metrics(
        module_row, 
        base_irradiance=request.base_irradiance,
        ambient_temp_c=request.ambient_temp_c,
        lifetime=request.lifetime,
        avg_price_wp=request.avg_price_wp,
        bos_cost_wp=request.bos_cost_wp,
        opex_annual=request.opex_annual,
        cbam_tax_rate_eur_t=request.cbam_tax_rate_eur_t,
        eol_recycling_rate_pct=request.eol_recycling_rate_pct,
        transport_distance_km=request.transport_distance_km
    )
    
    # We need the full dataframe to normalize scores properly against the dataset
    full_calc = PVEngine.calculate_metrics(
        df,
        base_irradiance=request.base_irradiance,
        ambient_temp_c=request.ambient_temp_c,
        lifetime=request.lifetime,
        avg_price_wp=request.avg_price_wp,
        bos_cost_wp=request.bos_cost_wp,
        opex_annual=request.opex_annual,
        cbam_tax_rate_eur_t=request.cbam_tax_rate_eur_t,
        eol_recycling_rate_pct=request.eol_recycling_rate_pct,
        transport_distance_km=request.transport_distance_km
    )
    full_calc, _ = PVEngine.normalize_scores(full_calc, request.scenario)
    
    module_scores = full_calc[full_calc['dataset_uuid'] == dataset_uuid].iloc[0]
    
    radar_data = [
        {"subject": "Eco (Low Carbon)", "A": module_scores.get('Score_Eco', 0) * 100, "fullMark": 100},
        {"subject": "Cost (Low LCOE)", "A": module_scores.get('Score_Cost', 0) * 100, "fullMark": 100},
        {"subject": "Tech (High Efficiency)", "A": module_scores.get('Score_Tech', 0) * 100, "fullMark": 100}
    ]
    
    # Run Sensitivity
    base_params = {
        'yield': request.base_irradiance,
        'ambient_temp_c': request.ambient_temp_c,
        'lifetime': request.lifetime,
        'avg_price_wp': request.avg_price_wp,
        'bos_cost_wp': request.bos_cost_wp,
        'opex_annual': request.opex_annual,
        'cbam_tax_rate_eur_t': request.cbam_tax_rate_eur_t,
        'eol_recycling_rate_pct': request.eol_recycling_rate_pct,
        'transport_distance_km': request.transport_distance_km
    }
    
    sens_df = PVEngine.run_sensitivity_analysis(module_row.iloc[0], base_params, variation=0.20)
    
    # Format sensitivity for Tornado chart
    # Recharts needs a format like { name: 'Parameter', Low: -0.5, High: +0.6 }
    carbon_sens = sens_df[sens_df['Metric'] == 'Carbon Intensity'].to_dict(orient="records")
    lcoe_sens = sens_df[sens_df['Metric'] == 'LCOE'].to_dict(orient="records")

    # Run Executive Financial Model
    # Pass the calculated module row (with 'Net_GWP_kgCO2e' etc)
    calc_row = df_calc.iloc[0].to_dict()
    exec_financials = ExecutiveFinancialModel.calculate_project_financials(
        module_row=calc_row,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct
    )

    return {
        "radar": radar_data,
        "sensitivity": {
            "carbon": carbon_sens,
            "lcoe": lcoe_sens
        },
        "executive": exec_financials
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
