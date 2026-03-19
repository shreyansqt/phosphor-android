#!/usr/bin/env python3
"""
Sync Phosphor icons from GitHub and convert to Android Vector Drawables.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

PHOSPHOR_REPO = "phosphor-icons/core"
PHOSPHOR_BRANCH = "main"
PHOSPHOR_WEIGHT = "regular"
ICONS_DIR = Path(__file__).parent.parent / "icons"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"

def get_auth_token():
    """Get GitHub auth token from gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def list_phosphor_icons():
    """List available Phosphor icons from GitHub API using gh CLI."""
    print("Fetching Phosphor icon list...")
    
    # Try to find gh CLI
    gh_path = os.path.expanduser("~/bin/gh")
    if not os.path.exists(gh_path):
        gh_path = "gh"  # Fallback to PATH
    
    try:
        result = subprocess.run(
            [gh_path, "api", f"repos/{PHOSPHOR_REPO}/contents/raw/{PHOSPHOR_WEIGHT}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return []
        
        data = json.loads(result.stdout)
        return [item for item in data if item["name"].endswith(".svg")]
    except Exception as e:
        print(f"Failed to fetch icons list: {e}")
        return []

def download_svg(icon_name):
    """Download a single SVG from raw.githubusercontent."""
    url = f"https://raw.githubusercontent.com/{PHOSPHOR_REPO}/{PHOSPHOR_BRANCH}/raw/{PHOSPHOR_WEIGHT}/{icon_name}"
    
    with urlopen(url) as response:
        return response.read().decode('utf-8')



def svg_to_vd_string(svg_content):
    """Convert SVG string to Android Vector Drawable XML."""
    # Extract viewBox
    viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)
    viewbox = viewbox_match.group(1) if viewbox_match else "0 0 256 256"
    parts = viewbox.split()
    
    # Extract path data
    path_match = re.search(r'<path[^>]*d="([^"]*)"', svg_content)
    path_data = path_match.group(1) if path_match else ""
    
    # Generate VectorDrawable XML
    vd_xml = f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="{parts[2] if len(parts) > 2 else '256'}"
    android:viewportHeight="{parts[3] if len(parts) > 3 else '256'}">
  <path
      android:fillColor="@android:color/white"
      android:pathData="{path_data}" />
</vector>'''
    
    return vd_xml

def main():
    # Ensure icons directory exists
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # List and download icons
    svg_items = list_phosphor_icons()
    print(f"Found {len(svg_items)} icons")
    
    # Convert SVGs to Vector Drawables
    print("Converting to Vector Drawables...")
    registry_icons = []
    
    for item in svg_items:
        icon_name = item["name"].replace(".svg", "")
        
        try:
            svg_content = download_svg(item["name"])
            vd_xml = svg_to_vd_string(svg_content)
            vd_path = ICONS_DIR / f"phosphor_{icon_name}.xml"
            
            with open(vd_path, 'w') as f:
                f.write(vd_xml)
            
            registry_icons.append({
                "name": icon_name,
                "category": "icon",
                "keywords": [icon_name.replace("-", " ")]
            })
        except Exception as e:
            print(f"Failed to process {icon_name}: {e}")
    
    # Write registry
    print("Building registry...")
    registry = {"icons": registry_icons}
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Done! {len(registry_icons)} icons in {ICONS_DIR}")
    print(f"Registry: {REGISTRY_FILE}")

if __name__ == "__main__":
    main()
