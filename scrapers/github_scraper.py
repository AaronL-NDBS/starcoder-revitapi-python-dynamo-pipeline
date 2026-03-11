import requests, json, time, base64
from pathlib import Path

def scrape(output_dir, token):
    Path(output_dir).mkdir(exist_ok=True)
    headers = {"Authorization": f"token {token}"}
    results = []

    queries = [
        "dynamo revit python clr language:python",
        "revit api FilteredElementCollector language:python",
        "dynamo IN OUT clr AddReference language:python",
    ]

    for query in queries:
        repos = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers,
            params={"q": query, "sort": "stars", "per_page": 30}
        ).json().get("items", [])

        for repo in repos:
            files = requests.get(
                "https://api.github.com/search/code",
                headers=headers,
                params={"q": f"repo:{repo['full_name']} clr IN OUT extension:py"}
            ).json().get("items", [])

            for file in files[:8]:
                try:
                    raw = requests.get(file["url"], headers=headers).json()
                    content = base64.b64decode(raw.get("content", "")).decode("utf-8", errors="ignore")

                    # filter to files that look like Dynamo nodes
                    if "IN[" in content and "OUT" in content and "clr" in content:
                        results.append({
                            "source": "github",
                            "repo": repo["full_name"],
                            "filename": file["name"],
                            "content": content
                        })
                    time.sleep(1)
                except Exception as e:
                    print(f"  Error {file['name']}: {e}")

        print(f"GitHub query done: {len(results)} total")
        time.sleep(2)

    out = Path(output_dir) / "raw_github.jsonl"
    with open(out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"GitHub done: {len(results)} records")