# youtube_judge.py
import json, requests, re
from pathlib import Path

RAW_DIR = Path("dataset/youtube/raw")
CANDIDATES_FILE = Path("dataset/scraped_candidates.jsonl")
OLLAMA_URL = "http://localhost:11434/api/chat"

# Prompt extracted from your Mistral logic
SYSTEM_PROMPT = "Extract Revit API/Dynamo Python pairs from this transcript. Return ONLY JSON: {'prompt': '...', 'completion': '...'}"

def process_youtube_queue():
    files = list(RAW_DIR.glob("*.json"))
    print(f"Judging {len(files)} transcripts...")
    
    with open(CANDIDATES_FILE, "a") as out:
        for f_path in files:
            with open(f_path, "r") as f:
                data = json.load(f)
            
            # Send to Mistral
            r = requests.post(OLLAMA_URL, json={
                "model": "mistral",
                "messages": [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{data['transcript'][:2000]}"}],
                "stream": False, "format": "json"
            })
            
            pair = json.loads(r.json()["message"]["content"])
            if pair.get("prompt"):
                pair["_source"] = f"youtube_{data['video_id']}"
                out.write(json.dumps(pair) + "\n")
            
            f_path.unlink() # Remove raw file once processed
            print(f"  Processed: {data['video_id']}")

if __name__ == "__main__":
    process_youtube_queue()