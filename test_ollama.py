import urllib.request
import json

print("Testing context limit with num_predict...")
req_data = {
    "model": "qwen3.5:9b",
    "messages": [
        {"role": "user", "content": "Hello! " * 500} # roughly 1000 tokens
    ],
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 1000,
        "num_ctx": 4096
    }
}

try:
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(req_data).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as response:
        raw_output = response.read().decode("utf-8")
        parsed = json.loads(raw_output)
        print("CHAT output length:", len(parsed.get('message', {}).get('content', '')))
except Exception as e:
    print("Failed:", e)
