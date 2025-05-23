#!/usr/bin/env python3
"""
Template Usage Audit Tool

Discovers all templates, maps their references, and identifies unused or broken templates.
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

def discover_templates() -> List[str]:
    """Recursively scan templates directory for all template files."""
    template_files = []
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        return []
    
    for template_file in templates_dir.rglob("*.html"):
        template_files.append(str(template_file))
    
    for template_file in templates_dir.rglob("*.jinja"):
        template_files.append(str(template_file))
        
    for template_file in templates_dir.rglob("*.tpl"):
        template_files.append(str(template_file))
    
    return sorted(template_files)

def find_template_references() -> Dict[str, List[Dict[str, any]]]:
    """Search all Python files for template references."""
    references = {}
    
    # Patterns to search for
    patterns = [
        r'render_template\(["\']([^"\']+)["\']',
        r'TemplateResponse\(["\']([^"\']+)["\']',
        r'template_name\s*=\s*["\']([^"\']+)["\']',
    ]
    
    # Search Python files
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file) or ".cache" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    template_name = match.group(1)
                    
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    if template_name not in references:
                        references[template_name] = []
                    
                    references[template_name].append({
                        'file': str(py_file),
                        'line': line_num,
                        'type': 'render_template'
                    })
        except Exception:
            continue
    
    return references

def find_template_extends_includes() -> Dict[str, List[Dict[str, any]]]:
    """Search template files for extends and include references."""
    references = {}
    
    # Patterns for template inheritance and includes
    patterns = [
        r'{%\s*extends\s+["\']([^"\']+)["\']',
        r'{%\s*include\s+["\']([^"\']+)["\']',
        r'{% extends "([^"]+)" %}',
        r'{% include "([^"]+)" %}',
    ]
    
    templates = discover_templates()
    
    for template_path in templates:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    referenced_template = match.group(1)
                    
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    if referenced_template not in references:
                        references[referenced_template] = []
                    
                    references[referenced_template].append({
                        'file': template_path,
                        'line': line_num,
                        'type': 'template_inheritance'
                    })
        except Exception:
            continue
    
    return references

def find_similar_templates(templates: List[str]) -> List[Tuple[str, str]]:
    """Find templates with very similar names that might be duplicates."""
    similar_pairs = []
    
    for i, template1 in enumerate(templates):
        name1 = Path(template1).name
        base1 = name1.split('.')[0]
        
        for template2 in templates[i+1:]:
            name2 = Path(template2).name
            base2 = name2.split('.')[0]
            
            # Check for very similar names
            if (name1 != name2 and 
                (base1.replace('_', '').replace('-', '') == base2.replace('_', '').replace('-', '') or
                 base1 in base2 or base2 in base1 or
                 abs(len(base1) - len(base2)) <= 1)):
                similar_pairs.append((template1, template2))
    
    return similar_pairs

def audit_templates():
    """Run complete template audit and return results."""
    
    # Discover all templates
    templates = discover_templates()
    
    # Find references from Python files
    py_references = find_template_references()
    
    # Find references from template files (extends/includes)
    template_references = find_template_extends_includes()
    
    # Merge all references
    all_references = {}
    for template, refs in py_references.items():
        all_references[template] = refs
    
    for template, refs in template_references.items():
        if template in all_references:
            all_references[template].extend(refs)
        else:
            all_references[template] = refs
    
    # Normalize template paths for comparison
    template_names = set()
    for template in templates:
        # Add both full path and just filename
        template_names.add(template)
        template_names.add(Path(template).name)
        # Add path relative to templates/ directory
        if template.startswith('templates/'):
            template_names.add(template[10:])  # Remove 'templates/' prefix
    
    # Find used templates
    used_templates = {}
    for template_ref, locations in all_references.items():
        # Try to match references to actual templates
        matched = False
        for template in templates:
            if (template_ref == template or 
                template_ref == Path(template).name or
                template.endswith('/' + template_ref)):
                used_templates[template] = locations
                matched = True
                break
        
        if not matched:
            # This is a broken reference
            if template_ref not in used_templates:
                used_templates[template_ref] = locations
    
    # Find unused templates
    unused_templates = []
    for template in templates:
        if template not in used_templates:
            # Check if referenced by filename only
            template_name = Path(template).name
            relative_path = template[10:] if template.startswith('templates/') else template
            
            found = False
            for ref in all_references.keys():
                if ref == template_name or ref == relative_path:
                    found = True
                    break
            
            if not found:
                unused_templates.append(template)
    
    # Find broken references
    broken_references = []
    for template_ref, locations in all_references.items():
        # Check if this reference points to an existing template
        exists = False
        for template in templates:
            if (template_ref == template or 
                template_ref == Path(template).name or
                template.endswith('/' + template_ref)):
                exists = True
                break
        
        if not exists:
            for location in locations:
                broken_references.append({
                    'reference': template_ref,
                    'file': location['file'],
                    'line': location['line']
                })
    
    # Find similar templates
    similar_templates = find_similar_templates(templates)
    
    return {
        'used_templates': used_templates,
        'unused_templates': unused_templates,
        'broken_references': broken_references,
        'similar_templates': similar_templates,
        'total_templates': len(templates),
        'total_references': sum(len(refs) for refs in all_references.values())
    }

def generate_markdown_report(audit_results):
    """Generate human-readable markdown report."""
    
    report = "# Template Usage Audit Report\n\n"
    
    # Summary
    report += "## Summary\n\n"
    report += f"- **Total Templates**: {audit_results['total_templates']}\n"
    report += f"- **Total References**: {audit_results['total_references']}\n"
    report += f"- **Used Templates**: {len(audit_results['used_templates'])}\n"
    report += f"- **Unused Templates**: {len(audit_results['unused_templates'])}\n"
    report += f"- **Broken References**: {len(audit_results['broken_references'])}\n"
    report += f"- **Similar Template Pairs**: {len(audit_results['similar_templates'])}\n\n"
    
    # Used templates
    if audit_results['used_templates']:
        report += "## Used Templates\n\n"
        for template, locations in audit_results['used_templates'].items():
            report += f"### `{template}`\n"
            report += f"Referenced {len(locations)} time(s):\n"
            for loc in locations:
                report += f"- `{loc['file']}:{loc['line']}` ({loc['type']})\n"
            report += "\n"
    
    # Unused templates
    if audit_results['unused_templates']:
        report += "## ⚠️ Unused Templates\n\n"
        report += "These templates have no references and might be safe to remove:\n\n"
        for template in audit_results['unused_templates']:
            report += f"- `{template}`\n"
        report += "\n"
    
    # Broken references
    if audit_results['broken_references']:
        report += "## 🚨 Broken References\n\n"
        report += "These references point to non-existent templates:\n\n"
        for broken in audit_results['broken_references']:
            report += f"- `{broken['reference']}` in `{broken['file']}:{broken['line']}`\n"
        report += "\n"
    
    # Similar templates
    if audit_results['similar_templates']:
        report += "## 🔍 Similar Template Names\n\n"
        report += "These templates have similar names and might be duplicates:\n\n"
        for template1, template2 in audit_results['similar_templates']:
            report += f"- `{template1}` ↔ `{template2}`\n"
        report += "\n"
    
    # Recommendations
    report += "## Recommendations\n\n"
    
    if audit_results['unused_templates']:
        report += "### Cleanup Unused Templates\n"
        report += "Consider removing unused templates to reduce clutter:\n"
        for template in audit_results['unused_templates']:
            report += f"```bash\nrm {template}\n```\n"
        report += "\n"
    
    if audit_results['broken_references']:
        report += "### Fix Broken References\n"
        report += "Update these references to point to existing templates or create the missing templates.\n\n"
    
    if audit_results['similar_templates']:
        report += "### Review Similar Templates\n"
        report += "Check if these similar templates can be consolidated:\n"
        for template1, template2 in audit_results['similar_templates']:
            report += f"- Compare `{template1}` and `{template2}` for potential merging\n"
        report += "\n"
    
    if not audit_results['unused_templates'] and not audit_results['broken_references']:
        report += "✅ **Great!** No cleanup needed - all templates are properly used and referenced.\n\n"
    
    return report

def main():
    """Run template audit and output results."""
    print("🔍 Running Template Usage Audit...")
    
    audit_results = audit_templates()
    
    # Generate JSON report
    json_report = json.dumps(audit_results, indent=2)
    
    # Generate markdown report
    markdown_report = generate_markdown_report(audit_results)
    
    # Save reports
    with open('template_audit.json', 'w') as f:
        f.write(json_report)
    
    with open('template_audit.md', 'w') as f:
        f.write(markdown_report)
    
    print("📊 Audit complete!")
    print("\n" + "="*50)
    print("JSON REPORT:")
    print("="*50)
    print(json_report)
    
    print("\n" + "="*50)
    print("MARKDOWN REPORT:")
    print("="*50)
    print(markdown_report)

if __name__ == "__main__":
    main()