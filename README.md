<div align="center">
  
# ⚡ EPC Solar Engine
**Next-Generation PV Lifecycle Assessment & Procurement Decision Engine**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Environdec API](https://img.shields.io/badge/Data-Environdec_Live-success)](#)
[![Compliance](https://img.shields.io/badge/Ready-CBAM_|_ESPR-purple)](#)

*Transitioning solar procurement from static compliance to strategic asset intelligence.*

</div>

---

## 🌍 Executive Summary

As the European Union and global markets aggressively tighten sustainability regulations (ESPR, CBAM), static spreadsheets and generic Carbon Footprint averages are no longer sufficient for utility-scale solar procurement.

**EPC Solar Engine** is a highly robust, API-driven procurement tool designed specifically for Engineering, Procurement, and Construction (EPC) firms and Project Developers. By seamlessly fusing live Environmental Product Declarations (EPDs) with rigorous financial forecasting, this engine empowers stakeholders to make mathematically optimal, multi-criteria decisions that balance Levelized Cost of Energy (LCOE), hardware reliability, and Scope 3 carbon penalties.

---

## ✨ Core Capabilities

### 🗄️ Live EPD Integration (Environdec API)
Stop relying on outdated PDFs. The Engine queries the global **Environdec API** in real-time to fetch specific, third-party verified Life Cycle Inventories for top-tier solar modules (Jinko, Trina, First Solar, etc.), instantly injecting carbon intensities into your local SQLite cache.

### ⚖️ Carbon Border Adjustment Mechanism (CBAM) Modeler
Stay ahead of regulatory tariffs. The Engine dynamically calculates CBAM financial penalties based on the manufacturing origin's carbon intensity, automatically internalizing import taxes directly into your upfront CAPEX and final LCOE calculations.

### ♻️ Cradle-to-Cradle (C2C) Circularity
Moving beyond standard "Cradle-to-Gate" assessments, the Engine introduces dynamic **End-of-Life (EoL)** recycling credits. Highly recyclable modules receive net-carbon reductions against their A1-A3 footprint, strategically rewarding circular economy investments.

### 🕸️ Multi-Criteria Decision Analysis (MCDA)
Utilizing the **TOPSIS** (Technique for Order of Preference by Similarity to Ideal Solution) algorithm, the software evaluates thousands of data points to rank modules against customizable scenarios:
- **Eco-Flagship:** Maximize carbon reduction for green-bidding tenders.
- **Utility Scale:** Heavily weight financial LCOE.
- **Space Constrained:** Prioritize raw technical efficiency (Wp/m²).

### 📊 Stochastic Risk Analysis
Solar assets live for 30+ years; your data should account for the unknown. Built-in **Monte Carlo Simulations** assess supply chain data uncertainties, while dynamic **Tornado Plots** expose precisely how sensitive your LCOE is to module degradation and O&M inflation.

---

## 🛠️ System Architecture

Built for scale, speed, and analytical rigor.
- **Frontend:** Streamlit (Python) for rapid, interactive dashboards and data visualization.
- **Backend Physics Engine:** Custom-built OOP Python engine (`PVEngine`) strictly adhering to EN 15804+A2 standards.
- **Data Persistence:** Lightweight SQLite database caching for lightning-fast scenario rendering and offline tender evaluations.
- **Visuals:** Plotly Express & Plotly Graph Objects for publication-ready charting.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- An Environdec API Token (Optional, for live fetching)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/epc-solar-engine.git
   cd epc-solar-engine
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `\.venv\Scripts\activate`
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Engine:**
   ```bash
   streamlit run streamlit_app.py
   # Or simply execute launch.bat on Windows
   ```

---

## 🎓 Academic & Industry Origins
*EPC Solar Engine* evolved from a comprehensive Master Thesis Project investigating the intersection of Photovoltaic Life Cycle Assessments and multi-criteria optimization. It bridges the gap between rigorous academic environmental science and real-world industrial procurement workflows.

> **Interested in collaboration, live demos, or technical deep-dives?**  
> Connect with me on [LinkedIn](#) or read the foundational methodology on [ResearchGate](#).

---
*Built for the clean energy transition. ☀️*
