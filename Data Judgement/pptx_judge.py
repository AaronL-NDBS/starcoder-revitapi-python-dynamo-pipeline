# pptx_judge.py
import json, requests, re, logging
from pathlib import Path

RAW_DIR = Path("dataset/pptx/raw")
CANDIDATES_FILE = Path("dataset/scraped_candidates.jsonl")
OLLAMA_URL = "http://localhost:11434/api/chat"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Prompt extracted from your Mistral logic
SYSTEM_PROMPT = "Extract Revit API/Dynamo Python pairs from this transcript. Return ONLY JSON: {'prompt': '...', 'completion': '...'}"

def process_pptx_queue():
    files = list(RAW_DIR.glob("*.json"))
    processed_files = set()

    if CANDIDATES_FILE.exists():
        with open(CANDIDATES_FILE, "r") as f:
            for line in f:
                pair = json.loads(line)
                if "_source" in pair:
                    processed_files.add(pair["_source"].split("_")[1])

    logging.info(f"Judging {len(files)} pptx files...")

    with open(CANDIDATES_FILE, "a") as out:
        for f_path in files:
            video_id = f_path.stem
            if video_id in processed_files:
                logging.info(f"  Skipping already processed: {video_id}")
                continue

            with open(f_path, "r") as f:
                data = json.load(f)

            slides = data.get("slides", [])
            grouped_slides = [slides[i:i+3] for i in range(0, len(slides), 3)]

            for chunk in grouped_slides:
                chunk_content = "\n\n".join([slide["content"] for slide in chunk])
                
                for attempt in range(3):
                    try:
                        r = requests.post(OLLAMA_URL, json={
                            "model": "mistral",
                            "messages": [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{chunk_content[:2000]}"}],
                            "stream": False, "format": "json"
                        }, timeout=120)
                        r.raise_for_status()
                        pair = json.loads(r.json()["message"]["content"])
                        if pair.get("prompt"):
                            pair["_source"] = f"pptx_{video_id}"
                            out.write(json.dumps(pair) + "\n")
                            break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                        logging.warning(f"Timeout/Connection error occurred: {e}")
                        if attempt == 2:
                            logging.error(f"Failed to process {video_id} after 3 attempts")
                    except Exception as e:
                        logging.error(f"Other error occurred: {e}")
                        if attempt == 2:
                            logging.error(f"Failed to process {video_id} after 3 attempts")

            f_path.unlink()  # Remove raw file once processed
            logging.info(f"  Processed: {video_id}")

if __name__ == "__main__":
    process_pptx_queue()