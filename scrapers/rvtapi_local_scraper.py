# scrapers/rvtapi_local_scraper.py
import os
import subprocess
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
SEVEN_ZIP_PATH = Path(r"C:\Program Files\7-Zip\7z.exe")

SDK_PATHS = [
    Path(r"C:\Revit 2023 SDK"),
    Path(r"C:\Revit 2023.1 SDK")
]

# Paths relative to /scrapers
RAW_OUT_DIR = Path(r"..\dataset\raw\rvt_api_local")
TEMP_EXTRACT_DIR = Path(r"..\dataset\temp_chm_extract")

def check_dependencies():
    """Verify 7-Zip exists and prompt user if missing."""
    if not SEVEN_ZIP_PATH.exists():
        print("="*60)
        print("ERROR: 7-Zip not found!")
        print(f"Expected location: {SEVEN_ZIP_PATH}")
        print("-"*60)
        print("Please install 7-Zip or update the SEVEN_ZIP_PATH in this script.")
        print("Download: https://www.7-zip.org/")
        print("="*60)
        input("\nPress any key to exit...")
        sys.exit(1)
    
    # Check if at least one SDK path exists
    valid_sdks = [p for p in SDK_PATHS if p.exists()]
    if not valid_sdks:
        print("="*60)
        print("ERROR: No Revit SDK folders found!")
        for p in SDK_PATHS:
            print(f"  Missing: {p}")
        print("="*60)
        input("\nPress any key to exit...")
        sys.exit(1)
    
    return valid_sdks

def extract_with_7zip(chm_path, extract_to):
    print(f"\n--- Ripping {chm_path.parent.name} with 7-Zip ---")
    extract_to.mkdir(parents=True, exist_ok=True)
    
    # Command: 7z.exe x <archive> -o<output_dir> -y
    cmd = [str(SEVEN_ZIP_PATH), "x", str(chm_path), f"-o{extract_to}", "-y"]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"!! 7-Zip failed during extraction: {e}")
        return False

def harvest_file(html_path):
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        h1 = soup.find("h1")
        if not h1: return None
        
        name = h1.get_text(strip=True)
        ns_div = soup.find("div", {"id": "namespace"})
        summary_div = soup.find("div", {"class": "summary"})

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
            "namespace": ns_div.get_text(strip=True) if ns_div else "Autodesk.Revit.DB",
            "summary": summary_div.get_text(strip=True) if summary_div else "",
            "members": members[:50],
            "file": html_path.name
        }
    except:
        return None

def main():
    # 1. Run Verification
    valid_sdk_paths = check_dependencies()
    
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)

    for sdk in valid_sdk_paths:
        chm = sdk / "RevitAPI.chm"
        if not chm.exists():
            print(f"Skipping {sdk.name} - RevitAPI.chm not found in folder.")
            continue

        extract_path = TEMP_EXTRACT_DIR / sdk.name.replace(" ", "_")
        
        if extract_with_7zip(chm, extract_path):
            all_htm = list(extract_path.rglob("*.htm")) + list(extract_path.rglob("*.html"))
            
            # Filter for API GUIDs or standard member prefixes
            valid_files = [f for f in all_htm if len(f.stem) > 20 or f.stem.startswith(('T_', 'M_', 'P_'))]
            
            print(f"Found {len(valid_files)} valid API pages. Harvesting to JSON...")

            count = 0
            for f_path in valid_files:
                data = harvest_file(f_path)
                if data and (data['members'] or data['summary']):
                    folder = "Enums" if "Enumeration" in data['name'] else "Classes"
                    save_dir = RAW_OUT_DIR / sdk.name.replace(" ", "_") / folder
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    with open(save_dir / f"{f_path.stem}.json", "w", encoding="utf-8") as out:
                        json.dump(data, out, indent=2)
                    count += 1
                
                if count % 1000 == 0 and count > 0:
                    print(f"    Harvested {count}...")

    print("\n" + "="*60)
    print(f"SUCCESS! Local data harvested to: {RAW_OUT_DIR.resolve()}")
    print("="*60)
    input("\nProcessing complete. Press any key to exit...")

if __name__ == "__main__":
    main()