import { useState, useEffect } from 'react';
import { Sliders, Zap, Leaf, Truck, Activity, Target } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis 
} from 'recharts';

function App() {
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState([]);
  const [hasSimulated, setHasSimulated] = useState(false);
  const [isStale, setIsStale] = useState(false);
  
  // Selected Module State for Deep Dive
  const [selectedModule, setSelectedModule] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);

  // Physics Parameters State
  const [params, setParams] = useState({
    base_irradiance: 1050,
    ambient_temp_c: 25.0,
    lifetime: 30,
    avg_price_wp: 0.22,
    bos_cost_wp: 0.45,
    opex_annual: 15.0,
    cbam_tax_rate_eur_t: 80.0,
    eol_recycling_rate_pct: 85.0,
    transport_distance_km: 20000.0,
    scenario: "Eco-Flagship (Minimize Carbon)",
    project_size_mwp: 50.0,
    ppa_rate_eur_mwh: 45.0,
    discount_rate_pct: 5.0
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setParams(prev => ({ 
      ...prev, 
      [name]: value === '' ? '' : (isNaN(value) ? value : Number(value)) 
    }));
    if (hasSimulated) setIsStale(true);
  };

  const calculateResults = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      const data = await response.json();
      setResults(data.results.slice(0, 10)); // Keep top 10 for Leaderboard
      
      // Trigger UI slide animation
      setHasSimulated(true);
      setIsStale(false);

      // Auto-select the #1 winner for deep dive
      if (data.results.length > 0) {
        handleModuleSelect(data.results[0]);
      }
    } catch (err) {
      console.error("Failed to connect to backend", err);
    }
    setLoading(false);
  };

  const handleModuleSelect = async (moduleRow) => {
    setSelectedModule(moduleRow);
    setAnalyzing(true);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/analyze/${moduleRow.dataset_uuid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      const data = await response.json();
      setAnalysisData(data);
    } catch (err) {
      console.error("Failed to fetch module analysis", err);
    }
    setAnalyzing(false);
  };

  // Wait for user to explicitly click Run to show animation
  useEffect(() => {
    // calculateResults();
  }, []);

  return (
    <>
      <div className="title-bar" />
      
      {/* HERO TITLE (Isolated from flexbox reflow) */}
      <div className={`home-hero ${hasSimulated ? 'hidden-hero' : ''}`}>
        <h1 style={{ fontSize: '3rem', letterSpacing: '-0.02em', marginBottom: '8px', color: 'white' }}>
          EPC Solar <span className="text-gradient">Engine</span>
        </h1>
        <p className="label-muted" style={{ fontSize: '1rem', marginTop: '10px' }}>MCDA Physics & Executive Financial Optimizer</p>
      </div>

      <div className={`app-wrapper ${hasSimulated ? 'layout-dashboard' : 'layout-home'}`}>
        
        {/* SIDEBAR CONTROLS */}
        <aside className="controls-sidebar">
          <div className="glass-panel">
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <Sliders size={20} color="var(--accent-cyan)" />
              <span className="text-gradient">Simulation Parameters</span>
            </h2>
            
            <div className="physics-inputs-grid">
              <div>
                <label className="label-muted">Optimization Scenario</label>
                <select className="input-glass" name="scenario" value={params.scenario} onChange={handleChange}>
                  <option value="Eco-Flagship (Minimize Carbon)">Eco-Flagship (Minimize Carbon)</option>
                  <option value="Utility Scale (Lowest LCOE)">Utility Scale (Lowest LCOE)</option>
                  <option value="Space Constrained">Space Constrained</option>
                </select>
              </div>

              <div>
                <label className="label-muted"><Leaf size={14} style={{display:'inline', marginRight: '4px'}}/> Ambient Temp (°C)</label>
                <input type="number" className="input-glass" name="ambient_temp_c" value={params.ambient_temp_c} onChange={handleChange} step="0.5" />
              </div>
              
              <div>
                <label className="label-muted"><Truck size={14} style={{display:'inline', marginRight: '4px'}}/> Transport Distance (km)</label>
                <input type="number" className="input-glass" name="transport_distance_km" value={params.transport_distance_km} onChange={handleChange} step="1000" />
              </div>

              <div>
                <label className="label-muted"><Zap size={14} style={{display:'inline', marginRight: '4px'}}/> Lifetime (Years)</label>
                <input type="number" className="input-glass" name="lifetime" value={params.lifetime} onChange={handleChange} />
              </div>

              <div className="executive-section">
                <h4 style={{ color: 'var(--accent-purple)', marginBottom: '12px' }}>Executive Financials</h4>
              </div>
                
              <div>
                <label className="label-muted">Project Size (MWp)</label>
                <input type="number" className="input-glass" name="project_size_mwp" value={params.project_size_mwp} onChange={handleChange} step="5" />
              </div>
              
              <div>
                <label className="label-muted">PPA Rate (€/MWh)</label>
                <input type="number" className="input-glass" name="ppa_rate_eur_mwh" value={params.ppa_rate_eur_mwh} onChange={handleChange} step="1" />
              </div>
            </div>

            <button 
              className={`btn-primary ${isStale ? 'btn-stale' : ''}`} 
              onClick={calculateResults}
            >
              {loading ? "Simulating..." : (isStale ? "Update Simulation" : "Run MCDA Simulation")}
            </button>
          </div>

          {/* LEADERBOARD LIST MOVED */}
        </aside>

        {/* MAIN VISUALIZATIONS */}
        <main className="main-content">
          
          {/* TOP BAR CHART */}
          <div className="glass-panel" style={{ height: '300px' }}>
            <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Target size={18} /> Market Overview (TOPSIS Score)
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={results} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <XAxis type="number" domain={[0, 100]} stroke="var(--border-highlight)" tick={{ fill: 'var(--text-muted)' }} />
                <YAxis dataKey="Display_Name" type="category" width={180} stroke="var(--text-muted)" style={{fontSize: '11px'}} />
                <Tooltip 
                  cursor={{fill: 'rgba(255,255,255,0.05)'}} 
                  contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-light)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-main)' }}
                />
                <Bar dataKey="TOPSIS_Score" radius={[0, 4, 4, 0]}>
                  {results.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={selectedModule?.dataset_uuid === entry.dataset_uuid ? "url(#colorGradient)" : "rgba(59, 130, 246, 0.4)"} 
                    />
                  ))}
                </Bar>
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* DEEP DIVE SECTION */}
          {selectedModule && analysisData && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                
                {/* RADAR CHART */}
                <div className="glass-panel" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ marginBottom: '8px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={18} /> Dimension Balance
                  </h3>
                  <div style={{ fontSize: '13px', color: 'var(--accent-blue)', marginBottom: '8px', fontWeight: '500' }}>
                    {selectedModule.Display_Name}
                  </div>
                  
                  {analyzing ? (
                    <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>Loading Analysis...</div>
                  ) : (
                    <div style={{ flexGrow: 1, minHeight: 0, width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={analysisData.radar}>
                          <PolarGrid stroke="var(--border-highlight)" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                          <Radar name="Score" dataKey="A" stroke="var(--accent-cyan)" fill="var(--accent-cyan)" fillOpacity={0.4} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-highlight)', borderRadius: '8px' }}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>

                {/* TORNADO CHART (SENSITIVITY) */}
                <div className="glass-panel" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ marginBottom: '8px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={18} /> Sensitivity Analysis (Carbon Swing)
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Impact of ±20% variation on {selectedModule.name}
                  </div>

                  {analyzing ? (
                    <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>Loading Analysis...</div>
                  ) : (
                    <div style={{ flexGrow: 1, minHeight: 0, width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analysisData.sensitivity.carbon} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }} stackOffset="sign">
                          <XAxis type="number" stroke="var(--border-highlight)" tick={{ fill: 'var(--text-muted)' }} />
                          <YAxis dataKey="Parameter" type="category" width={110} stroke="var(--text-muted)" style={{fontSize: '10px'}} />
                          <Tooltip 
                            cursor={{fill: 'rgba(255,255,255,0.05)'}}
                            contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-highlight)', borderRadius: '8px' }}
                          />
                          <Bar dataKey="Low" fill="#ef4444" stackId="stack" name="-20% Variation" />
                          <Bar dataKey="High" fill="#10b981" stackId="stack" name="+20% Variation" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>

                {/* EXECUTIVE FINANCIAL SUMMARY */}
                <div className="glass-panel" style={{ gridColumn: '1 / -1' }}>
                  <h3 style={{ marginBottom: '12px', color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={18} /> Executive Financial Projection ({params.project_size_mwp} MWp)
                  </h3>
                  
                  {analyzing ? (
                    <div style={{ color: 'var(--text-muted)' }}>Calculating ROI...</div>
                  ) : analysisData.executive ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid var(--accent-blue)' }}>
                          <div className="label-muted">Net Present Value (NPV)</div>
                          <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>€ {Number(analysisData.executive.npv_eur).toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                        </div>
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid var(--accent-green)' }}>
                          <div className="label-muted">Payback Period</div>
                          <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>{Number(analysisData.executive.payback_years).toFixed(1)} Years</div>
                        </div>
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid var(--accent-purple)' }}>
                          <div className="label-muted">Lifetime Revenue</div>
                          <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>€ {Number(analysisData.executive.total_lifetime_revenue_eur).toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                        </div>
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
                          <div className="label-muted">CBAM Tax Exposure</div>
                          <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>€ {Number(analysisData.executive.total_cbam_tax_eur).toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                        </div>
                      </div>
                      
                      <div style={{ padding: '16px', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', fontStyle: 'italic', lineHeight: '1.5' }}>
                        "{analysisData.executive.executive_pitch}"
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              {/* PARETO MODULES (Now in Main Deck) */}
              <div className="glass-panel" style={{ marginTop: '24px' }}>
                <h3 className="section-title">Top Pareto Modules</h3>
                <div className="pareto-wide-grid">
                  {results.slice(0, 3).map((result, idx) => (
                    <div 
                      key={idx} 
                      className={`pareto-item ${selectedModule?.dataset_uuid === result.dataset_uuid ? 'selected-pareto' : ''}`}
                      onClick={() => handleModuleSelect(result)}
                      style={{ cursor: 'pointer' }}
                    >
                      <span style={{color: 'var(--accent-blue)', fontWeight: 'bold'}}>#{idx + 1} - TOPSIS: {result.TOPSIS_Score.toFixed(1)}</span>
                      <br/>
                      <strong>{result.Display_Name}</strong>
                      <div style={{fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '6px'}}>
                        Carbon: {Number(result.Carbon_Intensity_Mean).toFixed(0)} kg CO2
                        <br/>
                        LCOE: €{Number(result.LCOE_Mean).toFixed(4)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

        </main>
      </div>
    </>
  );
}

export default App;
