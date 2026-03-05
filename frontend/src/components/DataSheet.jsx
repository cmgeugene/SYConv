import React, { useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

// Register all community features
ModuleRegistry.registerModules([AllCommunityModule]);

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';

import { Loader2 } from 'lucide-react';

const ActionCellRenderer = (props) => {
    if (props.data.isLoading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', height: '100%', color: '#3b82f6' }}>
                <Loader2 size={18} className="spin-animation" />
                <span style={{ marginLeft: '6px', fontSize: '0.85em', fontWeight: 500 }}>Translating...</span>
            </div>
        );
    }
    return (
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
            <button
                onClick={() => props.context.translateRow(props.node)}
                style={{ padding: '4px 8px', cursor: 'pointer', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontSize: '0.85em', fontWeight: 500 }}
            >
                ⟳ Translate
            </button>
        </div>
    );
};

export default function DataSheet({ rowData, onDataChange, selectedModel }) {
    const gridRef = React.useRef(null);

    const translateRow = useCallback(async (node) => {
        const data = node.data;
        if (!data.word || !data.word.trim() || !data.context || !data.context.trim()) {
            console.warn("Word or Context is missing. Cannot translate.");
            return;
        }

        node.setDataValue('isLoading', true);
        if (gridRef.current && gridRef.current.api) {
            gridRef.current.api.refreshCells({ rowNodes: [node], force: true });
        }

        try {
            const response = await fetch('http://localhost:8000/api/translate-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    word: data.word,
                    context: data.context,
                    model: selectedModel
                })
            });
            const result = await response.json();

            if (result.status === 'success' && result.data) {
                node.setDataValue('lemma', result.data.lemma || '');
                node.setDataValue('pos', result.data.pos || '');
                node.setDataValue('meaning', result.data.meaning || '');
            } else {
                console.error("Translation returned an error:", result);
            }
        } catch (err) {
            console.error("Translation API call failed:", err);
            alert("Translation failed. Ensure backend map is running.");
        } finally {
            node.setDataValue('isLoading', false);
            if (gridRef.current && gridRef.current.api) {
                gridRef.current.api.refreshCells({ rowNodes: [node], force: true });
            }
        }
    }, [selectedModel]);

    const columnDefs = useMemo(() => [
        { field: 'word', headerName: 'Word / Phrase', editable: true, flex: 1.5 },
        { field: 'lemma', headerName: 'Lemma (원형)', editable: true, flex: 1 },
        { field: 'pos', headerName: 'POS', editable: true, flex: 1 },
        { field: 'meaning', headerName: 'Meaning', editable: true, flex: 2 },
        { field: 'context', headerName: 'Context (원문)', editable: true, flex: 3 },
        {
            field: 'isLoading',
            headerName: 'Actions',
            flex: 0.8,
            cellRenderer: ActionCellRenderer,
            editable: false,
            sortable: false,
            filter: false
        }
    ], []);

    const defaultColDef = useMemo(() => ({
        resizable: true,
        sortable: true,
        filter: true,
    }), []);

    const onGridReady = (params) => {
        params.api.sizeColumnsToFit();
    };

    const onCellValueChanged = (params) => {
        // Sync data back to App.jsx parent component
        if (!gridRef.current || !gridRef.current.api) return;
        const updatedData = [];
        gridRef.current.api.forEachNode(node => updatedData.push(node.data));
        onDataChange(updatedData);

        // Auto-Trigger Logic: If word or context is edited, and both are populated, and meaning is empty, auto-translate
        const { data, colDef } = params;

        // Ensure we don't trigger if it's the loading state or LLM output updating the cell
        if (colDef.field === 'word' || colDef.field === 'context') {
            const hasWord = data.word && data.word.trim() !== '';
            const hasContext = data.context && data.context.trim() !== '';
            const lacksMeaning = !data.meaning || data.meaning.trim() === '';

            if (hasWord && hasContext && lacksMeaning && !data.isLoading) {
                translateRow(params.node);
            }
        }
    };

    const getRowId = useMemo(() => {
        return (params) => params.data.id;
    }, []);

    const gridContext = useMemo(() => ({
        translateRow
    }), [translateRow]);

    return (
        <div className="ag-theme-quartz-dark" style={{ height: '100%', width: '100%', borderRadius: '8px', overflow: 'hidden' }}>
            <AgGridReact
                ref={gridRef}
                rowData={rowData}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                getRowId={getRowId}
                onGridReady={onGridReady}
                onCellValueChanged={onCellValueChanged}
                context={gridContext}
                rowHeight={44}
                headerHeight={48}
            />
        </div>
    );
}
