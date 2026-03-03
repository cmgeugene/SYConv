import React, { useState, useRef } from 'react';

export default function DocumentViewer({ previewUrl, parsedData, extractedChunks, onToggleWord, onCreateCustomChunk, step }) {
    const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
    const [isDrawing, setIsDrawing] = useState(false);
    const [startPos, setStartPos] = useState({ x: 0, y: 0 });
    const [currentPos, setCurrentPos] = useState({ x: 0, y: 0 });
    const imgRef = useRef(null);

    const handleImageLoad = (e) => {
        setNaturalSize({
            width: e.target.naturalWidth,
            height: e.target.naturalHeight
        });
    };

    const handleMouseDown = (e) => {
        if (step !== 'SELECT') return;
        const rect = imgRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        setStartPos({ x, y });
        setCurrentPos({ x, y });
        setIsDrawing(true);
    };

    const handleMouseMove = (e) => {
        if (!isDrawing || step !== 'SELECT') return;
        const rect = imgRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        setCurrentPos({ x, y });
    };

    const handleMouseUp = (e) => {
        if (!isDrawing || step !== 'SELECT') return;
        setIsDrawing(false);

        const rect = imgRef.current.getBoundingClientRect();
        const scaleX = naturalSize.width / rect.width;
        const scaleY = naturalSize.height / rect.height;

        const x1 = Math.min(startPos.x, currentPos.x) * scaleX;
        const y1 = Math.min(startPos.y, currentPos.y) * scaleY;
        const x2 = Math.max(startPos.x, currentPos.x) * scaleX;
        const y2 = Math.max(startPos.y, currentPos.y) * scaleY;

        // Trigger callback if the drawn box is reasonably large (e.g. > 10x10 natural pixels)
        if (x2 - x1 > 10 && y2 - y1 > 10) {
            if (onCreateCustomChunk) {
                onCreateCustomChunk([Math.round(x1), Math.round(y1), Math.round(x2), Math.round(y2)]);
            }
        }
    };

    // Flatten data for rendering depending on the step
    let boxesToRender = [];
    if (step === 'SELECT' && extractedChunks) {
        extractedChunks.forEach((chunk, cIdx) => {
            // Render the Chunk bounding box
            if (chunk.chunk_bbox && chunk.chunk_bbox.length === 4) {
                boxesToRender.push({
                    text: `Chunk ${cIdx + 1}`,
                    bbox: chunk.chunk_bbox,
                    selected: false,
                    onClick: null,
                    title: `Chunk ${cIdx + 1}`,
                    type: 'chunk_bg'
                });
            }

            chunk.words.forEach((w, wIdx) => {
                boxesToRender.push({
                    text: w.text,
                    bbox: w.bbox,
                    selected: w.selected,
                    onClick: () => onToggleWord(cIdx, wIdx),
                    title: `Click to ${w.selected ? 'Exclude' : 'Include'}: ${w.text}`,
                    type: 'extract'
                });
            });
        });
    } else if (step === 'RESULT' && parsedData) {
        parsedData.forEach(item => {
            boxesToRender.push({
                text: item.word,
                bbox: item.bbox,
                selected: true,
                onClick: null,
                title: `${item.word} (${item.pos}): ${item.meaning}`,
                type: 'result'
            });
        });
    }

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'auto', backgroundColor: '#e2e8f0', borderRadius: '8px' }}>
            <div
                style={{ position: 'relative', display: 'inline-block', width: '100%', touchAction: 'none' }}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <img
                    ref={imgRef}
                    src={previewUrl}
                    alt="Document Viewer"
                    onLoad={handleImageLoad}
                    draggable={false}
                    style={{ width: '100%', display: 'block', userSelect: 'none' }}
                />

                {naturalSize.width > 0 && boxesToRender.map((box, idx) => {
                    if (!box.bbox || box.bbox.length !== 4) return null;

                    const [x1, y1, x2, y2] = box.bbox;

                    const leftPct = (x1 / naturalSize.width) * 100;
                    const topPct = (y1 / naturalSize.height) * 100;
                    const widthPct = ((x2 - x1) / naturalSize.width) * 100;
                    const heightPct = ((y2 - y1) / naturalSize.height) * 100;

                    if (box.type === 'chunk_bg') {
                        return (
                            <div
                                key={`chunk-${idx}`}
                                title={box.title}
                                style={{
                                    position: 'absolute',
                                    left: `${leftPct}%`,
                                    top: `${topPct}%`,
                                    width: `${widthPct}%`,
                                    height: `${heightPct}%`,
                                    backgroundColor: 'rgba(56, 189, 248, 0.05)',
                                    border: '1px dashed rgba(56, 189, 248, 0.5)',
                                    borderRadius: '6px',
                                    pointerEvents: 'none', // Allow clicking through to highlights
                                    zIndex: 1
                                }}
                            >
                                <span style={{
                                    position: 'absolute',
                                    top: '-20px',
                                    left: '0',
                                    fontSize: '11px',
                                    fontWeight: 'bold',
                                    color: 'rgba(56, 189, 248, 0.8)',
                                    backgroundColor: 'rgba(15, 23, 42, 0.7)',
                                    padding: '2px 6px',
                                    borderRadius: '4px'
                                }}>
                                    {box.text}
                                </span>
                            </div>
                        );
                    }

                    const isSelected = box.type === 'extract' && box.selected;

                    return (
                        <div
                            key={idx}
                            title={box.title}
                            onClick={box.onClick}
                            style={{
                                position: 'absolute',
                                left: `${leftPct}%`,
                                top: `${topPct}%`,
                                width: `${widthPct}%`,
                                height: `${heightPct}%`,
                                backgroundColor: isSelected ? 'var(--highlight-box)' : 'transparent',
                                border: isSelected ? '2px solid var(--accent)' : '2px dashed #ef4444',
                                borderRadius: '3px',
                                cursor: box.type === 'extract' ? 'pointer' : 'default',
                                transition: 'all 0.2s',
                                zIndex: 2
                            }}
                            onMouseEnter={(e) => {
                                if (box.type === 'extract') {
                                    e.currentTarget.style.backgroundColor = isSelected ? 'rgba(59, 130, 246, 0.6)' : 'rgba(239, 68, 68, 0.1)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (box.type === 'extract') {
                                    e.currentTarget.style.backgroundColor = isSelected ? 'var(--highlight-box)' : 'transparent';
                                }
                            }}
                        >
                        </div>
                    );
                })}

                {isDrawing && (
                    <div style={{
                        position: 'absolute',
                        left: `${Math.min(startPos.x, currentPos.x)}px`,
                        top: `${Math.min(startPos.y, currentPos.y)}px`,
                        width: `${Math.abs(currentPos.x - startPos.x)}px`,
                        height: `${Math.abs(currentPos.y - startPos.y)}px`,
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        border: '2px dashed #3b82f6',
                        pointerEvents: 'none',
                        zIndex: 10
                    }}></div>
                )}
            </div>
        </div>
    );
}
