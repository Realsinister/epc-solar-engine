import React, { useState } from 'react';
import { Sliders, Sun, DollarSign, Zap, ChevronDown, ChevronUp } from 'lucide-react';

export default function SidebarParameters({
  params,
  setParams,
  handleSimulate,
  loading,
  isStale,
  setIsStale,
  hasSimulated,
  selectedInverterId,
  setSelectedInverterId,
  inverters,
  targetDcAcRatio,
  setTargetDcAcRatio,
  currency = 'EUR'
}) {
  const CURRENCY_SYMBOLS = { EUR: '€', USD: '$', GBP: '£', AUD: 'A$' };
  const curSym = CURRENCY_SYMBOLS[currency] || '€';

  const [openSections, setOpenSections] = useState({
    physics: true,
    financials: true,
    inverter: true
  });

  const toggleSection = (sec) => {
    setOpenSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  const handleTextChange = (key, rawValue) => {
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

  // Determine button class and label based on state
  let buttonClass = 'btn-simulate-glow';
  let buttonLabel = 'Run Analytics';
  let isButtonDisabled = loading;

  if (loading) {
    buttonLabel = 'Running Analytics...';
    isButtonDisabled = true;
  } else if (isStale) {
    buttonClass = 'btn-simulate-glow nudge-shake-active';
    buttonLabel = '⚡ Run Analytics';
    isButtonDisabled = false;
  } else if (hasSimulated) {
    buttonClass = 'btn-simulate-glow btn-greyed-out';
    buttonLabel = '✓ Analytics Up to Date';
    isButtonDisabled = true;
  }

  return (
    <div className="parameters-drawer-container">
      <div className="drawer-header">
        <h3 className="drawer-title">
          <Sliders size={18} color="#38bdf8" /> Simulation Inputs
        </h3>
        {isStale && <span className="stale-pill animate-pulse">Inputs Modified</span>}
      </div>

      <div className="drawer-scroll-body">
        
        {/* PROJECT META */}
        <div className="input-group" style={{ marginBottom: '4px' }}>
          <label>Project Name / Tag:</label>
          <input 
            type="text" 
            value={params.project_name || ''} 
            onChange={(e) => {
              setParams(prev => ({ ...prev, project_name: e.target.value }));
              setIsStale(true);
            }}
            className="number-input"
            placeholder="e.g. Client A - 50MW"
          />
        </div>

        {/* ACCORDION 1: CLIMATE & LOCATION */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('physics')}>
            <span className="acc-title"><Sun size={15} color="#38bdf8" /> Climate & Location</span>
            {openSections.physics ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
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
                  <option value="Eco-Flagship (Minimize Carbon)">🌿 Eco-Flagship (Min Carbon)</option>
                  <option value="Utility Scale (Lowest LCOE)">⚡ Utility Scale (Lowest LCOE)</option>
                  <option value="Space Constrained (Max Efficiency)">🎯 Space Constrained (Max Eff)</option>
                </select>
              </div>

              <div className="input-group">
                <label>Technology Architecture:</label>
                <select 
                  value={params.tech_filter || "all"} 
                  onChange={(e) => handleTextChange('tech_filter', e.target.value)}
                  className="select-input"
                >
                  <option value="all">🌐 All Technologies (MCDA)</option>
                  <option value="topcon_hjt">⚡ N-Type TOPCon & HJT</option>
                  <option value="bifacial">🪞 Bifacial Glass-Glass Fleets</option>
                  <option value="thin_film">🌿 Thin-Film (CdTe / CIGS)</option>
                  <option value="low_carbon">🛡️ Low-Carbon Certified</option>
                </select>
              </div>

              <div className="row-inputs-2col">
                <div className="input-group">
                  <label>Irradiance (kWh/m²):</label>
                  <input 
                    type="text" 
                    inputMode="decimal"
                    value={params.base_irradiance ?? ''} 
                    onChange={(e) => handleTextChange('base_irradiance', e.target.value)}
                    className="number-input"
                    placeholder="1050"
                  />
                </div>

                <div className="input-group">
                  <label>Ambient Temp (°C):</label>
                  <input 
                    type="text" 
                    inputMode="decimal"
                    value={params.ambient_temp_c ?? ''} 
                    onChange={(e) => handleTextChange('ambient_temp_c', e.target.value)}
                    className="number-input"
                    placeholder="25"
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Bifacial Ground Albedo:</label>
                <select 
                  value={params.ground_albedo || "None"} 
                  onChange={(e) => handleTextChange('ground_albedo', e.target.value)}
                  className="select-input"
                >
                  <option value="None">Monofacial / Default (0.00)</option>
                  <option value="0.20">Grass / Concrete (0.20 - +5.2%)</option>
                  <option value="0.50">Light Sand / Paint (0.50 - +11.8%)</option>
                  <option value="0.85">Fresh Snow / Specular (0.85 - +19.4%)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* ACCORDION 2: SCALE & ECONOMICS */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('financials')}>
            <span className="acc-title"><DollarSign size={15} color="#a855f7" /> Scale & Economics</span>
            {openSections.financials ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </div>

          {openSections.financials && (
            <div className="accordion-content">
              <div className="input-group">
                <label>Market Region & Policy:</label>
                <select 
                  value={params.market_region || "EU"} 
                  onChange={(e) => handleTextChange('market_region', e.target.value)}
                  className="select-input"
                >
                  <option value="EU">🇪🇺 European Union (CBAM €80/t)</option>
                  <option value="US">🇺🇸 North America (US / IRA)</option>
                  <option value="APAC">🌍 APAC / Middle East / Global</option>
                </select>
              </div>
              <div className="input-group">
                <label>Project Capacity Scale:</label>
                <div className="row-inputs">
                  <input 
                    type="text" 
                    inputMode="decimal"
                    value={params.project_size_mwp ?? ''} 
                    onChange={(e) => handleTextChange('project_size_mwp', e.target.value)}
                    className="number-input flex-1"
                    placeholder="50"
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

              <div className="row-inputs-2col">
                <div className="input-group">
                  <label>PPA Tariff ({curSym}/MWh):</label>
                  <input 
                    type="text" 
                    inputMode="decimal"
                    value={params.ppa_rate_eur_mwh ?? ''} 
                    onChange={(e) => handleTextChange('ppa_rate_eur_mwh', e.target.value)}
                    className="number-input"
                    placeholder="45"
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
                    placeholder="5.0"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ACCORDION 3: INVERTER FLEET */}
        <div className="accordion-item">
          <div className="accordion-header" onClick={() => toggleSection('inverter')}>
            <span className="acc-title"><Zap size={15} color="#10b981" /> Inverter Fleet</span>
            {openSections.inverter ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
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
                  placeholder="1.25"
                />
              </div>
            </div>
          )}
        </div>

      </div>

      <div className="drawer-footer">
        <button 
          onClick={handleSimulate} 
          disabled={isButtonDisabled}
          className={buttonClass}
        >
          {buttonLabel}
        </button>
      </div>
    </div>
  );
}
