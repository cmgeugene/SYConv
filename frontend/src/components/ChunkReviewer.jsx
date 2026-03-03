import React from 'react';
import { Trash2, Merge, ArrowRight } from 'lucide-react';

export default function ChunkReviewer({ extractedChunks, onTextChange, onMergeChunkUp, onDeleteChunk, onNextStep }) {
    if (!extractedChunks || extractedChunks.length === 0) {
        return (
            <div className="upload-zone" style={{ border: 'none' }}>
                <p style={{ color: 'var(--text-muted)' }}>No highlights detected.</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', backgroundColor: 'var(--surface)' }}>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Review the chunked text below. The AI will use this text as the context to understand your highlighted words.
                    You can edit the text if OCR made any mistakes.
                </p>

                {extractedChunks.map((chunk, idx) => {
                    const selectedWordsCount = chunk.words.filter(w => w.selected).length;

                    if (selectedWordsCount === 0) return null; // Skip chunks with no active highlights

                    return (
                        <div key={idx} style={{
                            marginBottom: '1.5rem',
                            padding: '1rem',
                            backgroundColor: '#1e293b',
                            borderRadius: '8px',
                            border: '1px solid var(--border)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ fontWeight: '500', fontSize: '14px', color: 'var(--accent)' }}>Chunk {idx + 1}</span>
                                    {idx > 0 && (
                                        <button
                                            onClick={() => onMergeChunkUp(idx)}
                                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', padding: '4px' }}
                                            title="Merge into Previous Chunk"
                                        >
                                            <Merge size={14} />
                                        </button>
                                    )}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Highlights: {selectedWordsCount}</span>
                                    <button
                                        onClick={() => onDeleteChunk(idx)}
                                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#ef4444', display: 'flex', alignItems: 'center', padding: '4px' }}
                                        title="Delete Chunk"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>

                            <textarea
                                value={chunk.full_text}
                                onChange={(e) => onTextChange(idx, e.target.value)}
                                style={{
                                    width: '100%',
                                    minHeight: '120px',
                                    padding: '10px',
                                    borderRadius: '4px',
                                    border: '1px solid var(--border)',
                                    backgroundColor: '#0f172a',
                                    color: 'var(--text-light)',
                                    fontFamily: 'monospace',
                                    resize: 'vertical',
                                    lineHeight: '1.5'
                                }}
                            />
                        </div>
                    );
                })}
            </div>

            {/* Bottom Action Bar */}
            <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--bg-dark)' }}>
                <button
                    className="btn primary-btn"
                    onClick={onNextStep}
                    style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: '16px' }}
                >
                    Next: Word Corrections <ArrowRight size={18} style={{ marginLeft: '8px' }} />
                </button>
            </div>
        </div>
    );
}
