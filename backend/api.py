import os
import sys
import io
import pandas as pd
import numpy as np
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file securely
load_dotenv()

# Add src to path so we can import our engine
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from pv_engine.engine import PVEngine
from pv_engine.financial_model import ExecutiveFinancialModel
from pv_engine.history import history_db
from pv_engine.inverter_engine import InverterEngine
from pv_engine.bos_engine import BOSEngine
from pv_engine.report_gen import ReportGenerator
from pv_engine.custom_epd_engine import custom_epd_engine
from pv_engine.block_optimizer import BlockOptimizer

app = FastAPI(title="EPC Solar Engine Premium API")

# Allow CORS for local development with Electron/Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to desktop app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to get base path for PyInstaller bundle vs local development
def get_base_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(__file__)

# Serve compiled React frontend dist folder statically if present
base_dir = get_base_dir()
possible_dist_paths = [
    os.path.join(base_dir, "frontend", "dist"),
    os.path.join(base_dir, "..", "frontend", "dist"),
    os.path.join(base_dir, "dist")
]

frontend_dist_path = None
for p in possible_dist_paths:
    if os.path.exists(p) and os.path.isdir(p):
        frontend_dist_path = p
        break

if frontend_dist_path:
    assets_path = os.path.join(frontend_dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="static_assets")
    app.mount("/static_app", StaticFiles(directory=frontend_dist_path, html=True), name="static_app")

def load_data_from_parquet(project_size_mwp: float = None, ground_albedo: float = None, custom_dataset_id: str = None):
    # If custom dataset requested, fetch custom modules from SQLite
    if custom_dataset_id and custom_dataset_id != "baseline":
        custom_df = custom_epd_engine.get_custom_dataset(custom_dataset_id)
        if not custom_df.empty:
            return custom_df

    possible_parquet_paths = [
        os.path.join(get_base_dir(), "src", "pv_engine", "data", "pv_database_v2.parquet"),
        os.path.join(os.path.dirname(__file__), "src", "pv_engine", "data", "pv_database_v2.parquet")
    ]
    parquet_path = possible_parquet_paths[0]
    for pp in possible_parquet_paths:
        if os.path.exists(pp):
            parquet_path = pp
            break
    
    filters = []
    
    # 1. Albedo / Bifaciality Filter (Instant physical exclusion)
    if ground_albedo is not None:
         filters.append(('Is_Bifacial', '==', 'true'))
         
    # 2. Project Size Filter (SME vs Utility)
    if project_size_mwp is not None:
        if project_size_mwp < 1.0: # SME / Commercial
            filters.append(('module_power_Wp', '<=', 450.0))
        elif project_size_mwp > 10.0: # Utility Scale
            filters.append(('module_power_Wp', '>=', 400.0))

    if not filters:
        filters = None
        
    try:
        # PyArrow Predicate Pushdown: Only loads the rows that match the filters!
        df = pd.read_parquet(parquet_path, filters=filters)
        if not df.empty:
            df = PVEngine.process_dataframe(df)
        return df
    except Exception as e:
        print(f"Error loading parquet dataset: {e}")
        return pd.DataFrame()

class CalculationRequest(BaseModel):
    base_irradiance: float
    ambient_temp_c: float
    lifetime: int
    avg_price_wp: float
    bos_cost_wp: float = 0.45
    opex_annual: float = 15.0
    cbam_tax_rate_eur_t: float = 80.0
    eol_recycling_rate_pct: float = 85.0
    system_topology: str = "Fixed Tilt"
    ground_albedo: Optional[float] = None
    scenario: str = "Eco-Flagship (Minimize Carbon)"
    project_size_mwp: float = 50.0
    ppa_rate_eur_mwh: float = 45.0
    discount_rate_pct: float = 5.0
    inverter_id: Optional[str] = "auto"
    target_dc_ac_ratio: float = 1.25
    custom_dataset_id: Optional[str] = None
    user_block_size_mwp: Optional[float] = None
    custom_ratio_split: Optional[float] = None
    project_name: Optional[str] = None
    market_region: Optional[str] = "EU"
    tech_filter: Optional[str] = "all"


