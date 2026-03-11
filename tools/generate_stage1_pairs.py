# tools/generate_stage1_pairs.py
# Stage 1: Foundational Revit API knowledge.
# Generates training pairs that teach StarCoder what the Revit API IS —
# its object model, core classes, methods, and relationships.
# No Dynamo yet. Pure Revit API Python.

import json
import re
import requests
import time
from pathlib import Path
from datetime import datetime

OUTPUT_FILE = "dataset/stages/stage1_revit_api.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "mistral"
Path("dataset/stages").mkdir(parents=True, exist_ok=True)

SYSTEM = """You are an expert in the Autodesk Revit 2023 API.
Write a clear, accurate explanation of a Revit API concept as Python code with comments.

The code must:
- Use standard Python 3 with clr imports (NOT Dynamo IN/OUT pattern — pure API examples)
- Include all necessary clr.AddReference calls
- Use correct Revit 2023 API class and method names
- Include inline comments that explain WHAT each line does and WHY
- Be self-contained and demonstrate the concept fully
- Assume the reader knows Python but has never used the Revit API

Return ONLY the Python code. No prose outside code comments. No markdown fences.
If a concept requires showing multiple related examples, use clearly labeled comment sections."""

# ── Stage 1 prompts: Revit API object model ──────────────────────────────────
# Ordered from most fundamental to most specific.
# Each prompt teaches one concept. The model should be able to answer
# "what is X" and "how do I use X" for all of these after Stage 1 training.

