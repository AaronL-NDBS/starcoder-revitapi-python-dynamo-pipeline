# Staged Training Philosophy

## The Core Analogy

StarCoder arrives at this project the way an experienced drafter arrives at
Revit after years in AutoCAD. It has deep, genuine expertise in its home
domain — Python syntax, code logic, algorithms, data structures — but zero
context for the world it's being asked to work in.

It doesn't know what a Wall is in this context. It doesn't know that Document
means a Revit project file, not a text document. It doesn't know that
FilteredElementCollector is the only reliable way to query elements, or that
you must open a Transaction before modifying anything, or that coordinates are
in feet regardless of your project units.

You learned Revit by building on your MEP and structural drawing background —
you already understood what ducts, pipes, walls, and levels *were* in the
physical world. You just needed to learn how Revit represents and organizes
them. StarCoder is in the same position: it understands what a Python class,
method, and object are. It just needs to learn what the Revit API's specific
classes, methods, and objects mean and how they relate to each other.

The training strategy follows the same onboarding path a new Revit user would
take — but delivered as code examples instead of tutorials.

---

## Why Stages Matter

Training everything at once produces a model that has seen all the patterns
but understands none of them deeply. Staged training means each phase builds
on a foundation that was established in the previous one.

A model that doesn't understand the Revit API object model cannot reliably
generate Dynamo Python nodes — it will produce code that looks right but uses
methods that don't exist, references namespaces incorrectly, or misses required
transaction handling. Getting Stage 1 right makes every subsequent stage
more effective.

---

## The Four Stages

```
Stage 1 — Revit API Core
    What: The Revit API object model, classes, methods, relationships
    Goal: StarCoder understands what Revit objects ARE and how to work with them
    Source: SDK documentation, CHM reference, SDK C# samples (translated)
    No Dynamo yet. Pure Revit API Python.

         ↓

Stage 2 — Dynamo Concepts
    What: How Dynamo thinks — nodes, wires, data flow, lacing, lists
    Goal: StarCoder understands Dynamo's execution model and conventions
    Source: Dynamo Primer, forum conceptual posts, node documentation
    No code yet. Conceptual understanding of the environment.

         ↓

Stage 3 — Dynamo Python + Revit API
    What: The IN[]/OUT pattern, Dynamo's Python environment, CPython3 context
    Goal: StarCoder can write single-purpose Python nodes that correctly
          interface with the Revit API inside the Dynamo environment
    Source: Forum Python nodes, GitHub Dynamo scripts, hand-crafted pairs

         ↓

Stage 4 — Integration and Polish
    What: Multi-node workflows, chaining patterns, real-world use cases
    Goal: StarCoder generates reliable starting points for complete workflows
    Source: Your own validated graphs, complex real-world examples
```

---

## Stage 1 — Revit API Core

**What StarCoder needs to learn:**

The Revit API is a .NET framework exposed to Python via IronPython (legacy) or
CPython through `clr` (current). Every interaction with a Revit document goes
through a strict object hierarchy:

```
Application
  └── Document (the .rvt project file)
        ├── Elements (walls, floors, ducts, pipes, rooms, families...)
        │     ├── Parameters (built-in and shared)
        │     ├── Geometry
        │     └── ElementId (unique identifier)
        ├── Views (plans, sections, 3D, sheets)
        ├── Levels
        └── Transactions (required for any modification)
```

**Key concepts to establish in Stage 1 data:**

- `clr.AddReference` and namespace imports
- `FilteredElementCollector` — the only reliable query mechanism
- `BuiltInCategory` and `BuiltInParameter` enumerations
- `ElementId` and `doc.GetElement()`
- `Parameter`, `get_Parameter()`, `LookupParameter()`
- `Transaction` — required wrapper for all document modifications
- `XYZ` — coordinate system, units (always internal feet)
- Element vs ElementType distinction
- Linked models (`RevitLinkInstance`)
- MEP-specific namespaces and classes

**Dataset target:** 80–120 foundational pairs
**Script:** `tools/generate_stage1_pairs.py`

---

## Stage 2 — Dynamo Concepts

**What StarCoder needs to learn:**

