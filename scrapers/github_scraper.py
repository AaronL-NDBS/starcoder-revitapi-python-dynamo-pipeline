# scrapers/github_scraper.py
# Scrapes Python files from GitHub — both targeted repos and keyword searches.
# Targeted repos are pulled in full; search queries find additional repos.

import requests
import json
import time
import base64
from pathlib import Path

# ── Targeted repos — pulled directly, not via search ─────────────────────────
# These are known high-quality sources. Every .py file is fetched regardless
# of whether it matches the Dynamo IN[]/OUT filter — the revitapidocs.code
# repo in particular contains pure Revit API scripts without Dynamo scaffolding,
# which is valuable Stage 1 training data.
TARGET_REPOS = [
    "gtalarico/revitapidocs.code",   # community Revit API Python scripts
    "gtalarico/pyrevit",             # pyRevit framework — extensive Revit API Python
    "eirannejad/pyRevit",            # pyRevit main fork
]

# ── Search queries — finds repos matching keywords ───────────────────────────
SEARCH_QUERIES = [
    "dynamo revit python clr language:python",
    "revit api FilteredElementCollector language:python",
    "dynamo IN OUT clr AddReference language:python",
]

# File filter for search results — targeted repos bypass this
DYNAMO_SIGNALS = ["IN[", "OUT", "clr"]
REVIT_SIGNALS  = ["FilteredElementCollector", "Autodesk.Revit", "clr.AddReference",
                  "BuiltInCategory", "BuiltInParameter", "RevitAPI"]

def is_relevant(content: str) -> bool:
    """Accept files that look like Dynamo nodes OR pure Revit API Python."""
    is_dynamo = all(s in content for s in DYNAMO_SIGNALS)
    is_revit  = sum(1 for s in REVIT_SIGNALS if s in content) >= 2
    return is_dynamo or is_revit

def get_repo_python_files(repo_full_name: str, headers: dict,
                          max_files: int = 100) -> list[dict]:
    """
    Get all Python files from a specific repo using the Trees API.
    More reliable than code search for full repo traversal.
    """
    results = []

    # get default branch
    repo_info = requests.get(
        f"https://api.github.com/repos/{repo_full_name}",
        headers=headers
    ).json()
    branch = repo_info.get("default_branch", "main")

    # get full file tree
    tree = requests.get(
        f"https://api.github.com/repos/{repo_full_name}/git/trees/{branch}",
        headers=headers,
        params={"recursive": "1"}
    ).json()

    py_files = [
        item for item in tree.get("tree", [])
        if item["path"].endswith(".py") and item["type"] == "blob"
    ][:max_files]

    print(f"    {repo_full_name}: {len(py_files)} .py files found")

    for item in py_files:
        try:
            raw = requests.get(
                f"https://api.github.com/repos/{repo_full_name}/contents/{item['path']}",
                headers=headers
            ).json()
            content_b64 = raw.get("content", "")
            if not content_b64:
                continue
            content = base64.b64decode(content_b64).decode("utf-8", errors="ignore")

            if len(content) < 50:
                continue

            results.append({
                "source": "github_targeted",
                "repo": repo_full_name,
                "filename": Path(item["path"]).name,
                "filepath": item["path"],
                "content": content
            })
            time.sleep(0.5)
        except Exception as e:
            print(f"      Error {item['path']}: {e}")

    return results


def scrape(output_dir: str, token: str):
    Path(output_dir).mkdir(exist_ok=True)
    headers = {"Authorization": f"token {token}"}
    results = []

    # ── Phase 1: Targeted repos ───────────────────────────────────────────
    print("\n  Phase 1: Targeted repos")
    for repo_name in TARGET_REPOS:
        print(f"  Fetching {repo_name}...")
        try:
            files = get_repo_python_files(repo_name, headers)
            # targeted repos: keep all Revit-relevant files, not just Dynamo nodes
            relevant = [f for f in files if is_relevant(f["content"])]
            results.extend(relevant)
            print(f"    Kept {len(relevant)}/{len(files)} relevant files")
        except Exception as e:
            print(f"    Error fetching {repo_name}: {e}")
        time.sleep(2)

    print(f"\n  Targeted repos total: {len(results)} files")

    # ── Phase 2: Search queries ───────────────────────────────────────────
    print("\n  Phase 2: Search queries")
    for query in SEARCH_QUERIES:
        try:
            repos = requests.get(
                "https://api.github.com/search/repositories",
                headers=headers,
                params={"q": query, "sort": "stars", "per_page": 20}
            ).json().get("items", [])
        except Exception as e:
            print(f"  Search error '{query}': {e}")
            time.sleep(5)
            continue

        for repo in repos:
            # skip repos we already processed directly
            if repo["full_name"] in TARGET_REPOS:
                continue
            try:
                files = requests.get(
                    "https://api.github.com/search/code",
                    headers=headers,
                    params={"q": f"repo:{repo['full_name']} clr IN OUT extension:py"}
                ).json().get("items", [])

                for file in files[:6]:
                    try:
                        raw = requests.get(file["url"], headers=headers).json()
                        content = base64.b64decode(
                            raw.get("content", "")
                        ).decode("utf-8", errors="ignore")

                        if is_relevant(content):
                            results.append({
                                "source": "github_search",
                                "repo": repo["full_name"],
                                "filename": file["name"],
                                "filepath": file.get("path", file["name"]),
                                "content": content
                            })
                        time.sleep(1)
                    except Exception as e:
                        print(f"    Error {file['name']}: {e}")

            except Exception as e:
                print(f"  Repo error {repo['full_name']}: {e}")
            time.sleep(1)

        print(f"  Query done: {len(results)} total so far")
        time.sleep(3)  # avoid secondary rate limit between queries

    # ── Write output ──────────────────────────────────────────────────────
    out = Path(output_dir) / "raw_github.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    targeted = sum(1 for r in results if r["source"] == "github_targeted")
    searched = sum(1 for r in results if r["source"] == "github_search")
    print(f"\n  GitHub done: {len(results)} total "
          f"({targeted} targeted, {searched} from search)")