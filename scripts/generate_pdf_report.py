
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch

# Paths
ARTIFACT_DIR = r"C:\Users\yashg\.gemini\antigravity\brain\3f554246-56a3-47a9-9c58-9634ab3a312c"
MD_FILE = os.path.join(ARTIFACT_DIR, "thesis_report_content.md")
OUTPUT_PDF = "PV_EPD_Pipeline_Thesis_Report.pdf"

def generate_pdf():
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CustomCode', parent=styles['Normal'], fontName='Courier', fontSize=9, leading=11, textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='Quote', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10, leftIndent=20))
    
    story = []
    
    # Read Markdown
    with open(MD_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
            
        # Headers
        if line.startswith('# '):
            story.append(Paragraph(line[2:], styles['Title']))
            story.append(Spacer(1, 12))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], styles['Heading2']))
            story.append(Spacer(1, 10))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], styles['Heading3']))
            story.append(Spacer(1, 8))
        elif line.startswith('#### '):
            story.append(Paragraph(line[5:], styles['Heading4']))
            story.append(Spacer(1, 6))
            
        # Images: ![Alt](path)
        elif line.startswith('!['):
            match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
            if match:
                img_name = match.group(2)
                img_path = os.path.join(ARTIFACT_DIR, img_name)
                
                if os.path.exists(img_path):
                    try:
                        # constrain width
                        img = Image(img_path)
                        aspect = img.imageHeight / float(img.imageWidth)
                        target_width = 450
                        img.drawWidth = target_width
                        img.drawHeight = target_width * aspect
                        story.append(img)
                        story.append(Spacer(1, 6))
                        story.append(Paragraph(f"<i>Figure: {match.group(1)}</i>", styles['Normal']))
                        story.append(Spacer(1, 12))
                    except Exception as e:
                         story.append(Paragraph(f"[Image Error: {e}]", styles['Normal']))
                else:
                    story.append(Paragraph(f"[Image not found: {img_path}]", styles['CustomCode']))
                    
        # List items
        elif line.startswith('* ') or line.startswith('- '):
            story.append(Paragraph(f"• {line[2:]}", styles['Normal']))
            
        # Code/Formula (indented or backticks)
        elif line.startswith('`Formula:'):
             story.append(Paragraph(line.replace('`', ''), styles['CustomCode']))
             
        # Normal Text
        else:
             # Basic bold parsing
             text = line
             text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
             text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)
             story.append(Paragraph(text, styles['Normal']))

    doc.build(story)
    print(f"PDF generated successfully: {os.path.abspath(OUTPUT_PDF)}")

if __name__ == "__main__":
    generate_pdf()
