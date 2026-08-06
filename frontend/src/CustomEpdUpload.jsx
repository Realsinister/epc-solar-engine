import { useState, useEffect } from 'react';
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle, Trash2, Download, Database } from 'lucide-react';

export default function CustomEpdUpload({ onDatasetSelected }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [activeDatasetId, setActiveDatasetId] = useState('baseline');
  const [uploadResult, setUploadResult] = useState(null);

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/custom-epd/list');
      const data = await res.json();
      setDatasets(data);
    } catch (err) {
      console.error('Failed to fetch custom datasets', err);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file) => {
    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/custom-epd/upload', {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to upload file');
      }

      setUploadResult(data);
      fetchDatasets();
      if (data.dataset && data.dataset.id) {
        selectDataset(data.dataset.id, data.dataset.filename);
      }
    } catch (err) {
      alert("Upload Error: " + err.message);
    }
    setUploading(false);
  };

  const handleDeleteDataset = async (id) => {
    if (window.confirm("Are you sure you want to delete this custom vendor dataset?")) {
      try {
        await fetch(`http://127.0.0.1:8000/api/custom-epd/${id}`, { method: 'DELETE' });
        if (activeDatasetId === id) {
          selectDataset('baseline', 'Baseline Parquet EPD');
        }
        fetchDatasets();
      } catch (err) {
        console.error('Failed to delete custom dataset', err);
      }
    }
  };

  const selectDataset = (id, name) => {
    setActiveDatasetId(id);
    if (onDatasetSelected) {
      onDatasetSelected(id, name);
    }
  };

  const handleDownloadSampleCsv = () => {
    window.open('http://127.0.0.1:8000/api/custom-epd/sample-csv', '_blank');
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* HEADER & SAMPLE TEMPLATE DOWNLOAD */}
      <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 6px 0', color: 'var(--text-main)' }}>
            <FileSpreadsheet size={22} color="var(--accent-green)" />
            Custom EPD & Vendor Datasheet Import
          </h2>
          <p className="label-muted" style={{ margin: 0 }}>
            Upload custom vendor module datasheets (.csv or .xlsx) to evaluate non-standard panels against project parameters.
          </p>
        </div>

        <button
          onClick={handleDownloadSampleCsv}
          style={{
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.3)'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.15)'}
        >
          <Download size={16} /> Download Sample Template (.csv)
        </button>
      </div>

      {/* DROP ZONE */}
      <div 
        className="glass-panel"
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{
          border: dragActive ? '2px dashed var(--accent-cyan)' : '2px dashed var(--border-light)',
          backgroundColor: dragActive ? 'rgba(56, 189, 248, 0.1)' : 'rgba(0,0,0,0.2)',
          textAlign: 'center',
          padding: '36px 20px',
          cursor: 'pointer',
          borderRadius: '12px',
          transition: 'all 0.2s ease'
        }}
        onClick={() => document.getElementById('epd-file-input').click()}
      >
        <input 
          id="epd-file-input"
          type="file"
          accept=".csv, .xlsx, .xls"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        
        <UploadCloud size={48} color={dragActive ? 'var(--accent-cyan)' : 'var(--text-muted)'} style={{ marginBottom: '12px' }} />
        <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-main)' }}>
          {uploading ? 'Processing & Validating Vendor Datasheet...' : 'Drag & Drop Vendor CSV or Excel File Here'}
        </h3>
        <p className="label-muted" style={{ fontSize: '13px', margin: 0 }}>
          Supports <strong>.csv</strong> and <strong>.xlsx</strong> formats (Columns auto-mapped: Manufacturer, Model, Power, Efficiency, LCA Carbon, Price/Wp)
        </p>
      </div>

      {/* UPLOAD RESULT PREVIEW & WARNINGS */}
      {uploadResult && (
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 'bold' }}>
            <CheckCircle2 size={20} />
            Successfully imported '{uploadResult.dataset.filename}' ({uploadResult.dataset.module_count} modules loaded)
          </div>

          {uploadResult.warnings?.length > 0 && (
            <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.4)', padding: '12px', borderRadius: '6px' }}>
              <div style={{ color: '#fbbf24', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <AlertTriangle size={16} /> Column Auto-Mapping Notices:
              </div>
              <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-muted)', fontSize: '13px' }}>
                {uploadResult.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
              </ul>
            </div>
          )}

          {uploadResult.sample_preview?.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 10px 0', color: 'var(--text-main)' }}>Parsed Sample Preview:</h4>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: 'var(--text-main)', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-light)', backgroundColor: 'rgba(255,255,255,0.05)' }}>
                    <th style={{ padding: '8px' }}>Manufacturer</th>
                    <th style={{ padding: '8px' }}>Model</th>
                    <th style={{ padding: '8px' }}>Power (Wp)</th>
                    <th style={{ padding: '8px' }}>Efficiency (%)</th>
                    <th style={{ padding: '8px' }}>Carbon (gCO2e/kWh)</th>
                    <th style={{ padding: '8px' }}>Price (€/Wp)</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadResult.sample_preview.map((mod, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px' }}>{mod.manufacturer}</td>
                      <td style={{ padding: '8px' }}>{mod.name}</td>
                      <td style={{ padding: '8px' }}>{mod.module_power_Wp} Wp</td>
                      <td style={{ padding: '8px' }}>{mod.efficiency_pct}%</td>
                      <td style={{ padding: '8px' }}>{mod.carbon_intensity_mean}</td>
                      <td style={{ padding: '8px' }}>€{mod.estimated_price_wp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* MANAGED CUSTOM DATASETS LIST */}
      <div className="glass-panel">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 16px 0', color: 'var(--text-main)' }}>
          <Database size={20} color="var(--accent-blue)" />
          Available Datasets
        </h3>

        <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: 'var(--text-main)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
              <th style={{ padding: '10px' }}>Active</th>
              <th style={{ padding: '10px' }}>Dataset Source</th>
              <th style={{ padding: '10px' }}>Modules Count</th>
              <th style={{ padding: '10px' }}>Upload Date</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {/* Baseline Parquet Item */}
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', backgroundColor: activeDatasetId === 'baseline' ? 'rgba(59, 130, 246, 0.2)' : 'transparent' }}>
              <td style={{ padding: '10px' }}>
                <input 
                  type="radio" 
                  name="active_ds" 
                  checked={activeDatasetId === 'baseline'}
                  onChange={() => selectDataset('baseline', 'Baseline Parquet EPD')}
                />
              </td>
              <td style={{ padding: '10px', fontWeight: 'bold' }}>Baseline Parquet EPD Database (Standard)</td>
              <td style={{ padding: '10px' }}>20,000+ Modules</td>
              <td style={{ padding: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>Built-in Core</td>
              <td style={{ padding: '10px', textAlign: 'right', fontSize: '12px', color: 'var(--accent-green)' }}>Protected</td>
            </tr>

            {/* Custom Uploaded Items */}
            {datasets.map(ds => (
              <tr key={ds.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', backgroundColor: activeDatasetId === ds.id ? 'rgba(59, 130, 246, 0.2)' : 'transparent' }}>
                <td style={{ padding: '10px' }}>
                  <input 
                    type="radio" 
                    name="active_ds" 
                    checked={activeDatasetId === ds.id}
                    onChange={() => selectDataset(ds.id, ds.filename)}
                  />
                </td>
                <td style={{ padding: '10px' }}>{ds.filename}</td>
                <td style={{ padding: '10px' }}>{ds.module_count} Modules</td>
                <td style={{ padding: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>{new Date(ds.timestamp).toLocaleString()}</td>
                <td style={{ padding: '10px', textAlign: 'right' }}>
                  <button
                    onClick={() => handleDeleteDataset(ds.id)}
                    style={{
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      color: '#f87171',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}
