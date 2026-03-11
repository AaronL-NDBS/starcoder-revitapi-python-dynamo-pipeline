# tools/generate_stage2_pairs.py
# Stage 2: Dynamo concepts and execution model.
# Teaches StarCoder how Dynamo works as an environment BEFORE teaching it
# to write Python nodes. A model that doesn't understand Dynamo's data flow
# model will produce Python that is syntactically correct but wrong for the
# Dynamo context.

import json
import re
import requests
import time
from pathlib import Path
from datetime import datetime

OUTPUT_FILE = "dataset/stages/stage2_dynamo_concepts.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "mistral"
Path("dataset/stages").mkdir(parents=True, exist_ok=True)

SYSTEM = """You are an expert in Autodesk Dynamo for Revit.
Explain Dynamo concepts clearly, using Python code examples where relevant.

When writing Python examples for Dynamo:
- Use the IN[]/OUT pattern
- Include clr imports when demonstrating Revit API interaction
- Use CPython3 syntax (Dynamo 2.x)
- Add comments explaining how the code relates to Dynamo's execution model

Return ONLY code with explanatory comments. No prose outside code. No markdown fences."""

STAGE2_PROMPTS = [

    # ── Dynamo execution model ─────────────────────────────────────────────
    "Explain how Dynamo executes a node graph as a data flow — inputs flow left to right, each node transforms data and passes it to the next node",
    "Explain the IN[] list in a Dynamo Python node — how it maps to the node's input ports, what IN[0] through IN[n] represent, and how to document what each input expects",
    "Explain the OUT variable in a Dynamo Python node — it can be a single value, a list, or a list of lists, and how downstream nodes receive it",
    "Explain how Dynamo handles lists and why list management (levels, lacing) matters when designing Python nodes that output lists",

    # ── Dynamo Python environment ──────────────────────────────────────────
    "Explain the Dynamo Python Script node environment — what is pre-imported, what the IN list contains by default, and what Dynamo provides automatically",
    "Explain the difference between IronPython (legacy Dynamo) and CPython3 (Dynamo 2.x+) and what code differences this creates",
    "Explain how Dynamo provides the Revit Document to a Python node — show the correct way to get doc, uiapp, and uidoc from the Dynamo Python environment",
    "Explain Dynamo's transaction handling — when Dynamo manages the transaction automatically and when a Python node needs to open its own transaction",

    # ── IN[]/OUT patterns ──────────────────────────────────────────────────
    "Show the minimal correct structure of a Dynamo Python node that takes no inputs and returns a value — the simplest possible valid node",
    "Show a Dynamo Python node with multiple typed inputs — demonstrate how to document each IN[] input with its expected type and what happens with wrong input types",
    "Show how to handle optional inputs in a Dynamo Python node — check if IN[n] is None or an empty list before using it",
    "Show how to return multiple outputs from a Dynamo Python node using a list as OUT, and explain how downstream nodes receive each value",
    "Show a Dynamo Python node that accepts either a single element or a list of elements as input and handles both cases correctly",

    # ── Common Dynamo patterns ─────────────────────────────────────────────
    "Show the correct pattern for error handling in a Dynamo Python node — catch exceptions, return a meaningful error message as OUT rather than crashing the graph",
    "Show how to use Dynamo's built-in element unwrapping — when elements passed through IN[] need to be unwrapped and how to do it",
    "Explain Dynamo's Element binding — why you sometimes get stale elements and how to handle it in Python nodes",
    "Show how to chain two Dynamo Python nodes together — what the first node outputs, how the second node receives it, and type expectations at the boundary",

    # ── Dynamo + Revit context ─────────────────────────────────────────────
    "Show how to get the current Revit document from a Dynamo Python node using both the legacy IronPython method and the current CPython3 method",
    "Explain what DocumentManager and RevitServices are in the Dynamo context and when they are needed to access the document",
    "Show a complete minimal Dynamo Python node template that includes: correct imports, document access, typed IN[] inputs, logic section, error handling, and OUT",
]


def generate_pair(prompt: str) -> str | None:
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }, timeout=120)
        code = r.json()["message"]["content"].strip()
        code = re.sub(r'^```(?:python)?\s*\n', '', code)
        code = re.sub(r'\n```\s*$', '', code)
        return code.strip()
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    existing = set()
    if Path(OUTPUT_FILE).exists():
        for line in open(OUTPUT_FILE, encoding="utf-8"):
            r = json.loads(line)
            existing.add(r["prompt"])
        print(f"Resuming — {len(existing)} pairs already generated\n")

    new_count = 0
    for i, prompt in enumerate(STAGE2_PROMPTS):
        if prompt in existing:
            print(f"  [{i+1}/{len(STAGE2_PROMPTS)}] Skipping: {prompt[:60]}...")
            continue

        print(f"  [{i+1}/{len(STAGE2_PROMPTS)}] {prompt[:70]}...")
        completion = generate_pair(prompt)

        if completion and len(completion) > 80:
            record = {
                "stage": 2,
                "source": "generated",
                "prompt": prompt,
                "completion": completion,
                "date_added": datetime.now().strftime("%Y-%m-%d"),
            }
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            new_count += 1
            print(f"    Saved ({len(completion)} chars)")
        else:
            print(f"    Skipped — too short or failed")

        time.sleep(0.5)

    total = sum(1 for _ in open(OUTPUT_FILE))
    print(f"\nStage 2 complete. New: {new_count} | Total: {total}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
