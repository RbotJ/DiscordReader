#!/usr/bin/env python3
"""
Integration Checklist Tool

Automated checks to prevent frontend/backend disconnects.
Run this before adding new features to ensure consistency.
"""
import os
import re
from pathlib import Path

def check_template_integration():
    """Check that all templates extend base.html"""
    templates_dir = Path("templates")
    issues = []
    
    for template_file in templates_dir.rglob("*.html"):
        if template_file.name == "base.html":
            continue
            
        with open(template_file, 'r') as f:
            content = f.read()
            
        if not re.search(r'{%\s*extends\s+["\']base\.html["\']', content):
            issues.append(f"Template {template_file} does not extend base.html")
    
    return issues

def check_navigation_consistency():
    """Check that navigation links are properly integrated"""
    base_template = Path("templates/base.html")
    
    if not base_template.exists():
        return ["base.html template not found"]
    
    with open(base_template, 'r') as f:
        nav_content = f.read()
    
    # Check for standalone navigation in other templates
    issues = []
    templates_dir = Path("templates")
    
    for template_file in templates_dir.rglob("*.html"):
        if template_file.name == "base.html":
            continue
            
        with open(template_file, 'r') as f:
            content = f.read()
            
        if re.search(r'<nav\s+class=["\']navbar', content):
            issues.append(f"Template {template_file} has standalone navigation")
    
    return issues

def check_bootstrap_consistency():
    """Check for consistent Bootstrap usage"""
    base_template = Path("templates/base.html")
    issues = []
    
    if not base_template.exists():
        return ["base.html template not found"]
    
    with open(base_template, 'r') as f:
        base_content = f.read()
    
    # Extract Bootstrap version from base.html
    bootstrap_match = re.search(r'bootstrap@([\d.]+)', base_content)
    if not bootstrap_match:
        return ["No Bootstrap version found in base.html"]
    
    base_bootstrap_version = bootstrap_match.group(1)
    
    # Check other templates for different Bootstrap versions
    templates_dir = Path("templates")
    
    for template_file in templates_dir.rglob("*.html"):
        if template_file.name == "base.html":
            continue
            
        with open(template_file, 'r') as f:
            content = f.read()
            
        bootstrap_matches = re.findall(r'bootstrap@([\d.]+)', content)
        for version in bootstrap_matches:
            if version != base_bootstrap_version:
                issues.append(f"Template {template_file} uses Bootstrap {version}, base uses {base_bootstrap_version}")
    
    return issues

def check_duplicate_features():
    """Check for duplicate routes, templates, and functionality"""
    issues = []
    
    # Check for duplicate routes
    route_patterns = {}
    
    # Scan Python files for route definitions
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find route decorators
            routes = re.findall(r'@\w+\.route\(["\']([^"\']+)["\']', content)
            
            for route in routes:
                if route in route_patterns:
                    route_patterns[route].append(str(py_file))
                else:
                    route_patterns[route] = [str(py_file)]
        except:
            continue
    
    # Report duplicate routes
    for route, files in route_patterns.items():
        if len(files) > 1:
            issues.append(f"Duplicate route '{route}' found in: {', '.join(files)}")
    
    # Check for similar template names
    template_names = []
    for template_file in Path("templates").rglob("*.html"):
        template_names.append(template_file.name)
    
    # Find potential duplicates (similar names)
    for i, name1 in enumerate(template_names):
        for name2 in template_names[i+1:]:
            # Check for very similar names that might be duplicates
            if name1 != name2 and (name1.replace('_', '') == name2.replace('-', '') or 
                                   name1.split('.')[0] in name2 or name2.split('.')[0] in name1):
                issues.append(f"Potentially duplicate templates: {name1} and {name2}")
    
    return issues

def check_existing_functionality():
    """Scan for existing similar functionality before building new features"""
    functionality_map = {
        'dashboard': [],
        'discord': [],
        'trading': [],
        'setup': [],
        'message': [],
        'channel': [],
        'ticker': []
    }
    
    # Scan for existing features
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        file_path = str(py_file).lower()
        
        for feature in functionality_map.keys():
            if feature in file_path:
                functionality_map[feature].append(str(py_file))
    
    issues = []
    for feature, files in functionality_map.items():
        if len(files) > 3:  # Threshold for potential duplication
            issues.append(f"Many {feature}-related files found ({len(files)}): Consider consolidation")
    
    return issues

def main():
    """Run all integration checks"""
    print("🔍 Running Integration Checklist...")
    
    all_issues = []
    
    # Template integration check
    template_issues = check_template_integration()
    all_issues.extend(template_issues)
    
    # Navigation consistency check
    nav_issues = check_navigation_consistency()
    all_issues.extend(nav_issues)
    
    # Bootstrap consistency check
    bootstrap_issues = check_bootstrap_consistency()
    all_issues.extend(bootstrap_issues)
    
    # Duplicate feature check
    duplicate_issues = check_duplicate_features()
    all_issues.extend(duplicate_issues)
    
    # Existing functionality check
    existing_issues = check_existing_functionality()
    all_issues.extend(existing_issues)
    
    if all_issues:
        print("❌ Integration Issues Found:")
        for issue in all_issues:
            print(f"  • {issue}")
        return 1
    else:
        print("✅ All integration checks passed!")
        return 0

if __name__ == "__main__":
    exit(main())