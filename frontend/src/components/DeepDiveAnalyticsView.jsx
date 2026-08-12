import React, { useMemo } from 'react';
import { 
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, Cell, Label,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar
} from 'recharts';

export default function DeepDiveAnalyticsView({
  results,
  selectedModule,
  handleModuleSelect,
  analysisData,
  analyzing
}) {

  // Process scatter data to ensure clean, aesthetic visual separation (no ugly overlapping clumps!)
  const scatterData = useMemo(() => {
    if (!results || results.length === 0) return [];
    
    // Take top 30 Pareto modules for crystal-clear visual clarity
    const seenCoords = new Map();
    
    return results.slice(0, 30).map((mod, idx) => {
      const origLcoe = Number(mod.LCOE_EUR_MWh) || 45.0;
      const origCarbon = Number(mod.Net_GWP_kgCO2e || mod.GWP_total_A1A3_per_kWp_kgCO2e) || 600.0;
      
      const coordKey = `${origLcoe.toFixed(2)}_${Math.round(origCarbon)}`;
      const count = seenCoords.get(coordKey) || 0;
      seenCoords.set(coordKey, count + 1);
      
      // Apply deterministic micro-jitter offset for duplicate coordinates so every dot is distinct
      const jitterX = count > 0 ? (count % 2 === 1 ? 0.06 * count : -0.06 * count) : 0;
      const jitterY = count > 0 ? (count % 2 === 1 ? 5.5 * count : -5.5 * count) : 0;
      
      return {
        ...mod,
        displayLcoe: Number((origLcoe + jitterX).toFixed(3)),
        displayCarbon: Number((origCarbon + jitterY).toFixed(1)),
        origLcoe,
        origCarbon,
        rank: idx + 1
      };
    });
  }, [results]);

  // Calculate domain bounds with generous padding so dots don't stick to chart edges
  const xDomain = useMemo(() => {
    if (scatterData.length === 0) return [40, 50];
    const vals = scatterData.map(d => d.displayLcoe);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = Math.max(0.3, (max - min) * 0.15);
    return [Number((min - pad).toFixed(2)), Number((max + pad).toFixed(2))];
  }, [scatterData]);

  const yDomain = useMemo(() => {
    if (scatterData.length === 0) return [500, 700];
    const vals = scatterData.map(d => d.displayCarbon);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = Math.max(20, (max - min) * 0.15);
    return [Math.floor(min - pad), Math.ceil(max + pad)];
  }, [scatterData]);

  return (
    <div className="deep-dive-view-container fade-in">
      <div className="analytics-3panel-grid">
        
        {/* PANEL 1: PARETO TRADE-OFF SCATTER PLOT */}
        <div className="glass-panel analytics-panel">
          <div className="panel-header-badge">
            <span className="badge-num">1</span>
            <h3>Pareto Trade-Off Frontier Scatter</h3>
          </div>
          <p className="panel-desc">
            Interactive multi-objective frontier evaluating System LCOE vs Carbon Footprint.
          </p>

          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 20, right: 25, left: 15, bottom: 30 }}>
                <XAxis 
                  type="number" 
                  dataKey="displayLcoe" 
                  name="LCOE" 
                  stroke="var(--border-highlight)" 
                  tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                  tickFormatter={(val) => Number(val).toFixed(2)}
                  domain={xDomain}
                >
                  <Label value="System LCOE (€/MWh)" position="insideBottom" offset={-18} style={{ fill: 'var(--text-muted)', fontSize: '11px', textAnchor: 'middle' }} />
                </XAxis>
                <YAxis 
                  type="number" 
                  dataKey="displayCarbon" 
                  name="Carbon" 
                  stroke="var(--border-highlight)" 
                  tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                  tickFormatter={(val) => Math.round(val)}
                  domain={yDomain}
                >
                  <Label value="Carbon (kgCO2e/kWp)" angle={-90} position="insideLeft" offset={8} style={{ fill: 'var(--text-muted)', fontSize: '11px', textAnchor: 'middle' }} />
                </YAxis>
                <ZAxis type="number" dataKey="TOPSIS_Score" range={[100, 300]} name="TOPSIS Score" />
                
                <Tooltip 
                  cursor={{ stroke: 'rgba(56, 189, 248, 0.3)', strokeDasharray: '4 4' }}
                  content={({ payload }) => {
                    if (!payload || !payload.length) return null;
                    const data = payload[0].payload;
                    return (
                      <div className="scatter-tooltip-box">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <strong className="text-cyan">{data.Display_Name || data.name}</strong>
                          <span style={{ fontSize: '10px', background: 'rgba(56, 189, 248, 0.2)', padding: '1px 6px', borderRadius: '8px', color: '#38bdf8' }}>
                            #{data.rank} TOPSIS
                          </span>
                        </div>
                        <div className="tooltip-details">
                          <div>TOPSIS Score: <span className="text-white bold">{Number(data.TOPSIS_Score).toFixed(1)}</span></div>
                          <div>LCOE: <span className="text-white bold">€{Number(data.origLcoe || data.LCOE_EUR_MWh).toFixed(2)}/MWh</span></div>
                          <div>System Carbon: <span className="text-white bold">{Number(data.origCarbon || data.Net_GWP_kgCO2e).toFixed(0)} kgCO2e/kWp</span></div>
                          <div>Manufacturer: <span className="text-muted">{data.manufacturer || 'CEC Standard'}</span></div>
                        </div>
                      </div>
                    );
                  }}
                />
                
                <Scatter 
                  name="Modules" 
                  data={scatterData} 
                  onClick={(entry) => handleModuleSelect(entry.payload || entry)}
                >
                  {scatterData.map((entry, index) => {
                    const isSelected = selectedModule?.dataset_uuid === entry.dataset_uuid;
                    
                    // Distinct, aesthetic color palette by rank
                    let fillColor = 'rgba(56, 189, 248, 0.55)';
                    let strokeColor = 'rgba(56, 189, 248, 0.9)';
                    let strokeWidth = 1.5;

                    if (isSelected) {
                      fillColor = '#06b6d4';
                      strokeColor = '#ffffff';
                      strokeWidth = 3;
                    } else if (index === 0) {
                      fillColor = 'rgba(245, 158, 11, 0.9)'; // Gold for #1
                      strokeColor = '#fef08a';
                      strokeWidth = 2;
                    } else if (index < 3) {
                      fillColor = 'rgba(168, 85, 247, 0.85)'; // Purple for #2-#3
                      strokeColor = '#e9d5ff';
                      strokeWidth = 2;
                    } else if (index < 10) {
                      fillColor = 'rgba(16, 185, 129, 0.8)'; // Emerald for Top 10
                      strokeColor = '#a7f3d0';
                      strokeWidth = 1.5;
                    }

                    return (
                      <Cell 
                        key={`scatter-cell-${entry.dataset_uuid || index}`} 
                        fill={fillColor}
                        stroke={strokeColor}
                        strokeWidth={strokeWidth}
                        style={{ 
                          cursor: 'pointer', 
                          filter: isSelected ? 'drop-shadow(0px 0px 10px #06b6d4)' : 'drop-shadow(0px 2px 4px rgba(0,0,0,0.5))',
                          transition: 'all 0.2s ease'
                        }}
                      />
                    );
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* PANEL 2: DIMENSION BALANCE RADAR CHART */}
        <div className="glass-panel analytics-panel">
          <div className="panel-header-badge">
            <span className="badge-num">2</span>
            <h3>Dimension Balance Radar Chart</h3>
          </div>
          <p className="panel-desc highlight-blue">
            {selectedModule ? selectedModule.Display_Name || selectedModule.name : 'Select a panel'}
          </p>

          <div className="chart-wrapper">
            {analyzing || !analysisData?.radar ? (
              <div className="chart-loading-state">Loading Analysis...</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={analysisData.radar}>
                  <PolarGrid stroke="var(--border-highlight)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Score" dataKey="A" stroke="var(--accent-cyan)" fill="var(--accent-cyan)" fillOpacity={0.4} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-highlight)', borderRadius: '8px' }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* PANEL 3: CARBON FOOTPRINT TORNADO SENSITIVITY SWING CHART */}
        <div className="glass-panel analytics-panel">
          <div className="panel-header-badge">
            <span className="badge-num">3</span>
            <h3>Carbon Footprint Tornado Sensitivity</h3>
          </div>
          <p className="panel-desc">
            Bi-directional swing mapping ±20% parameter variations on Carbon footprint.
          </p>

          <div className="chart-wrapper">
            {analyzing || !analysisData?.sensitivity?.carbon ? (
              <div className="chart-loading-state">Loading Analysis...</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={analysisData.sensitivity.carbon} layout="vertical" margin={{ top: 5, right: 20, left: 30, bottom: 5 }} stackOffset="sign">
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
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
