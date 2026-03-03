import easyocr
import cv2
import numpy as np
from typing import List, Dict, Any

# Lazy initialization of the OCR Reader to avoid blocking API startup
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        # Assuming English texts. Add 'ko' if Korean extraction is also needed on the paper.
        _reader = easyocr.Reader(['en'], gpu=False) 
    return _reader

def extract_text_and_boxes(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Extracts text and bounding boxes from an image using EasyOCR.
    """
    reader = get_reader()
    try:
        # Convert to RGB (EasyOCR underlying cv2.imread loads normally in BGR, but passing a numpy array should be RGB ideally, or it handles BGR internally)
        result = reader.readtext(image)
    except Exception as e:
        print(f"EasyOCR error on image: {e}. Attempting fallback resize.")
        try:
            height, width = image.shape[:2]
            scale = 0.99
            resized = cv2.resize(image, (int(width * scale), int(height * scale)))
            fallback_result = reader.readtext(resized)
            
            # scale the bbox back
            result = []
            for (bbox, text, prob) in fallback_result:
                scaled_bbox = [[int(x / scale), int(y / scale)] for x, y in bbox]
                result.append((scaled_bbox, text, prob))
        except Exception as fallback_e:
            print(f"EasyOCR fallback failed: {fallback_e}")
            return []
    
    extracted = []
    for (bbox, text, prob) in result:
        # EasyOCR returns bbox as [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        clean_bbox = [int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords))]
        
        extracted.append({
            "text": text,
            "bbox": clean_bbox,
            "confidence": float(prob)
        })
    return extracted

def _calculate_overlap_area(boxA: List[int], boxB: List[int]) -> int:
    """Helper to calculate intersection area of two bounding boxes [x1,y1,x2,y2]"""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    return interArea

def intersect_highlight_with_ocr(ocr_results: List[Dict[str, Any]], highlight_boxes: List[List[int]]) -> List[Dict[str, Any]]:
    """
    Filters OCR results, returning only those words whose bounding boxes overlap with highlighted regions.
    """
    highlighted_words = []
    
    for ocr in ocr_results:
        ocr_box = ocr["bbox"]
        ocr_area = (ocr_box[2] - ocr_box[0] + 1) * (ocr_box[3] - ocr_box[1] + 1)
        
        for h_box in highlight_boxes:
            overlap = _calculate_overlap_area(ocr_box, h_box)
            # If at least 15% of the OCR text box is within the highlighted box
            # Reduced from 50% because highlighter strokes are often thinner than the text's full vertical height
            if ocr_area > 0 and overlap / ocr_area > 0.15:
                highlighted_words.append(ocr)
                break # Move to next OCR word once it's confirmed highlighted
                
    return highlighted_words
