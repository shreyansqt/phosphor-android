#!/usr/bin/env python3
"""
Sync Phosphor icons from GitHub and convert to Android Vector Drawables.
"""

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from zipfile import ZipFile

PHOSPHOR_REPO = "phosphor-icons/core"
PHOSPHOR_BRANCH = "main"
PHOSPHOR_WEIGHT = "regular"
ICONS_DIR = Path(__file__).parent.parent / "icons"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"

def download_phosphor_zip():
    """Download Phosphor repo as ZIP."""
    print("Downloading Phosphor icons repo...")
    zip_url = f"https://github.com/{PHOSPHOR_REPO}/archive/{PHOSPHOR_BRANCH}.zip"
    zip_path = "/tmp/phosphor-core.zip"
    
    try:
        urllib.request.urlretrieve(zip_url, zip_path)
        print(f"Downloaded to {zip_path}")
        return zip_path
    except Exception as e:
        print(f"Failed to download: {e}")
        return None

def extract_svgs_from_zip(zip_path):
    """Extract SVG files from the ZIP."""
    print("Extracting SVGs from ZIP...")
    extract_dir = "/tmp/phosphor-extract"
    os.makedirs(extract_dir, exist_ok=True)
    
    with ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    
    # Find the SVG directory
    svg_dir = Path(extract_dir) / "core-main" / "raw" / PHOSPHOR_WEIGHT
    if not svg_dir.exists():
        svg_dir = Path(extract_dir) / f"{PHOSPHOR_REPO.split('/')[-1]}-{PHOSPHOR_BRANCH}" / "raw" / PHOSPHOR_WEIGHT
    
    if svg_dir.exists():
        return list(svg_dir.glob("*.svg"))
    else:
        print(f"SVG directory not found at {svg_dir}")
        return []

def svg_to_vd_string(svg_content):
    """Convert SVG string to Android Vector Drawable XML."""
    # Normalize whitespace
    svg_content = re.sub(r'\s+', ' ', svg_content)
    
    # Extract viewBox
    viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)
    viewbox = viewbox_match.group(1) if viewbox_match else "0 0 256 256"
    parts = viewbox.split()
    
    paths_xml = ""
    
    # Extract path elements
    path_pattern = r'<path\s+d="([^"]*)"\s+([^>]*)/?>'
    for path_data, attrs in re.findall(path_pattern, svg_content):
        if not path_data.strip():
            continue
        
        stroke_width_match = re.search(r'stroke-width="([^"]*)"', attrs)
        stroke_width = stroke_width_match.group(1) if stroke_width_match else "16"
        has_stroke = 'stroke="currentColor"' in attrs and 'fill="none"' in attrs
        
        if has_stroke:
            paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:strokeColor="@android:color/white"
      android:strokeWidth="{stroke_width}"
      android:strokeLineCap="round"
      android:strokeLineJoin="round" />
'''
        else:
            paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:fillColor="@android:color/white" />
'''
    
    # Extract line elements -> convert to paths
    line_pattern = r'<line\s+x1="([^"]*)"\s+y1="([^"]*)"\s+x2="([^"]*)"\s+y2="([^"]*)"\s+([^>]*)/?>'
    for x1, y1, x2, y2, attrs in re.findall(line_pattern, svg_content):
        path_data = f"M{x1},{y1} L{x2},{y2}"
        stroke_width_match = re.search(r'stroke-width="([^"]*)"', attrs)
        stroke_width = stroke_width_match.group(1) if stroke_width_match else "16"
        
        paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:strokeColor="@android:color/white"
      android:strokeWidth="{stroke_width}"
      android:strokeLineCap="round"
      android:strokeLineJoin="round" />
'''
    
    # Extract circle elements -> convert to arc paths
    circle_pattern = r'<circle\s+cx="([^"]*)"\s+cy="([^"]*)"\s+r="([^"]*)"\s+([^>]*)/?>'
    for cx, cy, r, attrs in re.findall(circle_pattern, svg_content):
        try:
            cx_f = float(cx)
            cy_f = float(cy)
            r_f = float(r)
            # Two 180-degree arcs to make a full circle
            path_data = f"M{cx_f-r_f},{cy_f} A{r_f} {r_f} 0 1 0 {cx_f+r_f},{cy_f} A{r_f} {r_f} 0 1 0 {cx_f-r_f},{cy_f}"
            
            stroke_width_match = re.search(r'stroke-width="([^"]*)"', attrs)
            stroke_width = stroke_width_match.group(1) if stroke_width_match else "16"
            
            paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:strokeColor="@android:color/white"
      android:strokeWidth="{stroke_width}"
      android:strokeLineCap="round"
      android:strokeLineJoin="round" />
'''
        except:
            pass
    
    # Extract polyline elements -> convert to paths
    polyline_pattern = r'<polyline\s+points="([^"]*)"\s+([^>]*)/?>'
    for points_str, attrs in re.findall(polyline_pattern, svg_content):
        try:
            coords = re.findall(r'[\d.]+', points_str)
            if len(coords) >= 4:
                path_data = f"M{coords[0]} {coords[1]}"
                for i in range(2, len(coords), 2):
                    if i+1 < len(coords):
                        path_data += f" L{coords[i]} {coords[i+1]}"
                
                stroke_width_match = re.search(r'stroke-width="([^"]*)"', attrs)
                stroke_width = stroke_width_match.group(1) if stroke_width_match else "16"
                
                paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:strokeColor="@android:color/white"
      android:strokeWidth="{stroke_width}"
      android:strokeLineCap="round"
      android:strokeLineJoin="round" />
'''
        except:
            pass
    
    vd_xml = f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="{parts[2] if len(parts) > 2 else '256'}"
    android:viewportHeight="{parts[3] if len(parts) > 3 else '256'}">
{paths_xml}</vector>'''
    
    return vd_xml

def main():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download and extract
    zip_path = download_phosphor_zip()
    if not zip_path:
        return
    
    svg_files = extract_svgs_from_zip(zip_path)
    print(f"Found {len(svg_files)} SVG files")
    
    print("Converting to Vector Drawables...")
    registry_icons = []
    
    for svg_file in sorted(svg_files):
        icon_name = svg_file.stem
        
        try:
            with open(svg_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
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
    
    print("Building registry...")
    registry = {"icons": registry_icons}
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Done! {len(registry_icons)} icons in {ICONS_DIR}")
    print(f"Registry: {REGISTRY_FILE}")

if __name__ == "__main__":
    main()