STAGE1_PROMPTS = [

    # ── Imports and references ─────────────────────────────────────────────
    "Show the complete standard import block for Revit API Python, explaining what each line does and why it is needed",
    "Show all clr.AddReference calls needed for working with MEP elements (mechanical, electrical, plumbing) in the Revit API, with all corresponding namespace imports",
    "Explain the difference between RevitAPI and RevitAPIUI references and when each is needed",

    # ── Core document model ────────────────────────────────────────────────
    "Explain what a Revit Document object is and show how to access basic document properties like title, path, and project information",
    "Explain the Revit API Application and UIApplication objects and how they relate to Document and UIDocument",
    "Show how to get the active document, active view, and active selection in the Revit API",

    # ── FilteredElementCollector ───────────────────────────────────────────
    "Explain FilteredElementCollector in detail — what it is, how it works, and show five different ways to use it to collect different types of elements",
    "Explain the difference between OfClass() and OfCategory() filters in FilteredElementCollector, with examples of when to use each",
    "Explain WhereElementIsNotElementType() — what it does, why it is almost always needed, and what happens if you forget it",
    "Show how to chain multiple filters on FilteredElementCollector, including ElementCategoryFilter, ElementClassFilter, and BoundingBoxIntersectsFilter",
    "Show how to use FilteredElementCollector with a View parameter to collect only elements visible in a specific view",

    # ── Elements and ElementId ─────────────────────────────────────────────
    "Explain what an Element is in the Revit API and show how to get its category, name, ElementId, and basic properties",
    "Explain ElementId — what it is, how it is used to reference elements, and show how to retrieve an Element from its ElementId using doc.GetElement()",
    "Explain the difference between Element instances and Element types (ElementType/FamilySymbol) in the Revit API, with code showing how to get the type from an instance",

    # ── Parameters ────────────────────────────────────────────────────────
    "Explain the Revit API Parameter class — show how to get a parameter by BuiltInParameter, by name using LookupParameter, and how to read its value depending on StorageType",
    "Show how to read and write different parameter storage types in the Revit API: Double, Integer, String, and ElementId, with correct methods for each",
    "Explain BuiltInParameter — what it is, how to use it, and show examples of commonly used built-in parameters for walls, rooms, levels, and MEP elements",
    "Show how to get all parameters on an element and iterate through them, checking their name, value, and whether they are read-only",

    # ── Transactions ──────────────────────────────────────────────────────
    "Explain the Revit API Transaction class — what it is, why it is required for modifications, and show the correct pattern for opening, committing, and rolling back a transaction",
    "Show the correct transaction pattern with error handling using try/except/finally to ensure transactions are always closed even if an exception occurs",
    "Explain TransactionGroup and SubTransaction — when to use them and show an example",

    # ── Levels and grids ──────────────────────────────────────────────────
    "Show how to collect all Levels in a Revit document, get their elevation, and find a level by name",
    "Show how to get the level associated with a floor-hosted element and how to filter elements by level",

    # ── Walls, floors, ceilings ───────────────────────────────────────────
    "Show how to collect all walls in a Revit document, get their type, length, and base/top constraints",
    "Show how to get the wall type, compound structure layers, and material of each layer for a wall element",

    # ── MEP elements ──────────────────────────────────────────────────────
    "Show how to collect all ducts in a Revit MEP model using FilteredElementCollector with BuiltInCategory.OST_DuctCurves, and get their size, system, and level",
    "Show how to collect all pipes in a Revit MEP model and get their diameter, system type, and insulation thickness",
    "Show how to collect all mechanical equipment using BuiltInCategory.OST_MechanicalEquipment and get their family name, type name, and hosted level",
    "Show how to collect all air terminals and get their flow parameter value using BuiltInParameter",
    "Show how to get all electrical fixtures and panels using appropriate BuiltInCategory values",
    "Explain MEP connectors in the Revit API — show how to get connectors from a duct or pipe element and read their properties",
    "Show how to traverse an MEP system (MechanicalSystem or PipingSystem) from a root element through all connected elements",

    # ── Rooms and spaces ──────────────────────────────────────────────────
    "Show how to collect all rooms in a Revit document and get their name, number, area, volume, and level",
    "Show how to find which room a given XYZ point is located in using doc.GetRoomAtPoint()",
    "Show how to get all elements inside a room using a BoundingBoxIntersectsFilter combined with room boundary curves",

    # ── Families ──────────────────────────────────────────────────────────
    "Explain the Family, FamilySymbol (type), and FamilyInstance hierarchy in the Revit API with code showing how to navigate between them",
    "Show how to get all loaded families in a document, filter by category, and get their types",
    "Show how to get all instances of a specific family type using FilteredElementCollector with a FamilyInstanceFilter",

    # ── Views and sheets ──────────────────────────────────────────────────
    "Show how to collect all views in a Revit document, filter out templates, and group them by ViewType",
    "Show how to collect all sheets and for each sheet get the views placed on it using Viewport",
    "Show how to get all view templates and apply a view template to a view programmatically",

    # ── Geometry and coordinates ───────────────────────────────────────────
    "Explain the XYZ class in the Revit API — coordinate system, internal units (feet), and show common operations: distance, midpoint, normalize",
    "Show how to get the bounding box of an element using get_BoundingBox() and how to use it to find nearby elements",
    "Show how to get the location of an element — LocationPoint vs LocationCurve — and extract the point or curve",

    # ── Linked models ─────────────────────────────────────────────────────
    "Explain RevitLinkInstance — what it is, show how to get all linked models in a document, access each link's document, and get its transform",
    "Show how to collect elements from a linked Revit model and transform their coordinates to the host model coordinate system",

    # ── Worksets ──────────────────────────────────────────────────────────
    "Show how to get the workset of an element and how to filter elements by workset in a workshared Revit document",

    # ── Units ─────────────────────────────────────────────────────────────
    "Explain Revit API internal units — everything is stored in feet internally — and show how to convert between internal units and display units using UnitUtils",
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
    for i, prompt in enumerate(STAGE1_PROMPTS):
        if prompt in existing:
            print(f"  [{i+1}/{len(STAGE1_PROMPTS)}] Skipping (already done): {prompt[:60]}...")
            continue

        print(f"  [{i+1}/{len(STAGE1_PROMPTS)}] {prompt[:70]}...")
        completion = generate_pair(prompt)

        if completion and len(completion) > 100:
            record = {
                "stage": 1,
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
            print(f"    Skipped — response too short or failed")

        time.sleep(0.5)

    total = sum(1 for _ in open(OUTPUT_FILE))
    print(f"\nStage 1 complete. New pairs: {new_count} | Total: {total}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
