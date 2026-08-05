import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from .schemas import PVModuleSchema
from .logger import get_logger
from .inverter_engine import InverterEngine
from .bos_engine import BOSEngine
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

        # Remove impossible physical outliers (e.g. data entry typos < 50 kgCO2e/kWp)
        if 'GWP_total_A1A3_per_kWp_kgCO2e' in df.columns:
            df = df[df['GWP_total_A1A3_per_kWp_kgCO2e'] >= 50]

        # Remove duplicate panels based on manufacturer and module power rating (retaining lowest carbon representative)
        if 'manufacturer' in df.columns and 'module_power_Wp' in df.columns:
            if 'GWP_total_A1A3_per_kWp_kgCO2e' in df.columns:
                df = df.sort_values('GWP_total_A1A3_per_kWp_kgCO2e', ascending=True)
            df = df.drop_duplicates(subset=['manufacturer', 'module_power_Wp'], keep='first')

        def clean_brand_name(mfg):
            mfg_str = str(mfg).strip()
            mfg_clean = re.sub(r'\s*(Jiangsu|Zhejiang|Anhui|Changzhou|Hefei|Ningbo|Wuxi|Sichuan|Shanghai|Beijing|Guangdong|Suzhou)\b', '', mfg_str, flags=re.IGNORECASE)
            mfg_clean = re.sub(r'\s*(Co\.,?\s*Ltd\.?|Inc\.?|Corp\.?|LLC|GmbH|Company|Corporation|Technology|Green Energy|New Energy|Solar Technology|Electrics|Group|Holdings|Limited|SRL)\b', '', mfg_clean, flags=re.IGNORECASE).strip()
            upper = mfg_clean.upper()
            if 'FIRST SOLAR' in upper: return 'First Solar'
            if 'RUNERGY' in upper: return 'Runergy'
            if 'JINKO' in upper: return 'JinkoSolar'
            if 'LONGI' in upper: return 'LONGi'
            if 'TRINA' in upper: return 'Trina Solar'
            if 'CANADIAN' in upper: return 'Canadian Solar'
            if 'JA SOLAR' in upper: return 'JA Solar'
            if 'RISEN' in upper: return 'Risen Energy'
            if 'SOLARSPACE' in upper: return 'Solarspace'
            if 'ASTRONERGY' in upper: return 'Astronergy'
            return mfg_clean if len(mfg_clean) > 0 else mfg_str

        if 'manufacturer' in df.columns and 'name' in df.columns:
            df['Display_Name'] = df.apply(
                lambda x: f"{clean_brand_name(x['manufacturer'])} - {str(x['name'])}", axis=1
            )
        
        if 'module_power_Wp' in df.columns and 'module_area_m2' in df.columns:
            # Efficiency = (Power / (Area * 1000W/m2)) * 100
            df['Efficiency_Pct'] = (df['module_power_Wp'] / (df['module_area_m2'] * 1000)) * 100
        else:
            df['Efficiency_Pct'] = 0

        # Extract dynamic physical constraints based on technology heuristics
        def parse_physics(row):
            desc = str(row.get('Description / Note', '')).lower() + " " + str(row.get('name', '')).lower()
            
            # Default values (Standard Mono P-Type)
            temp_coef = -0.34 # % per °C
            deg_rate = 0.55 # % per year
            weight_t = 0.05 # tonnes / kWp
            
            if any(k in desc for k in ['n-type', 'hjt', 'topcon', 'hi-mo', 'maxeon']):
                temp_coef = -0.29
                deg_rate = 0.40
            elif any(k in desc for k in ['cigs', 'flexible']):
                temp_coef = -0.20
                deg_rate = 0.70
                weight_t = 0.015
            elif 'bipv' in desc or 'glass-glass' in desc:
                temp_coef = -0.35
                deg_rate = 0.50
                weight_t = 0.08
                
            is_bifacial = any(k in desc for k in ['bifacial', 'glass-glass', 'dual-glass'])
                
            return pd.Series({
                'Panel_Temp_Coef': temp_coef, 
                'Annual_Degradation_Pct': deg_rate, 
                'Weight_t_kWp': weight_t,
                'Is_Bifacial': is_bifacial
            })
            
        physics_cols = ['Panel_Temp_Coef', 'Annual_Degradation_Pct', 'Weight_t_kWp', 'Is_Bifacial']
        df = df.drop(columns=[c for c in physics_cols if c in df.columns], errors='ignore')
        physics_df = df.apply(parse_physics, axis=1)
        df = pd.concat([df, physics_df], axis=1)
        df = df.loc[:, ~df.columns.duplicated()]

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
        ambient_temp_c: float, 
        lifetime: int,
        avg_price_wp: float,
        bos_cost_wp: float,
        opex_annual: float,
        cbam_tax_rate_eur_t: float = 0.0,
        eol_recycling_rate_pct: float = 0.0,
        system_topology: str = "Fixed Tilt",
        ground_albedo: float = None,
        transport_emission_factor: float = 0.010, # kgCO2e / tonne-km
        project_size_mwp: float = 50.0,
        inverter_id: str = "auto",
        target_dc_ac_ratio: float = 1.25
    ) -> pd.DataFrame:
        """
        Calculates LCOE, Carbon Intensity, and Suitability scores with EoL and CBAM.
        """
        transport_distance_km = 20000.0 # Hardcoded scope 3 assumption
        
        if df.empty or 'GWP_total_A1A3_per_kWp_kgCO2e' not in df.columns:
            return df

        df = df.copy()
        df = df.dropna(subset=['GWP_total_A1A3_per_kWp_kgCO2e'])

        # Calculate dynamic temperature loss based on STC (25C) and ambient temp
        # Loss is calculated as: (Ambient - 25) * Panel_Temp_Coef (which is negative, so we subtract to reduce yield)
        # Assuming cell temp is roughly Ambient + 25C under full sun for standard mounting
        cell_temp = ambient_temp_c + 25
        temp_diff = cell_temp - 25
        
        # Apply temperature penalty per panel
        df['Dynamic_Temp_Loss_Pct'] = np.where(temp_diff > 0, temp_diff * abs(df['Panel_Temp_Coef']), 0)
        
        # --- Inverter & BOS Integration ---
        if inverter_id == "auto" or not inverter_id:
            inverter_data = InverterEngine.auto_pair_inverter(project_size_mwp)
        else:
            df_inv = InverterEngine.load_database()
            match = df_inv[df_inv['inverter_id'] == inverter_id]
            inverter_data = match.iloc[0].to_dict() if not match.empty else InverterEngine.auto_pair_inverter(project_size_mwp)
            
        inv_perf = InverterEngine.calculate_inverter_performance(inverter_data, target_dc_ac_ratio)
        bos_perf = BOSEngine.get_bos_performance(system_topology)

        # --- Bifacial Gain Physics ---
        if ground_albedo is not None:
            df['Bifacial_Gain_Pct'] = np.where(
                df['Is_Bifacial'] == True,
                ground_albedo * 0.70 * 0.90 * 100, # Albedo * Bifaciality Factor * View Factor
                0.0
            )
        else:
            df['Bifacial_Gain_Pct'] = 0.0

        system_eff = inv_perf['euro_efficiency'] * bos_perf['bos_electrical_efficiency'] * (1 - (inv_perf['clipping_loss_pct'] / 100.0))
        df['Effective_Yield'] = base_irradiance * (1 - (df['Dynamic_Temp_Loss_Pct'] / 100)) * bos_perf['yield_multiplier'] * (1 + (df['Bifacial_Gain_Pct'] / 100)) * system_eff
        
        # --- Scope 3 Logistics (Transport) ---
        df['Logistics_GWP_kgCO2e'] = df['Weight_t_kWp'] * transport_distance_km * transport_emission_factor
        
        # --- System Carbon Footprint (Module + Inverter + BOS) ---
        max_eol_credit_factor = 0.15 
        df['GWP_Inverter_kgCO2e'] = inv_perf['inverter_gwp_kgco2e_per_kwp']
        df['GWP_BOS_kgCO2e'] = bos_perf['total_bos_gwp_kgco2e_per_kwp']
        df['GWP_Module_Net_kgCO2e'] = (df['GWP_total_A1A3_per_kWp_kgCO2e'] + df['Logistics_GWP_kgCO2e']) * (1 - (max_eol_credit_factor * (eol_recycling_rate_pct / 100)))
        
        # Total System GWP
        df['Net_GWP_kgCO2e'] = df['GWP_Module_Net_kgCO2e'] + df['GWP_Inverter_kgCO2e'] + df['GWP_BOS_kgCO2e']
        df['Inverter_CAPEX_kWp'] = inv_perf['inverter_capex_eur_per_wp'] * 1000.0

        # --- Dynamic Degradation ---
        years = np.arange(1, lifetime + 1)
        # Apply panel-specific degradation to calculate total lifetime yield
        def get_lifetime_yield(row):
            deg_factors = (1 - (row['Annual_Degradation_Pct'] / 100)) ** (years - 1)
            return row['Effective_Yield'] * np.sum(deg_factors)
            
        df['Production_kWh_kWp'] = df.apply(get_lifetime_yield, axis=1)

        # 1. Environmental: Carbon Intensity (gCO2e/kWh)
        df['Carbon_Intensity_Mean'] = (df['Net_GWP_kgCO2e'] * 1000) / df['Production_kWh_kWp']
        
        # --- Economies of Scale (BOS & OPEX Optimization) ---
        if project_size_mwp < 1.0:
            scale_multiplier = 1.20 # 20% premium for tiny/residential projects
        elif project_size_mwp > 20.0:
            scale_multiplier = 0.90 # 10% discount for massive utility scale
        else:
            scale_multiplier = 1.0
            
        tracker_bos_mult = 1.10 if system_topology == "Single-Axis Tracker" else 1.0
        tracker_opex_mult = 1.20 if system_topology == "Single-Axis Tracker" else 1.0
        
        scaled_bos = (bos_cost_wp + bos_perf['total_bos_capex_eur_per_wp']) * scale_multiplier * tracker_bos_mult
        scaled_opex = opex_annual * scale_multiplier * tracker_opex_mult

        # 2. Economic: LCOE (€/MWh)
        df['Estimated_Price_Wp'] = avg_price_wp * (1 + (df['Efficiency_Pct'] - 20) / 100)
        
        # --- CBAM Tax Penalty ---
        # Tax = (Net_GWP_kgCO2e / 1000) * CBAM Rate per tonne 
        df['CBAM_Penalty_EUR_kWp'] = (df['Net_GWP_kgCO2e'] / 1000) * cbam_tax_rate_eur_t
        
        capex = (df['Estimated_Price_Wp'] + scaled_bos) * 1000 + df['CBAM_Penalty_EUR_kWp'] # €/kWp
        opex = scaled_opex * lifetime # Total lifetime OPEX per kWp
        
        # ((CAPEX + OPEX) / production) * 1000 to get €/MWh
        df['LCOE_EUR_MWh'] = ((capex + opex) / df['Production_kWh_kWp']) * 1000

        return df
        
    @staticmethod
    def filter_by_project_size(df: pd.DataFrame, project_size_mwp: float, ground_albedo: float = None) -> pd.DataFrame:
        """
        Hard filtering layer to eliminate modules that are physically incompatible
        with the scale of the project, prior to running the MCDA scenario optimization.
        Also filters out monofacial modules if the user has explicitly selected a ground albedo target.
        """
        if df.empty or 'module_power_Wp' not in df.columns:
            return df
            
        initial_count = len(df)
        
        # Bifaciality constraint
        if ground_albedo is not None:
            df = df[df['Is_Bifacial'].astype(str).str.lower() == 'true'].copy()
        
        if project_size_mwp < 1.0:
            # SME / Commercial: Filter out massive utility-scale panels
            df = df[df['module_power_Wp'] <= 450]
        elif project_size_mwp > 10.0:
            # Utility Scale: Filter out tiny residential panels
            df = df[df['module_power_Wp'] >= 400]
            
        return df

    @staticmethod
    def normalize_scores(df: pd.DataFrame, scenario: str) -> tuple[pd.DataFrame, tuple[float, float, float]]:
        """
        Applies MCDA normalization and weighting based on scenario.
        """
        if scenario == "Eco-Flagship (Minimize Carbon)":
            w_eco, w_cost, w_tech = 0.70, 0.15, 0.15
        elif scenario == "Utility Scale (Lowest LCOE)":
            w_eco, w_cost, w_tech = 0.20, 0.60, 0.20
        else: # Space Constrained
            w_eco, w_cost, w_tech = 0.20, 0.20, 0.60

        if df.empty:
            return df, (w_eco, w_cost, w_tech)

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
        if df.empty:
            return df
            
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
            cell_temp = params['ambient_temp_c'] + 25
            temp_diff = cell_temp - 25
            dyn_temp_loss = temp_diff * abs(row['Panel_Temp_Coef']) if temp_diff > 0 else 0
            eff_yield = params['yield'] * (1 - (dyn_temp_loss / 100))
            
            years = np.arange(1, params['lifetime'] + 1)
            degradation_factors = (1 - (row['Annual_Degradation_Pct'] / 100)) ** (years - 1)
            production = eff_yield * np.sum(degradation_factors)
            
            weight_tonnes = row['Weight_t_kWp']
            logistics = weight_tonnes * params.get('transport_distance_km', 0) * 0.010
            
            max_eol_credit_factor = 0.15
            net_carbon_kg = (row['GWP_total_A1A3_per_kWp_kgCO2e'] + logistics) * (1 - (max_eol_credit_factor * (params.get('eol_recycling_rate_pct', 0) / 100)))
            carbon = (net_carbon_kg * 1000) / production
            
            # Simplified LCOE for sensitivity
            est_price = params['avg_price_wp'] * (1 + (row['Efficiency_Pct'] - 20) / 100)
            cbam_penalty = (net_carbon_kg / 1000) * params.get('cbam_tax_rate_eur_t', 0)
            capex = (est_price + params['bos_cost_wp']) * 1000 + cbam_penalty
            opex = params['opex_annual'] * params['lifetime']
            lcoe = ((capex + opex) / production) * 1000
            return carbon, lcoe

        base_carbon, base_lcoe = get_point_metrics(base_params)

        param_labels = {
            'yield': 'Specific Yield',
            'ambient_temp_c': 'Ambient Temp',
            'lifetime': 'Project Lifetime',
            'avg_price_wp': 'Module Price',
            'bos_cost_wp': 'BOS Cost',
            'opex_annual': 'O&M Cost',
            'cbam_tax_rate_eur_t': 'CBAM Tax Rate',
            'eol_recycling_rate_pct': 'EoL Recycling Rate',
            'transport_distance_km': 'Shipping Distance'
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
