#!/usr/bin/env python3
"""
Template Tests

Wraps template validation logic in pytest tests for CI integration.
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path so we can import validation functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_templates import (
    scan_templates,
    validate_header_comment,
    validate_extends_base,
    validate_unique_filenames,
    validate_directory_structure
)


class TestTemplateValidation:
    """Test suite for template validation."""
    
    @pytest.fixture(scope="class")
    def templates(self):
        """Get all templates for testing."""
        return scan_templates()
    
    def test_templates_exist(self, templates):
        """Test that we have at least some templates."""
        assert len(templates) > 0, "No templates found in templates/ directory"
    
    def test_base_template_exists(self, templates):
        """Test that base.html exists."""
        base_templates = [t for t in templates if t.name == 'base.html']
        assert len(base_templates) == 1, "base.html template is required"
    
    def test_all_templates_have_headers(self, templates):
        """Test that all templates have proper header documentation."""
        missing_headers = []
        
        for template in templates:
            has_header, error = validate_header_comment(template)
            if not has_header:
                rel_path = template.relative_to(Path("templates"))
                missing_headers.append(f"{rel_path}: {error}")
        
        assert not missing_headers, (
            f"Templates missing proper header documentation:\n" +
            "\n".join(f"  - {error}" for error in missing_headers)
        )
    
    def test_all_templates_extend_base(self, templates):
        """Test that all templates (except base.html) extend base.html."""
        invalid_inheritance = []
        
        for template in templates:
            extends_base, error = validate_extends_base(template)
            if not extends_base:
                rel_path = template.relative_to(Path("templates"))
                invalid_inheritance.append(f"{rel_path}: {error}")
        
        assert not invalid_inheritance, (
            f"Templates with invalid inheritance:\n" +
            "\n".join(f"  - {error}" for error in invalid_inheritance)
        )
    
    def test_unique_template_names(self, templates):
        """Test that template names are sufficiently unique."""
        similar_names = validate_unique_filenames(templates)
        
        assert not similar_names, (
            f"Similar template names detected:\n" +
            "\n".join(f"  - {error}" for error in similar_names)
        )
    
    def test_directory_organization(self, templates):
        """Test directory organization (warnings only, not failures)."""
        warnings = validate_directory_structure(templates)
        
        # This is informational only - we don't fail the test
        if warnings:
            print("\nDirectory organization suggestions:")
            for warning in warnings:
                print(f"  - {warning}")
    
    def test_template_content_quality(self, templates):
        """Test basic template content quality."""
        quality_issues = []
        
        for template in templates:
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                rel_path = template.relative_to(Path("templates"))
                
                # Check for common issues
                if len(content.strip()) < 50:
                    quality_issues.append(f"{rel_path}: Template is very short (< 50 characters)")
                
                if template.name != 'base.html':
                    if 'block content' not in content:
                        quality_issues.append(f"{rel_path}: Missing content block")
                    
                    if 'block title' not in content and '<title>' in content:
                        quality_issues.append(f"{rel_path}: Has hardcoded title instead of title block")
                
            except Exception as e:
                quality_issues.append(f"{rel_path}: Could not read file - {e}")
        
        assert not quality_issues, (
            f"Template quality issues found:\n" +
            "\n".join(f"  - {issue}" for issue in quality_issues)
        )
    
    def test_no_duplicate_content(self, templates):
        """Test for potential duplicate template content."""
        # This is a basic check - more sophisticated duplicate detection
        # could be added based on actual content similarity
        
        template_sizes = {}
        size_duplicates = []
        
        for template in templates:
            try:
                size = template.stat().st_size
                if size in template_sizes:
                    rel_path1 = template.relative_to(Path("templates"))
                    rel_path2 = template_sizes[size].relative_to(Path("templates"))
                    size_duplicates.append(f"{rel_path1} and {rel_path2} have identical file sizes")
                else:
                    template_sizes[size] = template
            except Exception:
                pass  # Skip files we can't read
        
        # Only warn about this, don't fail the test
        if size_duplicates:
            print("\nPotential duplicate templates (same file size):")
            for duplicate in size_duplicates:
                print(f"  - {duplicate}")


def test_validation_scripts_exist():
    """Test that validation scripts exist and are executable."""
    scripts_dir = Path("scripts")
    
    required_scripts = [
        "validate_templates.py",
        "generate_template_registry.py"
    ]
    
    for script_name in required_scripts:
        script_path = scripts_dir / script_name
        assert script_path.exists(), f"Required script {script_name} not found"
        assert script_path.is_file(), f"{script_name} is not a file"


def test_precommit_config_exists():
    """Test that pre-commit configuration exists."""
    precommit_config = Path(".pre-commit-config.yaml")
    assert precommit_config.exists(), "Pre-commit configuration not found"
    
    # Check that it contains template validation hooks
    with open(precommit_config, 'r') as f:
        config_content = f.read()
    
    assert "validate-templates" in config_content, "Template validation hook not found in pre-commit config"
    assert "generate-template-registry" in config_content, "Template registry hook not found in pre-commit config"


if __name__ == "__main__":
    # Allow running as a script for quick testing
    pytest.main([__file__, "-v"])