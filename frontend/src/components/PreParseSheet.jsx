import React, { useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { Bot, Trash2, ArrowUp, ArrowDown } from 'lucide-react';

export default function PreParseSheet({
    extractedChunks,
    onWordChange,
    onAddWord,
    onRemoveWord,
    onMoveWordUp,
    onMoveWordDown,
    onParseWords,
    isLoading
}) {
    const [rowData, setRowData] = useState([]);

    // Flatten selected words for the grid
    useEffect(() => {
        const flatData = [];
        if (extractedChunks) {
            extractedChunks.forEach((chunk, cIdx) => {
                chunk.words.forEach((w, wIdx) => {
                    if (w.selected) {
                        flatData.push({
                            chunkIdx: cIdx,
                            wordIdx: wIdx,
                            chunkDisplay: `Chunk ${cIdx + 1}`,
                            originalWord: w.text,
                            correctedWord: w.text // Initially same as original
                        });
                    }
                });
            });
        }
        setRowData(flatData);
    }, [extractedChunks]);

    const handleCellValueChanged = (params) => {
        const { data, newValue, colDef } = params;
        if (colDef.field === 'correctedWord') {
            // Update app state when a word is manually corrected in the grid
            onWordChange(data.chunkIdx, data.wordIdx, newValue);
        }
    };

    const columnDefs = [
        { field: 'chunkDisplay', headerName: 'Source', width: 90, sortable: true, filter: true },
        { field: 'originalWord', headerName: 'Original OCR', flex: 1, cellStyle: { color: 'var(--text-muted)' } },
        {
            field: 'correctedWord',
            headerName: 'Corrected Text',
            flex: 1,
            editable: true,
            cellStyle: { backgroundColor: 'rgba(59, 130, 246, 0.1)', cursor: 'text', border: '1px solid transparent' },
            cellEditorParams: {
                useFormatter: true,
            }
        },
        {
            headerName: 'Actions',
            width: 140,
            cellRenderer: (params) => {
                const { chunkIdx, wordIdx } = params.data;
                return (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', height: '100%' }}>
                        <button
                            onClick={() => onMoveWordUp(chunkIdx, wordIdx)}
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '4px' }}
                            title="Move Up"
                        ><ArrowUp size={16} /></button>
                        <button
                            onClick={() => onMoveWordDown(chunkIdx, wordIdx)}
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '4px' }}
                            title="Move Down"
                        ><ArrowDown size={16} /></button>
                        <button
                            onClick={() => onRemoveWord(chunkIdx, wordIdx)}
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#ef4444', padding: '4px' }}
                            title="Remove Word"
                        ><Trash2 size={16} /></button>
                    </div>
                );
            }
        }
    ];

    const defaultColDef = {
        resizable: true
    };

    if (rowData.length === 0) {
        return (
            <div className="upload-zone" style={{ border: 'none' }}>
                <p style={{ color: 'var(--text-muted)' }}>No words fully selected.<br />Go back and click on words to include them.</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <p style={{ fontSize: '14px', margin: 0, color: 'var(--text-light)' }}>
                    Double-click cells in the <b>Corrected Text</b> column to fix typos before AI parsing.
                </p>
                <div style={{ display: 'flex', gap: '8px' }}>
                    {extractedChunks.map((chunk, idx) => (
                        <button
                            key={idx}
                            onClick={() => onAddWord(idx)}
                            style={{ padding: '6px 12px', fontSize: '12px', backgroundColor: 'var(--highlight-box)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '4px', cursor: 'pointer' }}
                        >
                            + Add to Chunk {idx + 1}
                        </button>
                    ))}
                </div>
            </div>

            <div className="ag-theme-alpine-dark" style={{ flex: 1, width: '100%' }}>
                <AgGridReact
                    rowData={rowData}
                    columnDefs={columnDefs}
                    defaultColDef={defaultColDef}
                    rowSelection="multiple"
                    animateRows={true}
                    onCellValueChanged={handleCellValueChanged}
                />
            </div>

            <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--bg-dark)' }}>
                <button
                    className="btn primary-btn"
                    onClick={onParseWords}
                    disabled={isLoading}
                    style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: '16px' }}
                >
                    <Bot size={20} />
                    {isLoading ? 'Processing via Local AI...' : `Final Confirm & Send to AI (${rowData.length} words)`}
                </button>
            </div>
        </div>
    );
}
