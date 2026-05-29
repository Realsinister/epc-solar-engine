@echo off
setlocal
cd /d "D:\PV_LCA_Software\pv-epd-pipeline"
echo Starting PV LCA Decision Engine...
echo Using isolated D: drive environment...
".\.venv\Scripts\python.exe" -m streamlit run streamlit_app.py
pause
