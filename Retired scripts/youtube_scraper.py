import os
import json
import time
import hashlib
import yt_dlp
from pathlib import Path
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TOTAL_IN = 0
TOTAL_OUT = 0

def get_best_model():
    try:
        models = [m.name for m in client.models.list() if 'generateContent' in m.supported_actions]
        for tier in ["flash", "pro"]:
            match = next((m for m in sorted(models, reverse=True) if tier in m.lower()), None)
            if match: return match
        return "gemini-2.5-flash"
    except: return "gemini-2.5-flash"

MODEL_ID = get_best_model()
STATE_FILE = Path("dataset/youtube/youtube_progress.json")
APPROVED_DIR = Path("dataset/youtube/approved")
APPROVED_DIR.mkdir(parents=True, exist_ok=True)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f: return json.load(f)
    return {"processed_ids": [], "seen_hashes": []}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)

def process_with_gemini(chunk):
    global TOTAL_IN, TOTAL_OUT
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=f"Extract Revit API JSON training pairs from this transcript:\n\n{chunk}",
                config={'response_mime_type': 'application/json'}
            )
            usage = response.usage_metadata
            TOTAL_IN += usage.prompt_token_count
            TOTAL_OUT += usage.candidates_token_count
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 30 * (2 ** attempt)
                print(f"\n   QUOTA HIT. Sleeping {wait}s...", end="")
                time.sleep(wait)
            else: raise e
    return []

def main():
    print(f"\n{'='*60}\n YOUTUBE API PIPELINE | Model: {MODEL_ID}\n{'='*60}")
    url = input("Enter Video/Playlist URL: ").strip()
    state = load_state()
    
    print(" FETCHING METADATA...", end="\r")
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        found_ids = [e['id'] for e in info.get('entries', [])] if 'entries' in info else [info['id']]

    to_process = [vid for vid in found_ids if vid not in state["processed_ids"]]
    print(f" - Found: {len(found_ids)} videos | Skipped: {len(found_ids) - len(to_process)}")
    print(f" - New to process: {len(to_process)}")
    print(f"{'-'*60}")

    for idx, vid in enumerate(to_process):
        print(f"[{idx+1}/{len(to_process)}] VIDEO: https://youtu.be/{vid}")
        try:
            t_data = YouTubeTranscriptApi.get_transcript(vid)
            text = " ".join([i['text'] for i in t_data])
            chunks = [text[i:i+2500] for i in range(0, len(text), 2000)]
            video_pairs = []
            for i, chunk in enumerate(chunks):
                print(f"   - Analyzing Chunk {i+1}/{len(chunks)}...", end="\r")
                pairs = process_with_gemini(chunk)
                for p in pairs:
                    h = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
                    if h not in state["seen_hashes"]:
                        video_pairs.append(p)
                        state["seen_hashes"].append(h)
                time.sleep(12)

            if video_pairs:
                with open(APPROVED_DIR / f"{vid}.jsonl", "a", encoding="utf-8") as f:
                    for p in video_pairs: f.write(json.dumps(p) + "\n")
            
            state["processed_ids"].append(vid)
            save_state(state)
            print(f"   SUCCESS: {len(video_pairs)} pairs. Tokens In: {TOTAL_IN}   ")
        except Exception as e:
            print(f"   FAILED: {vid} -> {str(e)[:100]}")

if __name__ == "__main__":
    main()