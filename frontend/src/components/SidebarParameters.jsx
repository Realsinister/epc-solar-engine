import React, { useState } from 'react';
import { Sliders, Sun, Mountain, Zap, DollarSign, ChevronDown, ChevronUp } from 'lucide-react';

export default function SidebarParameters({
  params,
  setParams,
  handleSimulate,
  loading,
  isStale,
  selectedInverterId,
  setSelectedInverterId,
  inverters,
  targetDcAcRatio,
  setTargetDcAcRatio
}) {
  const [openSection, setOpenSection] = useState('physics');

  const toggleSection = (sec) => {
    setOpenSection(openSection === sec ? null : sec);
  };

  return (
    <div className="parameters-drawer-container">
      <div className="drawer-header">
        <h3 className="drawer-title">
          <Sliders size={18} color="#38bdf8" /> Simulation Inputs
        </h3>
        {isStale && <span className="stale-pill">Stale - Re-calculate</span>}
      </div>

      <div className="drawer-scroll-body">
        
        {/* ACCORDION 1: PHYSICS & CLIMATE */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('physics')}>
            <span className="acc-title"><Sun size={15} color="#38bdf8" /> Climate & Location</span>
            {openSection === 'physics' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSection === 'physics' && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Optimization Strategy:</label>
                <select 
                  value={params.scenario} 
                  onChange={(e) => setParams({ ...params, scenario: e.target.value })}
                  className="select-input"
                >
                  <option value="Eco-Flagship (Minimize Carbon)">🌿 Eco-Flagship (Minimize Carbon)</option>
                  <option value="Utility Scale (Lowest LCOE)">⚡ Utility Scale (Lowest LCOE)</option>
                  <option value="Space Constrained (Max Efficiency)">🎯 Space Constrained (Max Efficiency)</option>
                </select>
              </div>

              <div className="input-group">
                <label>Annual Irradiance (kWh/m²/yr):</label>
                <input 
                  type="number" 
                  value={params.base_irradiance} 
                  onChange={(e) => setParams({ ...params, base_irradiance: parseFloat(e.target.value) || 0 })}
                  className="number-input"
                />
              </div>

              <div className="input-group">
                <label>Ambient Temperature (°C):</label>
                <input 
                  type="number" 
                  value={params.ambient_temp_c} 
                  onChange={(e) => setParams({ ...params, ambient_temp_c: parseFloat(e.target.value) || 0 })}
                  className="number-input"
                />
              </div>

              <div className="input-group">
                <label>Bifacial Ground Albedo:</label>
                <select 
                  value={params.ground_albedo} 
                  onChange={(e) => setParams({ ...params, ground_albedo: e.target.value })}
                  className="select-input"
                >
                  <option value="None">Monofacial / Default (0.00)</option>
                  <option value="0.20">Grass / Concrete (0.20 - +5.2% Gain)</option>
                  <option value="0.50">Light Sand / Paint (0.50 - +11.8% Gain)</option>
                  <option value="0.85">Fresh Snow / Specular (0.85 - +19.4% Gain)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* ACCORDION 2: PROJECT SCALE & FINANCIALS */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('financials')}>
            <span className="acc-title"><DollarSign size={15} color="#a855f7" /> Scale & Economics</span>
            {openSection === 'financials' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSection === 'financials' && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Project Capacity Scale:</label>
                <div className="row-inputs">
                  <input 
                    type="number" 
                    value={params.project_size_mwp} 
                    onChange={(e) => setParams({ ...params, project_size_mwp: parseFloat(e.target.value) || 0 })}
                    className="number-input flex-1"
                  />
                  <select 
                    value={params.project_size_unit} 
                    onChange={(e) => setParams({ ...params, project_size_unit: e.target.value })}
                    className="select-input-sm"
                  >
                    <option value="MWp">MWp</option>
                    <option value="kWp">kWp</option>
                  </select>
                </div>
              </div>

              <div className="input-group">
                <label>PPA Tariff Rate (€/MWh):</label>
                <input 
                  type="number" 
                  value={params.ppa_rate_eur_mwh} 
                  onChange={(e) => setParams({ ...params, ppa_rate_eur_mwh: parseFloat(e.target.value) || 0 })}
                  className="number-input"
                />
              </div>

              <div className="input-group">
                <label>Discount Rate (%):</label>
                <input 
                  type="number" 
                  step="0.5"
                  value={params.discount_rate_pct} 
                  onChange={(e) => setParams({ ...params, discount_rate_pct: parseFloat(e.target.value) || 0 })}
                  className="number-input"
                />
              </div>
            </div>
          )}
        </div>

        {/* ACCORDION 3: INVERTER FLEET */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('inverter')}>
            <span className="acc-title"><Zap size={15} color="#10b981" /> Inverter Fleet</span>
            {openSection === 'inverter' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSection === 'inverter' && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Inverter Selection:</label>
                <select 
                  value={selectedInverterId} 
                  onChange={(e) => setSelectedInverterId(e.target.value)}
                  className="select-input"
                >
                  <option value="auto">🤖 Auto-Match Best Inverter</option>
                  {inverters.map(inv => (
                    <option key={inv.id} value={inv.id}>
                      {inv.manufacturer} - {inv.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>Target DC/AC Sizing Ratio:</label>
                <input 
                  type="number" 
                  step="0.05"
                  value={targetDcAcRatio} 
                  onChange={(e) => setTargetDcAcRatio(parseFloat(e.target.value) || 1.25)}
                  className="number-input"
                />
              </div>
            </div>
          )}
        </div>

      </div>

      <div className="drawer-footer">
        <button 
          onClick={handleSimulate} 
          disabled={loading}
          className="btn-simulate-glow"
        >
          {loading ? 'Running MCDA Simulation...' : '🚀 Run Physics Engine Simulation'}
        </button>
      </div>
    </div>
  );
}
