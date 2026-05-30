from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
import io
import pandas as pd

class ReportGenerator:
    """
    Generates professional PDF reports for PV procurement decisions.
    """
    
    @staticmethod
    def generate_decision_report(winner: pd.Series, scenario: str, location: str) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = styles['Title']
        header_style = styles['Heading2']
        normal_style = styles['Normal']
        
        story = []
        
        # 1. Title
        story.append(Paragraph("PV LCA Procurement Decision Report", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # 2. Executive Summary
        story.append(Paragraph(f"Project Context: {location}", header_style))
        story.append(Paragraph(f"Optimization Strategy: {scenario}", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        story.append(Paragraph("Optimal Recommendation", header_style))
        story.append(Paragraph(
            f"Based on the multi-criteria decision analysis, the module <b>{winner['manufacturer']} {winner['name']}</b> "
            f"has been identified as the optimal choice for this project.", 
            normal_style
        ))
        story.append(Spacer(1, 0.3 * inch))
        
        # 3. Key Metrics Table
        data = [
            ["Metric", "Value", "Unit"],
            ["Suitability Index", f"{winner['Suitability_Index']:.1f}", "/ 100"],
            ["TOPSIS Reliability", f"{winner['TOPSIS_Score']:.1f}", "/ 100"],
            ["Carbon Intensity", f"{winner['Carbon_Intensity_Mean']:.2f}", "gCO2e/kWh"],
            ["Est. LCOE", f"{winner['LCOE_EUR_MWh']:.2f}", "€/MWh"],
            ["Module Efficiency", f"{winner['Efficiency_Pct']:.1f}", "%"]
        ]
        
        table = Table(data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5 * inch))
        
        # 4. Methodology Note
        story.append(Paragraph("Methodology & Data Quality", header_style))
        story.append(Paragraph(
            "The decision is based on Environmental Product Declaration (EPD) data. "
            "A stochastic Monte Carlo simulation (N=1000) was performed to assess environmental risk, "
            "and the TOPSIS method was used to ensure mathematical robustness against ideal solutions.",
            normal_style
        ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
