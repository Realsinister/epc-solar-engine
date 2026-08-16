import { useState, useEffect } from 'react';
import { Clock, Activity, Trash2 } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis 
} from 'recharts';

export default function HistoryCompare() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState([]);
  const [runA, setRunA] = useState(null);
  const [runB, setRunB] = useState(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/history?limit=50');
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
    setLoading(false);
  };

  const handleClearHistory = async () => {
    if (window.confirm("Are you sure you want to clear all simulation history logs? This action cannot be undone.")) {
      try {
        await fetch('http://127.0.0.1:8000/api/history', { method: 'DELETE' });
        setHistory([]);
        setSelectedIds([]);
        setRunA(null);
        setRunB(null);
      } catch (err) {
        console.error('Failed to clear history', err);
      }
    }
  };

  const handleSelect = (id) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(x => x !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
  };

  useEffect(() => {
    if (selectedIds.length === 2) {
      loadComparison(selectedIds[0], selectedIds[1]);
    } else {
      setRunA(null);
      setRunB(null);
    }
  }, [selectedIds]);

  const loadComparison = async (id1, id2) => {
    try {
      const [res1, res2] = await Promise.all([
        fetch(`http://127.0.0.1:8000/api/history/${id1}`),
        fetch(`http://127.0.0.1:8000/api/history/${id2}`)
      ]);
      setRunA(await res1.json());
      setRunB(await res2.json());
    } catch (err) {
      console.error('Failed to load comparison', err);
    }
  };

  const formatDate = (iso) => {
    return new Date(iso).toLocaleString();
  };

  const getRadarData = (runA, runB) => {
    if (!runA || !runB) return [];
    const modA = runA.results?.top_modules?.[0];
    const modB = runB.results?.top_modules?.[0];
    if (!modA || !modB) return [];

    return [
      {
        subject: 'Eco Score',
        A: (modA.Score_Eco || 0) * 100,
        B: (modB.Score_Eco || 0) * 100,
        fullMark: 100,
      },
      {
        subject: 'Cost Score',
        A: (modA.Score_Cost || 0) * 100,
        B: (modB.Score_Cost || 0) * 100,
        fullMark: 100,
      },
      {
        subject: 'Tech Score',
        A: (modA.Score_Tech || 0) * 100,
        B: (modB.Score_Tech || 0) * 100,
        fullMark: 100,
      }
    ];
  };

  const getBarData = (runA, runB) => {
    if (!runA || !runB) return [];
    const modA = runA.results?.top_modules?.[0];
    const modB = runB.results?.top_modules?.[0];
    if (!modA || !modB) return [];

    return [
      {
        name: 'LCOE (€/kWh)',
        RunA: parseFloat((modA.LCOE_EUR_MWh / 1000).toFixed(4)),
        RunB: parseFloat((modB.LCOE_EUR_MWh / 1000).toFixed(4))
      }
    ];
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="glass-panel" style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, color: 'var(--text-main)' }}>
            <Clock size={20} color="var(--accent-cyan)" />
            Simulation History (Top 50)
          </h2>
          {history.length > 0 && (
            <button 
              onClick={handleClearHistory}
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.15)'}
            >
              <Trash2 size={14} /> Clear History
            </button>
          )}
        </div>
        
        {/* User Guidance Banner */}
        <div style={{
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '10px',
          padding: '10px 16px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          color: '#38bdf8',
          fontSize: '0.84rem'
        }}>
          <Activity size={18} />
          <span>💡 <strong>Pro Tip:</strong> Select up to 2 simulation runs from the table below to compare parameters, winning panels, NPV differences, and carbon footprints side-by-side!</span>
        </div>

        {loading ? (
          <div style={{color: 'var(--text-muted)'}}>Loading history...</div>
        ) : (
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: 'var(--text-main)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <th style={{ padding: '8px' }}>Compare</th>
                <th style={{ padding: '8px' }}>Date</th>
                <th style={{ padding: '8px' }}>Project / Scenario</th>
                <th style={{ padding: '8px' }}>Size (MWp)</th>
                <th style={{ padding: '8px' }}>Winning Module</th>
                <th style={{ padding: '8px' }}>Suitability</th>
              </tr>
            </thead>
            <tbody>
              {history.map(row => (
                <tr key={row.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', backgroundColor: selectedIds.includes(row.id) ? 'rgba(59, 130, 246, 0.2)' : 'transparent' }}>
                  <td style={{ padding: '8px' }}>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(row.id)}
                      onChange={() => handleSelect(row.id)}
                    />
                  </td>
                  <td style={{ padding: '8px', fontSize: '12px' }}>{formatDate(row.timestamp)}</td>
                  <td style={{ padding: '8px', fontSize: '13px' }}>
                    <div style={{ fontWeight: 'bold' }}>{row.project_name || 'Unnamed Project'}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.scenario}</div>
                  </td>
                  <td style={{ padding: '8px' }}>{row.project_size_mwp}</td>
                  <td style={{ padding: '8px' }}>
                    {row.winner_mfg} {row.winner_name}
                  </td>
                  <td style={{ padding: '8px' }}>
                    {row.winner_suitability ? row.winner_suitability.toFixed(1) : 'N/A'}
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No simulation history found. Run a simulation to save it automatically.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {runA && runB && (
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0', color: 'var(--text-main)' }}>
            <Activity size={20} color="var(--accent-purple)" />
            Side-by-Side Comparison
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            
            {/* Run A */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #3b82f6' }}>
              <h3 style={{ color: '#3b82f6', marginTop: 0 }}>Run A</h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>{formatDate(runA.timestamp)}</div>
              
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ color: 'var(--text-main)' }}>Scenario:</strong> <span style={{ color: 'var(--text-muted)' }}>{runA.scenario}</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>Project Size:</strong> <span style={{ color: 'var(--text-muted)' }}>{runA.project_size_mwp} MWp</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>Base Yield:</strong> <span style={{ color: 'var(--text-muted)' }}>{runA.inputs.base_irradiance} kWh/kWp</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>CBAM Tax:</strong> <span style={{ color: 'var(--text-muted)' }}>€{runA.inputs.cbam_tax_rate_eur_t}/t</span>
              </div>

              {runA.results?.top_modules?.length > 0 && (
                <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '12px', borderRadius: '4px' }}>
                  <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-main)' }}>Top Module (Winner)</h4>
                  <div style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>
                    {runA.results.top_modules[0].manufacturer} {runA.results.top_modules[0].name}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Suitability Index: {runA.results.top_modules[0].Suitability_Index?.toFixed(1)}<br/>
                    Carbon: {runA.results.top_modules[0].Carbon_Intensity_Mean?.toFixed(1)} gCO2/kWh<br/>
                    LCOE: €{(runA.results.top_modules[0].LCOE_EUR_MWh / 1000)?.toFixed(4)}/kWh
                  </div>
                </div>
              )}
            </div>

            {/* Run B */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
              <h3 style={{ color: '#8b5cf6', marginTop: 0 }}>Run B</h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>{formatDate(runB.timestamp)}</div>
              
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ color: 'var(--text-main)' }}>Scenario:</strong> <span style={{ color: 'var(--text-muted)' }}>{runB.scenario}</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>Project Size:</strong> <span style={{ color: 'var(--text-muted)' }}>{runB.project_size_mwp} MWp</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>Base Yield:</strong> <span style={{ color: 'var(--text-muted)' }}>{runB.inputs.base_irradiance} kWh/kWp</span><br/>
                <strong style={{ color: 'var(--text-main)' }}>CBAM Tax:</strong> <span style={{ color: 'var(--text-muted)' }}>€{runB.inputs.cbam_tax_rate_eur_t}/t</span>
              </div>

              {runB.results?.top_modules?.length > 0 && (
                <div style={{ background: 'rgba(139, 92, 246, 0.1)', padding: '12px', borderRadius: '4px' }}>
                  <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-main)' }}>Top Module (Winner)</h4>
                  <div style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>
                    {runB.results.top_modules[0].manufacturer} {runB.results.top_modules[0].name}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Suitability Index: {runB.results.top_modules[0].Suitability_Index?.toFixed(1)}<br/>
                    Carbon: {runB.results.top_modules[0].Carbon_Intensity_Mean?.toFixed(1)} gCO2/kWh<br/>
                    LCOE: €{(runB.results.top_modules[0].LCOE_EUR_MWh / 1000)?.toFixed(4)}/kWh
                  </div>
                </div>
              )}
            </div>

          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
            
            {/* Radar Chart */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
              <h4 style={{ margin: '0 0 16px 0', color: 'var(--text-main)', textAlign: 'center' }}>Suitability Footprint</h4>
              <div style={{ height: '300px', width: '100%' }}>
                <ResponsiveContainer>
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={getRadarData(runA, runB)}>
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Radar name="Run A" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                    <Radar name="Run B" dataKey="B" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* LCOE Bar Chart */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
              <h4 style={{ margin: '0 0 16px 0', color: 'var(--text-main)', textAlign: 'center' }}>Financial Comparison</h4>
              <div style={{ height: '300px', width: '100%' }}>
                <ResponsiveContainer>
                  <BarChart data={getBarData(runA, runB)} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <XAxis dataKey="name" stroke="rgba(255,255,255,0.2)" tick={{ fill: 'var(--text-muted)' }} />
                    <YAxis stroke="rgba(255,255,255,0.2)" tick={{ fill: 'var(--text-muted)' }} />
                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Bar dataKey="RunA" fill="#3b82f6" name="Run A" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="RunB" fill="#8b5cf6" name="Run B" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
