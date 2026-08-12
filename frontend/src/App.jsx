import { useState, useEffect } from 'react';
import NavbarHeader from './components/NavbarHeader';
import IconSidebar from './components/IconSidebar';
import SidebarParameters from './components/SidebarParameters';
import ExecutiveFinancialView from './components/ExecutiveFinancialView';
import DeepDiveAnalyticsView from './components/DeepDiveAnalyticsView';
import MultiBlockFleetView from './components/MultiBlockFleetView';
import HistoryCompare from './HistoryCompare';
import CustomEpdUpload from './CustomEpdUpload';
import { Sun, Activity, Zap, Layers } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [subView, setSubView] = useState('financials'); // 'financials' | 'analytics' | 'hybrid'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState([]);
  const [hasSimulated, setHasSimulated] = useState(false);
  const [isStale, setIsStale] = useState(false);
  
  // Selected Module State for Deep Dive
  const [selectedModule, setSelectedModule] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [exportingPdf, setExportingPdf] = useState(false);

  // Inverter & System State
  const [inverters, setInverters] = useState([]);
  const [selectedInverterId, setSelectedInverterId] = useState('auto');
  const [targetDcAcRatio, setTargetDcAcRatio] = useState(1.25);

  const handleExportPdf = async () => {
    if (!selectedModule) return;
    setExportingPdf(true);
    try {
      const actualSizeMwp = params.project_size_unit === 'kWp' ? params.project_size_mwp / 1000 : params.project_size_mwp;
      const payload = {
        ...params,
        project_size_mwp: actualSizeMwp,
        ground_albedo: params.ground_albedo === "None" ? null : parseFloat(params.ground_albedo),
        inverter_id: selectedInverterId,
        target_dc_ac_ratio: targetDcAcRatio
      };

      const res = await fetch(`http://127.0.0.1:8000/api/export-pdf/${selectedModule.dataset_uuid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Executive_Procurement_Briefing_${selectedModule.name || 'Module'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export PDF", err);
    } finally {
      setExportingPdf(false);
    }
  };

  // Load Inverters on Mount
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/inverters')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setInverters(data);
      })
      .catch(err => console.error("Failed to fetch inverters", err));
  }, []);

  // Controls / Parameters State
  const [params, setParams] = useState({
    base_irradiance: 1050,
    ambient_temp_c: 25.0,
    lifetime: 30,
    avg_price_wp: 0.22,
    bos_cost_wp: 0.45,
    opex_annual: 15.0,
    cbam_tax_rate_eur_t: 80.0,
    eol_recycling_rate_pct: 85.0,
    system_topology: "Fixed Tilt",
    ground_albedo: "None",
    scenario: "Eco-Flagship (Minimize Carbon)",
    project_size_mwp: 50.0,
    project_size_unit: "MWp",
    ppa_rate_eur_mwh: 45.0,
    discount_rate_pct: 5.0
  });

  const handleSimulate = async () => {
    setLoading(true);
    setHasSimulated(true);
    setIsStale(false);
    try {
      const rawSize = parseFloat(params.project_size_mwp) || 50.0;
      const actualSizeMwp = params.project_size_unit === 'kWp' ? rawSize / 1000 : rawSize;

      const payload = {
        base_irradiance: parseFloat(params.base_irradiance) || 1050.0,
        ambient_temp_c: parseFloat(params.ambient_temp_c) || 25.0,
        lifetime: parseInt(params.lifetime) || 30,
        avg_price_wp: parseFloat(params.avg_price_wp) || 0.22,
        bos_cost_wp: parseFloat(params.bos_cost_wp) || 0.45,
        opex_annual: parseFloat(params.opex_annual) || 15.0,
        cbam_tax_rate_eur_t: parseFloat(params.cbam_tax_rate_eur_t) || 80.0,
        eol_recycling_rate_pct: parseFloat(params.eol_recycling_rate_pct) || 85.0,
        system_topology: params.system_topology || "Fixed Tilt",
        ground_albedo: params.ground_albedo === "None" || !params.ground_albedo ? null : parseFloat(params.ground_albedo),
        scenario: params.scenario || "Eco-Flagship (Minimize Carbon)",
        project_size_mwp: actualSizeMwp,
        project_size_unit: params.project_size_unit || "MWp",
        ppa_rate_eur_mwh: parseFloat(params.ppa_rate_eur_mwh) || 45.0,
        discount_rate_pct: parseFloat(params.discount_rate_pct) || 5.0,
        inverter_id: selectedInverterId || "auto",
        target_dc_ac_ratio: parseFloat(targetDcAcRatio) || 1.25
      };

      const res = await fetch('http://127.0.0.1:8000/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        console.error("API error response:", data);
        alert("Calculation Engine Error: " + (data.detail || JSON.stringify(data)));
        setResults([]);
        return;
      }

      const moduleList = Array.isArray(data) ? data : (data.results || []);
      setResults(moduleList);

      if (data.initial_analysis) {
        setAnalysisData(data.initial_analysis);
      }
      
      // Auto-select #1 TOPSIS module if available
      if (moduleList.length > 0) {
        handleModuleSelect(moduleList[0]);
      }
    } catch (err) {
      console.error("Simulation failed", err);
      alert("Simulation connection error: " + err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleModuleSelect = async (module) => {
    setSelectedModule(module);
    setAnalyzing(true);
    try {
      const actualSizeMwp = params.project_size_unit === 'kWp' ? params.project_size_mwp / 1000 : params.project_size_mwp;
      const payload = {
        ...params,
        project_size_mwp: actualSizeMwp,
        ground_albedo: params.ground_albedo === "None" ? null : parseFloat(params.ground_albedo),
        inverter_id: selectedInverterId,
        target_dc_ac_ratio: targetDcAcRatio
      };

      const res = await fetch(`http://127.0.0.1:8000/api/analyze/${module.dataset_uuid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setAnalysisData(data);
    } catch (err) {
      console.error("Analysis failed", err);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="app-root-shell">
      {/* TOP EXECUTIVE NAVBAR HEADER */}
      <NavbarHeader 
        params={params}
        selectedModule={selectedModule}
        handleExportPdf={handleExportPdf}
        exportingPdf={exportingPdf}
        hasSimulated={hasSimulated}
      />

      <div className="main-app-container">
        {/* ICON NAVIGATION RAIL */}
        <IconSidebar 
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          subView={subView}
          setSubView={setSubView}
          hasSimulated={hasSimulated}
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
        />

        {/* PARAMETERS SIDEBAR DRAWER (Only when on Dashboard) */}
        {activeTab === 'dashboard' && (
          <SidebarParameters 
            params={params}
            setParams={setParams}
            handleSimulate={handleSimulate}
            loading={loading}
            isStale={isStale}
            setIsStale={setIsStale}
            hasSimulated={hasSimulated}
            selectedInverterId={selectedInverterId}
            setSelectedInverterId={setSelectedInverterId}
            inverters={inverters}
            targetDcAcRatio={targetDcAcRatio}
            setTargetDcAcRatio={setTargetDcAcRatio}
          />
        )}

        {/* MAIN VIEW CONTENT AREA */}
        <main className="view-content-area">
          {activeTab === 'dashboard' && (
            hasSimulated ? (
              <>
                {subView === 'financials' && (
                  <ExecutiveFinancialView 
                    results={results}
                    selectedModule={selectedModule}
                    handleModuleSelect={handleModuleSelect}
                    analysisData={analysisData}
                    params={params}
                    handleExportPdf={handleExportPdf}
                    exportingPdf={exportingPdf}
                  />
                )}

                {subView === 'analytics' && (
                  <DeepDiveAnalyticsView 
                    results={results}
                    selectedModule={selectedModule}
                    handleModuleSelect={handleModuleSelect}
                    analysisData={analysisData}
                    analyzing={analyzing}
                  />
                )}

                {subView === 'hybrid' && (
                  <MultiBlockFleetView 
                    results={results}
                    selectedModule={selectedModule}
                    inverters={inverters}
                    selectedInverterId={selectedInverterId}
                    setSelectedInverterId={setSelectedInverterId}
                    targetDcAcRatio={targetDcAcRatio}
                    setTargetDcAcRatio={setTargetDcAcRatio}
                    params={params}
                  />
                )}
              </>
            ) : (
              /* WELCOMING INITIAL STATE (BEFORE SIMULATION) */
              <div className="glass-panel welcome-card fade-in" style={{ textAlign: 'center', padding: '60px 40px', marginTop: '40px' }}>
                <div className="logo-icon-bg" style={{ margin: '0 auto 16px', width: '56px', height: '56px' }}>
                  <Sun size={28} color="#38bdf8" />
                </div>
                <h2 style={{ fontSize: '1.6rem', marginBottom: '8px' }}>
                  Welcome to <span className="text-gradient">EPC Solar Engine</span>
                </h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '560px', margin: '0 auto 24px', fontSize: '0.95rem' }}>
                  An executive decision and procurement platform designed to sit alongside engineering CAD tools like PVsyst and Helioscope. Configure your parameters on the left and run the physics engine.
                </p>
                <button 
                  onClick={handleSimulate} 
                  disabled={loading}
                  className="btn-simulate-glow" 
                  style={{ maxWidth: '320px', margin: '0 auto' }}
                >
                  {loading ? 'Running MCDA Simulation...' : '🚀 Launch Physics Engine Simulation'}
                </button>
              </div>
            )
          )}

          {activeTab === 'vendor_data' && <CustomEpdUpload />}
          {activeTab === 'history' && <HistoryCompare />}
        </main>
      </div>
    </div>
  );
}

export default App;
