import shutil
import os
import cv2
import asyncio
import base64
import multiprocessing
import concurrent.futures
from typing import Tuple, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from core.image_processing import detect_highlighted_regions
from core.ocr_engine import extract_text_and_boxes, intersect_highlight_with_ocr
from core.llm_parser import parse_highlighted_words_with_llm
from models.schemas import ParseWordsRequest, TranslateRowRequest

router = APIRouter()

def sort_reading_order(boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not boxes: return []
    unassigned = sorted(boxes, key=lambda b: b["bbox"][1])
    lines = []
    
    while unassigned:
        seed_idx = 0
        while True:
            seed_box = unassigned[seed_idx]
            s_ytop, s_ybot = seed_box["bbox"][1], seed_box["bbox"][3]
            s_height = s_ybot - s_ytop
            found_left = False
            
            for i, cand in enumerate(unassigned):
                if i == seed_idx: continue
                c_xleft, c_ytop, _, c_ybot = cand["bbox"]
                c_height = c_ybot - c_ytop
                
                overlap_top = max(s_ytop, c_ytop)
                overlap_bot = min(s_ybot, c_ybot)
                overlap_h = max(0, overlap_bot - overlap_top)
                
                if overlap_h > 0.5 * min(s_height, c_height):
                    if c_xleft < seed_box["bbox"][0]:
                        seed_idx = i
                        found_left = True
                        break
            if not found_left:
                break
                
        current_line = [unassigned.pop(seed_idx)]
        
        while True:
            last_box = current_line[-1]
            l_xleft, l_ytop, l_xright, l_ybot = last_box["bbox"]
            l_height = l_ybot - l_ytop
            
            best_idx = -1
            min_dist = float('inf')
            
            for i, cand in enumerate(unassigned):
                c_xleft, c_ytop, _, c_ybot = cand["bbox"]
                c_height = c_ybot - c_ytop
                
                overlap_top = max(l_ytop, c_ytop)
                overlap_bot = min(l_ybot, c_ybot)
                overlap_h = max(0, overlap_bot - overlap_top)
                
                if overlap_h > 0.5 * min(l_height, c_height):
                    if c_xleft > l_xleft:
                        dist = c_xleft - l_xright
                        if dist < min_dist:
                            min_dist = dist
                            best_idx = i
                            
            if best_idx != -1:
                current_line.append(unassigned.pop(best_idx))
            else:
                break
                
        lines.append(current_line)
        
    sorted_boxes = []
    for line in lines:
        sorted_boxes.extend(line)
    return sorted_boxes

def _process_single_page(args: Tuple[str, int]) -> Dict[str, Any]:
    img_path, page_idx = args
    import cv2
    import base64
    from core.ocr_engine import extract_text_and_boxes
    
    try:
        img = cv2.imread(img_path)
        if img is None:
            return {"error": f"Failed to decode image: {img_path}"}
            
        ocr_results = extract_text_and_boxes(img)
        all_sorted_ocr = sort_reading_order(ocr_results)
        
        _, buffer = cv2.imencode('.jpg', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "page_index": page_idx,
            "image_b64": f"data:image/jpeg;base64,{img_b64}",
            "chunks": [],
            "all_ocr_results": [{"text": o["text"], "bbox": o["bbox"]} for o in all_sorted_ocr]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@router.post("/api/extract-highlights")
async def extract_highlights_endpoint(
    file: UploadFile = File(...),
    target_colors: str = Form(None)
):
    """
    Step 1: Receives an image or multi-page PDF, parallel extracts OCR using ProcessPoolExecutor.
    Returns the array of pages containing chunked words.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    allowed_extensions = [".png", ".jpg", ".jpeg", ".pdf"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    import uuid
    import traceback
    
    temp_filename = f"temp_{uuid.uuid4().hex}"
    temp_path = temp_filename + ext
    temp_paths = []
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Convert PDF to multiple images or keep single image
        if ext == ".pdf":
            import fitz
            doc = fitz.open(temp_path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=200, alpha=False)
                img_path = f"{temp_filename}_page{i}.jpg"
                pix.save(img_path)
                temp_paths.append((img_path, i))
            doc.close()
            os.remove(temp_path)
        else:
            temp_paths.append((temp_path, 0))
        
        # CPU Optimization: Parallelize OCR extraction to avoid connection timeouts on long PDFs
        max_workers = min(3, multiprocessing.cpu_count(), len(temp_paths))
        if max_workers < 1: max_workers = 1
        
        pages_data = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_process_single_page, temp_paths))
            
        for res in results:
            if "error" in res:
                raise ValueError(res["error"])
            pages_data.append(res)
            
        pages_data.sort(key=lambda x: x["page_index"])
        
        return {
            "status": "success",
            "filename": file.filename,
            "pages": pages_data
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        for p, _ in temp_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

@router.post("/api/parse-words")
async def parse_words_endpoint(request: ParseWordsRequest):
    """
    Step 2: Receives the user-verified highlighted chunks and parses them with LLM.
    """
    import traceback
    try:
        async def process_chunk(chunk_data):
            if not chunk_data.words:
                return []
            
            # Using the pre-calculated full chunk context instead of just building from highlight words
            full_text = chunk_data.full_text
            chunk_dicts = [{"text": w.text, "bbox": w.bbox} for w in chunk_data.words]
            return await asyncio.to_thread(parse_highlighted_words_with_llm, chunk_dicts, full_text)
            
        final_data = []
        for chunk in request.chunks:
            # Awaiting each chunk sequentially to prevent LLM rate limits/local overload
            res = await process_chunk(chunk)
            final_data.extend(res)
            
        return {
            "status": "success",
            "filename": "parsed_result",
            "data": final_data
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/models")
async def get_models_endpoint():
    """
    Fetches available models from the local Ollama instance.
    """
    import urllib.request
    import json as json_lib
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    tags_url = ollama_endpoint.replace("/api/generate", "/api/tags")
    
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json_lib.loads(response.read().decode('utf-8'))
            # Deduplicate and sort names
            models = sorted(list(set([m["name"] for m in data.get("models", [])])))
            return {"status": "success", "models": models}
    except Exception as e:
        # Fallback to empty list or provide env default if Ollama is unreachable
        print(f"Failed to fetch Ollama models: {e}")
        return {"status": "error", "message": str(e), "models": []}

@router.post("/api/translate-row")
async def translate_row_endpoint(request: TranslateRowRequest):
    """
    Endpoint for the manual Data Sheet flow. Performs a 2-stage (Translation + Verification) LLM pass.
    """
    import traceback
    try:
        from core.llm_parser import translate_and_verify_row_with_llm
        result = await asyncio.to_thread(translate_and_verify_row_with_llm, request.word, request.context, request.model)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
