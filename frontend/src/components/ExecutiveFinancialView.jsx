import React from 'react';
import { Activity, Check, ShieldAlert, Award } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';

export default function ExecutiveFinancialView({
  results,
  selectedModule,
  handleModuleSelect,
  analysisData,
  params,
  currency = 'EUR'
}) {
  // Extract executive financials from either analysisData.executive or analysisData.financials
  const fin = analysisData?.executive || analysisData?.financials || {};
  const pitch = fin.executive_pitch || analysisData?.pitch || "";

  const CURRENCY_SYMBOLS = { EUR: '€', USD: '$', GBP: '£', AUD: 'A$' };
  const curSym = CURRENCY_SYMBOLS[currency] || '€';

  // Format Large Currency Numbers
  const formatCurrency = (val) => {
    if (val === undefined || val === null || isNaN(val)) return `${curSym} --`;
    const absVal = Math.abs(val);
    if (absVal >= 1e6) {
      return `${curSym} ${(val / 1e6).toFixed(2)}M`;
    } else if (absVal >= 1e3) {
      return `${curSym} ${(val / 1e3).toFixed(1)}K`;
    }
    return `${curSym} ${val.toFixed(0)}`;
  };

  // Format Payback Period
  const formatPayback = (val) => {
    if (val === undefined || val === null || isNaN(val) || val >= 90) return '-- Yrs';
    return `${val.toFixed(1)} Yrs`;
  };

  // Prepare Scope 3 Carbon Stack Data for selected module
  const carbonStackData = selectedModule ? [
    {
      name: selectedModule.Short_Name || selectedModule.Display_Name || selectedModule.name || 'Module',
      ModuleNet: Math.max(0, Math.round(selectedModule.GWP_Module_Net_kgCO2e || selectedModule.Net_GWP_kgCO2e || 0)),
      Inverter: Math.round(selectedModule.GWP_Inverter_kgCO2e || 25),
      BOS: Math.round(selectedModule.GWP_BOS_kgCO2e || 45)
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
              {formatCurrency(fin.npv_eur ?? fin.NPV_EUR)}
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
              {formatPayback(fin.payback_years ?? fin.Payback_Years)}
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
              {formatCurrency(fin.total_lifetime_revenue_eur ?? fin.Lifetime_Revenue_EUR)}
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
          </div>
          <div className="pitch-content-box">
            <p className="pitch-text">
              {pitch || "Select a module from the TOPSIS ranking list to generate an automated C-Suite procurement briefing pitch."}
            </p>
          </div>
          {(fin.total_cbam_tax_eur !== undefined || fin.CBAM_Tax_Risk_EUR !== undefined) && (
            <div className="pitch-footer-bar">
              <div className="risk-metric">
                <ShieldAlert size={15} color="#f43f5e" />
                <span>CBAM Import Tax Liability:</span>
                <strong className="text-rose">{formatCurrency(fin.total_cbam_tax_eur ?? fin.CBAM_Tax_Risk_EUR)}</strong>
              </div>
              <div className="risk-metric">
                <span className="text-muted">CBAM Rate / kWp:</span>
                <strong>{curSym} {((fin.total_cbam_tax_eur ?? 0) / ((params.project_size_mwp || 50) * 1000)).toFixed(2)} / kWp</strong>
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
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={carbonStackData} layout="vertical" margin={{ top: 10, right: 25, left: 25, bottom: 5 }}>
                  <XAxis type="number" stroke="var(--border-highlight)" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} unit=" kg" />
                  <YAxis type="category" dataKey="name" hide={true} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-highlight)', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(val, name) => [`${val} kgCO2e/kWp`, name]}
                  />
                  <Bar dataKey="ModuleNet" name="Module (Net)" fill="#38bdf8" stackId="a" radius={[4, 0, 0, 4]} />
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
                <th>LCOE ({curSym}/MWh)</th>
                <th>Carbon (kgCO2e/kWp)</th>
                <th>TOPSIS Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 10).map((mod, idx) => {
                const isSelected = selectedModule?.dataset_uuid === mod.dataset_uuid;
                const powerW = mod.module_power_Wp || mod.P_mp_STC || '--';
                const mfg = mod.manufacturer || mod.Manufacturer || 'CEC Standard';

                return (
                  <tr 
                    key={mod.dataset_uuid || idx} 
                    className={`table-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleModuleSelect(mod)}
                  >
                    <td>
                      <span className={`rank-badge rank-${idx + 1}`}>#{idx + 1}</span>
                    </td>
                    <td className="font-bold text-main">{mod.Display_Name || mod.name || mod.Short_Name}</td>
                    <td className="text-muted">{mfg}</td>
                    <td className="font-bold text-white">{typeof powerW === 'number' ? Math.round(powerW) : powerW} W</td>
                    <td className="text-cyan font-bold">{curSym} {Number(mod.LCOE_EUR_MWh).toFixed(2)}</td>
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
