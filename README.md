<div align="center">
  <img src="https://img.shields.io/badge/Status-Premium_Desktop_App-green?style=for-the-badge&logo=electron" alt="Status" />
  <img src="https://img.shields.io/badge/Engine-FastAPI%20%2B%20Python-blue?style=for-the-badge&logo=fastapi" alt="Backend" />
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react" alt="Frontend" />
  <h1>EPC Solar Engine</h1>
  <p><strong>A Next-Generation Standalone Desktop Software for PV Module Analysis, Multi-Criteria Decision Making (MCDA), and Executive Financial Modeling.</strong></p>
</div>

---

## 🌟 Overview
**EPC Solar Engine** has officially evolved from a basic web-based calculator into a powerful, **standalone Windows desktop application**. Tailored for EPC (Engineering, Procurement, and Construction) firms, this software seamlessly combines real-time Physics calculations with advanced Multi-Criteria Decision Analysis (MCDA) and a dedicated Executive Financial Dashboard.

This tool acts as your ultimate "pitch generator" for PV module procurement, calculating real-world technical yields, carbon footprints (LCA), and massive project-scale economics instantly.

## ✨ Key Features
- 📄 **1-Click Executive PDF Export (Phase 2):** Instantly generate and download formal 2-Page C-Suite Procurement Briefing PDF reports equipped with project parameters, top-3 winner comparison matrices, LCA carbon footprint stacks, and automated executive pitch defenses.
- ⚡ **Standalone Desktop Experience:** Double-click the installer and launch the app natively on Windows (no python setup required).
- 🧮 **Physics-based MCDA Engine:** A Python/FastAPI backend instantly scores modules based on dynamic weighting of Cost, Performance, and Eco-Footprint using vector TOPSIS algorithms.
- 🎨 **Premium UI/UX:** Built with React & Vite, featuring a sleek dark-mode glassmorphism interface and interactive leaderboards.
- 📈 **Interactive Pareto Trade-Off Frontier (Phase 1):** 2D Scatter plot mapping **System LCOE (€/MWh)** vs **System Embodied Carbon (kgCO2e/kWp)** with TOPSIS-weighted bubble sizing.
- 🔌 **Inverter Database & BOS Configurator:** Real-world inverter dataset (Sungrow, SMA, Huawei, SolarEdge) with dynamic DC/AC ratio clipping, BOS racking/cabling carbon accounting, and Year 15 inverter replacement CAPEX modeling (-10% EoL credit).
- 💾 **SQLite History Engine & Comparison:** Local, privacy-first SQLite repository (`sim_history.db`) with automatic rolling 100-run pruning, top-50 UI display, and a dedicated side-by-side comparative dashboard.
- 📊 **Deep-Dive Analytics Dashboard:**
  - **Radar Charts:** Compare Eco, Cost, and Tech dimensions visually.
  - **Tornado Charts:** Perform instant sensitivity analysis on Carbon Footprints (e.g., how does a ±20% swing in grid emissions impact the module?).
  - **System Carbon Stacked Chart:** Visualizes $GWP_{module}$ vs $GWP_{inverter}$ vs $GWP_{BOS}$.
- 💼 **Executive Financial Layer:** Input your *Project Size (MWp)* and *PPA Rate (€/MWh)* to dynamically generate:
  - Net Present Value (NPV)
  - Payback Periods & Lifetime Revenue
  - CBAM Import Tax Exposure calculations
  - **Elevator Pitch Generator:** Ready-to-copy executive summaries for stakeholders.

---

## 🆕 Version Release History

### **v0.2.0 - Executive PDF Export & Precision Engine Release (Current)**
- 📄 **C-Suite Procurement Briefing PDF Export:** One-click generation of formal 2-page PDF executive briefs using ReportLab.
- 🎯 **LCOE TOPSIS Matrix Re-Weighting:** Re-aligned Utility Scale TOPSIS weights (75% LCOE preference) so the lowest LCOE module strictly leads the leaderboard.
- 🧹 **EPD Outlier Filtering:** Automatically filters out corrupted module area inputs (>24.5% efficiency outliers) ensuring 100% physically accurate commercial module pricing.
- 💾 **Rolling SQLite History & Clear Button:** Automatically caps simulation history at 100 runs in SQLite and adds a one-click "Clear History" button with confirmation prompts.

### **v0.1.0 - Initial Desktop & Financial Engine Release**
- **Pareto Trade-Off Surface:** Interactive multi-objective scatter chart evaluating LCOE vs Carbon Footprint.
- **Simulation Run History:** Local SQLite database logging previous runs with side-by-side run comparisons.
- **Inverter & BOS Engine:** Auto-pairing inverter selection and racking/cabling embodied carbon stack.

---

## 🚀 Launching the Software
The application is compiled into a single portable `.exe` using PyInstaller and Electron-Builder.

1. Locate the standalone executable file: `EPC Solar Engine 0.2.0.exe` in the main folder.
2. **Double-click** to run it natively on Windows (no installation required).
3. The background Python physics engine and React UI will spin up automatically!

---

## 🌐 Public Demo & Marketing
A stripped-down Alpha version of this software has been deployed to the web to showcase the core functionality and market the tool.
- **Marketing Page & Demo:** See the [EPC Solar Public Repository](https://github.com/Realsinister/epc-solar-landing-page) for the public-facing landing page and alpha web demo.
- **Software Website:** [EPC Solar Engine Website](https://realsinister.github.io/epc-solar-landing-page/)

---

## 🛠️ Architecture
- **Backend:** `FastAPI`, `ReportLab`, `Pydantic`, `Pandas` (Frozen into an executable via PyInstaller).
- **Frontend:** `React`, `Vite`, `Recharts` for interactive graphing, and `TailwindCSS` (glassmorphism tokens).
- **Desktop Wrapper:** `Electron` to merge the frontend and background processes into a seamless native OS window.

---

## 🔮 Future Roadmap (Scale-Ready)
- **Custom EPD & Vendor Data Upload (Phase 3)**
- **8,760-Hour Irradiance Profiles & Diurnal Weather Modeling (Phase 4)**
- **Battery Storage (BESS) LCA Integration (Phase 5)**
- **AI Predictive Integration:** Machine Learning models to forecast yield degradation and predict long-term financial impacts based on local climate data.

---
*Developed as a premium solution for solar engineering procurement.*

👨‍💻 **Connect with the developer:** [Yash J Gupta on LinkedIn](https://www.linkedin.com/in/yashjgupta/)
