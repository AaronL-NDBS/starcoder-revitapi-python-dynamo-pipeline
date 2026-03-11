#LLM quality filter
import json, requests

RUBRIC = """You evaluate training data for a model that generates Revit API / Dynamo Python nodes.

A good record must:
- Be a Python script usable as a Dynamo node (uses IN[] for inputs, OUT for output)
- Use Revit API correctly (clr references, FilteredElementCollector patterns, etc.)
- Be self-contained and not truncated
- Be free of HTML or encoding garbage

Score as JSON only — no explanation outside the JSON:
{"relevance": 0-3, "correctness": 0-3, "completeness": 0-2, "clean": 0-2, "total": 0-10}"""

def score_local(prompt, completion, model="mistral"):
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": f"PROMPT:\n{prompt[:500]}\n\nCOMPLETION:\n{completion[:1200]}"}
        ],
        "stream": False
    })
    try:
        return json.loads(r.json()["message"]["content"])
    except:
        return None

def filter_dataset(input_file, output_file, min_score=6, use_local=True):
    kept, dropped = 0, 0
    with open(input_file) as f_in, open(output_file, "w") as f_out:
        for line in f_in:
            record = json.loads(line)
            score = score_local(record["prompt"], record["completion"])
            if score and score.get("total", 0) >= min_score:
                record["_score"] = score
                f_out.write(json.dumps(record) + "\n")
                kept += 1
            else:
                dropped += 1

    print(f"Filter done — kept: {kept}, dropped: {dropped}")