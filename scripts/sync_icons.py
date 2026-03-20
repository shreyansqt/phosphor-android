#!/usr/bin/env python3
"""
Sync Phosphor icons from GitHub and convert to Android Vector Drawables.
"""

import json
import os
import re
import subprocess
import urllib.request
import math
from pathlib import Path
from zipfile import ZipFile

PHOSPHOR_REPO = "phosphor-icons/core"
PHOSPHOR_BRANCH = "main"
PHOSPHOR_WEIGHT = "regular"
ICONS_DIR = Path(__file__).parent.parent / "icons"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"

def parse_transform(transform_str):
    """Parse SVG transform string into list of (function, args) tuples."""
    if not transform_str:
        return []
    
    transforms = []
    # Find all transform functions: name(args)
    for match in re.finditer(r'(\w+)\s*\(([^)]*)\)', transform_str):
        func = match.group(1)
        # Split on commas OR whitespace
        args_str = match.group(2).replace(',', ' ')
        args = [float(x) for x in args_str.split() if x.strip()]
        transforms.append((func, args))
    
    return transforms

def apply_transforms_to_points(points, transforms):
    """Apply a list of transforms to a list of (x, y) points."""
    if not transforms:
        return points
    
    result = []
    for x, y in points:
        for func, args in transforms:
            if func == 'translate':
                tx = args[0] if len(args) > 0 else 0
                ty = args[1] if len(args) > 1 else 0
                x += tx
                y += ty
            elif func == 'rotate':
                angle = math.radians(args[0]) if len(args) > 0 else 0
                # SVG rotate uses explicit center or (0,0) - we'll use (0,0) as SVG spec
                cx = args[1] if len(args) > 1 else 0
                cy = args[2] if len(args) > 2 else 0
                
                x -= cx
                y -= cy
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                new_x = x * cos_a - y * sin_a
                new_y = x * sin_a + y * cos_a
                x = new_x + cx
                y = new_y + cy
            elif func == 'scale':
                sx = args[0] if len(args) > 0 else 1
                sy = args[1] if len(args) > 1 else sx
                x *= sx
                y *= sy
            elif func == 'skewX':
                angle = math.radians(args[0]) if len(args) > 0 else 0
                x += y * math.tan(angle)
            elif func == 'skewY':
                angle = math.radians(args[0]) if len(args) > 0 else 0
                y += x * math.tan(angle)
            elif func == 'matrix':
                if len(args) == 6:
                    a, b, c, d, e, f = args
                    new_x = a * x + c * y + e
                    new_y = b * x + d * y + f
                    x, y = new_x, new_y
        
        result.append((x, y))
    
    return result

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
        
        # Extract transform
        transform_match = re.search(r'transform="([^"]*)"', attrs)
        transforms = parse_transform(transform_match.group(1)) if transform_match else []
        
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
        transform_match = re.search(r'transform="([^"]*)"', attrs)
        transforms = parse_transform(transform_match.group(1)) if transform_match else []
        
        points = apply_transforms_to_points([(float(x1), float(y1)), (float(x2), float(y2))], transforms)
        x1_t, y1_t = points[0]
        x2_t, y2_t = points[1]
        
        path_data = f"M{x1_t},{y1_t} L{x2_t},{y2_t}"
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
    
    # Extract rect elements -> convert to paths (handle flexible attribute order)
    rect_pattern = r'<rect\s+([^>]*?)(?:\s+x="([^"]*)"\s+y="([^"]*)"\s+width="([^"]*)"\s+height="([^"]*)"|\s+width="([^"]*)"\s+height="([^"]*)"\s+x="([^"]*)"\s+y="([^"]*)")\s*([^>]*)/?>'
    
    # Simpler approach: find all rects and parse attributes individually
    rect_pattern = r'<rect\s+([^>]*)/?>'
    for elem_attrs in re.findall(rect_pattern, svg_content):
        # Skip background rect
        if 'width="256" height="256"' in elem_attrs and 'fill="none"' in elem_attrs and 'x=' not in elem_attrs:
            continue
            
        # Extract x, y, width, height from any order
        x_match = re.search(r'x="([^"]*)"', elem_attrs)
        y_match = re.search(r'y="([^"]*)"', elem_attrs)
        w_match = re.search(r'width="([^"]*)"', elem_attrs)
        h_match = re.search(r'height="([^"]*)"', elem_attrs)
        
        if not (x_match and y_match and w_match and h_match):
            continue
            
        x, y, w, h = x_match.group(1), y_match.group(1), w_match.group(1), h_match.group(1)
        attrs = elem_attrs
        try:
            x_f, y_f, w_f, h_f = float(x), float(y), float(w), float(h)
            
            # Extract transform
            transform_match = re.search(r'transform="([^"]*)"', attrs)
            transforms = parse_transform(transform_match.group(1)) if transform_match else []
            
            # Create rectangle corners
            points = [(x_f, y_f), (x_f+w_f, y_f), (x_f+w_f, y_f+h_f), (x_f, y_f+h_f)]
            points = apply_transforms_to_points(points, transforms)
            
            # Build path from transformed points
            path_data = f"M{points[0][0]} {points[0][1]}"
            for px, py in points[1:]:
                path_data += f" L{px} {py}"
            path_data += " Z"
            
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
                points = [(float(coords[i]), float(coords[i+1])) for i in range(0, len(coords), 2)]
                
                transform_match = re.search(r'transform="([^"]*)"', attrs)
                transforms = parse_transform(transform_match.group(1)) if transform_match else []
                points = apply_transforms_to_points(points, transforms)
                
                path_data = f"M{points[0][0]} {points[0][1]}"
                for px, py in points[1:]:
                    path_data += f" L{px} {py}"
                
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
    
    # Extract polygon elements -> convert to paths
    polygon_pattern = r'<polygon\s+points="([^"]*)"\s+([^>]*)/?>'
    for points_str, attrs in re.findall(polygon_pattern, svg_content):
        try:
            coords = re.findall(r'[\d.]+', points_str)
            if len(coords) >= 6:
                points = [(float(coords[i]), float(coords[i+1])) for i in range(0, len(coords), 2)]
                
                transform_match = re.search(r'transform="([^"]*)"', attrs)
                transforms = parse_transform(transform_match.group(1)) if transform_match else []
                points = apply_transforms_to_points(points, transforms)
                
                path_data = f"M{points[0][0]} {points[0][1]}"
                for px, py in points[1:]:
                    path_data += f" L{px} {py}"
                path_data += " Z"
                
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
    
    # Extract ellipse elements -> convert to circle paths
    ellipse_pattern = r'<ellipse\s+cx="([^"]*)"\s+cy="([^"]*)"\s+rx="([^"]*)"\s+ry="([^"]*)"\s+([^>]*)/?>'
    for cx, cy, rx, ry, attrs in re.findall(ellipse_pattern, svg_content):
        try:
            cx_f, cy_f, rx_f, ry_f = float(cx), float(cy), float(rx), float(ry)
            path_data = f"M{cx_f-rx_f},{cy_f} A{rx_f} {ry_f} 0 1 0 {cx_f+rx_f},{cy_f} A{rx_f} {ry_f} 0 1 0 {cx_f-rx_f},{cy_f}"
            
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
