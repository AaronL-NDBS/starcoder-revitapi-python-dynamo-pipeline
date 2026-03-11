#This runs the whole "shebang"
from config import CONFIG
from scrapers import discourse_scraper, stackoverflow_scraper, github_scraper, rvtapi_scraper
from processing.formatter import process_all
from processing.evaluator import filter_dataset
from pathlib import Path
import json, hashlib

RAW = "dataset/raw"
CLEANED = "dataset/cleaned"
Path(RAW).mkdir(parents=True, exist_ok=True)
Path(CLEANED).mkdir(parents=True, exist_ok=True)

print("=== Step 1: Scraping ===")
discourse_scraper.scrape(RAW)
stackoverflow_scraper.scrape(RAW, CONFIG["stackoverflow_key"])
github_scraper.scrape(RAW, CONFIG["github_token"])
rvtapi_scraper.scrape(RAW)

print("\n=== Step 2: Formatting ===")
process_all(RAW, f"{CLEANED}/formatted.jsonl")

print("\n=== Step 3: Deduplication ===")
seen, deduped = set(), []
for line in open(f"{CLEANED}/formatted.jsonl"):
    r = json.loads(line)
    h = hashlib.md5(r["completion"][:300].encode()).hexdigest()
    if h not in seen:
        seen.add(h)
        deduped.append(r)

with open(f"{CLEANED}/deduped.jsonl", "w") as f:
    for r in deduped:
        f.write(json.dumps(r) + "\n")
print(f"Deduped: {len(deduped)} records")

print("\n=== Step 4: Quality filter ===")
filter_dataset(
    f"{CLEANED}/deduped.jsonl",
    "dataset/final_dataset.jsonl",
    min_score=CONFIG["min_quality_score"]
)

print("\n=== Done ===")
count = sum(1 for _ in open("dataset/final_dataset.jsonl"))
print(f"Final dataset: {count} training pairs")