# pptx_judge.py
import json, requests
from pathlib import Path

RAW_DIR = Path("dataset/pptx/raw")
CANDIDATES_FILE = Path("dataset/scraped_candidates.jsonl")

def process_pptx_queue():
    files = list(RAW_DIR.glob("*.json"))
    for f_path in files:
        with open(f_path, "r") as f:
            data = json.load(f)
        
        print(f"Judging: {data['filename']}")
        # Group slides into chunks of 3 for context, then judge
        for i in range(0, len(data['slides']), 3):
            chunk = data['slides'][i:i+3]
            # ... Call Ollama similar to youtube_judge.py ...
            # Append result to CANDIDATES_FILE
        
        f_path.unlink() # Clean up

if __name__ == "__main__":
    process_pptx_queue()