@app.get("/")
def read_root():
    if frontend_dist_path:
        index_file = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {"status": "EPC Solar Engine Premium API is running"}

@app.get("/api/modules")
def get_modules():
    df = load_data_from_parquet()
    # Replace NaN with None for JSON serialization
    return df.replace({np.nan: None}).to_dict(orient="records")

@app.get("/api/inverters")
def get_inverters(project_size_mwp: float = 50.0):
    df_inv = InverterEngine.load_database()
    if df_inv.empty:
        return []
    records = df_inv.replace({np.nan: None}).to_dict(orient="records")
    
    auto_paired = InverterEngine.auto_pair_inverter(project_size_mwp)
    auto_id = auto_paired.get('inverter_id')
    
    for r in records:
        r['is_auto_paired'] = (r.get('inverter_id') == auto_id)
        
    # Sort so auto-paired is ALWAYS at index 0 (top of dropdown)
    records.sort(key=lambda x: 0 if x.get('is_auto_paired') else 1)
    return records

@app.post("/api/calculate")
def calculate(request: CalculationRequest):
    df = load_data_from_parquet(
        project_size_mwp=request.project_size_mwp, 
        ground_albedo=request.ground_albedo,
        custom_dataset_id=request.custom_dataset_id
    )
    if df.empty:
        raise HTTPException(status_code=500, detail="Database not loaded")
        
    if request.project_size_mwp <= 0:
        raise HTTPException(status_code=400, detail="Project size must be greater than 0")

    # CBAM tax applies in EU market region, while US/Global regions operate on pure market pricing
    effective_cbam_tax = request.cbam_tax_rate_eur_t if (request.market_region in ["EU", "eu", None]) else 0.0

    df_calc = PVEngine.calculate_metrics(
        df, 
        base_irradiance=request.base_irradiance,
        ambient_temp_c=request.ambient_temp_c,
        lifetime=request.lifetime,
        avg_price_wp=request.avg_price_wp,
        bos_cost_wp=request.bos_cost_wp,
        opex_annual=request.opex_annual,
        cbam_tax_rate_eur_t=effective_cbam_tax,
        eol_recycling_rate_pct=request.eol_recycling_rate_pct,
        system_topology=request.system_topology,
        ground_albedo=request.ground_albedo,
        project_size_mwp=request.project_size_mwp,
        inverter_id=request.inverter_id,
        target_dc_ac_ratio=request.target_dc_ac_ratio
    )
    
    df_calc = PVEngine.filter_by_project_size(
        df_calc, 
        request.project_size_mwp, 
        ground_albedo=request.ground_albedo,
        tech_filter=request.tech_filter or "all"
    )

    df_calc, weights = PVEngine.normalize_scores(df_calc, request.scenario)
    df_calc = PVEngine.calculate_topsis(df_calc, request.scenario)

    # Diverse Fleet Mode: 1 Best Panel per Brand
    if not df_calc.empty and 'manufacturer' in df_calc.columns:
        df_calc = df_calc.drop_duplicates(subset=['manufacturer'], keep='first')

    top_panels = df_calc.head(50).replace({np.nan: None}).to_dict(orient="records")
    
    weights_dict = {"eco": weights[0], "cost": weights[1], "tech": weights[2]}
    
    # Resolve dataset_name for history logging
    dataset_name = "Baseline Parquet EPD"
    if request.custom_dataset_id and request.custom_dataset_id != "baseline":
        custom_meta = custom_epd_engine.list_custom_datasets()
        matching = [d for d in custom_meta if d['id'] == request.custom_dataset_id]
        if matching:
            dataset_name = f"Custom: {matching[0]['filename']}"
        else:
            dataset_name = f"Custom: {request.custom_dataset_id}"

    request_dump = request.model_dump()
    request_dump["dataset_name"] = dataset_name
    
    # Log to history
    history_db.log_simulation(request_dump, top_panels, weights_dict)
    
    auto_paired = InverterEngine.auto_pair_inverter(request.project_size_mwp)
    bos_info = BOSEngine.get_bos_performance(request.system_topology)
    
    hybrid_layout = BlockOptimizer.generate_hybrid_layout(
        df_calc=df_calc,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct,
        user_block_size_mwp=request.user_block_size_mwp,
        custom_ratio_split=request.custom_ratio_split
    )

    # Generate instant initial_analysis for top module (#1 winner)
    winner_scores = df_calc.iloc[0]
    radar_data = [
        {"subject": "Eco (Low Carbon)", "A": float(winner_scores.get('Score_Eco', 0)) * 100, "fullMark": 100},
        {"subject": "Cost (Low LCOE)", "A": float(winner_scores.get('Score_Cost', 0)) * 100, "fullMark": 100},
        {"subject": "Tech (High Efficiency)", "A": float(winner_scores.get('Score_Tech', 0)) * 100, "fullMark": 100}
    ]
    
    base_params = {
        'yield': request.base_irradiance,
        'ambient_temp_c': request.ambient_temp_c,
        'lifetime': request.lifetime,
        'avg_price_wp': request.avg_price_wp,
        'bos_cost_wp': request.bos_cost_wp,
        'opex_annual': request.opex_annual,
        'cbam_tax_rate_eur_t': request.cbam_tax_rate_eur_t,
        'eol_recycling_rate_pct': request.eol_recycling_rate_pct,
        'transport_distance_km': 20000.0,
        'system_topology': request.system_topology,
        'ground_albedo': request.ground_albedo,
        'project_size_mwp': request.project_size_mwp,
        'inverter_id': request.inverter_id,
        'target_dc_ac_ratio': request.target_dc_ac_ratio
    }
    
    sens_df = PVEngine.run_sensitivity_analysis(winner_scores, base_params)
    carbon_sens = sens_df[sens_df['Metric'] == 'Carbon Intensity'].to_dict(orient='records') if not sens_df.empty else []
    lcoe_sens = sens_df[sens_df['Metric'] == 'LCOE'].to_dict(orient='records') if not sens_df.empty else []

    scaled_bos_wp, scaled_opex_kwp = BlockOptimizer.get_scaled_bos_and_opex(request.project_size_mwp)

    exec_financials = ExecutiveFinancialModel.calculate_project_financials(
        module_row=winner_scores,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct,
        override_bos_wp=scaled_bos_wp,
        override_opex_kwp=scaled_opex_kwp
    )

    gwp_breakdown = [
        {"component": "PV Module (Net)", "gwp": float(winner_scores.get('GWP_Module_Net_kgCO2e', 0))},
        {"component": "Inverter System", "gwp": float(winner_scores.get('GWP_Inverter_kgCO2e', 0))},
        {"component": "BOS & Racking", "gwp": float(winner_scores.get('GWP_BOS_kgCO2e', 0))}
    ]

    initial_analysis = {
        "radar": radar_data,
        "sensitivity": {
            "carbon": carbon_sens,
            "lcoe": lcoe_sens
        },
        "executive": exec_financials,
        "gwp_breakdown": gwp_breakdown,
        "hybrid_layout": hybrid_layout
    }
    
    return {
        "weights": weights_dict,
        "results": top_panels,
        "auto_paired_inverter": auto_paired,
        "bos_info": bos_info,
        "hybrid_layout": hybrid_layout,
        "initial_analysis": initial_analysis
    }

