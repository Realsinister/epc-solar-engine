import React from 'react';
import { Sun, FileText, CheckCircle, Clock, Zap, Search, User } from 'lucide-react';

export default function NavbarHeader({ 
  params, 
  selectedModule, 
  handleExportPdf, 
  exportingPdf,
  hasSimulated,
  currency = 'EUR',
  setCurrency
}) {
  return (
    <header className="top-exec-header">
      <div className="header-brand">
        <div className="logo-icon-bg">
          <Sun size={20} color="#38bdf8" />
        </div>
        <div className="brand-text">
          <span className="brand-name">EPC Solar <span className="text-gradient">Engine</span></span>
          <span className="brand-sub">Executive Decision & Procurement Platform</span>
        </div>
      </div>

      {hasSimulated && (
        <div className="header-status-bar">
          <div className="status-badge active-status">
            <span className="status-dot"></span>
            <span>Running / Optimal</span>
          </div>

          <div className="status-divider"></div>

          <div className="status-item">
            <span className="status-label">Project Scale:</span>
            <span className="status-val">{params.project_size_mwp} {params.project_size_unit}</span>
          </div>

          <div className="status-divider"></div>

          <div className="status-item">
            <span className="status-label">Scenario:</span>
            <span className="status-val highlight-cyan">{params.scenario}</span>
          </div>
        </div>
      )}

      <div className="header-actions">
        {setCurrency && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid var(--border-light)',
            borderRadius: '8px',
            padding: '2px 8px',
            fontSize: '12px'
          }}>
            <span style={{ color: 'var(--text-muted)', marginRight: '6px', fontSize: '11px' }}>CURRENCY:</span>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#38bdf8',
                fontWeight: 'bold',
                cursor: 'pointer',
                outline: 'none',
                fontSize: '12px'
              }}
            >
              <option value="EUR" style={{ background: '#1e293b', color: '#fff' }}>EUR (€)</option>
              <option value="USD" style={{ background: '#1e293b', color: '#fff' }}>USD ($)</option>
              <option value="GBP" style={{ background: '#1e293b', color: '#fff' }}>GBP (£)</option>
              <option value="AUD" style={{ background: '#1e293b', color: '#fff' }}>AUD (A$)</option>
            </select>
          </div>
        )}

        {hasSimulated && selectedModule && (
          <button
            onClick={handleExportPdf}
            disabled={exportingPdf}
            className="btn-export-pdf"
          >
            <FileText size={15} />
            <span>{exportingPdf ? 'Generating PDF...' : 'Export Executive Briefing (PDF)'}</span>
          </button>
        )}

        <div className="user-profile-badge">
          <div className="avatar-circle">
            <User size={16} color="#94a3b8" />
          </div>
          <span className="user-name">Executive Suite</span>
        </div>
      </div>
    </header>
  );
}
