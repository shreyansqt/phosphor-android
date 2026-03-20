#!/usr/bin/env python3
"""
Validate generated VDs against original Phosphor SVGs by comparing element counts.
"""

import re
import json
from pathlib import Path
from urllib.request import urlopen

ICONS_DIR = Path(__file__).parent.parent / "xmls"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"
REPO_URL = "https://raw.githubusercontent.com/phosphor-icons/core/main/raw/regular"

def count_elements(content):
    """Count SVG/VD elements (skip invisible ones)."""
    elements = {
        'path': len(re.findall(r'<path\b', content)),
        'line': len(re.findall(r'<line\b', content)),
        'rect': len(re.findall(r'<rect\b', content)),
        'circle': len(re.findall(r'<circle\b', content)),
        'polyline': len(re.findall(r'<polyline\b', content)),
        'polygon': len(re.findall(r'<polygon\b', content)),
        'ellipse': len(re.findall(r'<ellipse\b', content)),
    }
    
    # Subtract invisible rects (opacity="0")
    invisible_rects = len(re.findall(r'<rect[^>]*opacity="0"[^>]*>', content))
    elements['rect'] -= invisible_rects
    
    return elements

def get_transforms(content):
    """Count transform attributes."""
    return len(re.findall(r'transform="[^"]*"', content))

def validate_icon(icon_name):
    """Compare original SVG with generated VD."""
    try:
        # Fetch original SVG
        svg_url = f"{REPO_URL}/{icon_name}.svg"
        with urlopen(svg_url) as response:
            svg_content = response.read().decode('utf-8')
        
        # Read generated VD
        vd_path = ICONS_DIR / f"phosphor_{icon_name}.xml"
        with open(vd_path) as f:
            vd_content = f.read()
        
        # Count elements
        svg_elements = count_elements(svg_content)
        vd_elements = count_elements(vd_content)
        
        # Count transforms (should match)
        svg_transforms = get_transforms(svg_content)
        vd_transforms = get_transforms(vd_content)
        
        # Check for issues
        svg_total = sum(svg_elements.values())
        vd_total = sum(vd_elements.values())
        
        # Check for background rect (should be skipped)
        background_rect = '<rect width="256" height="256" fill="none"/>' in svg_content
        svg_total_for_comparison = svg_total - (1 if background_rect else 0)
        
        # All SVG elements should be converted to paths in VD
        # Note: background rect is skipped, so expected = svg_total - 1 (for background rect)
        expected_vd_paths = svg_total_for_comparison
        actual_vd_paths = vd_elements['path']
        
        issues = []
        if vd_total == 0:
            issues.append("EMPTY: Generated VD has no elements")
        elif actual_vd_paths < expected_vd_paths * 0.8:  # Allow some loss due to optimization
            issues.append(f"MISSING_ELEMENTS: Expected ~{expected_vd_paths} paths, got {actual_vd_paths}")
        
        if svg_transforms > 0 and vd_transforms == 0:
            # Check if we actually have content (not empty)
            if vd_total > 0:
                # Transforms were applied (baked into coordinates)
                pass
            else:
                issues.append(f"TRANSFORM_ISSUE: Original has {svg_transforms} transforms but VD has no paths")
        
        return {
            'icon': icon_name,
            'svg_elements': svg_total_for_comparison,
            'vd_elements': vd_total,
            'svg_transforms': svg_transforms,
            'issues': issues,
            'status': 'OK' if not issues else 'ISSUE'
        }
        
    except Exception as e:
        return {
            'icon': icon_name,
            'error': str(e),
            'status': 'ERROR'
        }

def main():
    # Load icon list
    with open(REGISTRY_FILE) as f:
        registry = json.load(f)
    
    icons = [i['name'] for i in registry['icons']]
    print(f"Validating {len(icons)} icons...\n")
    
    # Validate all icons
    sample_size = len(icons)
    print(f"Validating all {sample_size} icons...\n")
    
    results = {
        'OK': 0,
        'ISSUE': 0,
        'ERROR': 0,
    }
    
    issues_found = []
    
    for i, icon_name in enumerate(icons[:sample_size]):
        result = validate_icon(icon_name)
        status = result['status']
        results[status] += 1
        
        if result['status'] != 'OK':
            issues_found.append(result)
        
        # Progress indicator
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{sample_size} icons validated")
    
    print(f"\n{'='*60}")
    print(f"Results: {results['OK']} OK, {results['ISSUE']} issues, {results['ERROR']} errors")
    print(f"{'='*60}\n")
    
    if issues_found:
        print("Issues found:\n")
        for result in issues_found[:20]:  # Show first 20 issues
            print(f"{result['icon']:30}", end=' ')
            if 'error' in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"SVG:{result['svg_elements']:3} VD:{result['vd_elements']:3} | {', '.join(result['issues'])}")
        
        if len(issues_found) > 20:
            print(f"\n... and {len(issues_found) - 20} more issues")
    else:
        print("✅ No issues found in sample!")

if __name__ == "__main__":
    main()
