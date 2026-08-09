import React from 'react';
import { Activity, BarChart2, Zap } from 'lucide-react';
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
              <ScatterChart margin={{ top: 15, right: 20, left: 10, bottom: 25 }}>
                <XAxis 
                  type="number" 
                  dataKey="LCOE_EUR_MWh" 
                  name="LCOE" 
                  stroke="var(--border-highlight)" 
                  tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                  tickFormatter={(val) => Number(val).toFixed(2)}
                  domain={['auto', 'auto']}
                >
                  <Label value="System LCOE (€/MWh)" position="insideBottom" offset={-15} style={{ fill: 'var(--text-muted)', fontSize: '11px', textAnchor: 'middle' }} />
                </XAxis>
                <YAxis 
                  type="number" 
                  dataKey="Net_GWP_kgCO2e" 
                  name="Carbon" 
                  stroke="var(--border-highlight)" 
                  tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                  tickFormatter={(val) => Math.round(val)}
                  domain={['auto', 'auto']}
                >
                  <Label value="Carbon (kgCO2e/kWp)" angle={-90} position="insideLeft" offset={10} style={{ fill: 'var(--text-muted)', fontSize: '11px', textAnchor: 'middle' }} />
                </YAxis>
                <ZAxis type="number" dataKey="TOPSIS_Score" range={[60, 240]} name="TOPSIS Score" />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ payload }) => {
                    if (!payload || !payload.length) return null;
                    const data = payload[0].payload;
                    return (
                      <div className="scatter-tooltip-box">
                        <strong className="text-cyan">{data.Display_Name || data.name}</strong>
                        <div className="tooltip-details">
                          <div>TOPSIS Score: <span className="text-white bold">{Number(data.TOPSIS_Score).toFixed(1)}</span></div>
                          <div>LCOE: <span className="text-white bold">€{Number(data.LCOE_EUR_MWh).toFixed(2)}/MWh</span></div>
                          <div>System Carbon: <span className="text-white bold">{Number(data.Net_GWP_kgCO2e).toFixed(0)} kgCO2e/kWp</span></div>
                        </div>
                      </div>
                    );
                  }}
                />
                <Scatter 
                  name="Modules" 
                  data={results} 
                  onClick={(entry) => handleModuleSelect(entry.payload || entry)}
                >
                  {results.map((entry, index) => {
                    const isSelected = selectedModule?.dataset_uuid === entry.dataset_uuid;
                    return (
                      <Cell 
                        key={`scatter-cell-${index}`} 
                        fill={isSelected ? '#06b6d4' : index < 3 ? '#a855f7' : '#3b82f6'} 
                        stroke={isSelected ? '#ffffff' : 'transparent'}
                        strokeWidth={isSelected ? 3 : 0}
                        style={{ cursor: 'pointer', filter: isSelected ? 'drop-shadow(0px 0px 8px #06b6d4)' : 'none' }}
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
