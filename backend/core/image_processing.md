# Code Overview
- `chunk_document()`: Analyzes the 2-column layout and separates the document into logical chunks. Currently implemented as a simple middle-split PoC.
- `get_hsv_range_from_hex()`: Converts a frontend HEX color code into OpenCV's HSV lower and upper bound arrays by calculating tolerances for shadows and highlights.
- `detect_highlighted_regions()`: Analyzes the image using OpenCV to find HSV color ranges corresponding to highlights, returning bounding boxes of these regions. Now directly receives `np.ndarray` and utilizes a Universal Hue-Agnostic method (High Saturation `>25`, High Brightness `>110`) after a bilateral noise filter to catch any fluorescent color strokes. through the extracted HEX bounds and stacks `cv2.bitwise_or` masks to simultaneously detect multiple custom highlight colors.
- **Relationships & Flow**: These functions are intended to be called by the main API route (`api/routes.py`) to preprocess the uploaded document before sending data to OCR and LLM.

# TODOs in this Code
- [ ] Enhance `chunk_document` logic using refined contour detection to handle varied layouts.
- [x] Fine-tune HSV thresholds in `detect_highlighted_regions` for different lighting conditions.
- [ ] Add robustness to detect multiple highlight colors (e.g., yellow, green, pink).
