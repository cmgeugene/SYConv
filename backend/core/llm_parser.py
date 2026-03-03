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
    You are an expert English teacher. The user has highlighted some words in an English text snippet.
    
    Full context text:
    ---
    {full_context_text}
    ---
    
    Highlighted words raw extraction (might contain OCR errors):
    {raw_texts}
    
    For each highlighted word exactly matching the sequential order, return a JSON array under the key "words", with objects containing:
    - "word": The corrected lowercase base form (lemma) of the word. MUST convert plural to singular, past/participle to present base verb (e.g., "realized" -> "realize"). If it's part of an idiom like "taking off", extract the base idiom "take off".
    - "pos": Part of speech based on the context. If it functions as multiple or has dual usage, list them separated by a slash AND sort them in alphabetical order to maintain consistency (e.g., ALWAYS "adj / adv", never "adv / adj").
    - "meaning": The primary Korean meaning appropriate for the context first, followed by other common dictionary definitions. DO NOT write "(문맥)". If there are multiple POS tags, align the meanings (e.g., if pos is "adv / adj", meaning could be "빠르게 / 빠른, 신속한").
    - "is_idiom": A boolean (true/false) indicating if it's an idiom/phrase.
    
    Return ONLY valid JSON.
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
                    "num_ctx": 4096
                }
            }
            
            req = urllib.request.Request(chat_endpoint, data=json_lib.dumps(req_data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as response:
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
