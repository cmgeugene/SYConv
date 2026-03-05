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
            response_text = msg_obj.get("content", "") or msg_obj.get("thinking", "")
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[-1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[-2] if len(response_text.split("```")) >= 3 else response_text.replace("```", "")
            
            return json_lib.loads(response_text.strip())

    try:
        # Pass 1: Extraction
        system_prompt = "You are an expert English teacher API. Output ONLY valid JSON containing lemma, pos, meaning, and is_idiom. Do not include markdown formatting or thoughts."
        user_prompt_1 = f'''
        Full Context: "{context}"
        Target Word: "{word}"
        
        Extract:
        1. "lemma": Base dictionary form suitable for the context.
        2. "pos": Part of Speech in KOREAN. 
           - Single POS: Use full name (e.g., "명사", "동사", "형용사", "부사", "전치사", "접속사", "명사구", "형용사구").
           - Multiple POS: Use shortened names separated by a slash with spaces (e.g., "동 / 명", "형 / 부", "명 / 형"). Sort them alphabetically based on their original English names (noun, verb, adj, adv).
        3. "meaning": Korean meaning. CRITICAL: For each POS, use the format: "{{Context Meaning}}, {{Other Common Meanings}}". The meaning most suitable for the current context MUST come first. If there are multiple parts of speech, provide these blocks in the SAME ORDER, separated by a slash (e.g., if pos is "동 / 명", meaning must be "추적하다, 뒤쫒다 / 추적, 흔적"). Focus 100% on the surrounding sentence for the first meaning.
        4. "is_idiom": boolean.
        
        Format:
        {{
            "lemma": "example",
            "pos": "동사",
            "meaning": "문맥뜻, 일반뜻1, 일반뜻2",
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
        
        CRITICAL INSTRUCTIONS:
        1. STRONGLY PRESERVE CONTEXT-SPECIFIC MEANINGS. (e.g. keep "환율" instead of "비율" for "rates" in finance).
        2. Verify if this translation is perfectly accurate for the GIVEN CONTEXT.
        3. MEANING PRIORITY: The correct meaning for the context MUST be first. It should be in the format: "{{Context Meaning}}, {{Other Common Meanings}}".
        4. POS & MEANING KOREAN FORMATTING: 
           - Single POS: Full Korean name (e.g., "명사", "동사").
           - Multiple POS: Shortened Korean names with slashes (e.g., "동 / 명"). 
           - The "meaning" field must match the POS order exactly (e.g. "동사문맥뜻, 일반뜻 / 명사문맥뜻, 일반뜻").
        
        Output ONLY the final, corrected JSON. No explanation.
        '''
        
        messages.append({"role": "assistant", "content": json_lib.dumps(pass1_result, ensure_ascii=False)})
        messages.append({"role": "user", "content": user_prompt_2})
        
        pass2_result = call_ollama(messages)
        print("Pass 2 Result:", pass2_result)
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
