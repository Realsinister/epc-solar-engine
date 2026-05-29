import os
import pandas as pd
import numpy as np
import plotly.express as px
import sys

# Add src to path so we can import PVEngine
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from pv_engine.engine import PVEngine

def generate_graphs():
    os.makedirs('presentation_graphs', exist_ok=True)
    
    # 1. Define Demo Data (3 distinct profiles)
    data = [
        {
            'manufacturer': 'EcoSolar (Thin Film)',
            'module_name': 'GreenLine 500',
            'Efficiency_Pct': 19.5,
            'GWP_total_A1A3_per_kWp_kgCO2e': 210.0,
            'Uncertainty_SD': 0.1
        },
        {
            'manufacturer': 'StandardSolar (Mono-Si)',
            'module_name': 'Classic 550',
            'Efficiency_Pct': 21.0,
            'GWP_total_A1A3_per_kWp_kgCO2e': 400.0,
            'Uncertainty_SD': 0.15
        },
        {
            'manufacturer': 'CarbonHeavy (Poly-Si)',
            'module_name': 'Bulk 540',
            'Efficiency_Pct': 18.5,
            'GWP_total_A1A3_per_kWp_kgCO2e': 650.0,
            'Uncertainty_SD': 0.2
        }
    ]
    df_base = pd.DataFrame(data)
    
    # Base Assumptions
    base_irradiance = 1050
    temp_loss = 5.0
    lifetime = 30
    avg_price_wp = 0.22
    bos_cost_wp = 0.45
    opex_annual = 15.0
    
    # --- GRAPH 1: CBAM Impact on LCOE ---
    cbam_rates = np.linspace(0, 200, 21) # 0 to 200 EUR/tonne
    
    lcoe_results = []
    for rate in cbam_rates:
        df_calc = PVEngine.calculate_metrics(
            df_base, base_irradiance, temp_loss, lifetime, 
            avg_price_wp, bos_cost_wp, opex_annual,
            cbam_tax_rate_eur_t=rate,
            eol_recycling_rate_pct=0.0
        )
        for _, row in df_calc.iterrows():
            lcoe_results.append({
                'Manufacturer': row['manufacturer'],
                'CBAM Tax Rate (€/tonne)': rate,
                'LCOE (€/MWh)': row['LCOE_EUR_MWh']
            })
            
    df_lcoe = pd.DataFrame(lcoe_results)
    
    fig1 = px.line(
        df_lcoe, x='CBAM Tax Rate (€/tonne)', y='LCOE (€/MWh)', color='Manufacturer',
        title='Financial Risk: Impact of CBAM Carbon Taxes on Solar LCOE',
        markers=True, template='plotly_dark'
    )
    fig1.update_layout(title_font_size=22, legend_title_font_size=16, font_size=14, margin=dict(t=80, b=40, l=40, r=40))
    fig1.write_html('presentation_graphs/CBAM_LCOE_Impact.html')
    
    # --- GRAPH 2: End-of-Life Circularity ---
    recycling_rates = np.linspace(0, 100, 21)
    
    carbon_results = []
    for rate in recycling_rates:
        df_calc = PVEngine.calculate_metrics(
            df_base, base_irradiance, temp_loss, lifetime, 
            avg_price_wp, bos_cost_wp, opex_annual,
            cbam_tax_rate_eur_t=0.0,
            eol_recycling_rate_pct=rate
        )
        for _, row in df_calc.iterrows():
            carbon_results.append({
                'Manufacturer': row['manufacturer'],
                'Recycling Rate (%)': rate,
                'Net Carbon Intensity (gCO2e/kWh)': row['Carbon_Intensity_Mean']
            })
            
    df_carbon = pd.DataFrame(carbon_results)
    
    fig2 = px.line(
        df_carbon, x='Recycling Rate (%)', y='Net Carbon Intensity (gCO2e/kWh)', color='Manufacturer',
        title='Cradle-to-Cradle: Net Carbon Intensity vs EoL Recycling Capabilities',
        markers=True, template='plotly_dark'
    )
    fig2.update_layout(title_font_size=22, legend_title_font_size=16, font_size=14, margin=dict(t=80, b=40, l=40, r=40))
    fig2.write_html('presentation_graphs/EoL_Circularity_Impact.html')
    
    print("Presentation graphs successfully generated in 'presentation_graphs/' directory!")

if __name__ == "__main__":
    generate_graphs()
