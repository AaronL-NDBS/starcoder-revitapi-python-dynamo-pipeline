import requests, json, time
from pathlib import Path

BASE = "https://forum.dynamobim.com"

def scrape(output_dir, pages=30):
    Path(output_dir).mkdir(exist_ok=True)
    results = []

    for page in range(pages):
        topics = requests.get(
            f"{BASE}/latest.json?page={page}",
            headers={"User-Agent": "ResearchBot/1.0"}
        ).json().get("topic_list", {}).get("topics", [])

        for topic in topics:
            try:
                data = requests.get(
                    f"{BASE}/t/{topic['id']}.json",
                    headers={"User-Agent": "ResearchBot/1.0"}
                ).json()
                posts = data.get("post_stream", {}).get("posts", [])
                if len(posts) < 2:
                    continue

                # only keep threads with Python code
                full_text = " ".join(p.get("cooked", "") for p in posts)
                if "import clr" not in full_text and "IN[" not in full_text:
                    continue

                results.append({
                    "source": "dynamo_forum",
                    "topic": topic.get("title", ""),
                    "question": posts[0].get("cooked", ""),
                    "replies": [p.get("cooked", "") for p in posts[1:5]]
                })
                time.sleep(1)
            except Exception as e:
                print(f"  Error topic {topic['id']}: {e}")

        print(f"Discourse page {page}: {len(results)} records so far")
        time.sleep(2)

    out = Path(output_dir) / "raw_discourse.jsonl"
    with open(out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Discourse done: {len(results)} records")