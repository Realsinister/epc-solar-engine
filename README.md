<div align="center">
  <img src="https://img.shields.io/badge/Status-Premium_Desktop_App-green?style=for-the-badge&logo=electron" alt="Status" />
  <img src="https://img.shields.io/badge/Engine-FastAPI%20%2B%20Python-blue?style=for-the-badge&logo=fastapi" alt="Backend" />
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react" alt="Frontend" />
  <h1>EPC Solar Engine</h1>
  <p><strong>A Next-Generation Standalone Desktop Software for PV Module Analysis, Multi-Criteria Decision Making (MCDA), and Executive Financial Modeling.</strong></p>
</div>

---

![EPC Solar Engine Main Dashboard](docs/screenshots/hero_dashboard.png)

---

## 🌟 Overview
**EPC Solar Engine** has officially evolved into a powerful, **standalone Windows desktop application**. Tailored for EPC (Engineering, Procurement, and Construction) firms, this software seamlessly combines real-time Physics calculations with advanced Multi-Criteria Decision Analysis (MCDA), Multi-Block Module Hybridization, and a dedicated Executive Financial Dashboard.

This tool acts as your ultimate "pitch generator" for PV module procurement, calculating real-world technical yields, Scope 3 embodied carbon footprints (LCA), and massive project-scale economics instantly.

---

## 🖼️ Visual Feature Showcase

### 💼 Executive Financials & Multi-Block Hybridization
![Executive Financials & Hybridization](docs/screenshots/executive_financials_hybrid.png)
- **Multi-Block Hybrid Deployment:** Intelligently pairs primary LCOE leader modules with secondary carbon-offset modules across inverter blocks while enforcing strict 100% MPPT & string uniformity.
- **Actionable Economics:** Calculates project Net Present Value (NPV), Payback Period, Lifetime Revenue, and European Carbon Border Adjustment Mechanism (CBAM) tax liabilities.
- **1-Click Executive PDF Briefing Export:** Instant generation of formal 2-page C-Suite Procurement Briefing PDF reports with embedded board pitch defenses.

### 📊 Deep-Dive Analytics & Sensitivity
![Deep-Dive Analytics](docs/screenshots/deep_dive_analytics.png)
- **Dimension Balance Radar Chart:** Visually evaluates tradeoffs across Eco (Carbon), Cost (LCOE), and Tech (Efficiency) dimensions.
- **Carbon Swing Tornado Sensitivity:** Maps exact ±20% impacts of ambient temperature, specific yield, and lifetime variations on carbon footprints.

### 🌿 System Embodied Carbon Stack Breakdown
![System Carbon Stack](docs/screenshots/system_carbon_stack.png)
- **Scope 3 Life Cycle Assessment (LCA):** Visualizes $GWP_{Module}$ net of EoL credit vs $GWP_{Inverter}$ vs $GWP_{BOS}$ racking and electrical cabling.

### 💾 SQLite Simulation History & Comparison
![Simulation History](docs/screenshots/simulation_history.png)
- **Privacy-First Local History:** Automatically logs simulation runs in a local SQLite repository (`sim_history.db`) with rolling 100-run auto-pruning and a dedicated side-by-side comparative dashboard.

---

## ✨ Key Features
- ⚡ **Standalone Desktop Experience:** Double-click the installer and launch natively on Windows (no Python setup required).
- 🧮 **Physics-based MCDA Engine:** A Python/FastAPI backend scores modules based on dynamic weighting using vector TOPSIS algorithms.
- 🎨 **Premium Glassmorphism UI:** Built with React & Vite, featuring a sleek dark-mode glassmorphism interface and interactive leaderboards.
- 📈 **Interactive Pareto Trade-Off Frontier:** 2D Scatter plot mapping **System LCOE (€/MWh)** vs **System Embodied Carbon (kgCO2e/kWp)** with TOPSIS-weighted bubble scaling.
- 🔌 **Inverter Database & BOS Configurator:** Real-world inverter dataset (Sungrow, SMA, Huawei, SolarEdge) with dynamic DC/AC ratio clipping and Year 15 inverter replacement CAPEX modeling.
- 📁 **Custom EPD & Vendor Data Upload:** Ingest custom CSV/Excel vendor quotes directly into the calculation engine.

---

## 🆕 Version Release History

### **v0.3.0 - Multi-Block Hybridization & UI Layout Release (Current)**
- 🏢 **Multi-Block Hybrid Strategy:** Block-level sub-array allocation pairing primary LCOE leaders with secondary carbon-offset panels.
- 🖼️ **Symmetric Responsive Layout:** Optimized 3-column homepage parameter grid and un-squished 350px chart deck.
- 📄 **ReportLab PDF Header Refinement:** Formalized 2-page C-Suite Procurement Briefing document headers.

### **v0.2.0 - Executive PDF Export & Precision Engine Release**
- 📄 **C-Suite Procurement Briefing PDF Export:** One-click generation of formal 2-page PDF executive briefs using ReportLab.
- 🎯 **LCOE TOPSIS Matrix Re-Weighting:** Re-aligned Utility Scale TOPSIS weights so lowest LCOE strictly leads rankings.
- 🧹 **EPD Outlier Filtering:** Automatically filters corrupted module area inputs (>24.5% efficiency outliers).

---

## 🚀 Launching the Software
The application is compiled into a single portable `.exe` using PyInstaller and Electron-Builder.

1. Locate the standalone executable file: `EPC Solar Engine 0.3.0.exe` in the main folder.
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
- **8,760-Hour Irradiance Profiles & Diurnal Weather Modeling (Phase 4)**
- **Battery Storage (BESS) LCA Integration (Phase 5)**
- **AI Predictive Integration:** Machine Learning models to forecast yield degradation and predict long-term financial impacts based on local climate data.

---

*Developed as a premium solution for solar engineering procurement.*

👨‍💻 **Connect with the developer:** [Yash J Gupta on LinkedIn](https://www.linkedin.com/in/yashjgupta/)
