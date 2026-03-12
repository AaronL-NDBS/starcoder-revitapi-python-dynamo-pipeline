# Data Judgement/rvtapi_judge.py
#
# Generates Dynamo Python training pairs from the harvested Revit API JSON records.
# Reads from:  dataset/raw/rvt_api_local/  (output of rvtapi_local_scraper.py)
# Writes to:   dataset/scraped_candidates.jsonl
#
# Run from the project root:
#   python "Data Judgement/rvtapi_judge.py"
#
# Resume-safe: tracks processed files in dataset/raw/rvtapi_judge_progress.json
# Stop at any time with Ctrl+C — progress is saved after every record.

import json
import re
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

RAW_DIR       = Path("dataset/raw/rvt_api_local")
OUT_FILE      = Path("dataset/scraped_candidates.jsonl")
PROGRESS_FILE = Path("dataset/raw/rvtapi_judge_progress.json")

OLLAMA_URL    = "http://localhost:11434/api/chat"
MODEL         = "mistral"
TIMEOUT       = 120   # seconds per request
RETRY_LIMIT   = 3

# Pages with fewer members AND no summary are usually boilerplate index pages.
# Skip them — they won't produce useful training pairs.
MIN_CONTENT_SCORE = 1  # must have summary OR at least this many members

# ── MEP priority keywords ─────────────────────────────────────────────────────
# Files whose 'name' field matches these are processed first.
# Everything else follows in alphabetical order.

MEP_KEYWORDS = [
    "Duct", "Pipe", "Conduit", "CableTray", "Mechanical", "Plumbing",
    "Electrical", "Connector", "MEPSystem", "MechanicalSystem", "PipingSystem",
    "FlowElement", "AirTerminal", "FabricationPart", "Insulation",
    "FilteredElementCollector", "Transaction", "Element", "Parameter",
    "BuiltInCategory", "BuiltInParameter", "FamilyInstance", "Room", "Space",
    "Level", "RevitLinkInstance", "Document",
]

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert in the Autodesk Revit API and Dynamo Python scripting.

Given a Revit API class or member record (name, namespace, summary, members list),
write ONE complete Dynamo Python script that demonstrates practical use of this API element.

STRICT RULES:
- Use IN[] for all inputs and OUT for the single output
- Include ALL required clr.AddReference calls before imports
- Use CPython3 syntax (no IronPython-specific idioms)
- Wrap any document modifications in a Transaction
- Add concise inline comments explaining what each section does
- The script must be self-contained and runnable as a Dynamo Python node
- Do NOT include markdown fences, prose, or explanation outside the code

If the record describes something that cannot produce a meaningful Dynamo script
(e.g. a pure math utility, abstract base class with no useful members, or enum with
no practical Dynamo application), respond with exactly: SKIP

Otherwise respond with ONLY the Python code."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_progress() -> set:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_progress(done: set):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(sorted(done), f, indent=2)

def build_prompt(record: dict) -> str:
    lines = [
        f"Class/Member: {record['name']}",
        f"Namespace: {record['namespace']}",
    ]
    if record.get("summary"):
        lines.append(f"Summary: {record['summary']}")
    if record.get("members"):
        lines.append("Members (name | description):")
        for m in record["members"][:20]:  # cap at 20 to keep prompt tight
            lines.append(f"  {m['n']} | {m['d']}")
    return "\n".join(lines)

def has_content(record: dict) -> bool:
    has_summary = bool(record.get("summary", "").strip())
    has_members = len(record.get("members", [])) >= MIN_CONTENT_SCORE
    return has_summary or has_members

def is_mep_priority(record: dict) -> bool:
    name = record.get("name", "")
    return any(kw.lower() in name.lower() for kw in MEP_KEYWORDS)

def call_mistral(prompt_text: str) -> str | None:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt_text}
        ],
        "stream": False
    }
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except requests.exceptions.Timeout:
            print(f"    Timeout (attempt {attempt}/{RETRY_LIMIT})")
            if attempt < RETRY_LIMIT:
                time.sleep(5)
        except Exception as e:
            print(f"    Error: {e} (attempt {attempt}/{RETRY_LIMIT})")
            if attempt < RETRY_LIMIT:
                time.sleep(5)
    return None

