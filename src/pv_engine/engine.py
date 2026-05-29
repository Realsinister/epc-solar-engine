import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from .schemas import PVModuleSchema
from .logger import get_logger
import pandera as pa

logger = get_logger(__name__)

class PVEngine:
    """
    Core engine for PV Lifecycle Assessment and Financial Analysis.
    Decoupled from the UI to allow for testing and reuse.
    """

    @staticmethod
    def validate_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates the dataframe against the PVModuleSchema.
        """
        try:
            validated_df = PVModuleSchema.validate(df)
            logger.info("Data validation successful.")
            return validated_df
        except pa.errors.SchemaError as e:
            logger.error(f"Data validation failed: {e}")
            raise

    @staticmethod
    def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Runs the Engineering Physics calculations and cleans missing data.
        """
        df = df.copy()
        
        # Essential columns for calculation and display
        essential_cols = ['manufacturer', 'name', 'module_power_Wp', 'module_area_m2', 'GWP_total_A1A3_per_kWp_kgCO2e']
        
        # Drop rows where essential identifiers or values are missing
        df = df.dropna(subset=[col for col in essential_cols if col in df.columns])
        
        numeric_cols = ['module_power_Wp', 'module_area_m2', 'GWP_total_A1A3_per_kWp_kgCO2e']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Re-drop after numeric coercion in case of garbage strings
        df = df.dropna(subset=[col for col in numeric_cols if col in df.columns])

        if 'manufacturer' in df.columns and 'name' in df.columns:
            df['Display_Name'] = df.apply(
                lambda x: f"{x['manufacturer']} - {str(x['name'])[:25]}", axis=1
            )
        
        if 'module_power_Wp' in df.columns and 'module_area_m2' in df.columns:
            # Efficiency = (Power / (Area * 1000W/m2)) * 100
            df['Efficiency_Pct'] = (df['module_power_Wp'] / (df['module_area_m2'] * 1000)) * 100
        else:
            df['Efficiency_Pct'] = 0

        def calculate_uncertainty(row):
            # Heuristic-based uncertainty score
            score_rel = 1 if (pd.notna(row.get('source')) and '.pdf' in str(row['source']).lower()) else 3
            score_comp = 1 if (pd.notna(row.get('module_power_Wp')) and row['module_power_Wp'] > 0) else 4
            score_temp = 1 if (pd.notna(row.get('version'))) else 3
            
            uncertainty_factor = 0.05 + (0.02 * (score_rel - 1)) + (0.02 * (score_comp - 1)) + (0.02 * (score_temp - 1))
            return uncertainty_factor 

        df['Uncertainty_SD'] = df.apply(calculate_uncertainty, axis=1)
        return df

    @staticmethod
    def calculate_metrics(
        df: pd.DataFrame, 
        base_irradiance: float, 
        temp_loss: float, 
        lifetime: int,
        avg_price_wp: float,
        bos_cost_wp: float,
        opex_annual: float,
        cbam_tax_rate_eur_t: float = 0.0,
        eol_recycling_rate_pct: float = 0.0
    ) -> pd.DataFrame:
        """
        Calculates LCOE, Carbon Intensity, and Suitability scores with EoL and CBAM.
        """
        if df.empty or 'GWP_total_A1A3_per_kWp_kgCO2e' not in df.columns:
            return df

        df = df.copy()
        df = df.dropna(subset=['GWP_total_A1A3_per_kWp_kgCO2e'])

        effective_yield = base_irradiance * (1 - (temp_loss / 100))
        
        # --- End of Life (EoL) Circularity ---
        # Assume 100% recycling rate yields a max 15% carbon credit against A1-A3 manufacturing
        max_eol_credit_factor = 0.15 
        df['Net_GWP_kgCO2e'] = df['GWP_total_A1A3_per_kWp_kgCO2e'] * (1 - (max_eol_credit_factor * (eol_recycling_rate_pct / 100)))

        # 1. Environmental: Carbon Intensity (gCO2e/kWh)
        df['Carbon_Intensity_Mean'] = (df['Net_GWP_kgCO2e'] * 1000) / (effective_yield * lifetime)
        
        # 2. Economic: LCOE (€/MWh)
        df['Estimated_Price_Wp'] = avg_price_wp * (1 + (df['Efficiency_Pct'] - 20) / 100)
        
        # --- CBAM Tax Penalty ---
        # Tax = (Net_GWP_kgCO2e / 1000) * CBAM Rate per tonne 
        df['CBAM_Penalty_EUR_kWp'] = (df['Net_GWP_kgCO2e'] / 1000) * cbam_tax_rate_eur_t
        
        capex = (df['Estimated_Price_Wp'] + bos_cost_wp) * 1000 + df['CBAM_Penalty_EUR_kWp'] # €/kWp
        opex = opex_annual * lifetime # Total lifetime OPEX per kWp
        production = effective_yield * lifetime # Total lifetime kWh per kWp
        
        # ((CAPEX + OPEX) / production) * 1000 to get €/MWh
        df['LCOE_EUR_MWh'] = ((capex + opex) / production) * 1000
        
        return df

    @staticmethod
    def normalize_scores(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """
        Applies MCDA normalization and weighting based on scenario.
        """
        df = df.copy()
        
        def normalize(series, invert=False):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val: return 1.0
            norm = (series - min_val) / (max_val - min_val)
            return 1 - norm if invert else norm

        df['Score_Eco'] = normalize(df['Carbon_Intensity_Mean'], invert=True)
        df['Score_Cost'] = normalize(df['LCOE_EUR_MWh'], invert=True)
        df['Score_Tech'] = normalize(df['Efficiency_Pct'], invert=False)

        if scenario == "Eco-Flagship (Minimize Carbon)":
            w_eco, w_cost, w_tech = 0.70, 0.15, 0.15
        elif scenario == "Utility Scale (Lowest LCOE)":
            w_eco, w_cost, w_tech = 0.20, 0.60, 0.20
        else: # Space Constrained
            w_eco, w_cost, w_tech = 0.20, 0.20, 0.60

        df['Suitability_Index'] = (
            (df['Score_Eco'] * w_eco) + 
            (df['Score_Cost'] * w_cost) + 
            (df['Score_Tech'] * w_tech)
        ) * 100
        
        return df.sort_values('Suitability_Index', ascending=False), (w_eco, w_cost, w_tech)

    @staticmethod
    def calculate_topsis(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """
        Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS).
        A more robust MCDA method for industry decision making.
        """
        df = df.copy()
        criteria_cols = ['Carbon_Intensity_Mean', 'LCOE_EUR_MWh', 'Efficiency_Pct']
        
        # 1. Normalize Matrix (Vector Normalization)
        # r_ij = x_ij / sqrt(sum(x_ij^2))
        matrix = df[criteria_cols].values
        norm_matrix = matrix / np.sqrt((matrix**2).sum(axis=0))
        
        # 2. Weighted Normalized Matrix
        if scenario == "Eco-Flagship (Minimize Carbon)":
            weights = np.array([0.70, 0.15, 0.15])
        elif scenario == "Utility Scale (Lowest LCOE)":
            weights = np.array([0.20, 0.60, 0.20])
        else:
            weights = np.array([0.20, 0.20, 0.60])
            
        weighted_matrix = norm_matrix * weights
        
        # 3. Ideal Solutions (V+ and V-)
        # Carbon and LCOE: lower is better (minimize)
        # Efficiency: higher is better (maximize)
        v_plus = np.zeros(3)
        v_minus = np.zeros(3)
        
        v_plus[0] = weighted_matrix[:, 0].min() # Minimize Carbon
        v_minus[0] = weighted_matrix[:, 0].max()
        
        v_plus[1] = weighted_matrix[:, 1].min() # Minimize LCOE
        v_minus[1] = weighted_matrix[:, 1].max()
        
        v_plus[2] = weighted_matrix[:, 2].max() # Maximize Efficiency
        v_minus[2] = weighted_matrix[:, 2].min()
        
        # 4. Separation Measures (S+ and S-)
        s_plus = np.sqrt(((weighted_matrix - v_plus)**2).sum(axis=1))
        s_minus = np.sqrt(((weighted_matrix - v_minus)**2).sum(axis=1))
        
        # 5. Relative Closeness (Pi)
        # Pi = S- / (S+ + S-)
        df['TOPSIS_Score'] = (s_minus / (s_plus + s_minus)) * 100
        
        return df.sort_values('TOPSIS_Score', ascending=False)

    @staticmethod
    def run_monte_carlo(row: pd.Series, effective_yield: float, lifetime: int, n_sims: int = 1000) -> pd.DataFrame:
        """
        Runs Monte Carlo simulation for a single module's carbon intensity.
        """
        mean_gwp = row.get('Net_GWP_kgCO2e', row['GWP_total_A1A3_per_kWp_kgCO2e'])
        sigma = row['Uncertainty_SD']
        
        # Lognormal distribution parameters
        mu = np.log(mean_gwp) - 0.5 * sigma**2
        samples_gwp = np.random.lognormal(mu, sigma, n_sims)
        
        samples_intensity = (samples_gwp * 1000) / (effective_yield * lifetime)
        return pd.DataFrame({
            'Module': row['manufacturer'], 
            'Intensity (g/kWh)': samples_intensity
        })

    @staticmethod
    def run_sensitivity_analysis(
        row: pd.Series,
        base_params: Dict[str, float],
        variation: float = 0.20
    ) -> pd.DataFrame:
        """
        Calculates sensitivity of Carbon Intensity and LCOE to parameter variations.
        Returns a dataframe for Tornado plot visualization.
        """
        results = []
        
        # Helper to calculate metrics for a single point
        def get_point_metrics(params):
            eff_yield = params['yield'] * (1 - (params['temp_loss'] / 100))
            max_eol_credit_factor = 0.15
            net_carbon_kg = row['GWP_total_A1A3_per_kWp_kgCO2e'] * (1 - (max_eol_credit_factor * (params.get('eol_recycling_rate_pct', 0) / 100)))
            carbon = (net_carbon_kg * 1000) / (eff_yield * params['lifetime'])
            
            # Simplified LCOE for sensitivity
            est_price = params['avg_price_wp'] * (1 + (row['Efficiency_Pct'] - 20) / 100)
            cbam_penalty = (net_carbon_kg / 1000) * params.get('cbam_tax_rate_eur_t', 0)
            capex = (est_price + params['bos_cost_wp']) * 1000 + cbam_penalty
            opex = params['opex_annual'] * params['lifetime']
            prod = eff_yield * params['lifetime']
            lcoe = ((capex + opex) / prod) * 1000
            return carbon, lcoe

        base_carbon, base_lcoe = get_point_metrics(base_params)

        param_labels = {
            'yield': 'Specific Yield',
            'temp_loss': 'Temp. Loss',
            'lifetime': 'Project Lifetime',
            'avg_price_wp': 'Module Price',
            'bos_cost_wp': 'BOS Cost',
            'opex_annual': 'O&M Cost',
            'cbam_tax_rate_eur_t': 'CBAM Tax Rate',
            'eol_recycling_rate_pct': 'EoL Recycling Rate'
        }

        for p_name, label in param_labels.items():
            # Low variation (-20%)
            low_params = base_params.copy()
            low_params[p_name] *= (1 - variation)
            low_carbon, low_lcoe = get_point_metrics(low_params)
            
            # High variation (+20%)
            high_params = base_params.copy()
            high_params[p_name] *= (1 + variation)
            high_carbon, high_lcoe = get_point_metrics(high_params)
            
            results.append({
                'Parameter': label,
                'Metric': 'Carbon Intensity',
                'Low': low_carbon - base_carbon,
                'High': high_carbon - base_carbon
            })
            results.append({
                'Parameter': label,
                'Metric': 'LCOE',
                'Low': low_lcoe - base_lcoe,
                'High': high_lcoe - base_lcoe
            })
            
        return pd.DataFrame(results)
