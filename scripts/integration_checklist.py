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