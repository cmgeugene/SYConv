# Code Overview
- `parse_highlighted_words_with_llm()`: Takes raw OCR extracted texts that intersected with highlighted bounding boxes, and the full context text of the chunk, and queries the LLM (either OpenAI or Gemini based on environment variables) to return corrected lemmas, parts of speech, and meanings.
- `translate_and_verify_row_with_llm()`: Performs a manual 2-stage translation for a single row. Pass 1 extracts from context; Pass 2 verifies accuracy and preserves specialized context meanings.
### 2-Stage Translation & Verification
1. **Pass 1 (Extraction)**: Extracts lemma, POS, and split meanings (`context_meaning` vs `other_meanings`) from a given sentence.
    - **Conciseness**: Strictly limits meanings to words/short phrases (No sentences).
    - **POS Matching**: Definitions for `other_meanings` must strictly belong to the detected POS.
2. **Pass 2 (Verification)**: Reviewing and correcting any conversational noise or POS mismatches.
3. **Consolidation**: Merges and deduplicates meanings into a single comma-separated string: `{Contextual Meaning}, {Other Dictionary Meanings}`.

## TODOs in this Code
- [x] Implement field-based splitting for better precision.
- [x] Enforce strict concise rules to prevent descriptive sentences.
- [ ] Implement caching to reduce LLM costs.
- [ ] Add support for custom user dictionary overrides.
- [ ] Add retries for OpenAI/Gemini API calls.
- [x] Enhance the system prompt to explicitly format outputs matching the `ParsedWord` schema.
- [x] Integrate `google-generativeai` for Gemini support.
- [x] Allow multiple Parts of Speech (POS) if the word serves dual functions (e.g., noun/verb).
- [x] Enforce strict extraction of base forms (lemmas) for participles/plurals and allow both contextual and common dictionary meanings for richer studying.
