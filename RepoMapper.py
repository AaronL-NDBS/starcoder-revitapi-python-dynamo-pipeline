import os

def print_repo_structure(startpath, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', '.venv', '__pycache__', '.idea', '.vscode'}
    
    print(f"Structure for: {os.path.abspath(startpath)}\n")
    
    for root, dirs, files in os.walk(startpath):
        # Filter out excluded directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}📂 {os.path.basename(root)}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{sub_indent}📄 {f}")

if __name__ == "__main__":
    # Runs in the current directory
    print_repo_structure('.')