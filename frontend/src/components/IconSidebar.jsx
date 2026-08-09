import React from 'react';
import { 
  LayoutDashboard, Activity, Layers, FileSpreadsheet, Clock, Sliders, ChevronLeft, ChevronRight 
} from 'lucide-react';

export default function IconSidebar({ 
  activeTab, 
  setActiveTab, 
  subView, 
  setSubView, 
  hasSimulated,
  sidebarCollapsed,
  setSidebarCollapsed
}) {
  return (
    <aside className={`icon-nav-rail ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="nav-rail-group">
        <button
          className={`nav-rail-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
          title="Dashboard & Analytics"
        >
          <LayoutDashboard size={20} />
          <span className="rail-label">Dashboard</span>
        </button>

        <button
          className={`nav-rail-btn ${activeTab === 'vendor_data' ? 'active' : ''}`}
          onClick={() => setActiveTab('vendor_data')}
          title="Vendor EPD Data Upload"
        >
          <FileSpreadsheet size={20} />
          <span className="rail-label">Vendor EPDs</span>
        </button>

        <button
          className={`nav-rail-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
          title="Simulation Run History & Comparison"
        >
          <Clock size={20} />
          <span className="rail-label">History</span>
        </button>
      </div>

      <div className="rail-spacer"></div>

      {activeTab === 'dashboard' && hasSimulated && (
        <div className="subview-rail-group">
          <div className="rail-section-header">VIEWS</div>
          
          <button
            className={`rail-sub-btn ${subView === 'financials' ? 'active' : ''}`}
            onClick={() => setSubView('financials')}
            title="Executive Financials"
          >
            <LayoutDashboard size={16} />
            <span className="rail-label">Financials</span>
          </button>

          <button
            className={`rail-sub-btn ${subView === 'analytics' ? 'active' : ''}`}
            onClick={() => setSubView('analytics')}
            title="Deep-Dive Physics & Sensitivity"
          >
            <Activity size={16} />
            <span className="rail-label">Deep Dive</span>
          </button>

          <button
            className={`rail-sub-btn ${subView === 'hybrid' ? 'active' : ''}`}
            onClick={() => setSubView('hybrid')}
            title="Multi-Block Fleet Hybridization"
          >
            <Layers size={16} />
            <span className="rail-label">Hybrid Fleet</span>
          </button>
        </div>
      )}

      <button
        className="collapse-toggle-btn"
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
      >
        {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}
