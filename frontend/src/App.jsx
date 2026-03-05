import { useState, useEffect, useCallback } from 'react';
import './App.css';
import { Download, Trash2, Plus, RefreshCw } from 'lucide-react';
import DataSheet from './components/DataSheet';
import { exportToExcel } from './utils/exportHelper';

function App() {
  const [parsedData, setParsedData] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');

  const fetchModels = useCallback(() => {
    fetch('http://localhost:8000/api/models')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setModels(data.models);
          // Only auto-select first model if nothing is currently selected
          if (data.models.length > 0 && !selectedModel) {
            setSelectedModel(data.models[0]);
          }
        }
      })
      .catch(err => console.error("Error fetching models:", err));
  }, [selectedModel]);

  // Load from local storage on mount
  useEffect(() => {
    const saved = localStorage.getItem('syconv_vocabulary');
    if (saved) {
      try {
        const loaded = JSON.parse(saved);
        // Ensure all loaded items have a unique id for AG-Grid reconciliation
        const mapped = loaded.map(item => ({ ...item, id: item.id || crypto.randomUUID() }));
        setParsedData(mapped);
      } catch (e) {
        console.error("Failed to load vocabulary from local storage", e);
      }
    }

    fetchModels();
  }, []);

  // Sync to local storage on change
  useEffect(() => {
    localStorage.setItem('syconv_vocabulary', JSON.stringify(parsedData));
  }, [parsedData]);

  const clearAllData = () => {
    if (window.confirm("Are you sure you want to clear all accumulated vocabulary?")) {
      setParsedData([]);
      localStorage.removeItem('syconv_vocabulary');
    }
  };

  const handleExportExcel = () => {
    exportToExcel(parsedData, 'vocabulary_export.xlsx');
  };

  const handleAddRow = () => {
    setParsedData(prev => [
      ...prev,
      { id: crypto.randomUUID(), word: '', lemma: '', pos: '', meaning: '', context: '' }
    ]);
  };

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#1e1e1e', color: 'white' }}>
      <header className="app-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', backgroundColor: '#2d2d2d', borderBottom: '1px solid #404040' }}>
        <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>SYConv Data Sheet</h1>
        <div className="header-actions" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginRight: '20px', background: '#374151', padding: '4px 12px', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.85rem', color: '#9ca3af', fontWeight: 500 }}>Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ background: 'transparent', color: 'white', border: 'none', fontSize: '0.9rem', outline: 'none', cursor: 'pointer' }}
            >
              {models.length > 0 ? (
                models.map(m => <option key={m} value={m} style={{ background: '#2d2d2d', color: 'white' }}>{m}</option>)
              ) : (
                <option value="" style={{ background: '#2d2d2d', color: 'white' }}>No models found</option>
              )}
            </select>
            <button
              onClick={fetchModels}
              title="Refresh models"
              style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '0 0 0 4px' }}
            >
              <RefreshCw size={14} />
            </button>
          </div>

          <button
            onClick={handleAddRow}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 500 }}
          >
            <Plus size={18} /> Add Row
          </button>
          <button
            onClick={handleExportExcel}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: '#4b5563', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            <Download size={18} /> Export Excel
          </button>
          <button
            onClick={clearAllData}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            <Trash2 size={18} /> Clear Data
          </button>
        </div>
      </header>

      <main className="main-content" style={{ flex: 1, padding: '24px', overflow: 'hidden' }}>
        <DataSheet rowData={parsedData} onDataChange={setParsedData} selectedModel={selectedModel} />
      </main>
    </div>
  );
}

export default App;
