import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from .financial_model import ExecutiveFinancialModel
from .inverter_engine import InverterEngine
from .bos_engine import BOSEngine

class BlockOptimizer:
    """
    Utility-Scale Block-Level Hybrid System Optimizer.
    Divides large PV projects into discrete inverter blocks (e.g., 5 MWp or 10 MWp blocks).
    Allocates top-ranked module types to different blocks to optimize
    the trade-off between CAPEX, LCOE, and CBAM Carbon Tax Exposure.
    Enforces strict electrical uniformity per inverter block (never mixing module models inside an MPPT/string).
    """

    @staticmethod
    def get_default_block_size(project_size_mwp: float) -> float:
        """
        Determines realistic default block size based on project scale (One-Click Solution).
        """
        if project_size_mwp < 5.0:
            return float(project_size_mwp)
        elif project_size_mwp <= 20.0:
            return 2.5
        elif project_size_mwp <= 100.0:
            return 5.0
        else:
            return 10.0

    @staticmethod
    def get_scaled_bos_and_opex(project_size_mwp: float, base_bos_wp: float = 0.45, base_opex_kwp: float = 15.0) -> tuple[float, float]:
        """
        Computes realistic non-linear economies of scale for utility-scale BOS and OPEX.
        Small (<1 MWp): Standard rooftop costs.
        Mega Utility (>=50 MWp): Highly optimized bulk procurement BOS & low OPEX.
        """
        if project_size_mwp < 1.0:
            bos_cost_wp = base_bos_wp
            opex_kwp = base_opex_kwp
        elif project_size_mwp < 10.0:
            bos_cost_wp = max(0.28, base_bos_wp * 0.75)
            opex_kwp = max(11.0, base_opex_kwp * 0.80)
        elif project_size_mwp < 50.0:
            bos_cost_wp = max(0.24, base_bos_wp * 0.60)
            opex_kwp = max(9.0, base_opex_kwp * 0.65)
        else: # Utility scale >= 50 MWp
            bos_cost_wp = max(0.20, base_bos_wp * 0.50)
            opex_kwp = max(7.5, base_opex_kwp * 0.50)

        return bos_cost_wp, opex_kwp

    @staticmethod
    def generate_hybrid_layout(
        df_calc: pd.DataFrame,
        project_size_mwp: float,
        ppa_rate_eur_mwh: float,
        discount_rate_pct: float = 5.0,
        user_block_size_mwp: Optional[float] = None,
        custom_ratio_split: Optional[float] = None # e.g. 0.60 for 60% Mod 1 / 40% Mod 2
    ) -> Dict[str, Any]:
        """
        Generates an automated, realistic block-level hybrid deployment strategy.
        Pairs top 2 modules to optimize financial NPV & CBAM tax reduction.
        """
        if df_calc.empty:
            return {}

        project_size_mwp = float(project_size_mwp or 50.0)
        block_size_mwp = float(user_block_size_mwp) if user_block_size_mwp and user_block_size_mwp > 0 else BlockOptimizer.get_default_block_size(project_size_mwp)
        
        total_blocks = max(1, int(round(project_size_mwp / block_size_mwp)))
        actual_block_mwp = project_size_mwp / total_blocks

        # Scale BOS and OPEX according to project size
        scaled_bos_wp, scaled_opex_kwp = BlockOptimizer.get_scaled_bos_and_opex(project_size_mwp)

        # For small projects (< 10 MWp) or single-module fallback, 100% goes to #1 panel
        if total_blocks == 1 or len(df_calc) < 2 or project_size_mwp < 10.0:
            mod1 = df_calc.iloc[0]
            mod1_dict = mod1.to_dict()
            
            # Single module execution with scaled financials
            fin = ExecutiveFinancialModel.calculate_project_financials(
                module_row=mod1,
                project_size_mwp=project_size_mwp,
                ppa_rate_eur_mwh=ppa_rate_eur_mwh,
                discount_rate_pct=discount_rate_pct,
                override_bos_wp=scaled_bos_wp,
                override_opex_kwp=scaled_opex_kwp
            )
            
            return {
                "is_hybrid": False,
                "project_size_mwp": project_size_mwp,
                "block_size_mwp": actual_block_mwp,
                "total_blocks": total_blocks,
                "scaled_bos_wp": scaled_bos_wp,
                "scaled_opex_kwp": scaled_opex_kwp,
                "allocations": [{
                    "module_name": mod1.get("Display_Name", mod1.get("name")),
                    "dataset_uuid": mod1.get("dataset_uuid"),
                    "manufacturer": mod1.get("manufacturer"),
                    "blocks_assigned": total_blocks,
                    "capacity_mwp": project_size_mwp,
                    "capacity_share_pct": 100.0,
                    "role": "Single Primary Module Deployment",
                    "module_power_Wp": float(mod1.get("module_power_Wp", 0)),
                    "efficiency_pct": float(mod1.get("Efficiency_Pct", 0)),
                    "gwp_kgco2e_per_kwp": float(mod1.get("Net_GWP_kgCO2e", mod1.get("GWP_total_A1A3_per_kWp_kgCO2e", 0))),
                    "lcoe_eur_mwh": float(mod1.get("LCOE_EUR_MWh", 0)),
                    "cbam_tax_eur": fin["total_cbam_tax_eur"],
                    "annual_generation_mwh": (mod1.get("Effective_Yield", 1000) * project_size_mwp * 1000) / 1000.0
                }],
                "financials": fin
            }

        # Multi-block hybrid calculation for large utility projects (>= 10 MWp)
        top1 = df_calc.iloc[0]
        top2 = df_calc.iloc[1]

        # Determine block split (Default: ~60% Top 1, ~40% Top 2)
        if custom_ratio_split is not None and 0.0 < custom_ratio_split < 1.0:
            blocks_mod1 = max(1, int(round(total_blocks * custom_ratio_split)))
        else:
            blocks_mod1 = max(1, int(round(total_blocks * 0.60)))
            
        blocks_mod2 = max(1, total_blocks - blocks_mod1)

        cap_mod1_mwp = blocks_mod1 * actual_block_mwp
        cap_mod2_mwp = blocks_mod2 * actual_block_mwp

        # Compute block 1 financials & yield
        fin1 = ExecutiveFinancialModel.calculate_project_financials(
            module_row=top1,
            project_size_mwp=cap_mod1_mwp,
            ppa_rate_eur_mwh=ppa_rate_eur_mwh,
            discount_rate_pct=discount_rate_pct,
            override_bos_wp=scaled_bos_wp,
            override_opex_kwp=scaled_opex_kwp
        )

        # Compute block 2 financials & yield
        fin2 = ExecutiveFinancialModel.calculate_project_financials(
            module_row=top2,
            project_size_mwp=cap_mod2_mwp,
            ppa_rate_eur_mwh=ppa_rate_eur_mwh,
            discount_rate_pct=discount_rate_pct,
            override_bos_wp=scaled_bos_wp,
            override_opex_kwp=scaled_opex_kwp
        )

        # Aggregated Blended Metrics
        total_upfront_cost = fin1["total_upfront_cost_eur"] + fin2["total_upfront_cost_eur"]
        total_cbam_tax = fin1["total_cbam_tax_eur"] + fin2["total_cbam_tax_eur"]
        total_revenue = fin1["total_lifetime_revenue_eur"] + fin2["total_lifetime_revenue_eur"]
        blended_npv = fin1["npv_eur"] + fin2["npv_eur"]

        # Calculate blended payback
        annual_net_cash = (total_revenue / int(top1.get("Lifetime", 30))) - ((scaled_opex_kwp * project_size_mwp * 1000.0))
        blended_payback = total_upfront_cost / annual_net_cash if annual_net_cash > 0 else 99.9

        # Roles description
        gwp1 = float(top1.get("Net_GWP_kgCO2e", 500))
        gwp2 = float(top2.get("Net_GWP_kgCO2e", 500))
        
        if gwp1 < gwp2:
            role1 = "Carbon Optimization Leader (Minimizes CBAM)"
            role2 = "High Density / LCOE Optimizer"
        else:
            role1 = "Primary LCOE Optimization Leader"
            role2 = "Carbon Offset & Tax Saver"

        allocations = [
            {
                "module_name": top1.get("Display_Name", top1.get("name")),
                "dataset_uuid": top1.get("dataset_uuid"),
                "manufacturer": top1.get("manufacturer"),
                "blocks_assigned": blocks_mod1,
                "capacity_mwp": cap_mod1_mwp,
                "capacity_share_pct": (cap_mod1_mwp / project_size_mwp) * 100,
                "role": role1,
                "module_power_Wp": float(top1.get("module_power_Wp", 0)),
                "efficiency_pct": float(top1.get("Efficiency_Pct", 0)),
                "gwp_kgco2e_per_kwp": gwp1,
                "lcoe_eur_mwh": float(top1.get("LCOE_EUR_MWh", 0)),
                "cbam_tax_eur": fin1["total_cbam_tax_eur"],
                "annual_generation_mwh": (top1.get("Effective_Yield", 1000) * cap_mod1_mwp * 1000) / 1000.0
            },
            {
                "module_name": top2.get("Display_Name", top2.get("name")),
                "dataset_uuid": top2.get("dataset_uuid"),
                "manufacturer": top2.get("manufacturer"),
                "blocks_assigned": blocks_mod2,
                "capacity_mwp": cap_mod2_mwp,
                "capacity_share_pct": (cap_mod2_mwp / project_size_mwp) * 100,
                "role": role2,
                "module_power_Wp": float(top2.get("module_power_Wp", 0)),
                "efficiency_pct": float(top2.get("Efficiency_Pct", 0)),
                "gwp_kgco2e_per_kwp": gwp2,
                "lcoe_eur_mwh": float(top2.get("LCOE_EUR_MWh", 0)),
                "cbam_tax_eur": fin2["total_cbam_tax_eur"],
                "annual_generation_mwh": (top2.get("Effective_Yield", 1000) * cap_mod2_mwp * 1000) / 1000.0
            }
        ]

        blended_lcoe = (allocations[0]["lcoe_eur_mwh"] * (cap_mod1_mwp / project_size_mwp)) + (allocations[1]["lcoe_eur_mwh"] * (cap_mod2_mwp / project_size_mwp))

        hybrid_financials = {
            "total_upfront_cost_eur": total_upfront_cost,
            "total_cbam_tax_eur": total_cbam_tax,
            "total_lifetime_revenue_eur": total_revenue,
            "npv_eur": blended_npv,
            "payback_years": min(30.0, max(1.0, blended_payback)),
            "blended_lcoe_eur_mwh": blended_lcoe,
            "executive_pitch": (
                f"Multi-Block Hybrid Deployment ({total_blocks} Inverter Blocks of {actual_block_mwp:.1f} MWp each): "
                f"{blocks_mod1} blocks ({cap_mod1_mwp:.1f} MWp) allocated to {allocations[0]['module_name']} and "
                f"{blocks_mod2} blocks ({cap_mod2_mwp:.1f} MWp) allocated to {allocations[1]['module_name']}. "
                f"This block-level hybridization achieves a blended LCOE of €{blended_lcoe:.2f}/MWh and "
                f"yields a Net Present Value (NPV) of €{blended_npv:,.0f} with a payback period of {min(30.0, blended_payback):.1f} years."
            )
        }

        return {
            "is_hybrid": True,
            "project_size_mwp": project_size_mwp,
            "block_size_mwp": actual_block_mwp,
            "total_blocks": total_blocks,
            "scaled_bos_wp": scaled_bos_wp,
            "scaled_opex_kwp": scaled_opex_kwp,
            "allocations": allocations,
            "financials": hybrid_financials
        }
