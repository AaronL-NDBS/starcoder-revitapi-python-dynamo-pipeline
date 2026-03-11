# tools/add_training_pair.py
# Builds hand-crafted training pairs from Dynamo graph screenshots.
# Uses mistral-small3.1 (vision) to analyse screenshots and guess intent,
# then mistral to generate the Python script.

import json
import base64
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_FILE = "dataset/hand_crafted.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"
VISION_MODEL = "mistral-small3.1"   # vision — analyses screenshots
CODE_MODEL = "mistral"              # code generation
Path("dataset").mkdir(exist_ok=True)

# ── Prompts ───────────────────────────────────────────────────────────────────

VISION_SYSTEM = """You are an expert in Autodesk Dynamo and the Revit API.
You will be shown a screenshot of a Dynamo node graph, along with the script filename.

Your job is to describe what the graph does in plain English, structured as:
1. What are the inputs? (types and what they represent)
2. What does the graph do step by step?
3. What does it output?
4. In one sentence: what is the overall purpose of this script?

Be specific about Revit API concepts (categories, parameters, collectors, etc.)
where you can identify them from the node names."""

CODE_SYSTEM = """You convert Dynamo graph descriptions into Dynamo Python node scripts.
Rules:
- Use IN[] for inputs and OUT for output — match the number and order of inputs described
- Include all necessary clr.AddReference calls
- Use from Autodesk.Revit.DB import * and other relevant namespaces
- Target CPython3 (Dynamo 2.x)
- Keep scripts single-purpose and self-contained
- Do not use libraries unavailable in the Dynamo Python environment
- Return ONLY the Python code, no explanation, no markdown fences"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyse_screenshot(image_path: str, filename: str) -> str:
    """Send screenshot to vision model and get a description of what the graph does."""
    image_b64 = encode_image(image_path)
    ext = Path(image_path).suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"

    r = requests.post(OLLAMA_URL, json={
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Script filename: {filename}\n\nPlease analyse this Dynamo graph screenshot."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "stream": False
    }, timeout=120)
    return r.json()["message"]["content"].strip()

def generate_python(description: str) -> str:
    """Ask code model to write Python based on the graph description."""
    r = requests.post(OLLAMA_URL, json={
        "model": CODE_MODEL,
        "messages": [
            {"role": "system", "content": CODE_SYSTEM},
            {"role": "user", "content": f"Write a Dynamo Python node that does the following:\n\n{description}"}
        ],
        "stream": False
    }, timeout=120)
    code = r.json()["message"]["content"].strip()
    # strip markdown fences if model added them anyway
    import re
    code = re.sub(r'^```(?:python)?\s*\n', '', code)
    code = re.sub(r'\n```\s*$', '', code)
    return code.strip()

def validate(completion: str) -> list:
    warnings = []
    if "OUT" not in completion:
        warnings.append("  WARNING: No OUT = found")
    if "clr" not in completion:
        warnings.append("  WARNING: No clr reference found")
    if "IN[" not in completion:
        warnings.append("  WARNING: No IN[] inputs found")
    if "Autodesk" not in completion and "RevitAPI" not in completion:
        warnings.append("  WARNING: No Revit API imports found")
    return warnings

def save_pair(prompt: str, completion: str, origin: str = ""):
    record = {
        "source": "hand_crafted",
        "prompt": prompt.strip(),
        "completion": completion.strip(),
        "date_added": datetime.now().strftime("%Y-%m-%d"),
    }
    if origin:
        record["origin"] = origin
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    return sum(1 for _ in open(OUTPUT_FILE))

# ── Main loop ─────────────────────────────────────────────────────────────────

print("=" * 60)
print(" Dynamo Training Pair Builder")
print(f" Vision model : {VISION_MODEL}")
print(f" Code model   : {CODE_MODEL}")
print(f" Output       : {OUTPUT_FILE}")
print("=" * 60)

while True:
    print("\nOptions:")
    print("  1 - Analyse a screenshot (recommended)")
    print("  2 - Describe a graph manually (no screenshot)")
    print("  3 - Paste Python directly")
    print("  q - Quit")
    choice = input("\nChoice: ").strip().lower()

    if choice == "q":
        break

    # ── Option 1: Screenshot workflow ─────────────────────────────────────────
    if choice == "1":
        image_path = input("\nDrag and drop screenshot here (or paste full path): ").strip().strip('"')
        if not Path(image_path).exists():
            print("  File not found. Check the path and try again.")
            continue

        filename = Path(image_path).stem  # filename without extension
        print(f"\n  Filename detected: {filename}")
        print("  Sending to vision model...\n")

        description = analyse_screenshot(image_path, filename)

        print("── Vision model's interpretation ──────────────────────────")
        print(description)
        print("───────────────────────────────────────────────────────────")

        print("\nIs this description correct?")
        print("  y - Yes, generate Python from this")
        print("  e - Edit the description first")
        print("  x - Discard")
        action = input("\nAction: ").strip().lower()

        if action == "x":
            continue

        if action == "e":
            print("\nEdit the description below.")
            print("Paste your corrected version. Type END on a new line when done:\n")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            description = "\n".join(lines).strip()

        # build the one-line prompt from the description
        print("\nGenerating Python script from description...")
        completion = generate_python(description)

        print("\n── Generated Python ────────────────────────────────────────")
        print(completion)
        print("───────────────────────────────────────────────────────────")

        warnings = validate(completion)
        if warnings:
            for w in warnings:
                print(w)

        print("\nOptions:")
        print("  s - Save")
        print("  e - Edit completion before saving")
        print("  r - Regenerate Python")
        print("  x - Discard")
        action = input("\nAction: ").strip().lower()

        if action == "r":
            completion = generate_python(description)
            print("\n── Regenerated ─────────────────────────────────────────────")
            print(completion)
            print("───────────────────────────────────────────────────────────")
            action = input("\nSave? (s/x): ").strip().lower()

        if action == "e":
            print("\nPaste edited Python. Type END on a new line when done:\n")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            completion = "\n".join(lines).strip()

        if action in ("s", "e"):
            # use the last line of description as the prompt
            prompt_line = description.split("\n")[-1].strip()
            if not prompt_line or len(prompt_line) < 20:
                prompt_line = f"Dynamo Python node: {filename}"
            count = save_pair(prompt_line, completion, origin=filename)
            print(f"\n  Saved. Total hand-crafted pairs: {count}")

    # ── Option 2: Manual description ──────────────────────────────────────────
    elif choice == "2":
        print("\nDescribe what the script should do.")
        print("Press Enter twice when done:\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        description = "\n".join(lines).strip()
        if not description:
            continue

        print("\nGenerating Python...")
        completion = generate_python(description)

        print("\n── Generated Python ────────────────────────────────────────")
        print(completion)
        print("───────────────────────────────────────────────────────────")

        warnings = validate(completion)
        if warnings:
            for w in warnings:
                print(w)

        action = input("\nSave (s) / Edit (e) / Discard (x): ").strip().lower()
        if action == "e":
            print("\nPaste edited Python. Type END on a new line when done:\n")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            completion = "\n".join(lines).strip()

        if action in ("s", "e"):
            count = save_pair(description.split("\n")[0], completion)
            print(f"\n  Saved. Total hand-crafted pairs: {count}")

    # ── Option 3: Paste directly ───────────────────────────────────────────────
    elif choice == "3":
        print("\nEnter prompt (one line):\n")
        prompt = input().strip()

        print("\nPaste Python. Type END on a new line when done:\n")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        completion = "\n".join(lines).strip()

        warnings = validate(completion)
        if warnings:
            for w in warnings:
                print(w)
            if input("Save anyway? (y/n): ").strip().lower() != "y":
                continue

        count = save_pair(prompt, completion)
        print(f"\n  Saved. Total hand-crafted pairs: {count}")

print(f"\nDone. Dataset saved to {OUTPUT_FILE}")