# Fine-Tuning Guide

QLoRA fine-tuning of StarCoder2-7b on the Revit API / Dynamo Python dataset,
targeting local inference via Ollama on consumer hardware.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| GPU VRAM | 8GB | 16GB |
| System RAM | 16GB | 32GB |
| Disk space | 20GB free | 40GB free |
| CUDA version | 11.8 | 12.1 |

This guide is written for an **RTX 4070 Ti Super (16GB VRAM)** with CUDA 12.1.
The 7b model with 4-bit quantization uses approximately 10–13GB VRAM during
training, leaving comfortable headroom on 16GB.

---

## Prerequisites

- Python 3.11 virtual environment with `requirements.txt` installed
- `dataset/final_dataset.jsonl` produced by `pipeline.py` (minimum 400 records)
- CUDA-enabled PyTorch verified (`torch.cuda.is_available()` returns `True`)

Verify your dataset is ready:

```powershell
# Should return 400 or more
Get-Content dataset\final_dataset.jsonl | Measure-Object -Line
```

---

## Step 1 — Verify the dataset

Before training, do a quick sanity check on the dataset:

```python
# run this as a one-off script
import json

records = []
with open("dataset/final_dataset.jsonl") as f:
    for line in f:
        records.append(json.loads(line))

print(f"Total records: {len(records)}")
print(f"\nSample prompt:\n{records[0]['prompt']}")
print(f"\nSample completion:\n{records[0]['completion'][:300]}")

# check completion lengths
lengths = [len(r["completion"]) for r in records]
print(f"\nCompletion length — min: {min(lengths)}, max: {max(lengths)}, avg: {sum(lengths)//len(lengths)}")
```

---

## Step 2 — Create the fine-tuning script

Create `finetune.py` in the project root:

```python
# finetune.py
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import os

# ── Configuration ────────────────────────────────────────────────────────────

MODEL_NAME = "bigcode/starcoder2-7b"
DATASET_PATH = "dataset/final_dataset.jsonl"
OUTPUT_DIR = "starcoder2-revit-finetuned"
MAX_SEQ_LENGTH = 1024      # increase to 2048 if VRAM allows
BATCH_SIZE = 1             # keep at 1 for 16GB VRAM
GRAD_ACCUM_STEPS = 8       # effective batch size = 8
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# ── 4-bit quantization config ────────────────────────────────────────────────

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# ── Load model and tokenizer ─────────────────────────────────────────────────

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print("Loading model in 4-bit...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)

# ── LoRA config ───────────────────────────────────────────────────────────────

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ── Dataset ───────────────────────────────────────────────────────────────────

dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

def format_record(record):
    """Format prompt/completion pair into a single training string."""
    return {
        "text": f"### Instruction:\n{record['prompt']}\n\n### Response:\n{record['completion']}"
    }

dataset = dataset.map(format_record)
print(f"Dataset loaded: {len(dataset)} records")

# ── Training arguments ────────────────────────────────────────────────────────

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM_STEPS,
    learning_rate=LEARNING_RATE,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    report_to="none",           # set to "tensorboard" if you want loss curves
    dataloader_pin_memory=False,
)

# ── Trainer ───────────────────────────────────────────────────────────────────

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    tokenizer=tokenizer,
)

# ── Train ─────────────────────────────────────────────────────────────────────

print("Starting training...")
trainer.train()

print("Saving model...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}/")
```

---

## Step 3 — Run fine-tuning

With your venv active:

```powershell
python finetune.py
```

**Expected runtime on RTX 4070 Ti Super:**

| Dataset size | Epochs | Estimated time |
|---|---|---|
| 400 records | 3 | ~1.5–2 hours |
| 800 records | 3 | ~3–4 hours |
| 1500 records | 3 | ~5–7 hours |

Monitor VRAM usage in a second terminal:

```powershell
# run in a separate PowerShell window
while ($true) { nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader; Start-Sleep 5 }
```

If you hit OOM (out of memory) errors, reduce `MAX_SEQ_LENGTH` from 1024 to 512
first, then reduce `LORA_R` from 16 to 8 if the problem persists.

---

## Step 4 — Convert to GGUF for Ollama

After training completes, convert the LoRA adapter output to GGUF format using
`llama.cpp`. Clone it once:

```powershell
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
pip install -r requirements.txt
```

Merge the LoRA adapter back into the base model first:

```python
# merge_lora.py — run this before conversion
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

model = AutoPeftModelForCausalLM.from_pretrained(
    "starcoder2-revit-finetuned",
    device_map="cpu",       # merge on CPU to avoid VRAM limits
)
merged = model.merge_and_unload()
merged.save_pretrained("starcoder2-revit-merged")

tokenizer = AutoTokenizer.from_pretrained("starcoder2-revit-finetuned")
tokenizer.save_pretrained("starcoder2-revit-merged")
print("Merge complete.")
```

Then convert to GGUF:

```powershell
cd llama.cpp
python convert_hf_to_gguf.py ..\starcoder2-revit-merged --outfile ..\starcoder2-revit.gguf --outtype q4_k_m
```

`q4_k_m` is the recommended quantization — good balance of size and quality.

---

## Step 5 — Load into Ollama

Create a `Modelfile` in the project root:

```
FROM ./starcoder2-revit.gguf

SYSTEM """You are a Dynamo Python node generator specializing in the Autodesk Revit API.
Generate single-purpose Python scripts using the IN[]/OUT pattern.
Each script should do one thing, be self-contained, and use correct Revit API calls.
Always include necessary clr references. Target Dynamo's CPython3 engine.
Do not use libraries unavailable in the Dynamo Python environment."""

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
```

Register and run it:

```powershell
ollama create starcoder2-revit -f Modelfile
ollama run starcoder2-revit
```

Test it immediately:

```
>>> Write a Dynamo Python node that gets all walls in the current model grouped by their wall type name
```

---

## Step 6 — Evaluate output quality

After loading into Ollama, run a quick manual evaluation against 10–15 prompts
you know the correct answer to from your own Revit experience. Score each on:

- Does it use `IN[]` and `OUT` correctly?
- Are the `clr.AddReference` calls correct?
- Does the Revit API usage match the actual API (not hallucinated methods)?
- Would it run without modification in a Dynamo Python node?

If quality is below expectations, the most effective lever is **more
hand-crafted training pairs** added to the dataset before re-running the
pipeline and fine-tuning again. See the `Hand-Crafted Data` section in
`README.md` for guidance.

---

## Troubleshooting

**`CUDA out of memory`**
Reduce `MAX_SEQ_LENGTH` to 512, then `LORA_R` to 8 if still failing.

**`bitsandbytes` CUDA errors on Windows**
Ensure you are using the venv Python 3.11, not system Python 3.14.
Run `python --version` inside the venv to confirm.

**Model downloads slowly**
StarCoder2-7b is ~14GB from Hugging Face. First run will take time depending
on your connection. It caches to `C:\Users\<you>\.cache\huggingface\`.

**`trust_remote_code` warning**
StarCoder2 requires `trust_remote_code=True`. This is expected and safe for
the official BigCode model.

**Loss not decreasing**
Check that your dataset has enough variety. If most records are near-identical
patterns, the model has nothing to learn. Increase dataset diversity before
re-training.