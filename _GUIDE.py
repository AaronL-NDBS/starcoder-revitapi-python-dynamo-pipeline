import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

doc = IN[0]
# ... focused logic ...
OUT = result
```

Chained together, each node does one thing, takes typed inputs, returns typed outputs. This is a very learnable pattern for a fine-tuned model because it's highly consistent.

---

## Automated scraping pipeline

### Project structure
```
revit-starcoder-pipeline/
├── scrapers/
│   ├── discourse_scraper.py
│   ├── stackoverflow_scraper.py
│   ├── github_scraper.py
│   └── rvtapi_scraper.py
├── processing/
│   ├── cleaner.py
│   ├── formatter.py
│   └── evaluator.py
├── pipeline.py          # orchestrates everything
├── config.py
└── dataset/
    ├── raw/
    ├── cleaned/
    └── final_dataset.jsonl