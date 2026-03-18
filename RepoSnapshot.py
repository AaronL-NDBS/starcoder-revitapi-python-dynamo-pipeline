"""
repo_snapshot.py
Dumps a structured JSON snapshot of the repository for AI review.
Includes: directory tree, file metadata, and contents of all script files.
Run from the repo root. Output: repo_snapshot.json
"""

import json
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

# Extensions whose contents will be included verbatim
CONTENT_EXTENSIONS = {".py", ".yaml", ".yml", ".md", ".txt", ".bat"}

# Filenames to skip entirely
SKIP_FILES = {
    "repo_snapshot.py",
    "repo_snapshot.json",
    "RepoMapper.py",
    ".gitignore",
    ".gitattributes",
}

# Directory NAMES (not paths) to skip entirely — matched against entry.name only
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".continue",
    ".vscode",
    "temp_chm_extract",
}

# Directory NAMES whose contents are collapsed to a file-count summary
# — avoids listing thousands of SDK records individually
COLLAPSE_DIRS = {
    "Classes",
    "Enums",
    "cloned_repos",
}

# Max file size to read content (bytes)
MAX_CONTENT_BYTES = 100_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def should_include_content(path: Path) -> bool:
    if path.suffix not in CONTENT_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > MAX_CONTENT_BYTES:
            return False
    except OSError:
        return False
    return True


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[READ ERROR: {e}]"


def count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    except Exception:
        return -1


def summarise_dir(path: Path) -> dict:
    """Count files by extension without recursing into the tree output."""
    counts: dict[str, int] = {}
    try:
        for f in path.rglob("*"):
            if f.is_file():
                ext = f.suffix or "(no ext)"
                counts[ext] = counts.get(ext, 0) + 1
    except PermissionError:
        pass
    total = sum(counts.values())
    return {
        "type": "directory",
        "name": path.name,
        "collapsed": True,
        "reason": "bulk data directory — summarised only",
        "total_files": total,
        "file_counts_by_extension": dict(sorted(counts.items())),
    }


# ── Tree builder ──────────────────────────────────────────────────────────────

def build_tree(root: Path) -> dict:
    node = {
        "type": "directory",
        "name": root.name,
        "children": [],
    }

    try:
        # dirs first, then files, each group sorted alphabetically
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return node

    for entry in entries:
        if entry.is_dir():
            name = entry.name
            if name in SKIP_DIRS:
                node["children"].append({
                    "type": "directory",
                    "name": name,
                    "skipped": True,
                    "reason": "excluded from snapshot",
                })
            elif name in COLLAPSE_DIRS:
                node["children"].append(summarise_dir(entry))
            else:
                node["children"].append(build_tree(entry))

        elif entry.is_file():
            if entry.name in SKIP_FILES:
                continue

            try:
                size = entry.stat().st_size
            except OSError:
                size = -1

            file_node: dict = {
                "type": "file",
                "name": entry.name,
                "extension": entry.suffix,
                "size_bytes": size,
            }

            if should_include_content(entry):
                file_node["lines"] = count_lines(entry)
                file_node["content"] = read_file(entry)
            else:
                file_node["content_included"] = False
                if entry.suffix == ".jsonl":
                    file_node["skip_reason"] = "jsonl data file"
                elif entry.suffix == ".json":
                    file_node["skip_reason"] = "json data file"
                elif size > MAX_CONTENT_BYTES:
                    file_node["skip_reason"] = f"file too large ({size:,} bytes)"
                else:
                    file_node["skip_reason"] = "binary or non-script file"

            node["children"].append(file_node)

    return node


# ── Stats collector ───────────────────────────────────────────────────────────

def collect_stats(root: Path) -> dict:
    """Walk the same subset of files that build_tree visits."""
    total_files = 0
    total_dirs = 0
    py_files = 0
    jsonl_files = 0
    content_files = 0

    def _walk(path: Path):
        nonlocal total_files, total_dirs, py_files, jsonl_files, content_files
        try:
            entries = list(path.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir():
                name = entry.name
                if name in SKIP_DIRS or name in COLLAPSE_DIRS:
                    continue
                total_dirs += 1
                _walk(entry)
            elif entry.is_file():
                if entry.name in SKIP_FILES:
                    continue
                total_files += 1
                if entry.suffix == ".py":
                    py_files += 1
                elif entry.suffix == ".jsonl":
                    jsonl_files += 1
                if should_include_content(entry):
                    content_files += 1

    _walk(root)
    return {
        "total_files": total_files,
        "total_directories": total_dirs,
        "python_files": py_files,
        "jsonl_data_files": jsonl_files,
        "files_with_content_included": content_files,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    root = Path(__file__).parent.resolve()
    output_path = root / "repo_snapshot.json"

    print(f"Scanning: {root}")
    print("Building tree...")
    tree = build_tree(root)

    print("Collecting stats...")
    stats = collect_stats(root)

    snapshot = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "repo_root": str(root),
            "purpose": (
                "AI review snapshot — full file tree and script contents for "
                "the starcoder-revitapi-python-dynamo-pipeline project. "
                "Script files (.py, .yaml, .md, .bat, .txt) are included verbatim. "
                "Data files (.jsonl, .json) listed without content. "
                "Bulk SDK directories (Classes/, Enums/) collapsed to file counts."
            ),
            "content_extensions_included": sorted(CONTENT_EXTENSIONS),
            "skipped_directories": sorted(SKIP_DIRS),
            "collapsed_directories": sorted(COLLAPSE_DIRS),
            "stats": stats,
        },
        "tree": tree,
    }

    print(f"Writing {output_path.name}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"\nDone. {output_path.name} — {size_kb:.1f} KB")
    print(f"  Total files scanned:    {stats['total_files']}")
    print(f"  Python files:           {stats['python_files']}")
    print(f"  Files with content:     {stats['files_with_content_included']}")
    print(f"  JSONL data files:       {stats['jsonl_data_files']} (listed, no content)")


if __name__ == "__main__":
    main()