@app.post("/api/analyze/{dataset_uuid}")
def analyze_module(dataset_uuid: str, request: CalculationRequest):
    df = load_data_from_parquet(
        project_size_mwp=None, # Unfiltered load to guarantee target module is found 
        ground_albedo=None,
        custom_dataset_id=request.custom_dataset_id
    )
    if df.empty:
        raise HTTPException(status_code=500, detail="Database not loaded")
        
    module_row = df[df['dataset_uuid'] == dataset_uuid]
    if module_row.empty:
        module_row = df.head(1)
        
    if request.project_size_mwp <= 0:
        raise HTTPException(status_code=400, detail="Project size must be greater than 0")
        
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
        system_topology=request.system_topology,
        ground_albedo=request.ground_albedo,
        project_size_mwp=request.project_size_mwp,
        inverter_id=request.inverter_id,
        target_dc_ac_ratio=request.target_dc_ac_ratio
    )
    
    full_calc = load_data_from_parquet(
        project_size_mwp=request.project_size_mwp, 
        ground_albedo=request.ground_albedo,
        custom_dataset_id=request.custom_dataset_id
    )
    full_calc = PVEngine.calculate_metrics(
        full_calc,
        base_irradiance=request.base_irradiance,
        ambient_temp_c=request.ambient_temp_c,
        lifetime=request.lifetime,
        avg_price_wp=request.avg_price_wp,
        bos_cost_wp=request.bos_cost_wp,
        opex_annual=request.opex_annual,
        cbam_tax_rate_eur_t=request.cbam_tax_rate_eur_t,
        eol_recycling_rate_pct=request.eol_recycling_rate_pct,
        system_topology=request.system_topology,
        ground_albedo=request.ground_albedo,
        project_size_mwp=request.project_size_mwp,
        inverter_id=request.inverter_id,
        target_dc_ac_ratio=request.target_dc_ac_ratio
    )
    
    full_calc = PVEngine.filter_by_project_size(full_calc, request.project_size_mwp, ground_albedo=request.ground_albedo)
    full_calc, _ = PVEngine.normalize_scores(full_calc, request.scenario)
    full_calc = PVEngine.calculate_topsis(full_calc, request.scenario)
    if not full_calc.empty and 'manufacturer' in full_calc.columns:
        full_calc = full_calc.drop_duplicates(subset=['manufacturer'], keep='first')
    
    matching_scores = full_calc[full_calc['dataset_uuid'] == dataset_uuid]
    if matching_scores.empty:
        module_scores = df_calc.iloc[0] if not df_calc.empty else module_row.iloc[0]
    else:
        module_scores = matching_scores.iloc[0]
    
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
        'transport_distance_km': 20000.0,
        'system_topology': request.system_topology,
        'ground_albedo': request.ground_albedo,
        'project_size_mwp': request.project_size_mwp,
        'inverter_id': request.inverter_id,
        'target_dc_ac_ratio': request.target_dc_ac_ratio
    }
    
    sens_df = PVEngine.run_sensitivity_analysis(module_scores, base_params)
    carbon_sens = sens_df[sens_df['Metric'] == 'Carbon Intensity'].to_dict(orient='records') if not sens_df.empty else []
    lcoe_sens = sens_df[sens_df['Metric'] == 'LCOE'].to_dict(orient='records') if not sens_df.empty else []

    # Scaled BOS and OPEX for project size
    scaled_bos_wp, scaled_opex_kwp = BlockOptimizer.get_scaled_bos_and_opex(request.project_size_mwp)

    calc_row = df_calc.iloc[0]
    exec_financials = ExecutiveFinancialModel.calculate_project_financials(
        module_row=calc_row,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct,
        override_bos_wp=scaled_bos_wp,
        override_opex_kwp=scaled_opex_kwp
    )

    hybrid_layout = BlockOptimizer.generate_hybrid_layout(
        df_calc=full_calc,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct,
        user_block_size_mwp=request.user_block_size_mwp,
        custom_ratio_split=request.custom_ratio_split
    )

    gwp_breakdown = [
        {"component": "PV Module (Net)", "gwp": float(module_scores.get('GWP_Module_Net_kgCO2e', 0))},
        {"component": "Inverter System", "gwp": float(module_scores.get('GWP_Inverter_kgCO2e', 0))},
        {"component": "BOS & Racking", "gwp": float(module_scores.get('GWP_BOS_kgCO2e', 0))}
    ]

    return {
        "radar": radar_data,
        "sensitivity": {
            "carbon": carbon_sens,
            "lcoe": lcoe_sens
        },
        "executive": exec_financials,
        "gwp_breakdown": gwp_breakdown,
        "hybrid_layout": hybrid_layout
    }

