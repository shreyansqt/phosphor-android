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
SVGS_DIR = Path(__file__).parent.parent / "svgs"  # Original SVGs for reference
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

def matrix_mult(m1, m2):
    """Multiply two 2x3 affine matrices (represented as [a,b,c,d,e,f])."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    
    # 3x3 matrix multiplication for affine transforms
    # [a1 c1 e1]   [a2 c2 e2]
    # [b1 d1 f1] * [b2 d2 f2]
    # [0  0  1 ]   [0  0  1 ]
    
    a = a1*a2 + c1*b2
    b = b1*a2 + d1*b2
    c = a1*c2 + c1*d2
    d = b1*c2 + d1*d2
    e = a1*e2 + c1*f2 + e1
    f = b1*e2 + d1*f2 + f1
    
    return (a, b, c, d, e, f)

def apply_transforms_to_points(points, transforms):
    """Apply SVG transforms using proper matrix composition."""
    if not transforms:
        return points
    
    # Compose all transforms into a single matrix
    # Start with identity matrix
    matrix = (1, 0, 0, 1, 0, 0)  # [a, b, c, d, e, f]
    
    for func, args in transforms:
        if func == 'translate':
            tx = args[0] if len(args) > 0 else 0
            ty = args[1] if len(args) > 1 else 0
            t_matrix = (1, 0, 0, 1, tx, ty)
            matrix = matrix_mult(matrix, t_matrix)
            
        elif func == 'rotate':
            angle = math.radians(args[0]) if len(args) > 0 else 0
            cx = args[1] if len(args) > 1 else 0
            cy = args[2] if len(args) > 2 else 0
            
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # Rotate around (cx, cy): translate(-cx,-cy), rotate, translate(cx,cy)
            if cx != 0 or cy != 0:
                t1 = (1, 0, 0, 1, -cx, -cy)
                r_matrix = (cos_a, sin_a, -sin_a, cos_a, 0, 0)
                t2 = (1, 0, 0, 1, cx, cy)
                
                temp = matrix_mult(t1, r_matrix)
                temp = matrix_mult(temp, t2)
                matrix = matrix_mult(matrix, temp)
            else:
                r_matrix = (cos_a, sin_a, -sin_a, cos_a, 0, 0)
                matrix = matrix_mult(matrix, r_matrix)
        
        elif func == 'scale':
            sx = args[0] if len(args) > 0 else 1
            sy = args[1] if len(args) > 1 else sx
            s_matrix = (sx, 0, 0, sy, 0, 0)
            matrix = matrix_mult(matrix, s_matrix)
        
        elif func == 'skewX':
            angle = math.radians(args[0]) if len(args) > 0 else 0
            tan_a = math.tan(angle)
            sk_matrix = (1, 0, tan_a, 1, 0, 0)
            matrix = matrix_mult(matrix, sk_matrix)
        
        elif func == 'skewY':
            angle = math.radians(args[0]) if len(args) > 0 else 0
            tan_a = math.tan(angle)
            sk_matrix = (1, tan_a, 0, 1, 0, 0)
            matrix = matrix_mult(matrix, sk_matrix)
        
        elif func == 'matrix':
            if len(args) == 6:
                m_matrix = tuple(args)
                matrix = matrix_mult(matrix, m_matrix)
    
    # Apply the composed matrix to all points
    a, b, c, d, e, f = matrix
    result = []
    for x, y in points:
        new_x = a * x + c * y + e
        new_y = b * x + d * y + f
        result.append((new_x, new_y))
    
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
        return list(svg_dir.glob("*.svg")), extract_dir
    else:
        print(f"SVG directory not found at {svg_dir}")
        return [], extract_dir

def load_icon_metadata(extract_dir):
    """Load icon metadata (tags) from src/icons.ts."""
    metadata = {}
    icons_ts = Path(extract_dir) / "core-main" / "src" / "icons.ts"
    if not icons_ts.exists():
        return metadata
    
    try:
        with open(icons_ts) as f:
            content = f.read()
        
        # Parse the TypeScript file to extract icon data
        import re
        
        # Find each icon object
        icon_pattern = r'\{\s*name:\s*"([^"]+)"[^}]*?tags:\s*\[(.*?)\]'
        for match in re.finditer(icon_pattern, content, re.DOTALL):
            icon_name = match.group(1)
            tags_str = match.group(2)
            
            # Extract individual tags
            tags = re.findall(r'"([^"]*)"', tags_str)
            metadata[icon_name] = tags
    except Exception as e:
        print(f"Warning: Could not load icon metadata: {e}")
    
    return metadata

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
    # Handle flexible attribute order: cx, cy, r can appear in any order
    circle_pattern = r'<circle\s+([^>]*)/?>'
    for elem_attrs in re.findall(circle_pattern, svg_content):
        # Skip if it's the background rect (shouldn't happen but be safe)
        if 'width="256" height="256"' in elem_attrs:
            continue
        
        try:
            # Extract cx, cy, r from any order
            cx_match = re.search(r'cx="([^"]*)"', elem_attrs)
            cy_match = re.search(r'cy="([^"]*)"', elem_attrs)
            r_match = re.search(r'r="([^"]*)"', elem_attrs)
            
            if not (cx_match and cy_match and r_match):
                continue
            
            cx_f = float(cx_match.group(1))
            cy_f = float(cy_match.group(1))
            r_f = float(r_match.group(1))
            
            # Two 180-degree arcs to make a full circle
            path_data = f"M{cx_f-r_f},{cy_f} A{r_f} {r_f} 0 1 0 {cx_f+r_f},{cy_f} A{r_f} {r_f} 0 1 0 {cx_f-r_f},{cy_f}"
            
            # Check if stroke or fill
            has_stroke = 'stroke="currentColor"' in elem_attrs and 'fill="none"' in elem_attrs
            stroke_width_match = re.search(r'stroke-width="([^"]*)"', elem_attrs)
            stroke_width = stroke_width_match.group(1) if stroke_width_match else "16"
            
            if has_stroke:
                paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:strokeColor="@android:color/white"
      android:strokeWidth="{stroke_width}"
      android:strokeLineCap="round"
      android:strokeLineJoin="round" />
'''
            else:
                # Default to fill (for dot icons without explicit attributes)
                paths_xml += f'''  <path
      android:pathData="{path_data}"
      android:fillColor="@android:color/white" />
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
    SVGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download and extract
    zip_path = download_phosphor_zip()
    if not zip_path:
        return
    
    svg_files, extract_dir = extract_svgs_from_zip(zip_path)
    print(f"Found {len(svg_files)} SVG files")
    
    # Load icon metadata (tags)
    metadata = load_icon_metadata(extract_dir)
    print(f"Loaded metadata for {len(metadata)} icons")
    
    print("Converting to Vector Drawables...")
    registry_icons = []
    
    for svg_file in sorted(svg_files):
        icon_name = svg_file.stem
        
        try:
            with open(svg_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Save original SVG for reference
            svg_copy_path = SVGS_DIR / f"{icon_name}.svg"
            with open(svg_copy_path, 'w') as f:
                f.write(svg_content)
            
            vd_xml = svg_to_vd_string(svg_content)
            vd_path = ICONS_DIR / f"phosphor_{icon_name}.xml"
            
            with open(vd_path, 'w') as f:
                f.write(vd_xml)
            
            # Use metadata tags if available, otherwise use icon name
            keywords = metadata.get(icon_name, [icon_name.replace("-", " ")])
            if not keywords:  # If tags are empty, add the name as fallback
                keywords = [icon_name.replace("-", " ")]
            
            registry_icons.append({
                "name": icon_name,
                "category": "icon",
                "keywords": keywords,
                "vd": vd_xml  # Inline the VD XML for fast rendering
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
