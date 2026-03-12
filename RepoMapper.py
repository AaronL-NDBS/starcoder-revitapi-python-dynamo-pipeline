import os
from collections import Counter

COLLAPSE_THRESHOLD = 30

def print_repo_structure(startpath, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', '.venv', '__pycache__', '.idea', '.vscode'}

    print(f"Structure for: {os.path.abspath(startpath)}\n")

    for root, dirs, files in os.walk(startpath):
        dirs[:] = sorted(d for d in dirs if d not in exclude_dirs)

        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")

        sub_indent = ' ' * 4 * (level + 1)

        # Count files by extension
        ext_counts = Counter()
        for f in files:
            ext = os.path.splitext(f)[1].lower() or '(no extension)'
            ext_counts[ext] += 1

        # Decide which extensions to collapse
        collapse_exts = {ext for ext, count in ext_counts.items() if count >= COLLAPSE_THRESHOLD}

        # Print individual files for non-collapsed extensions
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower() or '(no extension)'
            if ext not in collapse_exts:
                print(f"{sub_indent}{f}")

        # Print summary lines for collapsed extensions
        for ext in sorted(collapse_exts):
            print(f"{sub_indent}[{ext_counts[ext]} {ext} files]")

if __name__ == "__main__":
    print_repo_structure('.')