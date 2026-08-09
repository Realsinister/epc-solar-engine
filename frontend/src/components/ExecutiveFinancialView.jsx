import React from 'react';
import { Activity, FileText, Check, DollarSign, TrendingUp, ShieldAlert, Award } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

export default function ExecutiveFinancialView({
  results,
  selectedModule,
  handleModuleSelect,
  analysisData,
  params,
  handleExportPdf,
  exportingPdf
}) {
  const fin = analysisData?.financials || {};
  const pitch = analysisData?.pitch || "";

  // Prepare Carbon Stack Data for selected module
  const carbonStackData = selectedModule ? [
    {
      name: selectedModule.Short_Name || selectedModule.name || 'Module',
      ModuleNet: Math.max(0, Math.round(selectedModule.Net_GWP_kgCO2e || 0)),
      Inverter: Math.round(selectedModule.Inverter_GWP_kgCO2e || 25),
      BOS: Math.round(selectedModule.BOS_GWP_kgCO2e || 45)
    }
  ] : [];

  return (
    <div className="exec-financial-view-container fade-in">
      {/* TOP ROW: 3 GLOW-PILL KPI CARDS */}
      <div className="exec-kpi-grid">
        {/* KPI 1: NPV */}
        <div className="exec-kpi-card cyan-border">
          <div className="kpi-card-header">
            <span className="kpi-title">Net Present Value (NPV)</span>
            <span className="kpi-badge positive">+12.5% vs target</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-value-lg">
              {fin.NPV_EUR !== undefined 
                ? `€ ${(fin.NPV_EUR / 1e6).toFixed(2)}M`
                : '€ --'}
            </div>
            <div className="kpi-sparkline-svg">
              <svg viewBox="0 0 100 24" className="spark-line">
                <path d="M 0 18 Q 25 14, 50 10 T 100 4" fill="none" stroke="#38bdf8" strokeWidth="2.5" />
              </svg>
            </div>
          </div>
          <div className="kpi-subtext">Estimated 30-Year Cash Flow Projection</div>
        </div>

        {/* KPI 2: Payback Period */}
        <div className="exec-kpi-card emerald-border">
          <div className="kpi-card-header">
            <span className="kpi-title">Payback Period</span>
            <span className="kpi-badge emerald-badge">-0.5 Yrs Faster</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-value-lg">
              {fin.Payback_Years !== undefined ? `${fin.Payback_Years.toFixed(1)} Yrs` : '-- Yrs'}
            </div>
            <div className="kpi-progress-bar">
              <div className="kpi-progress-fill" style={{ width: '68%' }}></div>
            </div>
          </div>
          <div className="kpi-subtext">Accelerated Capital Recovery Threshold</div>
        </div>

        {/* KPI 3: Lifetime Revenue */}
        <div className="exec-kpi-card purple-border">
          <div className="kpi-card-header">
            <span className="kpi-title">Lifetime Revenue</span>
            <span className="kpi-badge purple-badge">+8.2% vs plan</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-value-lg">
              {fin.Lifetime_Revenue_EUR !== undefined 
                ? `€ ${(fin.Lifetime_Revenue_EUR / 1e6).toFixed(2)}M`
                : '€ --'}
            </div>
            <div className="kpi-sparkline-svg">
              <svg viewBox="0 0 100 24" className="spark-line">
                <path d="M 0 20 Q 30 16, 60 12 T 100 2" fill="none" stroke="#a855f7" strokeWidth="2.5" />
              </svg>
            </div>
          </div>
          <div className="kpi-subtext">Projected Cumulative Yield (30 Years)</div>
        </div>
      </div>

      {/* MIDDLE ROW: PITCH CARD + CARBON STACK */}
      <div className="exec-middle-grid">
        {/* AUTOMATED EXECUTIVE PITCH CARD */}
        <div className="glass-panel pitch-card-panel">
          <div className="panel-header-row">
            <h3 className="panel-title text-cyan">
              <Activity size={18} /> Automated Board Executive Pitch
            </h3>
            {selectedModule && (
              <button 
                onClick={handleExportPdf}
                disabled={exportingPdf}
                className="btn-glass-action"
              >
                <FileText size={14} />
                <span>{exportingPdf ? 'Exporting...' : 'View Full PDF Report'}</span>
              </button>
            )}
          </div>
          <div className="pitch-content-box">
            <p className="pitch-text">
              {pitch || "Select a module from the TOPSIS ranking list to generate an automated C-Suite procurement briefing pitch."}
            </p>
          </div>
          {fin.CBAM_Tax_Risk_EUR !== undefined && (
            <div className="pitch-footer-bar">
              <div className="risk-metric">
                <ShieldAlert size={15} color="#f43f5e" />
                <span>CBAM Import Tax Liability:</span>
                <strong className="text-rose">€ {fin.CBAM_Tax_Risk_EUR.toLocaleString()}</strong>
              </div>
              <div className="risk-metric">
                <span className="text-muted">CBAM Rate per kWp:</span>
                <strong>€ {fin.CBAM_Tax_Per_kWp?.toFixed(2)} / kWp</strong>
              </div>
            </div>
          )}
        </div>

        {/* SYSTEM EMBODIED CARBON STACK */}
        <div className="glass-panel carbon-stack-panel">
          <h3 className="panel-title text-purple">
            <Activity size={18} /> Scope 3 System Embodied Carbon Stack
          </h3>
          <div className="panel-sub">
            {selectedModule ? selectedModule.Display_Name || selectedModule.name : 'Select Module'}
          </div>

          <div className="stack-chart-container">
            {selectedModule ? (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={carbonStackData} layout="vertical" margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                  <XAxis type="number" stroke="var(--border-highlight)" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <YAxis dataKey="name" type="category" width={100} stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-highlight)', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="ModuleNet" name="Module (Net)" fill="#38bdf8" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="Inverter" name="Inverter System" fill="#a855f7" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="BOS" name="BOS Racking & Cabling" fill="#10b981" stackId="a" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart-notice">Select a panel to inspect Scope 3 Carbon breakdown</div>
            )}
          </div>

          <div className="carbon-legend-pills">
            <span className="legend-pill cyan"><span className="dot"></span> Module Net</span>
            <span className="legend-pill purple"><span className="dot"></span> Inverter</span>
            <span className="legend-pill green"><span className="dot"></span> BOS Racking</span>
          </div>
        </div>
      </div>

      {/* BOTTOM ROW: TOP PARETO MODULES TABLE */}
      <div className="glass-panel pareto-table-panel">
        <div className="panel-header-row">
          <h3 className="panel-title text-cyan">
            <Award size={18} /> Top TOPSIS Ranked PV Modules
          </h3>
          <span className="table-subtitle">Showing Top Pareto Winners for {params.project_size_mwp} {params.project_size_unit} Project</span>
        </div>

        <div className="pareto-table-wrapper">
          <table className="pareto-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Module Model</th>
                <th>Manufacturer</th>
                <th>Power (W)</th>
                <th>LCOE (€/MWh)</th>
                <th>Carbon (kgCO2e/kWp)</th>
                <th>TOPSIS Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 8).map((mod, idx) => {
                const isSelected = selectedModule?.dataset_uuid === mod.dataset_uuid;
                return (
                  <tr 
                    key={mod.dataset_uuid || idx} 
                    className={`table-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleModuleSelect(mod)}
                  >
                    <td>
                      <span className={`rank-badge rank-${idx + 1}`}>#{idx + 1}</span>
                    </td>
                    <td className="font-bold text-main">{mod.name || mod.Short_Name}</td>
                    <td className="text-muted">{mod.Manufacturer || mod.bifaciality ? 'CEC Database' : 'Standard'}</td>
                    <td>{mod.P_mp_STC ? Math.round(mod.P_mp_STC) : '--'} W</td>
                    <td className="text-cyan font-bold">€ {Number(mod.LCOE_EUR_MWh).toFixed(2)}</td>
                    <td className="text-emerald">{Math.round(mod.Net_GWP_kgCO2e || 0)}</td>
                    <td>
                      <div className="score-pill">
                        {Number(mod.TOPSIS_Score).toFixed(1)}
                      </div>
                    </td>
                    <td>
                      <button className={`btn-table-select ${isSelected ? 'active' : ''}`}>
                        {isSelected ? <Check size={13} /> : 'Select'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
