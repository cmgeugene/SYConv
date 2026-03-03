# Code Overview
- `extract_highlights_endpoint()`: (Step 1) Receives an image or PDF, extracts OCR, runs a dynamic multi-color HSV highlight filter, and intersects the two to find potential highlighted words. Returns a JSON payload containing chunks of these words (without calling the LLM).
- `parse_words_endpoint()`: (Step 2) Receives a JSON payload of user-verified highlighted chunks, applies the vertical chunk grouping logic, and triggers the parallel `asyncio` routines to send chunks to the LLM. Combining results back to the frontend.
- **Relationships & Flow**: The frontend calls `/api/extract-highlights`, allows the user to visually toggle boxes on the canvas, and then sends the refined list to `/api/parse-words`.ing tools from `core` and resolving requests from the frontend.

# TODOs in this Code
- [x] Implement the `POST /api/process-document` endpoint.
- [x] Call image processing functions and return parsed response.
- [x] Refactor endpoint to chunk queries per question block and run LLM calls in parallel.
