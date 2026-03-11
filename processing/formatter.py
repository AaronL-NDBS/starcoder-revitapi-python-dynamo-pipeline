#This script converts raw sources into training pairs; normalize into same prompt/completion schema
import json, re
from pathlib import Path
from bs4 import BeautifulSoup

def strip_html(text):
    return BeautifulSoup(text, "html.parser").get_text(separator="\n")

def extract_code_blocks(text):
    return re.findall(r'```(?:python)?(.*?)```', text, re.DOTALL)

def extract_inline_code(text):
    """Fallback: grab indented blocks that look like Python nodes."""
    blocks = re.findall(r'((?:(?:import clr|IN\[|OUT\s*=).*\n(?:.*\n){2,20})+)', text)
    return blocks

def format_as_training_pair(prompt, completion):
    """Enforce consistent structure."""
    completion = completion.strip()
    # ensure it has the Dynamo scaffolding
    if "IN[" not in completion and "OUT" not in completion:
        return None
    return {
        "prompt": prompt.strip()[:800],
        "completion": completion[:2000]
    }

def process_all(raw_dir, output_file):
    raw_dir = Path(raw_dir)
    pairs = []

    # --- Discourse ---
    for line in open(raw_dir / "raw_discourse.jsonl"):
        r = json.loads(line)
        question = strip_html(r["question"])
        for reply in r["replies"]:
            reply_text = strip_html(reply)
            for block in extract_code_blocks(reply_text):
                pair = format_as_training_pair(
                    f"{r['topic']}\n{question}", block
                )
                if pair:
                    pairs.append(pair)

    # --- StackOverflow ---
    for line in open(raw_dir / "raw_stackoverflow.jsonl"):
        r = json.loads(line)
        answer = strip_html(r["answer"])
        for block in extract_code_blocks(answer) or extract_inline_code(answer):
            pair = format_as_training_pair(r["question"], block)
            if pair:
                pairs.append(pair)

    # --- GitHub ---
    for line in open(raw_dir / "raw_github.jsonl"):
        r = json.loads(line)
        pair = format_as_training_pair(
            f"Dynamo Python node from {r['repo']} ({r['filename']})",
            r["content"]
        )
        if pair:
            pairs.append(pair)

    with open(output_file, "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
            
    # --- Revit 2023 API Docs ---
    if (raw_dir / "raw_apidocs.jsonl").exists():
        for line in open(raw_dir / "raw_apidocs.jsonl"):
            r = json.loads(line)
            # code examples become completions directly
            for example in r["examples"]:
                if len(example) > 80:
                    pair = format_as_training_pair(
                        f"Show example usage of the Revit API {r['class']} class",
                        example
                    )
                    if pair:
                        pairs.append(pair)
            # member descriptions become prompt/completion reference pairs
            if r["members"]:
                members_text = "\n".join(
                    f"{m['member']}: {m['description']}"
                    for m in r["members"][:20]
                )
                pairs.append({
                    "prompt": f"What are the members of the Revit API {r['class']} class?",
                    "completion": members_text
                })
    # --- Hand-crafted pairs (highest quality, skip quality filter) ---
    hand_crafted_path = raw_dir.parent.parent / "dataset" / "hand_crafted.jsonl"
    if hand_crafted_path.exists():
        hc_count = 0
        for line in open(hand_crafted_path):
            r = json.loads(line)
            pairs.append({
                "prompt": r["prompt"],
                "completion": r["completion"],
                "_score": {"total": 10, "source": "hand_crafted"}
            })
            hc_count += 1
        print(f"Hand-crafted pairs loaded: {hc_count}")            

    print(f"Formatted: {len(pairs)} training pairs")
    return len(pairs)