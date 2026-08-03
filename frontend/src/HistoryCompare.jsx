import { useState, useEffect } from 'react';
import { Clock, Activity, Target, Mountain } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, 
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
      const res = await fetch('http://127.0.0.1:8000/api/history');
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
    setLoading(false);
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

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="glass-panel" style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 20px 0', color: 'var(--text-main)' }}>
          <Clock size={20} color="var(--accent-cyan)" />
          Simulation History
        </h2>
        <p className="label-muted" style={{marginBottom: '10px'}}>Select exactly 2 runs to compare them side-by-side.</p>
        
        {loading ? (
          <div style={{color: 'var(--text-muted)'}}>Loading history...</div>
        ) : (
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: 'var(--text-main)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <th style={{ padding: '8px' }}>Compare</th>
                <th style={{ padding: '8px' }}>Date</th>
                <th style={{ padding: '8px' }}>Scenario</th>
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
                  <td style={{ padding: '8px', fontSize: '13px' }}>{row.scenario}</td>
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
        </div>
      )}
    </div>
  );
}