@app.get("/api/history")
def get_history(limit: int = 50):
    return history_db.get_history(limit=limit)

@app.delete("/api/history")
def clear_history():
    history_db.clear_all_history()
    return {"status": "success", "message": "Simulation history cleared"}

@app.get("/api/history/{sim_id}")
def get_simulation_history(sim_id: str):
    data = history_db.get_simulation(sim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return data

@app.post("/api/export-pdf/{dataset_uuid}")
def export_pdf(dataset_uuid: str, request: CalculationRequest):
    df = load_data_from_parquet(
        project_size_mwp=request.project_size_mwp, 
        ground_albedo=request.ground_albedo,
        custom_dataset_id=request.custom_dataset_id
    )
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
        system_topology=request.system_topology,
        ground_albedo=request.ground_albedo,
        project_size_mwp=request.project_size_mwp,
        inverter_id=request.inverter_id,
        target_dc_ac_ratio=request.target_dc_ac_ratio
    )
    df_calc = PVEngine.filter_by_project_size(df_calc, request.project_size_mwp, ground_albedo=request.ground_albedo)
    df_calc, _ = PVEngine.normalize_scores(df_calc, request.scenario)
    df_topsis = PVEngine.calculate_topsis(df_calc, request.scenario)
    if not df_topsis.empty and 'manufacturer' in df_topsis.columns:
        df_topsis = df_topsis.drop_duplicates(subset=['manufacturer'], keep='first')

    top_3 = df_topsis.head(3).replace({np.nan: None}).to_dict(orient="records")
    
    winner_row = df_topsis[df_topsis['dataset_uuid'] == dataset_uuid]
    if winner_row.empty:
        winner = top_3[0]
    else:
        winner = winner_row.iloc[0].to_dict()
        
    exec_financials = ExecutiveFinancialModel.calculate_project_financials(
        module_row=winner,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct
    )
    
    auto_paired = InverterEngine.auto_pair_inverter(request.project_size_mwp)
    bos_info = BOSEngine.get_bos_performance(request.system_topology)
    
    hybrid_layout = BlockOptimizer.generate_hybrid_layout(
        df_calc=df_topsis,
        project_size_mwp=request.project_size_mwp,
        ppa_rate_eur_mwh=request.ppa_rate_eur_mwh,
        discount_rate_pct=request.discount_rate_pct,
        user_block_size_mwp=request.user_block_size_mwp,
        custom_ratio_split=request.custom_ratio_split
    )

    pdf_buffer = ReportGenerator.generate_csuite_briefing(
        winner=winner,
        top_3=top_3,
        request_params=request.model_dump(),
        exec_financials=exec_financials,
        inverter_info=auto_paired,
        bos_info=bos_info,
        hybrid_layout=hybrid_layout
    )
    
    filename = f"Executive_Procurement_Briefing_{winner.get('name', 'Module')}.pdf"
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/custom-epd/upload")
async def upload_custom_epd(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        raw_df = custom_epd_engine.parse_file(contents, file.filename)
        norm_df, warnings = custom_epd_engine.validate_and_normalize(raw_df)
        dataset_meta = custom_epd_engine.save_custom_dataset(file.filename, norm_df)
        
        sample_preview = norm_df.head(5).replace({np.nan: None}).to_dict(orient="records")
        return {
            "status": "success",
            "dataset": dataset_meta,
            "warnings": warnings,
            "sample_preview": sample_preview
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/custom-epd/list")
def list_custom_epds():
    return custom_epd_engine.list_custom_datasets()

@app.delete("/api/custom-epd/{dataset_id}")
def delete_custom_epd(dataset_id: str):
    success = custom_epd_engine.delete_custom_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom dataset not found")
    return {"status": "success", "message": "Custom dataset deleted"}

@app.get("/api/custom-epd/sample-csv")
def get_sample_csv():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_datasets", "sample_vendor_modules.csv")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample dataset file not found")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sample_vendor_modules.csv"'}
    )

if __name__ == "__main__":
    import uvicorn
    import multiprocessing
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000)
