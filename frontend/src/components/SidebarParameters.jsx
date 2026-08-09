import React, { useState } from 'react';
import { Sliders, Sun, DollarSign, Zap, ChevronDown, ChevronUp } from 'lucide-react';

export default function SidebarParameters({
  params,
  setParams,
  handleSimulate,
  loading,
  isStale,
  setIsStale,
  selectedInverterId,
  setSelectedInverterId,
  inverters,
  targetDcAcRatio,
  setTargetDcAcRatio
}) {
  const [openSections, setOpenSections] = useState({
    physics: true,
    financials: true,
    inverter: true
  });

  const toggleSection = (sec) => {
    setOpenSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  const handleTextChange = (key, rawValue) => {
    // When cleared, allow empty string '' so input box is completely blank without forcing '0' or '0100'
    const value = rawValue === '' ? '' : isNaN(rawValue) ? rawValue : Number(rawValue);
    setParams(prev => ({ ...prev, [key]: value }));
    setIsStale(true);
  };

  const handleInverterChange = (invId) => {
    setSelectedInverterId(invId);
    setIsStale(true);
  };

  const handleRatioChange = (rawValue) => {
    const value = rawValue === '' ? '' : isNaN(rawValue) ? rawValue : Number(rawValue);
    setTargetDcAcRatio(value);
    setIsStale(true);
  };

  return (
    <div className="parameters-drawer-container">
      <div className="drawer-header">
        <h3 className="drawer-title">
          <Sliders size={18} color="#38bdf8" /> Simulation Inputs
        </h3>
        {isStale && <span className="stale-pill animate-pulse">Inputs Modified</span>}
      </div>

      <div className="drawer-scroll-body">
        
        {/* ACCORDION 1: CLIMATE & LOCATION */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('physics')}>
            <span className="acc-title"><Sun size={15} color="#38bdf8" /> Climate & Location</span>
            {openSections.physics ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSections.physics && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Optimization Strategy:</label>
                <select 
                  value={params.scenario} 
                  onChange={(e) => handleTextChange('scenario', e.target.value)}
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
                  type="text" 
                  inputMode="decimal"
                  value={params.base_irradiance ?? ''} 
                  onChange={(e) => handleTextChange('base_irradiance', e.target.value)}
                  className="number-input"
                  placeholder="e.g. 1050"
                />
              </div>

              <div className="input-group">
                <label>Ambient Temperature (°C):</label>
                <input 
                  type="text" 
                  inputMode="decimal"
                  value={params.ambient_temp_c ?? ''} 
                  onChange={(e) => handleTextChange('ambient_temp_c', e.target.value)}
                  className="number-input"
                  placeholder="e.g. 25"
                />
              </div>

              <div className="input-group">
                <label>Bifacial Ground Albedo:</label>
                <select 
                  value={params.ground_albedo || "None"} 
                  onChange={(e) => handleTextChange('ground_albedo', e.target.value)}
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

        {/* ACCORDION 2: SCALE & ECONOMICS */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('financials')}>
            <span className="acc-title"><DollarSign size={15} color="#a855f7" /> Scale & Economics</span>
            {openSections.financials ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSections.financials && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Project Capacity Scale:</label>
                <div className="row-inputs">
                  <input 
                    type="text" 
                    inputMode="decimal"
                    value={params.project_size_mwp ?? ''} 
                    onChange={(e) => handleTextChange('project_size_mwp', e.target.value)}
                    className="number-input flex-1"
                    placeholder="e.g. 50"
                  />
                  <select 
                    value={params.project_size_unit} 
                    onChange={(e) => handleTextChange('project_size_unit', e.target.value)}
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
                  type="text" 
                  inputMode="decimal"
                  value={params.ppa_rate_eur_mwh ?? ''} 
                  onChange={(e) => handleTextChange('ppa_rate_eur_mwh', e.target.value)}
                  className="number-input"
                  placeholder="e.g. 45"
                />
              </div>

              <div className="input-group">
                <label>Discount Rate (%):</label>
                <input 
                  type="text" 
                  inputMode="decimal"
                  value={params.discount_rate_pct ?? ''} 
                  onChange={(e) => handleTextChange('discount_rate_pct', e.target.value)}
                  className="number-input"
                  placeholder="e.g. 5.0"
                />
              </div>
            </div>
          )}
        </div>

        {/* ACCORDION 3: INVERTER FLEET */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('inverter')}>
            <span className="acc-title"><Zap size={15} color="#10b981" /> Inverter Fleet</span>
            {openSections.inverter ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {openSections.inverter && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Inverter Selection:</label>
                <select 
                  value={selectedInverterId} 
                  onChange={(e) => handleInverterChange(e.target.value)}
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
                  type="text" 
                  inputMode="decimal"
                  value={targetDcAcRatio ?? ''} 
                  onChange={(e) => handleRatioChange(e.target.value)}
                  className="number-input"
                  placeholder="e.g. 1.25"
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
          className={`btn-simulate-glow ${isStale ? 'nudge-shake-active' : ''}`}
        >
          {loading ? 'Running MCDA Simulation...' : isStale ? '⚡ Re-Run Simulation (Save Run to History)' : '🚀 Run Physics Engine Simulation'}
        </button>
      </div>
    </div>
  );
}
