import json
import hashlib
from pathlib import Path

OUTPUT_FILE = "dataset/assembled_dataset.jsonl"

SOURCES = [
    ("stage1_revit_api",     "dataset/stages/stage1_revit_api.jsonl"),
    ("stage2_dynamo",        "dataset/stages/stage2_dynamo_concepts.jsonl"),
    ("stage3_dynamo_python", "dataset/stages/stage3_dynamo_python.jsonl"),
    ("hand_crafted",         "dataset/hand_crafted.jsonl"),
    ("scraped_pipeline",     "dataset/final_dataset.jsonl"),
    ("youtube_approved",     {"dir": "dataset/youtube/approved"}),
    ("pptx_approved",        {"dir": "dataset/pptx/approved"}),
]

def load_jsonl(path: Path, label: str) -> list[dict]:
    if not path.exists(): return []
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    r = json.loads(line)
                    r["_source_stage"] = label
                    records.append(r)
                except json.JSONDecodeError: pass
    except Exception as e:
        print(f"  [!] Error reading {path.name}: {e}")
    return records

def load_source(source_def, label: str) -> list[dict]:
    if isinstance(source_def, str):
        return load_jsonl(Path(source_def), label)
    elif isinstance(source_def, dict) and "dir" in source_def:
        d = Path(source_def["dir"])
        if not d.exists(): return []
        records = []
        for jsonl_file in sorted(d.glob("*.jsonl")):
            records.extend(load_jsonl(jsonl_file, label))
        return records
    return []

def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    seen_hashes = set()
    deduped = []
    removed_count = 0
    for r in records:
        content = r.get("completion", "").strip()
        if not content: continue
        h = hashlib.sha256(content[:400].encode('utf-8')).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped.append(r)
        else: removed_count += 1
    return deduped, removed_count

def main():
    print(f"\n{'='*60}\n      REVIT AI: MASTER DATASET ASSEMBLY\n{'='*60}\n")
    all_records = []
    source_counts = {}

    for label, source_def in SOURCES:
        records = load_source(source_def, label)
        source_counts[label] = len(records)
        all_records.extend(records)
        status = f"{len(records):>5} records" if records else "empty"
        print(f"  - {label:<25} {status}")

    deduped, removed = deduplicate(all_records)
    print(f"\n  Total Raw Records    : {len(all_records)}")
    print(f"  Duplicates Removed   : {removed}")
    print(f"  Final Unique Pairs   : {len(deduped)}")

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in deduped: f.write(json.dumps(r) + "\n")

    print(f"\n=== ASSEMBLY COMPLETE ===")
    for label, count in source_counts.items():
        if count > 0:
            pct = (count / len(all_records)) * 100 if all_records else 0
            bar = "#" * int(pct / 4)
            print(f"    {label:<25} {count:>5} {bar} ({pct:.1f}%)")

if __name__ == "__main__":
    main()