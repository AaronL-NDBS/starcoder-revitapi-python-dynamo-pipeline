# scrapers/rvtapi_local_harvester.py
import os
import subprocess
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
SDK_PATHS = [
    Path(r"C:\Revit 2023 SDK"),
    Path(r"C:\Revit 2023.1 SDK")
]
# Paths relative to the /scrapers folder
RAW_OUT_DIR = Path(r"..\dataset\raw\rvt_api_local")
TEMP_EXTRACT_DIR = Path(r"..\dataset\temp_chm_extract")

RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_chm(chm_path, extract_to):
    """Uses Windows hh.exe to decompile the CHM file."""
    print(f"\n--- Extracting {chm_path.parent.name} ---")
    if extract_to.exists():
        print(f"    Temp directory exists, skipping extraction...")
        return
    
    extract_to.mkdir(parents=True, exist_ok=True)
    try:
        # hh.exe -decompile <folder> <file>
        subprocess.run(["hh.exe", "-decompile", str(extract_to), str(chm_path)], check=True)
        print(f"    Extraction successful.")
    except Exception as e:
        print(f"    Extraction failed: {e}")

def harvest_file(html_path):
    """Extracts structured Revit API data from a local HTML file."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        # Check if this is a valid API member page
        h1 = soup.find("h1")
        if not h1: return None
        
        name = h1.text.strip()
        
        # Capture Namespace (Essential for StarCoder imports)
        ns_div = soup.find("div", {"id": "namespace"})
        namespace = ns_div.text.strip() if ns_div else "Autodesk.Revit.DB"

        # Capture Summary
        summary = ""
        summary_div = soup.find("div", {"class": "summary"})
        if summary_div: summary = summary_div.text.strip()

        # Members Table (Methods/Properties/Fields)
        members = []
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                members.append({
                    "n": cells[0].get_text(strip=True),
                    "d": cells[1].get_text(strip=True)
                })

        return {
            "name": name,
            "namespace": namespace,
            "summary": summary,
            "members": members[:50],
            "file": html_path.name
        }
    except:
        return None

def main():
    for sdk in SDK_PATHS:
        chm_file = sdk / "RevitAPI.chm"
        if not chm_file.exists():
            print(f"Skipping: {sdk.name} (CHM not found at {chm_file})")
            continue

        extract_path = TEMP_EXTRACT_DIR / sdk.name.replace(" ", "_")
        extract_chm(chm_file, extract_path)

        # Search for .htm AND .html recursively
        files = list(extract_path.rglob("*.htm")) + list(extract_path.rglob("*.html"))
        
        # Filter: Revit API docs usually have GUID-like names or start with T_ (Type), M_ (Method), P_ (Property)
        # We want to skip boilerplate like "html/toc.htm"
        valid_files = [f for f in files if len(f.stem) > 10 or f.stem.startswith(('T_', 'M_', 'P_'))]
        
        print(f"Found {len(valid_files)} valid API pages. Harvesting...")

        count = 0
        for f in valid_files:
            data = harvest_file(f)
            if data and (data['summary'] or data['members']):
                # Determine folder: Classes vs Enums
                folder = "Enums" if "Enumeration" in data['name'] else "Classes"
                out_path = RAW_OUT_DIR / sdk.name.replace(" ", "_") / folder
                out_path.mkdir(parents=True, exist_ok=True)
                
                with open(out_path / f"{f.stem}.json", "w", encoding="utf-8") as out_f:
                    json.dump(data, out_f, indent=2)
                count += 1
            
            if count % 1000 == 0 and count > 0:
                print(f"    Harvested {count} items...")

    print(f"\nSUCCESS: Harvested {RAW_OUT_DIR}")

if __name__ == "__main__":
    main()