def append_pair(record: dict, completion: str, sdk_name: str):
    pair = {
        "source":     "rvtapi_local",
        "sdk":        sdk_name,
        "prompt":     f"Write a Dynamo Python script demonstrating how to use {record['name']} from the Revit API.",
        "completion": completion,
        "class":      record["name"],
        "namespace":  record["namespace"],
        "date_added": datetime.now().strftime("%Y-%m-%d"),
    }
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(pair) + "\n")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not RAW_DIR.exists():
        print(f"ERROR: Raw directory not found: {RAW_DIR.resolve()}")
        print("Run rvtapi_local_scraper.py first.")
        input("\nPress any key to exit...")
        sys.exit(1)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    done = load_progress()

    # Collect all JSON files across both SDKs, Classes and Enums folders
    all_files = list(RAW_DIR.rglob("*.json"))
    total = len(all_files)

    if total == 0:
        print("No JSON files found in dataset/raw/rvt_api_local/")
        input("\nPress any key to exit...")
        sys.exit(1)

    # Load all records and sort: MEP-priority first, then alphabetical
    records = []
    for f in all_files:
        if f.name in done:
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data["_file"] = f.name
            data["_sdk"]  = f.parts[-3] if len(f.parts) >= 3 else "unknown"
            records.append(data)
        except Exception:
            done.add(f.name)  # skip corrupt files silently

    mep   = [r for r in records if is_mep_priority(r)]
    other = [r for r in records if not is_mep_priority(r)]
    mep.sort(key=lambda r: r["name"])
    other.sort(key=lambda r: r["name"])
    queue = mep + other

    skipped_already = total - len(queue)
    print("=" * 60)
    print(f" Revit API Judge | Model: {MODEL}")
    print("=" * 60)
    print(f" Total JSON records : {total}")
    print(f" Already processed  : {skipped_already}")
    print(f" To process         : {len(queue)}")
    print(f" MEP-priority first : {len(mep)}")
    print(f" Output             : {OUT_FILE}")
    print("-" * 60)
    print(" Ctrl+C at any time to stop. Progress is saved continuously.")
    print("=" * 60)

    generated = 0
    skipped_content = 0
    skipped_model = 0

    try:
        for i, record in enumerate(queue):
            fname = record["_file"]
            sdk   = record["_sdk"]
            name  = record.get("name", fname)
            priority_tag = " [MEP]" if is_mep_priority(record) else ""

            print(f"[{i+1}/{len(queue)}]{priority_tag} {name}", end=" ... ", flush=True)

            # Skip low-content records
            if not has_content(record):
                print("skipped (no content)")
                done.add(fname)
                skipped_content += 1
                save_progress(done)
                continue

            prompt_text = build_prompt(record)
            result = call_mistral(prompt_text)

            if result is None:
                print("failed (Ollama unreachable)")
                skipped_model += 1
                # Don't mark as done — retry next run
                continue

            if result.strip().upper() == "SKIP":
                print("skipped (model: not applicable)")
                done.add(fname)
                skipped_content += 1
                save_progress(done)
                continue

            # Strip any accidental markdown fences
            result = re.sub(r'^```(?:python)?\s*\n', '', result)
            result = re.sub(r'\n```\s*$', '', result)
            result = result.strip()

            if len(result) < 80:
                print("skipped (response too short)")
                done.add(fname)
                skipped_content += 1
                save_progress(done)
                continue

            append_pair(record, result, sdk)
            done.add(fname)
            save_progress(done)
            generated += 1
            print(f"OK ({len(result)} chars)")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress saved.")

    print("\n" + "=" * 60)
    print(f" Session complete")
    print(f" Pairs generated    : {generated}")
    print(f" Skipped (content)  : {skipped_content}")
    print(f" Skipped (errors)   : {skipped_model}")
    print(f" Total processed    : {len(done)}")
    print(f" Output             : {OUT_FILE.resolve()}")
    print("=" * 60)
    input("\nPress any key to exit...")

if __name__ == "__main__":
    main()
