import shutil
import os
import cv2
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from core.image_processing import detect_highlighted_regions
from core.ocr_engine import extract_text_and_boxes, intersect_highlight_with_ocr
from core.llm_parser import parse_highlighted_words_with_llm
from models.schemas import ParseWordsRequest

router = APIRouter()

@router.post("/api/extract-highlights")
async def extract_highlights_endpoint(
    file: UploadFile = File(...),
    target_colors: str = Form(None)
):
    """
    Step 1: Receives an image, extracts OCR, and filters by target color highlights.
    Returns the chunked words that the system believes are highlighted.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validation
    allowed_extensions = [".png", ".jpg", ".jpeg", ".pdf"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    import uuid
    import traceback
    
    # Temporary saving mechanism prioritizing ASCII path (PoC)
    temp_filename = f"temp_{uuid.uuid4().hex}"
    temp_path = temp_filename + ext
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Convert PDF to image
        if ext == ".pdf":
            import fitz
            doc = fitz.open(temp_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200, alpha=False)
            img_path = f"{temp_filename}.jpg"
            pix.save(img_path)
            os.remove(temp_path)
            temp_path = img_path
        
        img = cv2.imread(temp_path)
        if img is None:
            raise ValueError("Failed to decode image from path.")
            
        # 1. Automatic highlight detection is disabled for the fully manual pipeline
        # h_boxes = detect_highlighted_regions(img, target_hex=target_colors)
        
        # 2. Extract OCR
        ocr_results = extract_text_and_boxes(img)
        
        # 3. Sort OCR reading order supporting skewed/slanted text lines
        def sort_reading_order(boxes):
            if not boxes: return []
            unassigned = sorted(boxes, key=lambda b: b["bbox"][1])
            lines = []
            
            while unassigned:
                seed_idx = 0
                # Find true leftmost start by tracing backwards overlapping boxes
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
                
                # Trace rightward picking the closest overlapping box
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

        all_sorted_ocr = sort_reading_order(ocr_results)
        
        return {
            "status": "success",
            "filename": file.filename,
            "chunks": [], # No auto chunks anymore
            "all_ocr_results": [{"text": o["text"], "bbox": o["bbox"]} for o in all_sorted_ocr]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

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
