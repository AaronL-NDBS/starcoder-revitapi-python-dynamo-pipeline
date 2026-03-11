import requests, json, time
from pathlib import Path

API = "https://api.stackexchange.com/2.3"

def scrape(output_dir, api_key, pages=15):
    Path(output_dir).mkdir(exist_ok=True)
    results = []

    # target both tags — they have different but overlapping communities
    for tag in ["revit-api", "dynamo-revit"]:
        for page in range(1, pages + 1):
            qs = requests.get(f"{API}/questions", params={
                "order": "desc", "sort": "votes",
                "tagged": tag, "site": "stackoverflow",
                "filter": "withbody", "pagesize": 100,
                "page": page, "key": api_key
            }).json().get("items", [])

            for q in qs:
                if q.get("answer_count", 0) == 0:
                    continue
                answers = requests.get(
                    f"{API}/questions/{q['question_id']}/answers",
                    params={"order": "desc", "sort": "votes",
                            "site": "stackoverflow", "filter": "withbody",
                            "key": api_key}
                ).json().get("items", [])

                top = next((a for a in answers if a.get("score", 0) > 1), None)
                if not top:
                    continue

                results.append({
                    "source": "stackoverflow",
                    "tag": tag,
                    "question": q["title"] + "\n" + q.get("body", ""),
                    "answer": top.get("body", ""),
                    "score": top.get("score", 0)
                })
                time.sleep(0.5)

            print(f"SO [{tag}] page {page}: {len(results)} total")
            time.sleep(1)

    out = Path(output_dir) / "raw_stackoverflow.jsonl"
    with open(out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"StackOverflow done: {len(results)} records")