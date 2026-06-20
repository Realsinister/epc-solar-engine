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
- ⚡ **Standalone Desktop Experience:** No more python terminals or complex setups. Double-click the installer and launch the app offline.
- 🧮 **Physics-based MCDA Engine:** A Python/FastAPI backend instantly scores modules based on dynamic weighting of Cost, Performance, and Eco-Footprint.
- 🎨 **Premium UI/UX:** Built with React & Vite, featuring a sleek dark-mode glassmorphism interface and interactive leaderboards.
- 📊 **Deep-Dive Analytics Dashboard:**
  - **Radar Charts:** Compare Eco, Cost, and Tech dimensions visually.
  - **Tornado Charts:** Perform instant sensitivity analysis on Carbon Footprints (e.g., how does a ±20% swing in grid emissions impact the module?).
- 💼 **Executive Financial Layer:** Input your *Project Size (MWp)* and *PPA Rate (€/MWh)* to dynamically generate:
  - Net Present Value (NPV)
  - Payback Periods & Lifetime Revenue
  - CBAM Import Tax Exposure calculations
  - **Elevator Pitch Generator:** Ready-to-copy executive summaries for stakeholders.

## 🆕 What's New in v0.1.0
- **Interactive Sandbox:** The left sidebar inputs are now "sticky", allowing you to tweak simulation parameters on the fly without losing sight of the bottom charts.
- **Dynamic Pareto Grid:** The Top 3 modules are displayed in a wide horizontal grid at the bottom. Clicking any module dynamically updates the radar charts, sensitivity analysis, and Executive Financial Pitch to strictly reflect that specific module's data.
- **Smart Stale-State Animation:** The "Run Simulation" button instantly turns grayscale and shakes if you tweak inputs after a run, reminding you to update the simulation.
- **Portable Architecture:** The software is now compiled into a standalone, portable `.exe` file that doesn't even require installation.

## 🚀 Launching the Software
The application has been compiled into a single portable `.exe` using PyInstaller and Electron-Builder.

1. Locate the standalone executable file: `EPC Solar Engine 0.1.0.exe` in the main folder.
2. **Double-click** to run it natively on Windows (no installation required).
3. The background Python physics engine and React UI will spin up automatically!

## 🛠️ Architecture
- **Backend:** `FastAPI`, `Pydantic`, `Pandas` (Frozen into an executable via PyInstaller).
- **Frontend:** `React`, `Vite`, `Recharts` for interactive graphing, and `TailwindCSS` (glassmorphism tokens).
- **Desktop Wrapper:** `Electron` to merge the frontend and background processes into a seamless native OS window.

## 🔮 Future Roadmap (Scale-Ready)
The Python engine's architecture has been strictly modularized. Future expansions will easily plug into the existing Executive Financial Model:
- **Inverter Clipping Models**
- **Hourly Irradiance Profiles**
- **Battery Storage LCA Integration**
- **AI Predictive Integration:** Machine Learning models to forecast yield degradation and predict long-term financial impacts based on local climate data.
- **User Profiles & Simulation History Database:** SQLite-backed local repository to store historical simulation inputs and results, supporting side-by-side comparative analysis of multiple runs.

---
*Developed as a premium solution for solar engineering procurement.*

👨‍💻 **Connect with the developer:** [Yash J Gupta on LinkedIn](https://www.linkedin.com/in/yashjgupta/)
