import { useState } from 'react';
import './App.css';
import { Upload, Download, FileType, ArrowRight } from 'lucide-react';
import DocumentViewer from './components/DocumentViewer';
import DataSheet from './components/DataSheet';
import ChunkReviewer from './components/ChunkReviewer';
import PreParseSheet from './components/PreParseSheet';
import { exportToExcel } from './utils/exportHelper';

function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [parsedData, setParsedData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [extractedChunks, setExtractedChunks] = useState(null);
  const [allOcrWords, setAllOcrWords] = useState([]);
  const [step, setStep] = useState('UPLOAD'); // UPLOAD, SELECT, PRE_PARSE, RESULT

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('http://localhost:8000/api/extract-highlights', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (result.status === 'success') {
        setExtractedChunks([]);
        setAllOcrWords(result.all_ocr_results || []);
        setStep('SELECT');
      } else {
        alert('Failed to extract highlights');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error connecting to backend');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleWord = (chunkIdx, wordIdx) => {
    const newChunks = [...extractedChunks];
    newChunks[chunkIdx].words[wordIdx].selected = !newChunks[chunkIdx].words[wordIdx].selected;
    setExtractedChunks(newChunks);
  };

  const handleUpdateWordText = (chunkIdx, wordIdx, newText) => {
    const newChunks = [...extractedChunks];
    newChunks[chunkIdx].words[wordIdx].text = newText;
    setExtractedChunks(newChunks);
  };

  const handleTextChange = (chunkIdx, newText) => {
    const newChunks = [...extractedChunks];
    newChunks[chunkIdx].full_text = newText;
    setExtractedChunks(newChunks);
  };

  const handleDeleteChunk = (chunkIdx) => {
    setExtractedChunks(extractedChunks.filter((_, idx) => idx !== chunkIdx));
  };

  const handleAddWord = (chunkIdx) => {
    const newChunks = [...extractedChunks];
    newChunks[chunkIdx].words.push({ text: 'new', bbox: [0, 0, 0, 0], selected: true });
    setExtractedChunks(newChunks);
  };

  const handleRemoveWord = (chunkIdx, wordIdx) => {
    const newChunks = [...extractedChunks];
    newChunks[chunkIdx].words.splice(wordIdx, 1);
    setExtractedChunks(newChunks);
  };

  const handleMoveWordUp = (chunkIdx, wordIdx) => {
    if (wordIdx === 0) return;
    const newChunks = [...extractedChunks];
    const words = newChunks[chunkIdx].words;
    [words[wordIdx - 1], words[wordIdx]] = [words[wordIdx], words[wordIdx - 1]];
    setExtractedChunks(newChunks);
  };

  const handleMoveWordDown = (chunkIdx, wordIdx) => {
    const newChunks = [...extractedChunks];
    const words = newChunks[chunkIdx].words;
    if (wordIdx === words.length - 1) return;
    [words[wordIdx + 1], words[wordIdx]] = [words[wordIdx], words[wordIdx + 1]];
    setExtractedChunks(newChunks);
  };

  const handleMergeChunkUp = (chunkIdx) => {
    if (chunkIdx === 0) return;
    const newChunks = [...extractedChunks];
    const topChunk = newChunks[chunkIdx - 1];
    const bottomChunk = newChunks[chunkIdx];

    // Merge words
    topChunk.words = [...topChunk.words, ...bottomChunk.words];
    // Merge full text
    topChunk.full_text = `${topChunk.full_text}\n\n${bottomChunk.full_text}`;
    // Merge bbox
    if (topChunk.chunk_bbox.length === 4 && bottomChunk.chunk_bbox.length === 4) {
      topChunk.chunk_bbox = [
        Math.min(topChunk.chunk_bbox[0], bottomChunk.chunk_bbox[0]),
        Math.min(topChunk.chunk_bbox[1], bottomChunk.chunk_bbox[1]),
        Math.max(topChunk.chunk_bbox[2], bottomChunk.chunk_bbox[2]),
        Math.max(topChunk.chunk_bbox[3], bottomChunk.chunk_bbox[3])
      ];
    }

    // Remove the bottom chunk
    newChunks.splice(chunkIdx, 1);
    setExtractedChunks(newChunks);
  };

  const handleCreateCustomChunk = (bbox) => {
    const [x1, y1, x2, y2] = bbox;

    // Find all raw OCR words that intersect with this custom drawn bbox
    const wordsInRegion = allOcrWords.filter(w => {
      const [wx1, wy1, wx2, wy2] = w.bbox;
      const interX1 = Math.max(x1, wx1);
      const interY1 = Math.max(y1, wy1);
      const interX2 = Math.min(x2, wx2);
      const interY2 = Math.min(y2, wy2);

      const interArea = Math.max(0, interX2 - interX1 + 1) * Math.max(0, interY2 - interY1 + 1);
      const wordArea = (wx2 - wx1 + 1) * (wy2 - wy1 + 1);

      return interArea / wordArea > 0.15; // 15% overlap
    });

    if (wordsInRegion.length === 0) return;

    // Apply robust reading-order sort handling slanted/skewed documents
    const sortReadingOrder = (boxes) => {
      if (!boxes || boxes.length === 0) return [];
      let unassigned = [...boxes].sort((a, b) => a.bbox[1] - b.bbox[1]);
      const lines = [];

      while (unassigned.length > 0) {
        let seedIdx = 0;

        // Find true leftmost start by tracing backwards overlapping boxes
        while (true) {
          const seedBox = unassigned[seedIdx];
          const [sX1, sY1, , sY2] = seedBox.bbox;
          const sH = sY2 - sY1;
          let foundLeft = false;

          for (let i = 0; i < unassigned.length; i++) {
            if (i === seedIdx) continue;
            const cand = unassigned[i];
            const [cX1, cY1, , cY2] = cand.bbox;
            const cH = cY2 - cY1;

            const overlapTop = Math.max(sY1, cY1);
            const overlapBot = Math.min(sY2, cY2);
            const overlapH = Math.max(0, overlapBot - overlapTop);

            if (overlapH > 0.5 * Math.min(sH, cH)) {
              if (cX1 < sX1) {
                seedIdx = i;
                foundLeft = true;
                break;
              }
            }
          }
          if (!foundLeft) break;
        }

        const currentLine = [unassigned.splice(seedIdx, 1)[0]];

        // Trace rightward picking the closest overlapping box
        while (true) {
          const lastBox = currentLine[currentLine.length - 1];
          const [lX1, lY1, lX2, lY2] = lastBox.bbox;
          const lH = lY2 - lY1;

          let bestIdx = -1;
          let minDist = Infinity;

          for (let i = 0; i < unassigned.length; i++) {
            const cand = unassigned[i];
            const [cX1, cY1, , cY2] = cand.bbox;
            const cH = cY2 - cY1;

            const overlapTop = Math.max(lY1, cY1);
            const overlapBot = Math.min(lY2, cY2);
            const overlapH = Math.max(0, overlapBot - overlapTop);

            if (overlapH > 0.5 * Math.min(lH, cH)) {
              if (cX1 > lX1) {
                const dist = cX1 - lX2;
                if (dist < minDist) {
                  minDist = dist;
                  bestIdx = i;
                }
              }
            }
          }

          if (bestIdx !== -1) {
            currentLine.push(unassigned.splice(bestIdx, 1)[0]);
          } else {
            break;
          }
        }
        lines.push(currentLine);
      }

      return lines.flat();
    };

    const sortedWords = sortReadingOrder(wordsInRegion);

    const newChunk = {
      chunk_index: extractedChunks.length, // Appended to end
      words: sortedWords.map(w => ({ ...w, selected: false })), // Unselected by default
      full_text: sortedWords.map(w => w.text).join(' '),
      chunk_bbox: bbox
    };

    setExtractedChunks([...extractedChunks, newChunk]);
  };

  const handleParseWords = async () => {
    setIsLoading(true);
    try {
      const payloadChunks = extractedChunks.map(chunk => ({
        chunk_index: chunk.chunk_index,
        words: chunk.words.filter(w => w.selected && w.text.trim() !== ''),
        full_text: chunk.full_text,
        chunk_bbox: chunk.chunk_bbox
      })).filter(chunk => chunk.words.length > 0);

      const response = await fetch('http://localhost:8000/api/parse-words', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunks: payloadChunks })
      });
      const result = await response.json();
      if (result.status === 'success') {
        setParsedData(result.data);
        setStep('RESULT');
      } else {
        alert('Failed to parse words');
      }
    } catch (error) {
      console.error(error);
      alert('Error connecting to backend');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = () => {
    exportToExcel(parsedData, 'extracted_words.xlsx');
  };

  return (
    <div className="app-container">
      <header>
        <h1 className="title">SYConv | Intelligent English Parser</h1>
        {parsedData.length > 0 && (
          <button className="btn" onClick={handleExport}>
            <Download size={18} /> Export List
          </button>
        )}
      </header>

      <div className="split-pane">
        {/* LEFT PANEL */}
        <div className="panel">
          <div className="panel-header">Source Document</div>
          {step === 'UPLOAD' ? (
            <div className="upload-container" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%', justifyContent: 'center' }}>
              <label className="upload-zone">
                <Upload className="upload-icon" />
                <h3>Upload Highlighted Paper</h3>
                <p style={{ color: 'var(--text-muted)' }}>Drag & drop or click to select (PDF, JPG, PNG)</p>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          ) : (
            <div style={{ position: 'relative', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
                <DocumentViewer
                  previewUrl={previewUrl}
                  parsedData={parsedData}
                  extractedChunks={extractedChunks}
                  onToggleWord={handleToggleWord}
                  onCreateCustomChunk={handleCreateCustomChunk}
                  step={step}
                />
                {isLoading && (
                  <div className="overlay">
                    <div className="spinner"></div>
                    <p style={{ marginTop: '1rem' }}>{step === 'SELECT' ? 'Processing with AI...' : 'Analyzing Image...'}</p>
                  </div>
                )}
              </div>

              {/* Contextual Action Bar */}
              {(step === 'SELECT' || step === 'PRE_PARSE') && (
                <div style={{ padding: '1rem', background: 'var(--surface)', borderTop: '1px solid var(--border)', textAlign: 'center', zIndex: 10 }}>
                  <p style={{ fontSize: '14px', marginBottom: '0px' }}>Draw a box to create a paragraph, then click words to include them (blue).</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="panel">
          <div className="panel-header">
            {step === 'RESULT' ? 'Extracted Vocab Sheet' :
              step === 'PRE_PARSE' ? 'Word Correction (Pre-Parse)' : 'Context Review'}
          </div>
          {step === 'UPLOAD' ? (
            <div className="upload-zone" style={{ border: 'none' }}>
              <FileType className="upload-icon" style={{ opacity: 0.3 }} />
              <p style={{ color: 'var(--text-muted)' }}>Context & Results will appear here<br />after processing is complete.</p>
            </div>
          ) : step === 'SELECT' ? (
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <ChunkReviewer
                extractedChunks={extractedChunks}
                onTextChange={handleTextChange}
                onMergeChunkUp={handleMergeChunkUp}
                onDeleteChunk={handleDeleteChunk}
                onNextStep={() => setStep('PRE_PARSE')}
              />
            </div>
          ) : step === 'PRE_PARSE' ? (
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <PreParseSheet
                extractedChunks={extractedChunks}
                onWordChange={handleUpdateWordText}
                onAddWord={handleAddWord}
                onRemoveWord={handleRemoveWord}
                onMoveWordUp={handleMoveWordUp}
                onMoveWordDown={handleMoveWordDown}
                onParseWords={handleParseWords}
                isLoading={isLoading}
              />
            </div>
          ) : (
            <div style={{ flex: 1, overflow: 'auto' }}>
              <DataSheet rowData={parsedData} onDataChange={setParsedData} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
