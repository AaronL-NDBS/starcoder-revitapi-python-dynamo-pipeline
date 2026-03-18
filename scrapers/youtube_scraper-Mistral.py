# youtube_scraper-Mistral.py
import json, os, logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

RAW_DIR = Path("dataset/youtube/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def scrape_youtube_folder(folder_path):
    files = list(Path(folder_path).rglob("*.json"))
    for p in files:
        logging.info(f"Scraping: {p.name}")
        try:
            with open(p, "r") as f:
                data = json.load(f)
            
            new_data = {
                "video_id": data.get("id"),
                "transcript": data.get("text")
            }
            
            with open(RAW_DIR / f"{p.stem}.json", "w") as f:
                json.dump(new_data, f)
        except Exception as e:
            logging.error(f"  Error: {e}")

if __name__ == "__main__":
    path = input("Enter path to YouTube JSON folder: ").strip('"')
    scrape_youtube_folder(path)