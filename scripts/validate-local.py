#!/usr/bin/env python3
"""
Fast validation using local SVG copies (no network calls).
Reports issues but doesn't fail (suitable for CI logging).
"""

import re
import json
from pathlib import Path
from collections import defaultdict

ICONS_DIR = Path(__file__).parent.parent / "icons"
SVGS_DIR = Path(__file__).parent.parent / "svgs"
REGISTRY_FILE = Path(__file__).parent.parent / "icons.json"

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
    
    # Subtract background rects and invisible rects
    bg_rects = len(re.findall(r'<rect\s+width="256"\s+height="256"', content))
    invisible_rects = len(re.findall(r'<rect[^>]*opacity="0"[^>]*>', content))
    elements['rect'] -= (bg_rects + invisible_rects)
    
    return elements

def validate_icon(icon_name):
    """Compare original SVG with generated VD."""
    try:
        svg_path = SVGS_DIR / f"{icon_name}.svg"
        vd_path = ICONS_DIR / f"phosphor_{icon_name}.xml"
        
        if not svg_path.exists():
            return {'status': 'SKIP', 'reason': 'SVG not found'}
        if not vd_path.exists():
            return {'status': 'SKIP', 'reason': 'VD not found'}
        
        with open(svg_path) as f:
            svg_content = f.read()
        with open(vd_path) as f:
            vd_content = f.read()
        
        svg_elements = count_elements(svg_content)
        vd_elements = count_elements(vd_content)
        
        svg_total = sum(svg_elements.values())
        vd_total = sum(vd_elements.values())
        
        issues = []
        if vd_total == 0:
            issues.append("EMPTY")
        elif vd_total < svg_total * 0.8:
            issues.append(f"MISSING ({svg_total}→{vd_total})")
        
        return {
            'status': 'ISSUE' if issues else 'OK',
            'svg_elements': svg_total,
            'vd_elements': vd_total,
            'issues': issues
        }
        
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)}

def main():
    if not SVGS_DIR.exists():
        print("⚠️  SVG directory not found. Run sync first.")
        return
    
    # Load icon list
    with open(REGISTRY_FILE) as f:
        registry = json.load(f)
    
    icons = [i['name'] for i in registry['icons']]
    print(f"Validating {len(icons)} icons (local SVGs)...\n")
    
    results = defaultdict(int)
    issues_by_type = defaultdict(list)
    
    for i, icon_name in enumerate(icons):
        result = validate_icon(icon_name)
        status = result['status']
        results[status] += 1
        
        if status == 'ISSUE':
            for issue in result.get('issues', []):
                issues_by_type[issue].append(icon_name)
        
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(icons)} validated")
    
    print(f"\n{'='*60}")
    print(f"Results: {results['OK']} OK, {results['ISSUE']} issues, "
          f"{results['ERROR']} errors, {results['SKIP']} skipped")
    print(f"{'='*60}\n")
    
    if issues_by_type:
        print("Issues by type:\n")
        for issue_type, icons_list in sorted(issues_by_type.items()):
            print(f"  {issue_type}: {len(icons_list)} icons")
            for icon in icons_list[:5]:
                print(f"    - {icon}")
            if len(icons_list) > 5:
                print(f"    ... and {len(icons_list) - 5} more")
        
        print(f"\nTotal issues: {sum(len(v) for v in issues_by_type.values())}")
    else:
        print("✅ No issues found!")

if __name__ == "__main__":
    main()
