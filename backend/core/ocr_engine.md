# Code Overview
- `extract_text_and_boxes()`: Initializes `EasyOCR` and extracts raw text along with its bounding boxes from the document. It now takes a pre-loaded OpenCV `np.ndarray` and implements a 0.99x scaling fallback mechanism to prevent `!ssize.empty()` assertion crashes when EasyOCR's internal `cv2.resize` fails on edge-case crops.
- `_calculate_overlap_area()`: Helper function returning intersection rectangle area between two coordinates.
- `intersect_highlight_with_ocr()`: Computes overlap ratio. Reduced threshold to 15% overlap to accommodate thin highlighter strokes over tall text characters. Returns dictionaries of confirmed highlighted words.
- **Relationships & Flow**: This sits right after the `image_processing` module in the pipeline. Once the image is chunked and highlights are located, OCR extracts all text, and the intersection logic filters out non-highlighted text.

# TODOs in this Code
- [x] Initialize the `EasyOCR` Reader (consider loading onto GPU if available).
- [x] Implement the `extract_text_and_boxes` function to return standardized dicts and handle internal cv2 crash fallbacks.
- [x] Implement the Intersection over Union (IoU) or basic overlap logic in `intersect_highlight_with_ocr`.
