# processing/cleaner.py
# Cleans raw scraped text before formatting into training pairs.

import re
from bs4 import BeautifulSoup


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    return BeautifulSoup(text, "html.parser").get_text(separator="\n")


def remove_encoding_garbage(text: str) -> str:
    """Remove non-ASCII sequences that indicate encoding bleed."""
    return re.sub(r'[^\x00-\x7F]+', ' ', text)


def remove_html_entities(text: str) -> str:
    """Catch any leftover HTML entities not handled by BeautifulSoup."""
    entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines; preserve indentation."""
    # collapse 3+ consecutive newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def strip_markdown_fences(text: str) -> str:
    """Remove ```python / ``` wrapper if the whole string is a fenced block."""
    text = text.strip()
    text = re.sub(r'^```(?:python)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    return text.strip()


def is_likely_dynamo_node(code: str) -> bool:
    """
    Heuristic check: does this code look like a Dynamo Python node?
    Requires at least one of the Dynamo scaffolding patterns.
    """
    has_clr = "import clr" in code or "clr.AddReference" in code
    has_in = re.search(r'IN\s*\[', code) is not None
    has_out = re.search(r'OUT\s*=', code) is not None
    return (has_clr or has_in) and has_out


def clean_code_block(code: str) -> str:
    """Full cleaning pass on a code completion candidate."""
    code = strip_markdown_fences(code)
    code = remove_encoding_garbage(code)
    code = remove_html_entities(code)
    code = normalize_whitespace(code)
    return code


def clean_prompt(text: str) -> str:
    """Full cleaning pass on a prompt/question string."""
    text = strip_html(text)
    text = remove_html_entities(text)
    text = remove_encoding_garbage(text)
    text = normalize_whitespace(text)
    return text[:800]  # hard cap consistent with formatter
