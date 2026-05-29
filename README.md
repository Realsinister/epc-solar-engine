# PV LCA Decision Engine v1.4

## Overview
A production-grade Multi-Criteria Decision Analysis (MCDA) engine for sustainable photovoltaic (PV) procurement. This tool transforms Environmental Product Declaration (EPD) data into actionable insights, helping stakeholders choose modules based on real-world Carbon Intensity and LCOE.

## Key Features
- **Robust Scoring:** Uses **TOPSIS** (Technique for Order of Preference by Similarity to Ideal Solution) for reliable multi-variable ranking.
- **Risk Assessment:** Integrated **Monte Carlo** simulations (N=1000) to model environmental uncertainty.
- **Sensitivity Analysis:** Interactive **Tornado Plots** to identify critical project drivers.
- **Professional Reporting:** Automated PDF generation for executive procurement decisions.
- **Enterprise Security:** Built-in authentication and role-based access hints.
- **Data Integrity:** Strict schema validation via **Pandera**.

## Technical Architecture
- **Engine:** Decoupled core logic in `src/pv_engine/`.
- **UI:** Streamlit-based interactive dashboard.
- **Reporting:** ReportLab for dynamic PDF creation.
- **Validation:** Pydantic for configuration, Pandera for data.

## Getting Started

### Prerequisites
- Python 3.10+
- Virtual Environment (recommended)

### Installation
```bash
pip install -r requirements.txt
```

### Running the App
```bash
streamlit run streamlit_app.py
```

### Default Credentials
- **Admin:** `admin` / `admin123`
- **Analyst:** `analyst` / `admin123`
*(Note: Change these in `auth_config.yaml` for production)*

## Deployment (Docker)
A `Dockerfile` is provided for containerized deployment.
```bash
docker build -t pv-lca-engine .
docker run -p 8501:8501 pv-lca-engine
```

## Testing
Run unit tests to verify calculation accuracy:
```bash
pytest tests/
```
