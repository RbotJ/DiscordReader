#!/usr/bin/env python3
"""
Template Registry Generator

Recursively scans templates/ for all .html files, parses metadata from header comments,
and generates a comprehensive templates/README.md with template documentation.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def parse_template_metadata(template_path: Path) -> Dict[str, str]:
    """
    Parse metadata from template header comments.
    
    Expected format:
    <!--
    Template: Template Name
    Purpose: Brief description of what this template does
    Used by: List of routes/views that use this template
    Dependencies: Other templates this depends on
    -->
    """
    metadata = {
        'template': '',
        'purpose': '',
        'used_by': '',
        'dependencies': '',
        'has_header': False
    }
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for header comment block
        header_match = re.search(r'<!--\s*(.*?)\s*-->', content, re.DOTALL)
        if not header_match:
            return metadata
            
        header_content = header_match.group(1)
        metadata['has_header'] = True
        
        # Parse each metadata field
        for line in header_content.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in metadata:
                    metadata[key] = value
                    
    except Exception as e:
        print(f"Warning: Could not parse {template_path}: {e}")
        
    return metadata


def scan_templates() -> List[Tuple[Path, Dict[str, str]]]:
    """Recursively scan templates directory for all .html files."""
    templates = []
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("Warning: templates/ directory not found")
        return templates
    
    for template_file in templates_dir.rglob("*.html"):
        metadata = parse_template_metadata(template_file)
        templates.append((template_file, metadata))
    
    return sorted(templates, key=lambda x: str(x[0]))


def generate_readme_content(templates: List[Tuple[Path, Dict[str, str]]]) -> str:
    """Generate README.md content from template data."""
    
    total_templates = len(templates)
    templates_with_headers = sum(1 for _, meta in templates if meta['has_header'])
    templates_without_headers = total_templates - templates_with_headers
    
    readme_content = f"""# Template Registry

*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Summary

- **Total Templates**: {total_templates}
- **With Header Documentation**: {templates_with_headers}
- **Missing Header Documentation**: {templates_without_headers}

## Template Inventory

| Template | Location | Purpose | Used By | Dependencies |
|----------|----------|---------|---------|--------------|
"""
    
    # Add table rows for each template
    for template_path, metadata in templates:
        # Get relative path from templates/
        rel_path = template_path.relative_to(Path("templates"))
        
        # Format template name
        template_name = metadata.get('template', '') or rel_path.stem.replace('_', ' ').title()
        
        # Truncate long values for table readability
        purpose = metadata.get('purpose', 'No description')[:80]
        if len(metadata.get('purpose', '')) > 80:
            purpose += '...'
            
        used_by = metadata.get('used_by', 'Not documented')[:60]
        if len(metadata.get('used_by', '')) > 60:
            used_by += '...'
            
        dependencies = metadata.get('dependencies', 'None')[:50]
        if len(metadata.get('dependencies', '')) > 50:
            dependencies += '...'
        
        readme_content += f"| {template_name} | `{rel_path}` | {purpose} | {used_by} | {dependencies} |\n"
    
    # Add section for templates missing headers
    if templates_without_headers > 0:
        readme_content += f"\n## Templates Missing Header Documentation\n\n"
        readme_content += "The following templates need header comment blocks with metadata:\n\n"
        
        for template_path, metadata in templates:
            if not metadata['has_header']:
                rel_path = template_path.relative_to(Path("templates"))
                readme_content += f"- `{rel_path}`\n"
        
        readme_content += "\n### Expected Header Format\n\n"
        readme_content += """```html
<!--
Template: Your Template Name
Purpose: Brief description of what this template does
Used by: List of routes/views that use this template
Dependencies: Other templates this depends on (e.g., base.html, modals/_confirm.html)
-->
```
"""
    
    # Add directory structure
    readme_content += "\n## Directory Structure\n\n"
    readme_content += """```
templates/
├── base.html              # Main layout template
├── layouts/               # Shared layout components
│   ├── _modal.html        # Modal dialogs
│   ├── _table.html        # Data tables
│   └── _navigation.html   # Navigation components
├── setups/                # Trading setup views
├── trading/               # Trading interface views
└── discord/               # Discord integration views
```
"""
    
    # Add best practices
    readme_content += "\n## Template Best Practices\n\n"
    readme_content += """1. **Always extend base.html**: Every template should start with `{% extends "base.html" %}`
2. **Add header documentation**: Include metadata in HTML comment block at the top
3. **Use semantic naming**: Template names should clearly indicate their purpose
4. **Organize by feature**: Place templates in appropriate subdirectories
5. **Document dependencies**: List any templates this one includes or extends
6. **Keep it DRY**: Extract common elements into layout components

## Validation

Run the template validation script to check for issues:

```bash
python scripts/validate_templates.py
```

This will verify:
- All templates extend base.html
- All templates have header documentation
- No duplicate or similar template names
- Proper directory organization
"""
    
    return readme_content


def main():
    """Generate template registry and update README.md."""
    print("🔍 Scanning templates directory...")
    
    templates = scan_templates()
    
    if not templates:
        print("❌ No templates found in templates/ directory")
        return 1
    
    print(f"📝 Found {len(templates)} templates")
    
    # Generate README content
    readme_content = generate_readme_content(templates)
    
    # Write to templates/README.md
    readme_path = Path("templates/README.md")
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✅ Generated {readme_path}")
    except Exception as e:
        print(f"❌ Failed to write {readme_path}: {e}")
        return 1
    
    # Summary
    templates_with_headers = sum(1 for _, meta in templates if meta['has_header'])
    templates_without_headers = len(templates) - templates_with_headers
    
    print(f"\n📊 Summary:")
    print(f"   • Total templates: {len(templates)}")
    print(f"   • With documentation: {templates_with_headers}")
    print(f"   • Missing documentation: {templates_without_headers}")
    
    if templates_without_headers > 0:
        print(f"\n⚠️  {templates_without_headers} templates need header documentation")
    
    return 0


if __name__ == "__main__":
    exit(main())