# Code Overview
- `parse_highlighted_words_with_llm()`: Takes raw OCR extracted texts that intersected with highlighted bounding boxes, and the full context text of the chunk, and queries the LLM (either OpenAI or Gemini based on environment variables) to return corrected lemmas, parts of speech, and meanings.
- `translate_and_verify_row_with_llm()`: Performs a manual 2-stage translation for a single row. Pass 1 extracts from context; Pass 2 verifies accuracy and preserves specialized context meanings.
- **Relationships & Flow**: The frontend triggers `translate_and_verify_row_with_llm` for on-demand or auto-translation. It uses a 2-stage prompt architecture to ensure contextual precision (e.g., financial terms) while providing secondary dictionary meanings. Format: `{Context-Specific Meaning}, {Other Dictionary Meanings}`.

# TODOs in this Code
- [x] Implement robust error handling if the API key is missing or invalid.
- [ ] Add retries for OpenAI/Gemini API calls.
- [x] Enhance the system prompt to explicitly format outputs matching the `ParsedWord` schema.
- [x] Integrate `google-generativeai` for Gemini support.
- [x] Allow multiple Parts of Speech (POS) if the word serves dual functions (e.g., noun/verb).
- [x] Enforce strict extraction of base forms (lemmas) for participles/plurals and allow both contextual and common dictionary meanings for richer studying.
