# revit-starcoder-pipeline

An automated data scraping and preprocessing pipeline for fine-tuning 
[StarCoder2](https://huggingface.co/bigcode/starcoder2-7b) on Autodesk Revit API 
and Dynamo Python scripting patterns.

The goal is a locally-deployable code model (via Ollama) that reliably generates 
single-purpose Python nodes for use in Dynamo — focused on clean, efficient 
Revit API interactions using the `IN[]/OUT` pattern.

## Background
See [PHILOSOPHY.md](PHILOSOPHY.md) for the intent and approach behind this project.
If AI generated code/content rubs you the wrong way, please take the time to review this document.

## What this does

1. Scrapes Dynamo Forum, Stack Overflow, GitHub, and revitapidocs.com
2. Extracts and normalizes Python code examples into prompt/completion pairs
3. Filters low-quality records using an LLM judge (local via Ollama or Claude API)
4. Outputs a clean JSONL dataset ready for QLoRA fine-tuning

## License
Apache 2.0 — see [LICENSE](LICENSE)

## Data Notice
This pipeline scrapes publicly available forum and documentation content.
The resulting dataset is not included in this repository. Users are responsible
for complying with the terms of service of scraped sources.

## Dependencies
- StarCoder2 base model: BigCode/Apache 2.0
- Hugging Face transformers/peft/trl: Apache 2.0
- BeautifulSoup4: MIT
- Requests: Apache 2.0

## Target output pattern

The model is trained to generate nodes like:
```python
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

doc = IN[0]
# focused single-purpose logic
OUT = result
```

## Setup
```bash
pip install -r requirements.txt
```

Edit `config.py` with your API keys, then:
```bash
python pipeline.py
```

## Requirements

- Python 3.10+
- Ollama running locally (for LLM judge)
- Stack Overflow API key (free at stackapps.com)
- GitHub personal access token

## Data & legal notice

This pipeline collects publicly available data from third-party sources.
The **code in this repository** is licensed under Apache 2.0.

The **scraped dataset** is not included in this repo and is not covered by 
this license. Users are responsible for compliance with the terms of service 
of each source:
- [Dynamo Forum ToS](https://forum.dynamobim.com)
- [Stack Overflow ToS](https://stackoverflow.com/legal)
- [GitHub ToS](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- [Autodesk API Docs](https://www.autodesk.com/company/legal-notices-trademarks)

Respect `robots.txt` and rate limits. The pipeline includes delays for this purpose.

## Fine-tuning

See `FINETUNING.md` for QLoRA training instructions targeting StarCoder2-7b 
on consumer hardware.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for full terms.
```

---

## `requirements.txt`
```
requests>=2.31.0
beautifulsoup4>=4.12.0
anthropic>=0.25.0
datasets>=2.18.0
transformers>=4.40.0
peft>=0.10.0
trl>=0.8.6
bitsandbytes>=0.43.0
torch>=2.2.0
accelerate>=0.29.0