Dynamo is a visual programming environment that executes as a data flow graph.
Understanding its conventions matters even for Python node generation because:

- Data flows left to right through wired connections
- Every node has typed inputs and outputs
- List lacing (shortest, longest, cross-product) affects how multi-input nodes run
- Dynamo manages the document and transaction context — Python nodes inherit this
- The `IN` list maps to node input ports in order: `IN[0]`, `IN[1]`, etc.
- `OUT` is a single value or list returned to the next node

**Key concepts for Stage 2 data:**

- The `IN[]/OUT` pattern and its relationship to node ports
- How Dynamo passes the Document, UIDocument, and UIApplication
- Transaction handling in Dynamo context (Dynamo manages the transaction)
- List vs single value outputs
- Why node inputs should be typed explicitly in comments
- Common Dynamo node patterns and their Python equivalents

**Dataset target:** 30–50 conceptual pairs
**Script:** `tools/generate_stage2_pairs.py`

---

## Stage 3 — Dynamo Python + Revit API

**What StarCoder needs to learn:**

This is where Stage 1 and Stage 2 combine. A correctly structured Dynamo Python
node looks like this:

```python
# Standard imports — always required
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

# Dynamo provides the document via IN[0] by convention
# Additional inputs follow: IN[1], IN[2], etc.
doc = IN[0]
level_name = IN[1]   # str — name of the target level

# --- Logic ---
levels = FilteredElementCollector(doc)\
    .OfClass(Level)\
    .ToElements()

target = next((l for l in levels if l.Name == level_name), None)

# OUT returns a single value or list to the next node
OUT = target
```

**Key patterns for Stage 3 data:**

- Standard import block structure
- `IN[]` typing conventions (always comment what each input expects)
- When Dynamo handles transactions vs when you need to open one
- Error handling that returns meaningful output rather than crashing
- Single-purpose node design
- Chaining patterns (output of one node feeds input of next)

**Dataset target:** 200–400 usage pairs
**Scripts:** `tools/generate_stage3_pairs.py`, `tools/add_training_pair.py`,
             scraping pipeline (`pipeline.py`)

---

## Stage 4 — Integration

**What StarCoder needs to learn:**

Real workflows chain multiple nodes together. Stage 4 teaches the model to
think in terms of complete workflows — what a node needs to receive, what it
should return, and how it connects to adjacent nodes.

**Key patterns for Stage 4 data:**

- Multi-node workflow descriptions with each node's role explained
- Input/output type contracts between chained nodes
- Your own validated production graphs converted to Python
- MEP-specific workflows: system traversal, clash detection, parameter bulk-edit
- Error handling at the workflow level

**Dataset target:** 50–100 complex pairs
**Script:** `tools/add_training_pair.py` (manual, using your own graphs)

---

## Running the Staged Pipeline

Each stage generates its own JSONL file in `dataset/stages/`. The full dataset
is assembled from all stages before fine-tuning.

```powershell
# Generate foundational data for all stages
python tools/generate_stage1_pairs.py
python tools/generate_stage2_pairs.py
python tools/generate_stage3_pairs.py

# Run the web scraping pipeline (Stage 3 data)
python pipeline.py

# Add your own graphs (Stage 3/4 data)
python tools/add_training_pair.py

# Assemble final dataset from all stages
python tools/assemble_dataset.py

# Fine-tune
python finetune.py
```

See the individual stage documents in `stages/` for detail on each phase.
See `FINETUNING.md` for the full fine-tuning workflow.

---

## A Note on Iteration

The first fine-tuned model will not be perfect. Treat it as a baseline to
evaluate against. The most effective improvement loop is:

1. Run the model on prompts you know the correct answer to
2. Identify the category of failure (wrong API, wrong pattern, wrong imports)
3. Add more training pairs that specifically address that failure category
4. Re-fine-tune and compare

Stage 1 failures (wrong API methods, hallucinated classes) → add Stage 1 pairs
Stage 3 failures (wrong IN/OUT structure, missing imports) → add Stage 3 pairs
Stage 4 failures (incomplete workflows, wrong chaining) → add Stage 4 pairs
