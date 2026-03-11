# Data Judgement/rvtapi_judge.py
import json
import requests
from pathlib import Path

RAW_DIR = Path("dataset/raw/rvt_api_2023")
OUT_FILE = Path("dataset/scraped_candidates.jsonl")
OLLAMA_URL = "http://localhost:11434/api/chat"

def judge_class(data):
    prompt = f"Create a Dynamo Python script for the Revit API class: {data['name']}. {data['summary']}"
    # This is where your Mistral logic lives
    payload = {
        "model": "mistral",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False, "format": "json"
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload)
        return r.json()['message']['content']
    except: return None

def main():
    files = list(RAW_DIR.glob("*.json"))
    with open(OUT_FILE, "a") as out:
        for f in files:
            with open(f, "r") as src:
                raw_data = json.load(src)
            result = judge_class(raw_data)
            if result:
                out.write(result + "\n")
                f.unlink() # Delete raw file after successful processing

if __name__ == "__main__":
    main()