from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.units import inch
import io
from typing import Dict, Any, List

class ReportGenerator:
    """
    Generates professional 2-page C-Suite Procurement Briefing PDF reports.
    """
    
    @staticmethod
    def generate_csuite_briefing(
        winner: Dict[str, Any],
        top_3: List[Dict[str, Any]],
        request_params: Dict[str, Any],
        exec_financials: Dict[str, Any],
        inverter_info: Dict[str, Any],
        bos_info: Dict[str, Any],
        hybrid_layout: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Color Palette
        navy_dark = colors.HexColor("#0f172a")
        blue_accent = colors.HexColor("#1e40af")
        cyan_glow = colors.HexColor("#0284c7")
        gray_bg = colors.HexColor("#f8fafc")
        gray_border = colors.HexColor("#e2e8f0")
        text_dark = colors.HexColor("#1e293b")
        
        # Custom Paragraph Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.white,
            alignment=0
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#94a3b8")
        )
        
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=blue_accent,
            spaceAfter=6
        )
        
        normal_style = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=text_dark
        )

        pitch_style = ParagraphStyle(
            'PitchText',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#0f172a")
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
            alignment=1
        )
        
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=text_dark,
            alignment=1
        )
        
        table_cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=text_dark,
            alignment=1
        )

        story = []
        
        # =========================================================================
        # PAGE 1: EXECUTIVE BRIEFING & TOP RECOMMENDATIONS
        # =========================================================================
        
        # 1. Header Banner Box
        header_table_data = [
            [
                Paragraph("<b>EPC SOLAR ENGINE</b>", title_style),
                Paragraph("<b>C-SUITE PROCUREMENT BRIEFING</b><br/>Executive Analysis & Procurement Briefing", subtitle_style)
            ]
        ]
        header_table = Table(header_table_data, colWidths=[3.2 * inch, 4.0 * inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), navy_dark),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT')
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))

        # 2. Project Parameters Summary Table
        story.append(Paragraph("1. Project Context & Simulation Parameters", section_style))
        
        p_size = request_params.get("project_size_mwp", 50.0)
        p_scenario = request_params.get("scenario", "Utility Scale (Lowest LCOE)")
        p_ppa = request_params.get("ppa_rate_eur_mwh", 45.0)
        p_cbam = request_params.get("cbam_tax_rate_eur_t", 80.0)
        p_topo = request_params.get("system_topology", "Fixed Tilt")
        p_temp = request_params.get("ambient_temp_c", 35.0)

        param_data = [
            [
                Paragraph("<b>Project Scale:</b>", normal_style), Paragraph(f"{p_size} MWp", normal_style),
                Paragraph("<b>Topology:</b>", normal_style), Paragraph(f"{p_topo}", normal_style)
            ],
            [
                Paragraph("<b>Optimization Strategy:</b>", normal_style), Paragraph(f"{p_scenario}", normal_style),
                Paragraph("<b>Ambient Temp:</b>", normal_style), Paragraph(f"{p_temp} °C", normal_style)
            ],
            [
                Paragraph("<b>Target PPA Rate:</b>", normal_style), Paragraph(f"€{p_ppa:.2f} / MWh", normal_style),
                Paragraph("<b>CBAM Tax Rate:</b>", normal_style), Paragraph(f"€{p_cbam:.2f} / tonne CO2", normal_style)
            ]
        ]
        param_table = Table(param_data, colWidths=[1.8 * inch, 1.9 * inch, 1.7 * inch, 1.8 * inch])
        param_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), gray_bg),
            ('BOX', (0, 0), (-1, -1), 1, gray_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, gray_border),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(param_table)
        story.append(Spacer(1, 12))

        # 3. Primary Winner Recommendation Pitch Box
        story.append(Paragraph("2. Board Recommendation & Executive Pitch", section_style))
        
        winner_mfg = winner.get("manufacturer", "N/A")
        winner_name = winner.get("name", "N/A")
        winner_lcoe = winner.get("LCOE_EUR_MWh", 0.0)
        winner_carbon = winner.get("Net_GWP_kgCO2e", 0.0)
        winner_score = winner.get("TOPSIS_Score", 0.0)
        
        pitch_text = exec_financials.get("pitch_text", f"Based on MCDA evaluation, {winner_mfg} {winner_name} achieves optimal performance.")

        pitch_data = [
            [
                Paragraph(
                    f"<b>PRIMARY RECOMMENDED MODULE:</b> <font color='#0284c7'><b>{winner_mfg} {winner_name}</b></font><br/>"
                    f"TOPSIS Score: <b>{winner_score:.1f} / 100</b> &nbsp;|&nbsp; "
                    f"System LCOE: <b>€{winner_lcoe:.2f} / MWh</b> &nbsp;|&nbsp; "
                    f"Carbon Footprint: <b>{winner_carbon:.0f} kgCO2e / kWp</b><br/><br/>"
                    f"<b>Executive Pitch Defense:</b><br/>\"{pitch_text}\"",
                    pitch_style
                )
            ]
        ]
        pitch_table = Table(pitch_data, colWidths=[7.2 * inch])
        pitch_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
            ('BOX', (0, 0), (-1, -1), 1.5, cyan_glow),
            ('PADDING', (0, 0), (-1, -1), 10)
        ]))
        story.append(pitch_table)
        story.append(Spacer(1, 14))

        # 4. Top-3 Winner Comparison Matrix
        story.append(Paragraph("3. Top-3 Module Winner Comparison Matrix", section_style))
        
        matrix_headers = ["Rank", "Manufacturer & Model", "Wattage", "LCOE (€/MWh)", "Carbon (kgCO2e/kWp)", "TOPSIS Score"]
        matrix_rows = [[Paragraph(f"<b>{h}</b>", table_header_style) for h in matrix_headers]]

        for idx, row in enumerate(top_3[:3], 1):
            mfg = row.get("manufacturer", "Unknown")
            name = row.get("name", "Unknown")
            wp = row.get("module_power_Wp", 0.0)
            lcoe = row.get("LCOE_EUR_MWh", 0.0)
            carbon = row.get("Net_GWP_kgCO2e", 0.0)
            score = row.get("TOPSIS_Score", 0.0)
            
            rank_str = f"<b>#{idx}</b>" if idx == 1 else f"#{idx}"
            matrix_rows.append([
                Paragraph(rank_str, table_cell_bold if idx == 1 else table_cell_style),
                Paragraph(f"{mfg} - {name}", table_cell_style),
                Paragraph(f"{wp:.0f} Wp", table_cell_style),
                Paragraph(f"€{lcoe:.2f}", table_cell_bold if idx == 1 else table_cell_style),
                Paragraph(f"{carbon:.0f}", table_cell_style),
                Paragraph(f"<b>{score:.1f}</b>", table_cell_bold if idx == 1 else table_cell_style)
            ])

        comp_table = Table(matrix_rows, colWidths=[0.6 * inch, 2.6 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 0.9 * inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), blue_accent),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, gray_border),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(comp_table)
        
        # End Page 1
        story.append(PageBreak())

        # =========================================================================
        # PAGE 2: EMBODIED CARBON STACK & FINANCIAL DEFENSE
        # =========================================================================
        
        story.append(Paragraph("4. System Embodied Carbon Footprint Breakdown (Scope 3)", section_style))
        story.append(Paragraph(f"Detailed Life Cycle Assessment (LCA) embodied carbon stack for recommended module: <b>{winner_mfg} {winner_name}</b>.", normal_style))
        story.append(Spacer(1, 8))

        gwp_mod = winner.get("GWP_Module_Net_kgCO2e", winner.get("GWP_total_A1A3_per_kWp_kgCO2e", 0.0))
        gwp_inv = winner.get("GWP_Inverter_kgCO2e", 0.0)
        gwp_bos = winner.get("GWP_BOS_kgCO2e", 0.0)
        gwp_tot = winner.get("Net_GWP_kgCO2e", gwp_mod + gwp_inv + gwp_bos)

        carbon_stack_data = [
            [
                Paragraph("System Component", table_header_style),
                Paragraph("Embodied Carbon (kgCO2e / kWp)", table_header_style),
                Paragraph("Share of Total", table_header_style)
            ],
            [
                Paragraph("<b>PV Module (Net of EoL Recycling)</b>", table_cell_style),
                Paragraph(f"{gwp_mod:.1f}", table_cell_style),
                Paragraph(f"{(gwp_mod / gwp_tot * 100):.1f}%" if gwp_tot > 0 else "0%", table_cell_style)
            ],
            [
                Paragraph("<b>Inverter System</b>", table_cell_style),
                Paragraph(f"{gwp_inv:.1f}", table_cell_style),
                Paragraph(f"{(gwp_inv / gwp_tot * 100):.1f}%" if gwp_tot > 0 else "0%", table_cell_style)
            ],
            [
                Paragraph("<b>BOS Racking & Cabling</b>", table_cell_style),
                Paragraph(f"{gwp_bos:.1f}", table_cell_style),
                Paragraph(f"{(gwp_bos / gwp_tot * 100):.1f}%" if gwp_tot > 0 else "0%", table_cell_style)
            ],
            [
                Paragraph("<b>TOTAL SYSTEM EMBODIED CARBON</b>", table_cell_bold),
                Paragraph(f"<b>{gwp_tot:.1f}</b>", table_cell_bold),
                Paragraph("<b>100.0%</b>", table_cell_bold)
            ]
        ]
        
        carbon_table = Table(carbon_stack_data, colWidths=[3.2 * inch, 2.2 * inch, 1.8 * inch])
        carbon_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy_dark),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, gray_border),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e0f2fe")),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(carbon_table)
        story.append(Spacer(1, 14))

        # 5. Financial & CBAM Risk Summary Table
        story.append(Paragraph("5. Project Financial Economics & CBAM Tax Exposure", section_style))

        npv = exec_financials.get("npv_eur", 0.0)
        payback = exec_financials.get("payback_years")
        payback_str = f"{payback:.1f} Years" if payback is not None else "N/A (> Lifetime)"
        rev = exec_financials.get("lifetime_revenue_eur", 0.0)
        cbam_pen_kwp = winner.get("CBAM_Penalty_EUR_kWp", 0.0)
        cbam_tot_proj = (cbam_pen_kwp * p_size * 1000)

        fin_data = [
            [
                Paragraph("<b>Net Present Value (NPV):</b>", normal_style),
                Paragraph(f"€{npv:,.2f}", normal_style),
                Paragraph("<b>Payback Period:</b>", normal_style),
                Paragraph(f"{payback_str}", normal_style)
            ],
            [
                Paragraph("<b>Lifetime Revenue:</b>", normal_style),
                Paragraph(f"€{rev:,.2f}", normal_style),
                Paragraph("<b>CBAM Penalty / kWp:</b>", normal_style),
                Paragraph(f"€{cbam_pen_kwp:.2f} / kWp", normal_style)
            ],
            [
                Paragraph("<b>Total CBAM Import Tax Risk:</b>", normal_style),
                Paragraph(f"<b>€{cbam_tot_proj:,.2f}</b>", normal_style),
                Paragraph("<b>Auto Inverter Match:</b>", normal_style),
                Paragraph(f"{inverter_info.get('model_name', 'Auto-Paired')}", normal_style)
            ]
        ]
        
        fin_table = Table(fin_data, colWidths=[2.2 * inch, 1.6 * inch, 1.8 * inch, 1.6 * inch])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), gray_bg),
            ('BOX', (0, 0), (-1, -1), 1, gray_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, gray_border),
            ('PADDING', (0, 0), (-1, -1), 5)
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 10))

        # 6. Multi-Block Hybrid Deployment Strategy Table (For Utility Scale Projects)
        if hybrid_layout and hybrid_layout.get("is_hybrid"):
            story.append(Paragraph("6. Multi-Block Hybrid System Procurement Plan", section_style))
            
            tot_blocks = hybrid_layout.get("total_blocks", 1)
            b_size = hybrid_layout.get("block_size_mwp", 5.0)
            
            story.append(Paragraph(
                f"Multi-block allocation split into <b>{tot_blocks} Inverter Blocks</b> @ {b_size:.1f} MWp each. "
                f"Maintains 100% electrical MPPT & string uniformity per block while optimizing blended LCOE and CBAM tax exposure.",
                normal_style
            ))
            story.append(Spacer(1, 6))

            hybrid_headers = ["Block Group", "Strategy Role", "Vendor & Module Model", "Capacity (MWp)", "Blocks", "LCOE (€/MWh)", "CBAM Tax (€)"]
            hybrid_rows = [[Paragraph(f"<b>{h}</b>", table_header_style) for h in hybrid_headers]]

            for idx, alloc in enumerate(hybrid_layout.get("allocations", [])):
                grp_label = f"Group {'A' if idx == 0 else 'B'} ({alloc.get('capacity_share_pct', 0):.0f}%)"
                role_label = alloc.get("role", "Vendor Block")
                m_name = alloc.get("module_name", "PV Module")
                cap_mwp = alloc.get("capacity_mwp", 0.0)
                blks = alloc.get("blocks_assigned", 0)
                lcoe_val = alloc.get("lcoe_eur_mwh", 0.0)
                cbam_val = alloc.get("cbam_tax_eur", 0.0)

                hybrid_rows.append([
                    Paragraph(f"<b>{grp_label}</b>", table_cell_bold),
                    Paragraph(f"<font color='#1e40af'><b>{role_label}</b></font>", table_cell_style),
                    Paragraph(f"{m_name}", table_cell_style),
                    Paragraph(f"{cap_mwp:.1f} MWp", table_cell_style),
                    Paragraph(f"{blks}", table_cell_style),
                    Paragraph(f"€{lcoe_val:.2f}", table_cell_bold),
                    Paragraph(f"€{cbam_val:,.0f}", table_cell_style)
                ])

            hybrid_table = Table(hybrid_rows, colWidths=[1.1 * inch, 1.6 * inch, 1.7 * inch, 0.9 * inch, 0.5 * inch, 0.8 * inch, 0.6 * inch])
            hybrid_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue_accent),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, gray_border),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gray_bg]),
                ('PADDING', (0, 0), (-1, -1), 5)
            ]))
            story.append(hybrid_table)
            story.append(Spacer(1, 10))

        # 7. Footer Disclaimer & Governance
        story.append(HRFlowable(width="100%", thickness=1, color=gray_border, spaceAfter=8))
        story.append(Paragraph(
            "<b>Methodology & Compliance Statement:</b> This report is synthetically generated by the EPC Solar Engine MCDA engine "
            "incorporating SAM CEC electrical parameters, vector TOPSIS normalization, and EPD Scope 3 Life Cycle Assessment benchmarks. "
            "Calculations strictly account for local temperature penalties, inverter DC/AC ratio clipping, multi-block MPPT uniformity, and CBAM import tariff exposure.",
            ParagraphStyle('FooterDisclaimer', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor("#64748b"))
        ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
