import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from google import genai
from google.genai import types
from models.schemas import ParsedWord

def parse_highlighted_words_with_llm(highlighted_texts_with_boxes: List[Dict[str, Any]], full_context_text: str) -> List[Dict[str, Any]]:
    """
    Sends the highlighted text along with the full chunk context to the LLM to extract POS and meanings.
    Supports both OpenAI and Gemini based on the LLM_PROVIDER environment variable.
    Returns a list of dicts that conform to the ParsedWord schema format.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    ollama_model = os.getenv("OLLAMA_MODEL", "translategemma:4b")
    
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
                    "think": False,
                    "num_ctx": 4096,
                    "num_predict": 2500
                }
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
        try:
            req_data = {
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1, "think": False}
            }
            
            req = urllib.request.Request(chat_endpoint, data=json_lib.dumps(req_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as response:
                result_json = json_lib.loads(response.read().decode('utf-8'))
                msg_obj = result_json.get("message", {})
                response_text = (msg_obj.get("content", "") or msg_obj.get("thinking", "")).strip()
                
                # Robust JSON extraction
                if "```json" in response_text:
                    response_text = response_text.split("```json")[-1].split("```")[0]
                elif "```" in response_text:
                    blocks = response_text.split("```")
                    response_text = blocks[-2] if len(blocks) >= 3 else blocks[0]
                
                # If no code blocks, try to find the outermost braces
                if not ("{" in response_text and "}" in response_text):
                    import re
                    match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(0)

                return json_lib.loads(response_text.strip())
        except Exception as inner_e:
            print(f"Internal call_ollama error: {inner_e}")
            # Return a minimal valid structure to keep the pipe flowing
            return {"lemma": word, "pos": "error", "context_meaning": "Error parsing JSON", "other_meanings": "", "is_idiom": False}

    try:
        # Pass 1: Extraction
        system_prompt = "You are an expert English teacher API. Output ONLY valid JSON. Do not include markdown formatting or thoughts."
        user_prompt_1 = f'''
        Full Context: "{context}"
        Target Word: "{word}"
        
        Extract:
        1. "lemma": Base dictionary form.
           - If POS is "형용사" and it is a participle, use the adjective form (e.g., "impaired", "exciting").
           - Otherwise, use the base present form (e.g., "realize", not "realized").
        2. "pos": Part of Speech in KOREAN. 
           - Single: full name (e.g., "명사", "동사", "형용사").
           - Multiple: shortened names with slashes (e.g., "동 / 명"). Sort alphabetically (noun, verb, adj, adv).
           - CRITICAL: Participles ("-ed", "-ing") modifying nouns are usually "형용사".
        3. "context_meaning": The CONCISE Korean meaning for the current sentence.
           - CRITICAL: NO SENTENCES. Use a word matching the POS (e.g., if POS is "형용사", use "손상된", not "손상").
           - If multiple POS, separate with slashes (e.g., "달리다 / 매달림").
        4. "other_meanings": Other meanings strictly for the ABOVE POS.
           - List as a comma-separated string.
           - CRITICAL: DO NOT include noun meanings (e.g., "손상") if the POS is "형용사". Use "손상된", "장애가 있는".
           - CRITICAL: NO LABELS like "(명사)" or "(동사)".
           - If multiple POS, separate blocks with slashes.
        5. "is_idiom": boolean.
        
        Format:
        {{
            "lemma": "word",
            "pos": "동사",
            "context_meaning": "문맥뜻",
            "other_meanings": "일반뜻1, 일반뜻2",
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
        A previous model translated the word "{word}" from the sentence "{context}" as follows:
        {json_lib.dumps(pass1_result, ensure_ascii=False)}
        
        CRITICAL VERIFICATION:
        1. CONCISENESS: Ensure "context_meaning" is a word/short phrase, NOT a description or sentence.
        2. POS MATCHING: "other_meanings" MUST ONLY contain definitions for the specified POS in "pos".
           - Example: If POS is "동사", do NOT include noun definitions like "표준".
        3. NO LABELS: Remove ANY extra markers like "(명사)", "(동사)", "본래 의미:", etc.
        4. MULTI-POS: Both meaning fields must match the POS order.
        
        Output ONLY the final, corrected JSON.
        '''
        
        messages.append({"role": "assistant", "content": json_lib.dumps(pass1_result, ensure_ascii=False)})
        messages.append({"role": "user", "content": user_prompt_2})
        
        pass2_result = call_ollama(messages)
        print("Pass 2 Result:", pass2_result)
        
        # Combine contextual and other meanings while deduplicating
        if isinstance(pass2_result, dict) and "context_meaning" in pass2_result:
            import re
            ctx_orig = pass2_result.get("context_meaning") or ""
            oth_orig = pass2_result.get("other_meanings") or ""
            
            def combine_and_dedup(ctx_block, oth_block):
                # Split by comma or semicolon
                all_words = re.split(r'[,;]', f"{ctx_block},{oth_block}")
                seen = set()
                unique = []
                for w in [w.strip() for w in all_words if w.strip()]:
                    if w not in seen:
                        unique.append(w)
                        seen.add(w)
                return ", ".join(unique)

            if "/" in ctx_orig or "/" in oth_orig:
                # Handle multi-POS blocks
                ctx_parts = [s.strip() for s in ctx_orig.split("/")]
                oth_parts = [s.strip() for s in oth_orig.split("/")]
                
                # Match them up by index, fill with empty if lengths differ
                max_len = max(len(ctx_parts), len(oth_parts))
                final_parts = []
                for i in range(max_len):
                    c = ctx_parts[i] if i < len(ctx_parts) else ""
                    o = oth_parts[i] if i < len(oth_parts) else ""
                    final_parts.append(combine_and_dedup(c, o))
                
                pass2_result["meaning"] = " / ".join(final_parts)
            else:
                # Handle single POS block
                pass2_result["meaning"] = combine_and_dedup(ctx_orig, oth_orig)
            
            # Remove internal fields before returning to frontend
            pass2_result.pop("context_meaning", None)
            pass2_result.pop("other_meanings", None)

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
