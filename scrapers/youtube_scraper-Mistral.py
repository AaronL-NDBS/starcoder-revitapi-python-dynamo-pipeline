# scrapers/youtube_scraper.py
import json
from pathlib import Path
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

RAW_DIR = Path("dataset/youtube/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def scrape_yt():
    url = input("Enter YouTube Playlist/Video URL: ")
    ydl_opts = {'quiet': True, 'extract_flat': True}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get('entries', [info])
        
    for entry in entries:
        v_id = entry['id']
        print(f"Fetching: {v_id}")
        try:
            ts = YouTubeTranscriptApi.get_transcript(v_id)
            full_text = " ".join([t['text'] for t in ts])
            with open(RAW_DIR / f"{v_id}.json", "w") as f:
                json.dump({"id": v_id, "title": entry.get('title'), "text": full_text}, f)
        except:
            print(f" No transcript for {v_id}")

if __name__ == "__main__":
    scrape_yt()