#!/usr/bin/env python3
"""
Template Validation Script

Validates all templates in the templates/ directory for:
- Presence of header comment blocks with metadata
- Proper inheritance from base.html
- Unique filenames (no near-duplicates)
- Proper directory organization
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set
from difflib import SequenceMatcher


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def validate_header_comment(template_path: Path) -> Tuple[bool, str]:
    """
    Validate that template has a proper header comment block.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {e}"
    
    # Look for header comment block
    header_match = re.search(r'<!--\s*(.*?)\s*-->', content, re.DOTALL)
    if not header_match:
        return False, "Missing header comment block"
    
    header_content = header_match.group(1)
    
    # Check for required metadata fields
    required_fields = ['template:', 'purpose:', 'used by:', 'dependencies:']
    found_fields = []
    
    for line in header_content.split('\n'):
        line = line.strip().lower()
        for field in required_fields:
            if line.startswith(field):
                found_fields.append(field)
                break
    
    missing_fields = [field for field in required_fields if field not in found_fields]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, ""


def validate_extends_base(template_path: Path) -> Tuple[bool, str]:
    """
    Validate that template extends base.html (except base.html itself).
    
    Returns:
        (is_valid, error_message)
    """
    # Skip validation for base.html itself
    if template_path.name == 'base.html':
        return True, ""
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {e}"
    
    # Look for extends statement
    extends_pattern = r'{%\s*extends\s+["\']base\.html["\']'
    if not re.search(extends_pattern, content):
        return False, "Does not extend base.html"
    
    return True, ""


def validate_unique_filenames(templates: List[Path]) -> List[str]:
    """
    Validate that template filenames are unique (Levenshtein distance >= 3).
    
    Returns:
        List of error messages for similar filenames
    """
    errors = []
    template_names = [(t.stem, t) for t in templates]
    
    for i, (name1, path1) in enumerate(template_names):
        for j, (name2, path2) in enumerate(template_names[i+1:], i+1):
            if name1 != name2:
                distance = calculate_levenshtein_distance(name1.lower(), name2.lower())
                if distance < 3:
                    rel_path1 = path1.relative_to(Path("templates"))
                    rel_path2 = path2.relative_to(Path("templates"))
                    errors.append(
                        f"Similar template names detected: "
                        f"'{rel_path1}' and '{rel_path2}' "
                        f"(distance: {distance})"
                    )
    
    return errors


def validate_directory_structure(templates: List[Path]) -> List[str]:
    """
    Validate proper directory organization.
    
    Returns:
        List of warnings for templates that might be in wrong directories
    """
    warnings = []
    
    # Define expected directories and their purposes
    expected_dirs = {
        'layouts': ['modal', 'table', 'nav', 'form', 'component'],
        'setups': ['setup', 'trade', 'signal', 'ticker'],
        'trading': ['trade', 'order', 'portfolio', 'market'],
        'discord': ['discord', 'channel', 'message', 'bot']
    }
    
    for template in templates:
        if template.name == 'base.html':
            continue
            
        rel_path = template.relative_to(Path("templates"))
        template_name = template.stem.lower()
        
        # Check if template is in root but should be in subdirectory
        if len(rel_path.parts) == 1:  # Template is in root
            suggested_dir = None
            for dir_name, keywords in expected_dirs.items():
                if any(keyword in template_name for keyword in keywords):
                    suggested_dir = dir_name
                    break
            
            if suggested_dir:
                warnings.append(
                    f"Template '{rel_path}' might belong in '{suggested_dir}/' directory"
                )
        
        # Check if template is in wrong subdirectory
        elif len(rel_path.parts) > 1:
            current_dir = rel_path.parts[0]
            if current_dir in expected_dirs:
                keywords = expected_dirs[current_dir]
                if not any(keyword in template_name for keyword in keywords):
                    warnings.append(
                        f"Template '{rel_path}' might not belong in '{current_dir}/' directory"
                    )
    
    return warnings


def scan_templates() -> List[Path]:
    """Scan templates directory for all .html files."""
    templates = []
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("⚠️  WARNING: templates/ directory not found, creating it...")
        templates_dir.mkdir(exist_ok=True)
        return templates
    
    for template_file in templates_dir.rglob("*.html"):
        templates.append(template_file)
    
    return sorted(templates)


def main():
    """Run all template validations."""
    print("🔍 Validating templates...")
    
    templates = scan_templates()
    
    if not templates:
        print("❌ ERROR: No templates found")
        return 1
    
    print(f"📝 Found {len(templates)} templates")
    
    all_errors = []
    all_warnings = []
    
    # Validate each template
    for template in templates:
        rel_path = template.relative_to(Path("templates"))
        
        # Validate header comment
        has_header, header_error = validate_header_comment(template)
        if not has_header:
            all_errors.append(f"❌ {rel_path}: {header_error}")
        
        # Validate extends base.html
        extends_base, extends_error = validate_extends_base(template)
        if not extends_base:
            all_errors.append(f"❌ {rel_path}: {extends_error}")
    
    # Validate unique filenames
    filename_errors = validate_unique_filenames(templates)
    all_errors.extend([f"❌ {error}" for error in filename_errors])
    
    # Validate directory structure (warnings only)
    structure_warnings = validate_directory_structure(templates)
    all_warnings.extend([f"⚠️  {warning}" for warning in structure_warnings])
    
    # Report results
    if all_errors:
        print(f"\n❌ VALIDATION FAILED ({len(all_errors)} errors)")
        for error in all_errors:
            print(f"   {error}")
    
    if all_warnings:
        print(f"\n⚠️  WARNINGS ({len(all_warnings)} suggestions)")
        for warning in all_warnings:
            print(f"   {warning}")
    
    if not all_errors and not all_warnings:
        print("\n✅ All template validation checks passed!")
        return 0
    elif not all_errors:
        print(f"\n✅ All critical checks passed (with {len(all_warnings)} suggestions)")
        return 0
    else:
        print(f"\n💡 Fix these errors and run validation again")
        return 1


if __name__ == "__main__":
    exit(main())