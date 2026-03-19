#!/usr/bin/env python3
"""
Sync Phosphor icons from GitHub and convert to Android Vector Drawables.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

PHOSPHOR_RELEASE = "https://github.com/phosphor-icons/core/releases/download/v5.2.0/phosphor-5.2.0.zip"
ICONS_DIR = Path(__file__).parent.parent / "icons"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"

def download_phosphor():
    """Download latest Phosphor icons from GitHub."""
    print("Downloading Phosphor icons...")
    zip_path = "/tmp/phosphor.zip"
    
    with urlopen(PHOSPHOR_RELEASE) as response:
        with open(zip_path, 'wb') as out:
            out.write(response.read())
    
    return zip_path

def extract_svgs(zip_path):
    """Extract SVGs from the Phosphor zip."""
    print("Extracting SVGs...")
    extract_dir = "/tmp/phosphor-extract"
    os.makedirs(extract_dir, exist_ok=True)
    
    with ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    
    # Find regular weight SVGs (Phosphor naming: icon-name.svg)
    svg_dir = Path(extract_dir) / "phosphor-5.2.0" / "regular"
    return list(svg_dir.glob("*.svg"))

def convert_svg_to_vd(svg_path):
    """
    Convert SVG to Android Vector Drawable.
    Simple conversion: extract viewBox and path data.
    """
    with open(svg_path, 'r') as f:
        content = f.read()
    
    # Extract viewBox
    viewbox_match = re.search(r'viewBox="([^"]+)"', content)
    viewbox = viewbox_match.group(1) if viewbox_match else "0 0 256 256"
    
    # Extract path data (assume single path for simplicity)
    path_match = re.search(r'<path[^>]*d="([^"]*)"', content)
    path_data = path_match.group(1) if path_match else ""
    
    # Generate VectorDrawable XML
    vd_xml = f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="{viewbox.split()[2]}"
    android:viewportHeight="{viewbox.split()[3]}"
    android:tint="?attr/colorControlNormal">
  <path
      android:fillColor="@android:color/white"
      android:pathData="{path_data}" />
</vector>'''
    
    return vd_xml

def build_registry(svg_files):
    """Build icons.json registry."""
    registry = {"icons": []}
    
    for svg_file in sorted(svg_files):
        icon_name = svg_file.stem
        registry["icons"].append({
            "name": icon_name,
            "category": "icon",
            "keywords": [icon_name.replace("-", " ")]
        })
    
    return registry

def main():
    # Ensure icons directory exists
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download and extract
    zip_path = download_phosphor()
    svg_files = extract_svgs(zip_path)
    
    print(f"Found {len(svg_files)} icons")
    
    # Convert SVGs to Vector Drawables
    print("Converting to Vector Drawables...")
    for svg_file in svg_files:
        icon_name = svg_file.stem
        vd_xml = convert_svg_to_vd(svg_file)
        vd_path = ICONS_DIR / f"phosphor_{icon_name}.xml"
        
        with open(vd_path, 'w') as f:
            f.write(vd_xml)
    
    # Build registry
    print("Building registry...")
    registry = build_registry(svg_files)
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Done! {len(svg_files)} icons in {ICONS_DIR}")
    print(f"Registry: {REGISTRY_FILE}")

if __name__ == "__main__":
    main()
