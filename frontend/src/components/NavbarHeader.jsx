import React from 'react';
import { Sun, FileText, CheckCircle, Clock, Zap, Search, User } from 'lucide-react';

export default function NavbarHeader({ 
  params, 
  selectedModule, 
  handleExportPdf, 
  exportingPdf,
  hasSimulated 
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
