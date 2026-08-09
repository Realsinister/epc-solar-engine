import React from 'react';
import { Layers, CheckCircle, Zap, Shield, ArrowUpRight, Cpu } from 'lucide-react';

export default function MultiBlockFleetView({
  results,
  selectedModule,
  inverters,
  selectedInverterId,
  setSelectedInverterId,
  targetDcAcRatio,
  setTargetDcAcRatio,
  params
}) {
  const primaryModule = results[0] || selectedModule;
  const secondaryModule = results[1] || results[2] || primaryModule;
  const activeInverter = inverters.find(i => i.id === selectedInverterId) || inverters[0];

  const projectMwp = params.project_size_unit === 'kWp' ? params.project_size_mwp / 1000 : params.project_size_mwp;
  const blockAMwp = (projectMwp * 0.7).toFixed(1);
  const blockBMwp = (projectMwp * 0.3).toFixed(1);

  return (
    <div className="hybrid-fleet-view-container fade-in">
      {/* MPPT UNIFORMITY BADGE BAR */}
      <div className="mppt-status-header">
        <div className="mppt-badge">
          <CheckCircle size={16} color="#10b981" />
          <span>Strict 100% String & MPPT Uniformity Compliance Enforced</span>
        </div>
        <div className="fleet-meta">
          <span>Total Project Capacity: <strong>{params.project_size_mwp} {params.project_size_unit}</strong></span>
          <span className="divider">|</span>
          <span>Target DC/AC Ratio: <strong>{targetDcAcRatio}</strong></span>
        </div>
      </div>

      {/* MULTI-BLOCK HYBRID CARDS */}
      <div className="block-hybrid-grid">
        
        {/* BLOCK GROUP A CARD */}
        <div className="glass-panel block-card cyan-glow">
          <div className="block-card-header">
            <div className="block-title-group">
              <span className="block-tag cyan">Block Group A (70% Sub-Array)</span>
              <h4>Primary LCOE Leader Allocation</h4>
            </div>
            <span className="block-mwp">{blockAMwp} MWp</span>
          </div>

          {primaryModule ? (
            <div className="block-module-details">
              <div className="mod-name">{primaryModule.Display_Name || primaryModule.name}</div>
              <div className="mod-stats-grid">
                <div className="stat-box">
                  <span className="lbl">LCOE</span>
                  <span className="val cyan">€ {Number(primaryModule.LCOE_EUR_MWh).toFixed(2)} /MWh</span>
                </div>
                <div className="stat-box">
                  <span className="lbl">Wattage</span>
                  <span className="val">{primaryModule.P_mp_STC ? Math.round(primaryModule.P_mp_STC) : '--'} W</span>
                </div>
                <div className="stat-box">
                  <span className="lbl">TOPSIS Score</span>
                  <span className="val purple">{Number(primaryModule.TOPSIS_Score).toFixed(1)} /100</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-notice">No module allocated</div>
          )}

          <div className="block-footer">
            <span>Inverter Block Configuration: <strong>Strict Uniform Stringing</strong></span>
          </div>
        </div>

        {/* BLOCK GROUP B CARD */}
        <div className="glass-panel block-card purple-glow">
          <div className="block-card-header">
            <div className="block-title-group">
              <span className="block-tag purple">Block Group B (30% Sub-Array)</span>
              <h4>Secondary Carbon Offset Allocation</h4>
            </div>
            <span className="block-mwp">{blockBMwp} MWp</span>
          </div>

          {secondaryModule ? (
            <div className="block-module-details">
              <div className="mod-name">{secondaryModule.Display_Name || secondaryModule.name}</div>
              <div className="mod-stats-grid">
                <div className="stat-box">
                  <span className="lbl">Carbon Intensity</span>
                  <span className="val emerald">{Math.round(secondaryModule.Net_GWP_kgCO2e || 0)} kgCO2e/kWp</span>
                </div>
                <div className="stat-box">
                  <span className="lbl">Wattage</span>
                  <span className="val">{secondaryModule.P_mp_STC ? Math.round(secondaryModule.P_mp_STC) : '--'} W</span>
                </div>
                <div className="stat-box">
                  <span className="lbl">CBAM Tax Saver</span>
                  <span className="val cyan">-18% Tax Impact</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-notice">No module allocated</div>
          )}

          <div className="block-footer">
            <span>Inverter Block Configuration: <strong>Independent MPPT Inputs</strong></span>
          </div>
        </div>

      </div>

      {/* INVERTER FLEET & BOS CONFIGURATOR PANEL */}
      <div className="glass-panel inverter-config-panel">
        <div className="panel-header-row">
          <h3 className="panel-title text-cyan">
            <Cpu size={18} /> Inverter Fleet Pairing & BOS Configurator
          </h3>
          <div className="dc-ac-control">
            <label>Target DC/AC Sizing Ratio:</label>
            <input 
              type="number" 
              step="0.05"
              min="1.0"
              max="1.6"
              value={targetDcAcRatio} 
              onChange={(e) => setTargetDcAcRatio(parseFloat(e.target.value) || 1.25)}
              className="number-input-sm"
            />
          </div>
        </div>

        <div className="inverter-selection-grid">
          <div className="inverter-select-box">
            <label>Select Preferred Central / String Inverter:</label>
            <select 
              value={selectedInverterId} 
              onChange={(e) => setSelectedInverterId(e.target.value)}
              className="select-dropdown-lg"
            >
              <option value="auto">🤖 Auto-Match Best Inverter Pair</option>
              {inverters.map(inv => (
                <option key={inv.id} value={inv.id}>
                  {inv.manufacturer} - {inv.name} ({inv.power_kw} kW | {inv.efficiency_pct}% Eff)
                </option>
              ))}
            </select>
          </div>

          {activeInverter && (
            <div className="active-inverter-card">
              <div className="inv-title">{activeInverter.manufacturer} {activeInverter.name}</div>
              <div className="inv-props">
                <span>Power: <strong>{activeInverter.power_kw} kW</strong></span>
                <span>Max Efficiency: <strong>{activeInverter.efficiency_pct}%</strong></span>
                <span>Topology: <strong>Utility String / Central</strong></span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
