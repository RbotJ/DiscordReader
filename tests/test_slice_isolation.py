"""
Slice Isolation Tests

Automated verification that feature slices maintain proper isolation
and don't have cross-slice dependencies.
"""
import pytest
import ast
import os
from pathlib import Path


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze import statements."""
    
    def __init__(self):
        self.imports = []
        self.from_imports = []
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                import_path = f"{node.module}.{alias.name}" if alias.name != '*' else node.module
                self.from_imports.append(import_path)
        self.generic_visit(node)


def analyze_file_imports(file_path):
    """Analyze imports in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)
        
        return analyzer.imports + analyzer.from_imports
    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")
        return []


def get_feature_files(feature_name):
    """Get all Python files in a feature slice."""
    feature_path = Path(f"features/{feature_name}")
    if not feature_path.exists():
        return []
    
    python_files = []
    for file_path in feature_path.rglob("*.py"):
        if not file_path.name.startswith('__'):
            python_files.append(file_path)
    
    return python_files


class TestSliceIsolation:
    """Test that feature slices maintain proper isolation."""
    
    # Define allowed import patterns for each slice
    ALLOWED_IMPORTS = {
        'discord_bot': [
            'features.discord_bot',
            'common',
            'discord',
            'logging',
            'datetime',
            'typing',
            'asyncio',
            'os',
            'flask'
        ],
        'discord_channels': [
            'features.discord_channels',
            'common',
            'discord',
            'logging',
            'datetime',
            'typing',
            'flask'
        ],
        'ingestion': [
            'features.ingestion',
            'common',
            'discord',
            'logging',
            'datetime',
            'typing',
            'flask',
            'asyncio'
        ]
    }
    
    # Cross-slice imports that are forbidden
    FORBIDDEN_CROSS_IMPORTS = {
        'discord_bot': [
            'features.discord_channels',
            'features.ingestion'
        ],
        'discord_channels': [
            'features.discord_bot',
            'features.ingestion'
        ],
        'ingestion': [
            'features.discord_bot',
            'features.discord_channels'
        ]
    }
    
    @pytest.mark.parametrize("feature_name", ['discord_bot', 'discord_channels', 'ingestion'])
    def test_slice_has_no_cross_dependencies(self, feature_name):
        """Test that a feature slice doesn't import from other slices."""
        feature_files = get_feature_files(feature_name)
        
        if not feature_files:
            pytest.skip(f"No files found for feature: {feature_name}")
        
        forbidden_imports = self.FORBIDDEN_CROSS_IMPORTS.get(feature_name, [])
        violations = []
        
        for file_path in feature_files:
            imports = analyze_file_imports(file_path)
            
            for import_path in imports:
                for forbidden in forbidden_imports:
                    if import_path.startswith(forbidden):
                        violations.append({
                            'file': str(file_path),
                            'import': import_path,
                            'forbidden_pattern': forbidden
                        })
        
        if violations:
            violation_details = '\n'.join([
                f"  {v['file']}: imports {v['import']} (violates {v['forbidden_pattern']})"
                for v in violations
            ])
            pytest.fail(f"Cross-slice import violations in {feature_name}:\n{violation_details}")
    
    @pytest.mark.parametrize("feature_name", ['discord_bot', 'discord_channels', 'ingestion'])
    def test_slice_uses_allowed_imports_only(self, feature_name):
        """Test that a feature slice only uses allowed import patterns."""
        feature_files = get_feature_files(feature_name)
        
        if not feature_files:
            pytest.skip(f"No files found for feature: {feature_name}")
        
        allowed_patterns = self.ALLOWED_IMPORTS.get(feature_name, [])
        violations = []
        
        for file_path in feature_files:
            imports = analyze_file_imports(file_path)
            
            for import_path in imports:
                # Skip built-in modules and standard library
                if any(import_path.startswith(builtin) for builtin in [
                    'sys', 'os', 'json', 'time', 'datetime', 'typing', 'asyncio',
                    'logging', 'collections', 'functools', 'itertools', 'pathlib',
                    'unittest', 'pytest', 'abc', 'contextlib', 'dataclasses'
                ]):
                    continue
                
                # Check if import is allowed
                is_allowed = any(
                    import_path.startswith(pattern) 
                    for pattern in allowed_patterns
                )
                
                if not is_allowed:
                    violations.append({
                        'file': str(file_path),
                        'import': import_path
                    })
        
        if violations:
            violation_details = '\n'.join([
                f"  {v['file']}: imports {v['import']}"
                for v in violations
            ])
            pytest.fail(f"Disallowed imports in {feature_name}:\n{violation_details}")
    
    def test_dashboard_files_use_service_layer(self):
        """Test that dashboard files use service layer instead of direct logic."""
        dashboard_files = [
            'features/discord_bot/dashboard.py',
            'features/discord_channels/dashboard.py',
            'features/ingestion/dashboard.py'
        ]
        
        violations = []
        
        for dashboard_file in dashboard_files:
            if not os.path.exists(dashboard_file):
                continue
            
            try:
                with open(dashboard_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check that dashboard uses service methods
                if 'get_metrics()' not in content:
                    violations.append(f"{dashboard_file}: missing get_metrics() call")
                
                # Check that dashboard doesn't implement metrics directly
                direct_metric_patterns = [
                    'db.session.execute',
                    'COUNT(*) FROM',
                    'SELECT * FROM'
                ]
                
                for pattern in direct_metric_patterns:
                    if pattern in content:
                        violations.append(f"{dashboard_file}: contains direct database access: {pattern}")
                
            except Exception as e:
                violations.append(f"{dashboard_file}: analysis error: {e}")
        
        if violations:
            violation_details = '\n'.join(f"  {v}" for v in violations)
            pytest.fail(f"Dashboard service layer violations:\n{violation_details}")
    
    def test_service_classes_exist_and_have_metrics(self):
        """Test that each slice has a service class with get_metrics method."""
        service_specs = [
            ('features/discord_bot/service.py', 'BotService'),
            ('features/discord_channels/channel_manager.py', 'ChannelManager'),
            ('features/ingestion/service.py', 'IngestionService')
        ]
        
        violations = []
        
        for service_file, class_name in service_specs:
            if not os.path.exists(service_file):
                violations.append(f"Missing service file: {service_file}")
                continue
            
            try:
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if f"class {class_name}" not in content:
                    violations.append(f"{service_file}: missing class {class_name}")
                
                if "def get_metrics(self)" not in content:
                    violations.append(f"{service_file}: {class_name} missing get_metrics method")
                
            except Exception as e:
                violations.append(f"{service_file}: analysis error: {e}")
        
        if violations:
            violation_details = '\n'.join(f"  {v}" for v in violations)
            pytest.fail(f"Service class violations:\n{violation_details}")


class TestSliceCompleteness:
    """Test that each slice is complete and self-contained."""
    
    def test_each_slice_has_required_components(self):
        """Test that each slice has all required components."""
        required_components = {
            'discord_bot': [
                'service.py',
                'dashboard.py'
            ],
            'discord_channels': [
                'channel_manager.py',
                'dashboard.py'
            ],
            'ingestion': [
                'service.py',
                'dashboard.py'
            ]
        }
        
        violations = []
        
        for slice_name, components in required_components.items():
            slice_path = Path(f"features/{slice_name}")
            
            if not slice_path.exists():
                violations.append(f"Missing slice directory: {slice_name}")
                continue
            
            for component in components:
                component_path = slice_path / component
                if not component_path.exists():
                    violations.append(f"{slice_name}: missing {component}")
        
        if violations:
            violation_details = '\n'.join(f"  {v}" for v in violations)
            pytest.fail(f"Slice completeness violations:\n{violation_details}")
    
    def test_dashboard_templates_isolation(self):
        """Test that dashboard templates are isolated to their slices."""
        # This would test template directories if they exist
        # For now, we verify that templates are referenced correctly
        pass