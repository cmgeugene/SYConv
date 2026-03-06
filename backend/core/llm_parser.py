import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from google import genai
from google.genai import types
from models.schemas import ParsedWord

def parse_highlighted_words_with_llm(highlighted_texts_with_boxes: List[Dict[str, Any]], full_context_text: str, model: str = None) -> List[Dict[str, Any]]:
    """
    Sends the highlighted text along with the full chunk context to the LLM to extract POS and meanings.
    Supports both OpenAI and Gemini based on the LLM_PROVIDER environment variable.
    Returns a list of dicts that conform to the ParsedWord schema format.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    ollama_model = model if model else os.getenv("OLLAMA_MODEL", "translategemma:4b")
    
    # Just isolating the texts for the prompt
    raw_texts = [item["text"] for item in highlighted_texts_with_boxes]
    
    prompt = f"""
    You are an expert English teacher API. Your ONLY job is to extract vocabulary data from the provided text and output it as a strict JSON array.
    DO NOT provide any explanations, greetings, or reasoning. Output ONLY valid JSON starting with `{{` and ending with `}}`.
    
    Full Context Text:
    ---
    {full_context_text}
    ---
    
    Target Words (Raw OCR extraction):
    {raw_texts}
    
    Instructions for each target word:
    1. "word": Extract the base form (lemma) used in the context. Convert plurals to singular, and past/participle to present base verb (e.g., "realized" -> "realize"). If it's an idiom (e.g., "taking off"), extract the base idiom ("take off").
    2. "pos": Determine the Part of Speech in the context. If it acts as multiple, separate them by a slash and sort using this EXACT priority order: noun, verb, adj, adv, prep, conj (e.g., "noun / verb", NEVER "verb / noun").
    3. "meaning": Provide the primary Korean meaning appropriate for the context first. Then, optionally add other common dictionary definitions. DO NOT write "(문맥)". Align meanings if there are multiple POS tags (e.g., pos: "noun / verb", meaning: "예시 / 예시를 들다").
       - SEMANTIC BOUNDARY: Even if the target word is part of a larger phrase (e.g., "currency" in "currency exchange rates"), provide the meaning of the SPECIFIC target word (e.g., "화폐", "통화"), NOT the entire phrase (e.g., "환율").
    4. "is_idiom": true or false.
    
    MUST RETURN IN THIS EXACT JSON FORMAT:
    {{
      "words": [
        {{
          "word": "example",
          "pos": "noun / verb",
          "meaning": "예시 / 예시를 들다",
          "is_idiom": false
        }}
      ]
    }}
    """
    
    if provider == "ollama":
        import urllib.request
        import json as json_lib
            
        try:
            # Change to /api/chat instead of /api/generate for better Qwen/Instruct model compatibility
            chat_endpoint = ollama_endpoint.replace("/api/generate", "/api/chat")
            
            req_data = {
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": "You are a data extraction assistant. Output ONLY the raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096,
                    "num_predict": 2500
                },
                "think": "medium" if "gpt-oss" in ollama_model else True
            }
            
            req = urllib.request.Request(chat_endpoint, data=json_lib.dumps(req_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as response:
                result_bytes = response.read()
                result_str = result_bytes.decode('utf-8')
                
                print(f"DEBUG - HTTP Status Code: {response.getcode()}")
                print(f"DEBUG - Raw HTTP Response String: \n{repr(result_str)}\n")
                
                result_json = json_lib.loads(result_str)
                
                # chat endpoint returns in .message.content, but reasoning models might use .message.thinking if cut off
                msg_obj = result_json.get("message", {})
                raw_content = msg_obj.get("content", "")
                thinking_content = msg_obj.get("thinking", "")
                
                response_text = raw_content if raw_content.strip() else thinking_content
                
                # We need to aggressively extract just the JSON part, especially if it's buried in thinking logs
                if "```json" in response_text:
                    response_text = response_text.split("```json")[-1].split("```")[0]
                elif "```" in response_text:
                    blocks = response_text.split("```")
                    if len(blocks) >= 3:
                        response_text = blocks[-2]
                    else:
                        response_text = response_text.replace("```", "")
                
                # Remove any leftover whitespace
                response_text = response_text.strip()
                print("RAW OLLAMA OUTPUT EXTRACTED:\n", repr(response_text))
                
                parsed_res = json_lib.loads(response_text)
                parsed_words = parsed_res.get("words", [])
                
                # If still empty for some reason, maybe the model just returned an array directly instead of {"words": []}
                if not parsed_words and isinstance(parsed_res, list):
                    parsed_words = parsed_res
                    
                return _merge_boxes(parsed_words, highlighted_texts_with_boxes)
        except Exception as e:
            print(f"Ollama parsing failed: {e}")
            return _error_fallback(highlighted_texts_with_boxes, f"Ollama Error: {str(e)}")
            
    elif provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("WARNING: GEMINI_API_KEY is not set.")
            return _dummy_fallback(highlighted_texts_with_boxes, "(Gemini API Key Required)")
            
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            result = json.loads(response.text)
            parsed_words = result.get("words", [])
            return _merge_boxes(parsed_words, highlighted_texts_with_boxes)
        except Exception as e:
            print(f"Gemini parsing failed: {e}")
            return _error_fallback(highlighted_texts_with_boxes, str(e))
            
    else:
        # Default to OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: OPENAI_API_KEY is not set.")
            return _dummy_fallback(highlighted_texts_with_boxes, "(OpenAI API Key Required)")
            
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output strict JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.1
            )
            result = json.loads(response.choices[0].message.content)
            parsed_words = result.get("words", [])
            return _merge_boxes(parsed_words, highlighted_texts_with_boxes)
        except Exception as e:
            print(f"OpenAI parsing failed: {e}")
            return _error_fallback(highlighted_texts_with_boxes, str(e))


def _dummy_fallback(boxes, reason):
    return [
        {
            "word": item["text"].lower(),
            "pos": "unknown",
            "meaning": reason,
            "is_idiom": False,
            "bbox": item["bbox"]
        } for item in boxes
    ]

def _error_fallback(boxes, err_msg):
    return [
        {
            "word": item["text"].lower(),
            "pos": "error",
            "meaning": f"Error: {err_msg}",
            "is_idiom": False,
            "bbox": item["bbox"]
        } for item in boxes
    ]

def _merge_boxes(parsed_words, highlighted_texts_with_boxes):
    final_list = []
    for i, parsed in enumerate(parsed_words):
        if i < len(highlighted_texts_with_boxes):
            parsed["bbox"] = highlighted_texts_with_boxes[i]["bbox"]
            final_list.append(parsed)
    return final_list

def translate_and_verify_row_with_llm(word: str, context: str, model: str = None) -> Dict[str, Any]:
    """
    Performs a 2-stage LLM translation for a single row from the Data Sheet.
    Pass 1: Initial extraction and translation from context.
    Pass 2: LLM Verification of the Pass 1 result.
    """
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    # Use provided model or default from env
    ollama_model = model if model else os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    
    import urllib.request
    import json as json_lib
    
    chat_endpoint = ollama_endpoint.replace("/api/generate", "/api/chat")
    
    def call_ollama(messages):
        response_text = ""
        try:
            req_data = {
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.0
                },
                "think": "medium" if "gpt-oss" in ollama_model else True
            }
            
            req = urllib.request.Request(chat_endpoint, data=json_lib.dumps(req_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as response:
                result_json = json_lib.loads(response.read().decode('utf-8'))
                msg_obj = result_json.get("message", {})
                response_text = (msg_obj.get("content", "") or msg_obj.get("thinking", "")).strip()
                
                # Helper for iterative JSON parsing to handle trailing garbage or premature closure
                def try_parse_prefix(text):
                    if not ('{' in text and '}' in text): return None
                    
                    # Try to find the last '}' and try parsing until there
                    # We start from the end to find the LARGEST valid JSON object
                    last_brace_idx = text.rfind('}')
                    while last_brace_idx != -1:
                        try:
                            # Extract everything up to this brace
                            candidate = text[:last_brace_idx+1].strip()
                            # If it doesn't start with {, it might have leading garbage
                            if not candidate.startswith('{'):
                                first_brace = candidate.find('{')
                                if first_brace != -1:
                                    candidate = candidate[first_brace:]
                            
                            return json_lib.loads(candidate)
                        except:
                            # Move to the previous brace and try again
                            last_brace_idx = text.rfind('}', 0, last_brace_idx)
                    return None

                # 1. Try code block extraction
                temp_text = response_text
                if "```json" in temp_text:
                    temp_text = temp_text.split("```json")[-1].split("```")[0].strip()
                elif "```" in temp_text:
                    blocks = temp_text.split("```")
                    temp_text = blocks[-2] if len(blocks) >= 3 else blocks[0]
                
                res = try_parse_prefix(temp_text.strip())
                if res: return res

                # 2. Try whole response
                res = try_parse_prefix(response_text)
                if res: return res

                raise ValueError("All JSON extraction methods failed")

        except Exception as inner_e:
            print(f"Internal call_ollama error: {inner_e}")
            if response_text:
                print(f"Raw response preview: {response_text[:200]}...")
            return {"lemma": word, "pos": "error", "full_definitions": [], "is_idiom": False}

    try:
        # Pass 1: Extraction
        system_prompt = "You are an expert English teacher API. Output ONLY valid JSON. Keep lists intact."
        user_prompt_1 = f'''
        Full Context: "{context}"
        Target Word/Phrase: "{word}"
        
        Extract:
        1. "lemma": The normalized dictionary form.
           - STEP 1 (Idiom Check): If the target word/phrase is part of a larger multi-word idiom or phrasal verb, use the FULL base phrase (e.g., "fall prey to").
           - STEP 2 (Normalization): If not an idiom, STERNLY remove ANY inflections (-s, -es, -ed, -ing). 
             - MUST be base present form (e.g., "relates" -> "relate", "falling" -> "fall").
             - EXCEPTION: If POS is "형용사" and it's an adjective-participle, use the adjective form (e.g., "impaired").
        2. "pos": Part of Speech in KOREAN. 
           - Single: full name (e.g., "명사", "동사", "형용사").
           - Multiple: shortened names with slashes (e.g., "동 / 명").
           - Idioms: Treat the entire phrase as a single POS based on function (e.g., "동사구").
        3. "full_definitions": A list of objects for EACH POS identified in "pos".
           - Format: {{"pos": "품사명", "context_meaning": "문맥뜻", "other_meanings": ["일반뜻1", "일반뜻2"]}}
           - CRITICAL: "context_meaning" and "other_meanings" MUST be CONCISE KOREAN SYNONYMS (대역어).
           - CRITICAL: "context_meaning" should be the most natural phrasing (Collocation).
           - SEMANTIC BOUNDARY: Even if the target word is part of a larger phrase (e.g., "currency" in "currency exchange rates"), provide the meaning of the SPECIFIC target word itself (e.g., "화폐", "통화"), NOT the entire phrase (e.g., "환율").
           - CRITICAL: NO SENTENCES. NO DESCRIPTIONS. NO EXPLANATIONS.
           - CRITICAL: Use correct KOREAN suffixes (~한/인 for Adj, ~하다 for Verb).
        4. "is_idiom": boolean.
           - Set to true ONLY for multi-word expressions (idioms, phrasal verbs).
        
        Format Example:
        {{
            "lemma": "relate",
            "pos": "동사",
            "full_definitions": [
                {{
                    "pos": "동사",
                    "context_meaning": "말하다",
                    "other_meanings": ["관련시키다"]
                }}
            ],
            "is_idiom": false
        }}
        '''
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_1}
        ]
        
        pass1_result = call_ollama(messages)
        print("Pass 1 Result:", pass1_result)
        
        # Pass 2: Verification
        user_prompt_2 = f'''
        A previous model translated the word/phrase "{word}" from the sentence "{context}" as follows:
        {json_lib.dumps(pass1_result, ensure_ascii=False)}
        
        CRITICAL VERIFICATION & REFINEMENT:
        1. LEMMA NORMALIZATION: Ensure "lemma" is the BASE form.
           - REMOVE plural or 3rd-person 's' (e.g., "relates" MUST be corrected to "relate").
           - Even for IDIOMS, the main verb must be in its base present form (e.g., "putting it off" -> "put off", "taken back" -> "take back").
        2. KOREAN NATURALNESS: Refine "context_meaning" for the best collocation.
           - For alternative synonyms, using a slash (e.g., "빠지다 / 굴복하다") is RECOMMENDED.
        3. POS SUFFIX CONSISTENCY: MUST match POS suffix rules. NEVER use nominalized endings (~함, ~기) for verbs.
        4. NO SENTENCES/DESCRIPTIONS: Use only short words/synonyms.
        5. STRICT SEMANTIC FILTERING: Ensure the meaning reflects ONLY the target word, not its neighbors. Correct any cases where the meaning of a neighboring word has leaked into the target word (e.g., "currency" in "currency exchange rates" should be "화폐/통화", NOT "환율").
        6. STRICT FILTERING: Remove any meanings that don't match the POS.
        
        Output ONLY the final, corrected JSON.
        '''
        
        messages.append({"role": "assistant", "content": json_lib.dumps(pass1_result, ensure_ascii=False)})
        messages.append({"role": "user", "content": user_prompt_2})
        
        pass2_result = call_ollama(messages)
        print("Pass 2 Result:", pass2_result)
        
        # Combine contextual and other meanings while deduplicating
        if isinstance(pass2_result, dict) and "full_definitions" in pass2_result:
            import re
            defs = pass2_result.get("full_definitions") or []
            
            def combine_and_dedup(ctx_str, other_list):
                # Ensure other_list is actually a list
                if not isinstance(other_list, list):
                    other_list = [str(other_list)]
                
                all_words = [ctx_str] + other_list
                seen = set()
                unique = []
                for w in [str(w).strip() for w in all_words if w and str(w).strip()]:
                    if w not in seen:
                        unique.append(w)
                        seen.add(w)
                return ", ".join(unique)

            # Assemble POS blocks
            pos_blocks = []
            for d in defs:
                ctx = d.get("context_meaning", "").strip()
                oth = d.get("other_meanings", [])
                if ctx or oth:
                    pos_blocks.append(combine_and_dedup(ctx, oth))
            
            # Final join with slashes
            pass2_result["meaning"] = " / ".join(pos_blocks)
            
            # Clean up internal fields
            pass2_result.pop("full_definitions", None)

        return pass2_result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Translation failed: {e}")
        return {
            "lemma": word,
            "pos": "error",
            "meaning": f"Error: {str(e)}",
            "is_idiom": False
        }
