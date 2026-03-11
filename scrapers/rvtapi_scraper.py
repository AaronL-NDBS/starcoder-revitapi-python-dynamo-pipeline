# scrapers/apidocs_scraper.py
import requests, json, time
from pathlib import Path
from bs4 import BeautifulSoup

BASE = "https://www.revitapidocs.com"

# High-value pages to target directly — these cover the most common Dynamo node patterns
TARGET_PATHS = [
    "/2023/",                                          # index — links to classes
    "/2023/eb16b9c3-c4fb-4268-840f-7dc72af6cb8a.htm", # FilteredElementCollector
    "/2023/fdb6e9a2-6c63-4b2c-a9c3-88a0c01a213b.htm", # Transaction
    "/2023/4e5f5b5a-1c7a-4e2a-b50d-56b4b8d3c2e1.htm", # Element
    "/2023/8b9f5c3d-2e4a-4b6c-9d8e-7f2a1b3c4d5e.htm", # Wall
    "/2023/6c7d8e9f-3f5b-4c6d-8e9f-1a2b3c4d5e6f.htm", # Floor
]

def scrape_class_page(url):
    r = requests.get(url, headers={"User-Agent": "ResearchBot/1.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    class_name = soup.find("h1")
    class_name = class_name.text.strip() if class_name else "Unknown"

    # grab code examples
    examples = []
    for block in soup.find_all("pre"):
        code = block.get_text()
        if len(code) > 50:
            examples.append(code)

    # grab method descriptions
    descriptions = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            descriptions.append({
                "member": cells[0].get_text(strip=True),
                "description": cells[1].get_text(strip=True)
            })

    return {
        "class": class_name,
        "url": url,
        "examples": examples,
        "members": descriptions
    }

def scrape(output_dir, pages=5):
    Path(output_dir).mkdir(exist_ok=True)
    results = []

    # first crawl the index to get class URLs
    index = requests.get(f"{BASE}/2023/", headers={"User-Agent": "ResearchBot/1.0"})
    soup = BeautifulSoup(index.text, "html.parser")
    
    class_links = [
        a["href"] for a in soup.find_all("a", href=True)
        if "/2023/" in a["href"] and ".htm" in a["href"]
    ][:200]  # cap at 200 classes

    for path in class_links:
        url = BASE + path if path.startswith("/") else path
        try:
            data = scrape_class_page(url)
            if data["examples"] or len(data["members"]) > 3:
                results.append(data)
            time.sleep(0.75)
        except Exception as e:
            print(f"  Error {url}: {e}")

    out = Path(output_dir) / "raw_apidocs.jsonl"
    with open(out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"API docs done: {len(results)} classes scraped")