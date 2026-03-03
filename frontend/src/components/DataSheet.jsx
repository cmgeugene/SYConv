import React, { useState, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

// Register all community features
ModuleRegistry.registerModules([AllCommunityModule]);

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css'; // Using modern Quartz theme, or balham-dark

export default function DataSheet({ rowData, onDataChange }) {
    const gridRef = React.useRef(null);

    const columnDefs = useMemo(() => [
        { field: 'word', headerName: 'Word / Phrase', editable: true, flex: 1.5 },
        { field: 'pos', headerName: 'POS', editable: true, flex: 1 },
        { field: 'meaning', headerName: 'Meaning', editable: true, flex: 2 },
        { field: 'is_idiom', headerName: 'Idiom?', editable: true, width: 100, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: [true, false] } }
    ], []);

    const defaultColDef = useMemo(() => ({
        resizable: true,
        sortable: true,
        filter: true,
    }), []);

    const onGridReady = (params) => {
        params.api.sizeColumnsToFit();
    };

    const onCellValueChanged = () => {
        if (!gridRef.current || !gridRef.current.api) return;
        const updatedData = [];
        gridRef.current.api.forEachNode(node => updatedData.push(node.data));
        onDataChange(updatedData);
    };

    return (
        <div className="ag-theme-quartz-dark" style={{ height: '100%', width: '100%', borderRadius: '8px', overflow: 'hidden' }}>
            <AgGridReact
                ref={gridRef}
                rowData={rowData}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                onGridReady={onGridReady}
                onCellValueChanged={onCellValueChanged}
                rowHeight={40}
                headerHeight={48}
            />
        </div>
    );
}
