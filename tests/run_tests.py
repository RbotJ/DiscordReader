#!/usr/bin/env python
"""
Test runner script for A+ Trading App.

This script discovers and runs all tests in the tests directory.
"""
import unittest
import sys
import os
import importlib.util

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

# Check that modules are importable
def check_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec:
        print(f"Error: Could not find module {name} at {path}")
        return False
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return True
    except Exception as e:
        print(f"Error importing {name}: {e}")
        return False

def run_tests():
    """Discover and run all tests."""
    print("=" * 80)
    print("Running A+ Trading App Tests")
    print("=" * 80)
    print(f"Project root: {project_root}")
    
    # Check core modules
    print("\nVerifying modules:")
    core_modules = [
        ("features.setups.parser", os.path.join(project_root, "features/setups/parser.py")),
        ("features.setups.api", os.path.join(project_root, "features/setups/api.py")),
        ("common.models", os.path.join(project_root, "common/models.py")),
    ]
    for name, path in core_modules:
        if os.path.exists(path):
            print(f"✓ Found {name} at {path}")
        else:
            print(f"✗ Missing {name} at {path}")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    
    # Run unit tests
    print("\nRunning Unit Tests:")
    unit_tests_dir = os.path.join(current_dir, 'unit')
    unit_tests = loader.discover(start_dir=unit_tests_dir, pattern='test_*.py')
    unit_result = unittest.TextTestRunner(verbosity=2).run(unit_tests)
    
    # Run integration tests
    print("\nRunning Integration Tests:")
    integration_tests_dir = os.path.join(current_dir, 'integration')
    
    # Debug info
    print(f"Integration tests directory: {integration_tests_dir}")
    print(f"Directory exists: {os.path.exists(integration_tests_dir)}")
    print(f"Directory content: {os.listdir(integration_tests_dir)}")
    
    try:
        # Use absolute path and check if it exists
        abs_integration_dir = os.path.abspath(integration_tests_dir)
        if not os.path.exists(abs_integration_dir):
            print(f"Error: Integration tests directory {abs_integration_dir} not found.")
            integration_result = unittest.TestResult()
        else:
            # Manually create suite for integration tests
            integration_suite = unittest.TestSuite()
            for test_file in os.listdir(abs_integration_dir):
                if test_file.startswith('test_') and test_file.endswith('.py'):
                    module_name = f"tests.integration.{test_file[:-3]}"
                    try:
                        module = __import__(module_name, fromlist=['*'])
                        for name in dir(module):
                            obj = getattr(module, name)
                            if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                                integration_suite.addTests(loader.loadTestsFromTestCase(obj))
                    except Exception as e:
                        print(f"Error loading test {module_name}: {e}")
                        
            integration_result = unittest.TextTestRunner(verbosity=2).run(integration_suite)
    except Exception as e:
        print(f"Failed to run integration tests: {e}")
        integration_result = unittest.TestResult()
    
    # Summarize results
    print("\n" + "=" * 80)
    print(f"Unit Tests: {unit_result.testsRun} run, {len(unit_result.errors)} errors, {len(unit_result.failures)} failures")
    print(f"Integration Tests: {integration_result.testsRun} run, {len(integration_result.errors)} errors, {len(integration_result.failures)} failures")
    print("=" * 80)
    
    # Return success if no tests failed
    return (len(unit_result.errors) + len(unit_result.failures) + 
            len(integration_result.errors) + len(integration_result.failures)) == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)