# Code Overview
- `parse_highlighted_words_with_llm()`: Takes raw OCR extracted texts that intersected with highlighted bounding boxes, and the full context text of the chunk, and queries the LLM (either OpenAI or Gemini based on environment variables) to return corrected lemmas, parts of speech, and meanings.
- **Relationships & Flow**: This is the final step in the backend data extraction pipeline before formatting and returning the response to the frontend.

# TODOs in this Code
- [x] Implement robust error handling if the API key is missing or invalid.
- [ ] Add retries for OpenAI/Gemini API calls.
- [x] Enhance the system prompt to explicitly format outputs matching the `ParsedWord` schema.
- [x] Integrate `google-generativeai` for Gemini support.
- [x] Allow multiple Parts of Speech (POS) if the word serves dual functions (e.g., noun/verb).
- [x] Enforce strict extraction of base forms (lemmas) for participles/plurals and allow both contextual and common dictionary meanings for richer studying.
