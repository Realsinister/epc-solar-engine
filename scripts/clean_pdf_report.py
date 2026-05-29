
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch

# Paths
ARTIFACT_DIR = r"C:\Users\yashg\.gemini\antigravity\brain\3f554246-56a3-47a9-9c58-9634ab3a312c"
MD_FILE = os.path.join(ARTIFACT_DIR, "thesis_report_final.md")
OUTPUT_PDF = r"c:\Users\yashg\OneDrive\Projects\pv-epd-pipeline\PV_EPD_Pipeline_Thesis_Report.pdf"

def generate_pdf():
    print(f"Generating PDF to: {OUTPUT_PDF}")
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    # "CustomCode" to avoid conflict if "Code" exists
    if 'CustomCode' not in styles:
        styles.add(ParagraphStyle(name='CustomCode', parent=styles['Normal'], fontName='Courier', fontSize=9, leading=11, textColor=colors.darkblue))
    
    story = []
    
    try:
        with open(MD_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Markdown file not found at {MD_FILE}")
        return

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
            
        # --- IMAGES ---
        # Regex to handle ![Alt](Path)
        img_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
        if img_match:
            alt_text = img_match.group(1)
            img_filename = img_match.group(2).strip()
            
            # Construct absolute path
            # If the filename is just a name, join with ARTIFACT_DIR
            if not os.path.isabs(img_filename):
                img_path = os.path.join(ARTIFACT_DIR, img_filename)
            else:
                img_path = img_filename
                
            print(f"Processing image: {img_path}")
            
            if os.path.exists(img_path):
                try:
                    # Constrain image size
                    img = Image(img_path)
                    # A4 width is ~595 pts. Margins 72*2 = 144. Content width ~450.
                    max_width = 450
                    aspect = img.imageHeight / float(img.imageWidth)
                    
                    if img.imageWidth > max_width:
                        img.drawWidth = max_width
                        img.drawHeight = max_width * aspect
                    
                    story.append(img)
                    story.append(Spacer(1, 6))
                    story.append(Paragraph(f"<i>Figure: {alt_text}</i>", styles['Normal']))
                    story.append(Spacer(1, 12))
                except Exception as e:
                    story.append(Paragraph(f"[Error loading image: {e}]", styles['CustomCode']))
            else:
                story.append(Paragraph(f"[Image file not found: {img_filename}]", styles['CustomCode']))
            continue

        # --- HEADERS ---
        # Strip # and use styles
        if line.startswith('# '):
            text = line[2:].strip()
            story.append(Paragraph(text, styles['Title']))
            story.append(Spacer(1, 12))
            continue
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, styles['Heading2']))
            story.append(Spacer(1, 10))
            continue
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, styles['Heading3']))
            story.append(Spacer(1, 8))
            continue
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, styles['Heading4']))
            story.append(Spacer(1, 6))
            continue
            
        # --- LISTS ---
        if line.startswith('* ') or line.startswith('- '):
            text = line[2:].strip()
            # Clean Bold/Italic markers
            text = text.replace('**', '').replace('*', '') 
            story.append(Paragraph(f"• {text}", styles['Normal']))
            continue

        # --- SPECIAL BLOCKS ---
        if line.startswith('`Formula:'):
             text = line.replace('`', '').replace('Formula:', 'Formula: ').strip()
             story.append(Paragraph(text, styles['CustomCode']))
             continue
             
        # --- NORMAL TEXT ---
        # Clean formatting for plain PDF readability
        text = line
        # Replace **bold** with just bold text (no stars)
        text = text.replace('**', '') 
        # Replace *italic* with just text
        text = text.replace('*', '')
        # Replace `code` with just text
        text = text.replace('`', '')
        
        story.append(Paragraph(text, styles['Normal']))

    try:
        doc.build(story)
        print("PDF generation complete.")
    except Exception as e:
        print(f"Failed to build PDF: {e}")

if __name__ == "__main__":
    generate_pdf()
