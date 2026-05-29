import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np
from io import BytesIO
import sys
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# ---------- 1. Page Configuration (MUST BE FIRST) ----------
st.set_page_config(
    page_title="PV LCA Decision Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add src to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from pv_engine import PVEngine
from pv_engine.config import LOCATION_PRESETS, ProjectDefaults
from pv_engine.report_gen import ReportGenerator
from pv_engine.database import load_epds_as_dataframe, init_db
from pv_engine.environdec_client import EnvirondecClient

# ---------- 0. Authentication ----------
with open('auth_config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render the login widget
authenticator.login('main')

if st.session_state["authentication_status"] == False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] == None:
    st.warning('Please enter your username and password')
elif st.session_state["authentication_status"]:
    name = st.session_state["name"]
    username = st.session_state["username"]
    # --- LOGOUT BUTTON IN SIDEBAR ---
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.write(f'Welcome *{name}*')

    # --- CSS STYLING ---
    st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        div[data-testid="stMetric"] {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 8px;
            padding: 10px;
        }
        .recommendation-box {
            border-left: 5px solid #27ae60;
            background-color: rgba(39, 174, 96, 0.1);
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)
    # ---------- 2. Data Loading ----------
    WB = "data/EPD_Hub_V3_PV_master_curated_v1.xlsx"
    TARGET_SHEET = "INDICATORS_NORMALIZED"
    REQUIRED_COLUMNS = ['manufacturer', 'name', 'module_power_Wp', 'module_area_m2', 'GWP_total_A1A3_per_kWp_kgCO2e']

    @st.cache_data
    def load_master_data():
        try:
            xl = pd.ExcelFile(WB)
            sheet_names = xl.sheet_names
            load_sheet = TARGET_SHEET if TARGET_SHEET in sheet_names else sheet_names[0]
            df = pd.read_excel(WB, sheet_name=load_sheet)
            df = PVEngine.process_dataframe(df)
            return PVEngine.validate_data(df)
        except Exception as e:
            st.error(f"Critical Data Error: {e}")
            return pd.DataFrame()

    df_master = load_master_data()
    
    # Load EPDs from SQLite
    try:
        init_db() # Ensure DB is initialized
        df_epd = load_epds_as_dataframe()
        if not df_epd.empty:
            df_epd['module_area_m2'] = 2.0  # Approx default for 1kWp
            df_epd['module_power_Wp'] = df_epd['power_wp']
            df_master = pd.concat([df_epd, df_master], ignore_index=True)
    except Exception as e:
        st.warning(f"Could not load live EPD database: {e}")

    # (Pre-calculate some initial variables for the reporting sidebar)
    selected_loc = "🇩🇪 Germany (Berlin)" # Placeholder for initial load
    scenario = "Eco-Flagship (Minimize Carbon)" # Placeholder

    # We need to compute metrics first to have a 'winner' for the report generator in sidebar
    # However, sidebar is rendered before main content. Let's compute a default winner.
    df_init = df_master.copy()
    df_init = PVEngine.calculate_metrics(df_init, 1050, 5.0, 30, 0.22, 0.45, 15.0, 80.0, 85.0)
    df_init, _ = PVEngine.normalize_scores(df_init, scenario)
    df_init = PVEngine.calculate_topsis(df_init, scenario)
    default_winner = df_init.iloc[0]

    # ---------- 3. Sidebar: Data Manager ----------
    st.sidebar.title("📂 Data Manager")

    # NEW: Export Report Button
    st.sidebar.subheader("📄 Reporting")
    pdf_report = ReportGenerator.generate_decision_report(default_winner, scenario, selected_loc)
    st.sidebar.download_button(
        label="📥 Export Decision Report (PDF)",
        data=pdf_report,
        file_name=f"PV_Decision_Report_{selected_loc.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

    st.sidebar.divider()

    with st.sidebar.expander("➕ Import Project Database", expanded=False):
        st.info(
            """
            **How to Import:**
            1. Download the **Blank Template** below.
            2. Fill in the 5 mandatory columns:
               - `manufacturer` & `name` (Text)
               - `module_power_Wp` (e.g., 450)
               - `module_area_m2` (e.g., 2.1)
               - `GWP_total_A1A3_per_kWp_kgCO2e` (e.g., 450.5)
            3. Upload the CSV back here.
            """
        )

        template_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        csv_template = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Blank Template (CSV)",
            data=csv_template,
            file_name="module_import_template.csv",
            mime="text/csv"
        )

        uploaded_file = st.file_uploader("Upload Filled CSV", type=["csv"])

        if uploaded_file is not None:
            try:
                df_new = pd.read_csv(uploaded_file)
                df_new['source'] = "Custom Import"
                df_new = PVEngine.process_dataframe(df_new)
                df_new = PVEngine.validate_data(df_new)
                df_master = pd.concat([df_new, df_master], ignore_index=True)
                st.success(f"✅ Loaded {len(df_new)} custom modules!")
            except Exception as e:
                st.error(f"Import Failed: Data does not meet industry standards. {e}")

    # ---------- 4. Sidebar: Project Scenarios ----------
    st.sidebar.divider()
    st.sidebar.subheader("🏗️ Optimization Setup")

    selected_loc = st.sidebar.selectbox("📍 Select Project Location", list(LOCATION_PRESETS.keys()))
    defaults = LOCATION_PRESETS[selected_loc]

    scenario = st.sidebar.selectbox(
        "Optimization Goal",
        ["Eco-Flagship (Minimize Carbon)", "Utility Scale (Lowest LCOE)", "Space Constrained (Rooftop)"],
        index=0
    )

    with st.sidebar.expander("⚙️ Technical Specs", expanded=False):
        base_irradiance = st.number_input("Specific Yield (kWh/kWp/yr)", min_value=500, max_value=2600, value=int(defaults.yield_kwh))
        lifetime = st.slider("Project Lifetime (Years)", 10, 40, ProjectDefaults().lifetime_years)
        temp_loss = st.slider("Temp. Loss Factor (%)", 0.0, 25.0, defaults.temp_loss)

    with st.sidebar.expander("💰 Market Assumptions", expanded=False):
        avg_price_wp = st.number_input("Avg. Module Price (€/Wp)", 0.08, 1.50, ProjectDefaults().avg_price_wp_eur, 0.01)
        bos_cost_wp = st.number_input("BOS Cost (€/Wp)", 0.20, 3.00, ProjectDefaults().bos_cost_wp_eur)
        opex_annual = st.number_input("O&M Cost (€/kWp/yr)", 2.0, 100.0, ProjectDefaults().opex_annual_eur_kwp)

    with st.sidebar.expander("♻️ Compliance & EoL", expanded=False):
        cbam_tax = st.number_input("CBAM Tax (€/tonne CO2e)", 0.0, 200.0, 80.0)
        eol_recycling = st.slider("EoL Recycling Rate (%)", 0.0, 100.0, 85.0)

    # Filter
    if 'manufacturer' in df_master.columns:
        manufacturers = sorted(df_master['manufacturer'].dropna().astype(str).unique())
        selected_mfg = st.sidebar.multiselect("Filter Brand", manufacturers)
    else:
        selected_mfg = []

    # ---------- 5. Calculation Engine ----------
    df_calc = df_master.copy()
    if selected_mfg:
        df_calc = df_calc[df_calc['manufacturer'].astype(str).isin(selected_mfg)]

    # Run Calculations via Engine
    df_calc = PVEngine.calculate_metrics(
        df_calc, base_irradiance, temp_loss, lifetime, 
        avg_price_wp, bos_cost_wp, opex_annual,
        cbam_tax_rate_eur_t=cbam_tax,
        eol_recycling_rate_pct=eol_recycling
    )
    # Normalize and Score
    df_calc, weights = PVEngine.normalize_scores(df_calc, scenario)
    df_calc = PVEngine.calculate_topsis(df_calc, scenario)
    w_eco, w_cost, w_tech = weights
    winner = df_calc.iloc[0]

    # ---------- 6. Dashboard ----------
    st.title(f"PV LCA Optimization Engine v1.4")

    if 'Custom Import' in df_calc['source'].values:
        st.info("ℹ️ Displaying results including imported custom data.")

    st.markdown(f"""
    <div class="recommendation-box">
        <h3>🏆 Optimal Choice: {winner['manufacturer']} {str(winner['name'])[:20]}...</h3>
        <p>Based on the <b>{selected_loc}</b> location profile and <b>{scenario}</b> strategy.</p>
        <ul>
            <li><b>Suitability Index:</b> {winner['Suitability_Index']:.1f}/100</li>
            <li><b>TOPSIS Reliability:</b> {winner['TOPSIS_Score']:.1f}/100</li>
            <li><b>Est. LCOE:</b> {winner['LCOE_EUR_MWh']:.2f} €/MWh</li>
            <li><b>Carbon Intensity:</b> {winner['Carbon_Intensity_Mean']:.1f} gCO2e/kWh</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🕸️ MCDA Analysis", "📊 Stochastic Risk", "🌪️ Sensitivity", "💾 Raw Data", "🗄️ Live EPD DB"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Trade-off Topology")
            categories = ['Low Carbon', 'Low Cost (LCOE)', 'High Efficiency']
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[winner['Score_Eco'], winner['Score_Cost'], winner['Score_Tech']],
                theta=categories, fill='toself', name=f"Winner"
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=[df_calc['Score_Eco'].mean(), df_calc['Score_Cost'].mean(), df_calc['Score_Tech'].mean()],
                theta=categories, name='Market Avg', line=dict(color='gray', dash='dot')
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
            st.plotly_chart(fig_radar, use_container_width=True)
        with c2:
            st.markdown("**Optimization Weights:**")
            st.progress(w_eco, text=f"Environmental: {int(w_eco*100)}%")
            st.progress(w_cost, text=f"Economic: {int(w_cost*100)}%")
            st.progress(w_tech, text=f"Technical: {int(w_tech*100)}%")

    with tab2:
        st.subheader("Risk Analysis (Monte Carlo N=1000)")
        top_3 = df_calc.head(3)
        effective_yield = base_irradiance * (1 - (temp_loss / 100))

        df_sim_list = []
        for _, row in top_3.iterrows():
            df_sim_list.append(PVEngine.run_monte_carlo(row, effective_yield, lifetime))

        df_sim = pd.concat(df_sim_list, ignore_index=True)
        fig_mc = px.histogram(df_sim, x="Intensity (g/kWh)", color="Module", barmode="overlay", nbins=50, opacity=0.7)
        st.plotly_chart(fig_mc, use_container_width=True)

    with tab3:
        st.subheader("Sensitivity Analysis (Tornado Plot)")
        st.markdown("How much do project parameters impact the outcome of the **Winner**?")

        base_params = {
            'yield': base_irradiance,
            'temp_loss': temp_loss,
            'lifetime': lifetime,
            'avg_price_wp': avg_price_wp,
            'bos_cost_wp': bos_cost_wp,
            'opex_annual': opex_annual
        }

        df_sens = PVEngine.run_sensitivity_analysis(winner, base_params)

        metric_to_show = st.radio("Select Sensitivity Metric", ["Carbon Intensity", "LCOE"])
        df_plot = df_sens[df_sens['Metric'] == metric_to_show]

        fig_tornado = go.Figure()
        fig_tornado.add_trace(go.Bar(
            y=df_plot['Parameter'], x=df_plot['Low'], name='Low (-20%)',
            orientation='h', marker_color='red'
        ))
        fig_tornado.add_trace(go.Bar(
            y=df_plot['Parameter'], x=df_plot['High'], name='High (+20%)',
            orientation='h', marker_color='blue'
        ))
        fig_tornado.update_layout(barmode='relative', title=f"Sensitivity of {metric_to_show} (Delta from Baseline)")
        st.plotly_chart(fig_tornado, use_container_width=True)

    with tab4:
        cols = ['manufacturer', 'name', 'Suitability_Index', 'TOPSIS_Score', 'Carbon_Intensity_Mean', 'LCOE_EUR_MWh', 'Efficiency_Pct', 'source']
        st.dataframe(df_calc[cols].style.background_gradient(subset=['Suitability_Index', 'TOPSIS_Score'], cmap='Greens'), use_container_width=True)

    with tab5:
        st.subheader("Live EPD Database (Environdec API)")
        st.markdown("Search the global Environdec registry and add modules to your local project database for comparison.")
        
        search_q = st.text_input("Search Module (e.g. 'Tiger Neo' or 'Vertex')")
        if st.button("Fetch from API"):
            with st.spinner("Connecting to Environdec API..."):
                client = EnvirondecClient()
                results = client.fetch_pv_epds(search_q)
                if results:
                    st.success(f"Found {len(results)} matching EPDs!")
                    st.dataframe(pd.DataFrame(results))
                    client.sync_to_db(results)
                    st.info("Synced to local database. Please refresh the page to include them in the calculation engine.")
                else:
                    st.warning("No EPDs found.")