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
    
    # Enhanced route duplicate detection
    route_patterns = {}
    similar_routes = []
    
    # Scan Python files for route definitions
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find both app.route and blueprint.route patterns
            routes = re.findall(r'@(?:app|\w+)\.route\(["\']([^"\']+)["\']', content)
            
            for route in routes:
                if route in route_patterns:
                    route_patterns[route].append(str(py_file))
                else:
                    route_patterns[route] = [str(py_file)]
        except:
            continue
    
    # Report exact duplicate routes
    for route, files in route_patterns.items():
        if len(files) > 1:
            issues.append(f"🚨 DUPLICATE ROUTE: '{route}' found in: {', '.join(files)}")
    
    # Check for similar routes that might conflict
    route_list = list(route_patterns.keys())
    for i, route1 in enumerate(route_list):
        for route2 in route_list[i+1:]:
            # Check for similar patterns that might overlap
            if route1 != route2:
                # Remove trailing slashes for comparison
                r1_clean = route1.rstrip('/')
                r2_clean = route2.rstrip('/')
                
                # Check if one route is contained in another
                if r1_clean in r2_clean or r2_clean in r1_clean:
                    issues.append(f"⚠️  SIMILAR ROUTES: '{route1}' and '{route2}' might conflict")
                
                # Check for very similar patterns (same words, different order)
                r1_parts = set(r1_clean.split('/'))
                r2_parts = set(r2_clean.split('/'))
                if len(r1_parts.intersection(r2_parts)) > 1 and len(r1_parts) == len(r2_parts):
                    issues.append(f"⚠️  SIMILAR ROUTES: '{route1}' and '{route2}' have similar structure")
    
    # Enhanced template similarity analysis
    template_info = {}
    for template_file in Path("templates").rglob("*.html"):
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Analyze template content
            word_count = len(content.split())
            has_form = 'form' in content.lower()
            has_table = 'table' in content.lower()
            has_chart = 'chart' in content.lower()
            
            template_info[template_file.name] = {
                'path': str(template_file),
                'word_count': word_count,
                'has_form': has_form,
                'has_table': has_table,
                'has_chart': has_chart,
                'content_snippet': content[:200].lower()
            }
        except:
            continue
    
    # Find potentially duplicate templates
    template_names = list(template_info.keys())
    for i, name1 in enumerate(template_names):
        for name2 in template_names[i+1:]:
            if name1 != name2:
                info1 = template_info[name1]
                info2 = template_info[name2]
                
                # Check for similar names
                name1_base = name1.split('.')[0].replace('_', '').replace('-', '')
                name2_base = name2.split('.')[0].replace('_', '').replace('-', '')
                
                if name1_base == name2_base:
                    issues.append(f"🚨 SIMILAR TEMPLATE NAMES: {name1} and {name2}")
                
                # Check for similar content structure
                if (info1['has_form'] == info2['has_form'] and 
                    info1['has_table'] == info2['has_table'] and
                    info1['has_chart'] == info2['has_chart'] and
                    abs(info1['word_count'] - info2['word_count']) < 50):
                    
                    # Check content similarity
                    snippet1_words = set(info1['content_snippet'].split())
                    snippet2_words = set(info2['content_snippet'].split())
                    similarity = len(snippet1_words.intersection(snippet2_words)) / max(len(snippet1_words), len(snippet2_words))
                    
                    if similarity > 0.6:  # 60% word similarity threshold
                        issues.append(f"⚠️  SIMILAR TEMPLATE CONTENT: {name1} and {name2} have similar structure and content")
    
    return issues

def check_function_name_overlaps():
    """Check for duplicate or similar function names across files"""
    issues = []
    function_map = {}
    
    # Scan Python files for function definitions
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find function definitions (both def and async def)
            functions = re.findall(r'(?:async\s+)?def\s+(\w+)\s*\(', content)
            
            for func_name in functions:
                if func_name.startswith('_'):  # Skip private functions
                    continue
                    
                if func_name in function_map:
                    function_map[func_name].append(str(py_file))
                else:
                    function_map[func_name] = [str(py_file)]
        except:
            continue
    
    # Report duplicate function names
    for func_name, files in function_map.items():
        if len(files) > 1:
            # Check if they're API endpoint functions (more critical)
            is_api_function = any(keyword in func_name.lower() for keyword in ['get_', 'post_', 'api_', 'route_'])
            if is_api_function:
                issues.append(f"🚨 DUPLICATE API FUNCTION: '{func_name}' found in: {', '.join(files)}")
            else:
                issues.append(f"⚠️  DUPLICATE FUNCTION: '{func_name}' found in: {', '.join(files)}")
    
    return issues

def check_existing_functionality():
    """Scan for existing functionality and suggest consolidation opportunities"""
    functionality_map = {
        'dashboard': [],
        'discord': [],
        'trading': [],
        'setup': [],
        'message': [],
        'channel': [],
        'ticker': [],
        'admin': [],
        'api': []
    }
    
    # Scan for existing features by file paths and content
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        file_path = str(py_file).lower()
        
        # Check file path for feature indicators
        for feature in functionality_map.keys():
            if feature in file_path:
                functionality_map[feature].append(str(py_file))
    
    issues = []
    consolidation_suggestions = []
    
    # Analyze feature distribution and suggest consolidation
    for feature, files in functionality_map.items():
        if len(files) > 4:  # Threshold for potential over-fragmentation
            consolidation_suggestions.append(f"📦 CONSOLIDATION OPPORTUNITY: {feature} functionality spread across {len(files)} files")
            
        elif len(files) > 1:
            # Check if files have very similar purposes
            route_files = [f for f in files if 'route' in f or 'api' in f]
            model_files = [f for f in files if 'model' in f]
            view_files = [f for f in files if 'view' in f or 'template' in f]
            
            if len(route_files) > 1:
                consolidation_suggestions.append(f"🔗 MULTIPLE ROUTE FILES: {feature} has {len(route_files)} route files - consider merging")
            if len(model_files) > 1:
                consolidation_suggestions.append(f"🗃️  MULTIPLE MODEL FILES: {feature} has {len(model_files)} model files - consider merging")
    
    # Add consolidation suggestions as informational items
    issues.extend(consolidation_suggestions)
    
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
    
    # Function name overlap check
    function_issues = check_function_name_overlaps()
    all_issues.extend(function_issues)
    
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