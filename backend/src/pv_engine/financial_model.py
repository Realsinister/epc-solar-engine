import numpy as np

class ExecutiveFinancialModel:
    """
    Handles Executive-level financial projections (NPV, ROI, CBAM Exposure).
    Designed to be highly modular so future technical models (inverter clipping, battery LCA)
    can easily feed into this layer without modifying legacy code.
    """
    
    @staticmethod
    def calculate_project_financials(
        module_row, 
        project_size_mwp: float, 
        ppa_rate_eur_mwh: float, 
        discount_rate_pct: float = 5.0
    ) -> dict:
        """
        Scales the per-kWp physics calculations up to a full Utility/Commercial project size.
        Returns NPV, Payback Period, and Total CBAM Tax Exposure.
        """
        # Convert MWp to kWp
        total_kwp = project_size_mwp * 1000.0
        
        # 1. Total CAPEX & OPEX
        capex_kwp = (module_row['Estimated_Price_Wp'] + module_row.get('BOS_Cost_Wp', 0.45)) * 1000
        total_capex = capex_kwp * total_kwp
        
        annual_opex_kwp = module_row.get('OPEX_Annual_kWp', 15.0)
        total_annual_opex = annual_opex_kwp * total_kwp
        
        # 2. CBAM Financial Exposure (Tax)
        # Net_GWP_kgCO2e is per kWp. Convert to metric tonnes.
        cbam_tax_rate = module_row.get('CBAM_Tax_Rate', 80.0)
        total_carbon_tonnes = (module_row['Net_GWP_kgCO2e'] * total_kwp) / 1000.0
        total_cbam_tax = total_carbon_tonnes * cbam_tax_rate
        
        # Add CBAM to Day-0 CAPEX
        total_upfront_cost = total_capex + total_cbam_tax
        
        # 3. Dynamic Yield & Cash Flow over Lifetime
        lifetime = int(module_row.get('Lifetime', 30))
        annual_deg = module_row['Annual_Degradation_Pct'] / 100.0
        base_annual_yield_kwp = module_row['Effective_Yield'] # kWh/kWp/year (Year 1)
        
        cash_flows = [-total_upfront_cost]
        cumulative_cash = -total_upfront_cost
        payback_year = None
        
        total_lifetime_revenue = 0
        
        # NOTE for future expansion: This loop is where hourly irradiance arrays or 
        # inverter clipping functions would be injected in the future.
        for year in range(1, lifetime + 1):
            deg_factor = (1 - annual_deg) ** (year - 1)
            yearly_production_kwh = base_annual_yield_kwp * deg_factor * total_kwp
            yearly_production_mwh = yearly_production_kwh / 1000.0
            
            revenue = yearly_production_mwh * ppa_rate_eur_mwh
            net_cash_flow = revenue - total_annual_opex
            
            cash_flows.append(net_cash_flow)
            total_lifetime_revenue += revenue
            cumulative_cash += net_cash_flow
            
            if cumulative_cash >= 0 and payback_year is None:
                # Interpolate fraction of year
                prev_cash = cumulative_cash - net_cash_flow
                fraction = abs(prev_cash) / net_cash_flow
                payback_year = (year - 1) + fraction

        # 4. Net Present Value (NPV)
        npv = sum(cf / (1 + (discount_rate_pct / 100.0)) ** t for t, cf in enumerate(cash_flows))
        
        # Generate Executive Pitch
        pitch = ExecutiveFinancialModel.generate_executive_pitch(
            module_name=module_row['Display_Name'],
            npv=npv,
            cbam_tax=total_cbam_tax,
            temp_coef=module_row['Panel_Temp_Coef'],
            payback=payback_year
        )

        return {
            "total_upfront_cost_eur": total_upfront_cost,
            "total_cbam_tax_eur": total_cbam_tax,
            "total_lifetime_revenue_eur": total_lifetime_revenue,
            "npv_eur": npv,
            "payback_years": payback_year if payback_year else 99.9,
            "executive_pitch": pitch
        }

    @staticmethod
    def generate_executive_pitch(module_name: str, npv: float, cbam_tax: float, temp_coef: float, payback: float) -> str:
        """
        Dynamically generates a persuasive executive summary based on the module's specific physics.
        """
        temp_advantage = "superior thermal resistance" if abs(temp_coef) < 0.30 else "standard thermal profile"
        
        cbam_risk = "very low CBAM import tax exposure" if cbam_tax < 50000 else "significant CBAM import tax exposure"
        
        pitch = (
            f"The {module_name} is mathematically optimized for this project. "
            f"Its {temp_advantage} (Temp. Coef: {temp_coef}%/°C) secures long-term yield under these ambient conditions, "
            f"driving an estimated NPV of €{npv:,.0f}. "
            f"Furthermore, its factory carbon footprint results in {cbam_risk} (€{cbam_tax:,.0f}), "
            f"ensuring an accelerated payback period of {payback:.1f} years."
        )
        return pitch
