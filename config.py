#Configuration file
CONFIG = {
    "stackoverflow_key": "YOUR_KEY",
    "github_token": "YOUR_TOKEN",
    "anthropic_key": "YOUR_KEY",        # optional, for LLM judge
    "use_llm_judge": True,
    "llm_judge_model": "local",         # "local" = ollama, "claude" = API
    "ollama_judge_model": "mistral",
    "min_quality_score": 6,
    "output_dir": "dataset",
    "rate_limit_delay": 1.0,
}