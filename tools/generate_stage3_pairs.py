# tools/generate_stage3_pairs.py
# Stage 3: Dynamo Python nodes that interface with the Revit API.
# This is where Stage 1 (Revit API knowledge) and Stage 2 (Dynamo context)
# combine into the actual target output format: single-purpose Python nodes
# using IN[]/OUT that call the Revit API correctly.

import json
import re
import requests
import time
from pathlib import Path
from datetime import datetime

OUTPUT_FILE = "dataset/stages/stage3_dynamo_python.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "mistral"
Path("dataset/stages").mkdir(parents=True, exist_ok=True)

SYSTEM = """You are an expert in Autodesk Dynamo Python scripting and the Revit 2023 API.
Write single-purpose Dynamo Python nodes that correctly interface with the Revit API.

Every script must:
- Use IN[] for inputs (comment each input with its expected type)
- Use OUT for the single output value or list
- Include correct clr.AddReference calls
- Use from Autodesk.Revit.DB import * and relevant namespaces
- Target CPython3 (Dynamo 2.x)
- Be self-contained and focused on one task
- Include a comment block at the top describing purpose, inputs, and output
- Handle None/empty inputs gracefully

Return ONLY the Python code. No prose. No markdown fences."""

STAGE3_PROMPTS = [

    # ── Element collection nodes ───────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all walls in the model as a list",
    "Write a Dynamo Python node that takes a document (IN[0]) and a level name string (IN[1]) and returns all elements on that level",
    "Write a Dynamo Python node that takes a document (IN[0]) and a BuiltInCategory name string (IN[1]) and returns all instances of that category",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all rooms with their name, number, area, and level as a list of dictionaries",
    "Write a Dynamo Python node that takes a document (IN[0]) and a family name string (IN[1]) and returns all instances of that family",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all levels sorted by elevation",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all view templates as a list",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all sheets with their sheet number and name",

    # ── Parameter read nodes ───────────────────────────────────────────────
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and a parameter name string (IN[1]) and returns the parameter value for each element",
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and a BuiltInParameter enum name string (IN[1]) and returns the parameter values",
    "Write a Dynamo Python node that takes an element (IN[0]) and returns all its parameters as a list of name-value pairs",
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and returns their ElementIds as integers",

    # ── Parameter write nodes ──────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]), a list of elements (IN[1]), a parameter name (IN[2]), and a value (IN[3]), and sets that parameter on all elements using a Transaction",
    "Write a Dynamo Python node that takes a document (IN[0]), a list of elements (IN[1]), and renames them by appending a suffix string (IN[2]) to their current name parameter",

    # ── MEP collection nodes ───────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all ducts with their width, height, system name, and level",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all pipes with their diameter, system name, and level",
    "Write a Dynamo Python node that takes a document (IN[0]) and a level name (IN[1]) and returns all mechanical equipment on that level",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all air terminals with their flow parameter value",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all unconnected MEP connectors in the model",
    "Write a Dynamo Python node that takes a duct or pipe element (IN[0]) and returns all elements connected to it through its connectors",

    # ── Filtering and querying nodes ───────────────────────────────────────
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and a parameter name (IN[1]) and a value (IN[2]) and returns only elements where that parameter matches the value",
    "Write a Dynamo Python node that takes a document (IN[0]) and a bounding box defined by two XYZ points (IN[1], IN[2]) and returns all elements within that box",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns elements grouped by their level as a dictionary of level name to element list",
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and returns only those that are on a workset matching a name string (IN[1])",

    # ── Linked model nodes ─────────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all RevitLinkInstances with their name and transform",
    "Write a Dynamo Python node that takes a document (IN[0]), a link instance name (IN[1]), and a BuiltInCategory (IN[2]) and returns all elements of that category from the linked model",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all walls from all linked models, transforming their bounding boxes to the host coordinate system",

    # ── View and sheet nodes ───────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]) and a view type name string (IN[1]) and returns all views of that type",
    "Write a Dynamo Python node that takes a document (IN[0]) and returns a dictionary mapping sheet number to a list of view names on that sheet",
    "Write a Dynamo Python node that takes a document (IN[0]), a list of views (IN[1]), and a view template name (IN[2]) and applies that template to all views using a Transaction",

    # ── Geometry nodes ────────────────────────────────────────────────────
    "Write a Dynamo Python node that takes a list of elements (IN[0]) and returns their bounding box center points as XYZ values",
    "Write a Dynamo Python node that takes two elements (IN[0], IN[1]) and returns the distance between their location points",
    "Write a Dynamo Python node that takes a wall element (IN[0]) and returns its location curve start point, end point, and length",

    # ── MEP workflow nodes ─────────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]) and returns all MEP systems (mechanical, piping, electrical) with their name, type, and element count",
    "Write a Dynamo Python node that takes a document (IN[0]) and a system name (IN[1]) and traverses the system returning all connected duct or pipe elements in order",
    "Write a Dynamo Python node that takes a document (IN[0]) and checks all ducts for missing insulation, returning a list of duct elements where insulation thickness is zero",

    # ── Clash detection nodes ──────────────────────────────────────────────
    "Write a Dynamo Python node that takes a document (IN[0]), a list of MEP elements (IN[1]), and a list of structural elements (IN[2]) and returns pairs of elements whose bounding boxes intersect",
    "Write a Dynamo Python node that takes a document (IN[0]) and finds all ducts or pipes that pass through walls by checking bounding box intersections with wall elements",
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
    for i, prompt in enumerate(STAGE3_PROMPTS):
        if prompt in existing:
            print(f"  [{i+1}/{len(STAGE3_PROMPTS)}] Skipping: {prompt[:60]}...")
            continue

        print(f"  [{i+1}/{len(STAGE3_PROMPTS)}] {prompt[:70]}...")
        completion = generate_pair(prompt)

        if completion and len(completion) > 100:
            record = {
                "stage": 3,
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
    print(f"\nStage 3 complete. New: {new_count} | Total: {total}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
