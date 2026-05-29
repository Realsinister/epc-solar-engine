import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from pv_engine import PVEngine

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'manufacturer': ['TestMfg'],
        'name': ['TestMod'],
        'module_power_Wp': [400],
        'module_area_m2': [2.0],
        'GWP_total_A1A3_per_kWp_kgCO2e': [500]
    })

def test_process_dataframe(sample_df):
    processed = PVEngine.process_dataframe(sample_df)
    assert 'Efficiency_Pct' in processed.columns
    # Efficiency = (400 / (2.0 * 1000)) * 100 = 20.0
    assert processed['Efficiency_Pct'].iloc[0] == 20.0
    assert 'Uncertainty_SD' in processed.columns

def test_calculate_metrics(sample_df):
    processed = PVEngine.process_dataframe(sample_df)
    results = PVEngine.calculate_metrics(
        processed, 
        base_irradiance=1000, 
        temp_loss=0, 
        lifetime=30,
        avg_price_wp=0.20,
        bos_cost_wp=0.50,
        opex_annual=10
    )
    
    # effective_yield = 1000
    # Carbon Intensity = (500 * 1000) / (1000 * 30) = 500,000 / 30,000 = 16.666
    assert pytest.approx(results['Carbon_Intensity_Mean'].iloc[0], 0.01) == 16.67
    
    # LCOE: 
    # price_wp = 0.20 (efficiency is 20, no change)
    # capex = (0.2 + 0.5) * 1000 = 700
    # opex = 10 * 30 = 300
    # production = 1000 * 30 = 30,000
    # LCOE = ((700 + 300) / 30000) * 1000 = (1000 / 30000) * 1000 = 33.33
    assert pytest.approx(results['LCOE_EUR_MWh'].iloc[0], 0.01) == 33.33

def test_topsis(sample_df):
    # Add a second row to allow ranking
    df2 = pd.DataFrame({
        'manufacturer': ['BetterMfg'],
        'name': ['BetterMod'],
        'module_power_Wp': [450],
        'module_area_m2': [2.0],
        'GWP_total_A1A3_per_kWp_kgCO2e': [400]
    })
    df = pd.concat([sample_df, df2], ignore_index=True)
    
    processed = PVEngine.process_dataframe(df)
    metrics = PVEngine.calculate_metrics(processed, 1000, 0, 30, 0.2, 0.5, 10)
    scored = PVEngine.calculate_topsis(metrics, "Eco-Flagship (Minimize Carbon)")
    
    # BetterMfg should be winner (lower GWP, higher power)
    assert scored.iloc[0]['manufacturer'] == 'BetterMfg'
    assert scored.iloc[0]['TOPSIS_Score'] > scored.iloc[1]['TOPSIS_Score']
