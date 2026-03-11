#Configuration file
from dotenv import load_dotenv
import os

load_dotenv()

CONFIG = {
    "stackoverflow_key": os.getenv("STACKOVERFLOW_KEY", ""),
    "github_token": os.getenv("GITHUB_TOKEN", ""),
    "anthropic_key": os.getenv("ANTHROPIC_KEY", ""),
    "use_llm_judge": True,
    "llm_judge_model": "local",
    "ollama_judge_model": "mistral",
    "min_quality_score": 6,
    "output_dir": "dataset",
    "rate_limit_delay": 1.0,
}