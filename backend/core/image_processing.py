import cv2
import numpy as np
from typing import List, Dict, Any

def chunk_document(image_path: str) -> List[Dict[str, Any]]:
    """
    Reads an image and attempts to split it into 2 columns and chunk into questions.
    Returns a list of dicts with chunk coordinates.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path} for chunking")
    
    # Placeholder: Simple column split based on width for PoC
    height, width = image.shape[:2]
    mid = width // 2
    
    chunks = [
        {"id": "col1", "bbox": [0, 0, mid, height]},
        {"id": "col2", "bbox": [mid, 0, width, height]}
    ]
    return chunks

def detect_highlighted_regions(image: np.ndarray, target_hex: str = None) -> List[List[int]]:
    """
    Detects highlighted regions and returns a list of bounding boxes [x1, y1, x2, y2].
    Uses a Universal Hue-Agnostic approach: filters by High Saturation & High Brightness
    to catch all fluorescent highlight colors (yellow, pink, green, blue, etc).
    """
    if image is None:
        return []
        
    # Pre-processing: Apply Bilateral Filter 
    # This smooths out background paper noise and color gradients while keeping text edges sharp.
    filtered_img = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
    
    hsv = cv2.cvtColor(filtered_img, cv2.COLOR_BGR2HSV)
    
    # Universal Highlighter HSV range:
    # H: 0-179 (Ignore Hue, catch all colors)
    # S: 25-255 (Lowered to catch heavily faded ink)
    # V: 110-255 (Lowered to catch highlighters in dark shadows of scans)
    lower_bound = np.array([0, 25, 110], dtype=np.uint8)
    upper_bound = np.array([179, 255, 255], dtype=np.uint8)
    
    mask = cv2.inRange(hsv, lower_bound, upper_bound)
    
    # Morphological operations to group broken highlighted texts
    kernel = np.ones((5, 25), np.uint8) # significantly wider kernel to connect grouped words securely
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bounding_boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Filter out noise (too small)
        if w > 20 and h > 10:
            # Add padding to the bounding box to catch OCR text completely
            pad = 5
            bounding_boxes.append([x - pad, y - pad, x + w + pad, y + h + pad])
            
    return bounding_boxes
