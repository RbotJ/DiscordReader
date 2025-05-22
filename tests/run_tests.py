#!/usr/bin/env python
"""
Test runner script for A+ Trading App.

This script discovers and runs all tests in the tests directory structure.
Tests are categorized into:
- Unit tests: tests/unit/
- Integration tests: tests/integration/
- API tests: tests/api/
- Discord tests: tests/discord/
"""
import unittest
import sys
import os
import importlib.util
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

# Check that modules are importable
def check_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec:
        logger.error(f"Error: Could not find module {name} at {path}")
        return False
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return True
    except Exception as e:
        logger.error(f"Error importing {name}: {e}")
        return False

def run_tests():
    """
    Discover and run all tests across test categories.
    
    Test categories:
    - Unit tests (tests/unit/): Tests for individual components in isolation
    - Integration tests (tests/integration/): Tests for component interactions
    - API tests (tests/api/): Tests for API endpoints and functionality
    - Discord tests (tests/discord/): Tests for Discord integration features
    """
    logger.info("=" * 80)
    logger.info("Running A+ Trading App Tests")
    logger.info("=" * 80)
    logger.info(f"Project root: {project_root}")
    
    # Check core modules
    logger.info("\nVerifying modules:")
    core_modules = [
        ("features.setups.parser", os.path.join(project_root, "features/setups/parser.py")),
        ("features.setups.api", os.path.join(project_root, "features/setups/api.py")),
        ("common.models", os.path.join(project_root, "common/models.py")),
    ]
    for name, path in core_modules:
        if os.path.exists(path):
            logger.info(f"✓ Found {name} at {path}")
        else:
            logger.info(f"✗ Missing {name} at {path}")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    
    # Dictionary to store test results for each category
    results = {}
    
    # Run tests for each category
    categories = {
        'Unit': 'unit',
        'Integration': 'integration',
        'API': 'api',
        'Discord': 'discord'
    }
    
    for category_name, category_dir in categories.items():
        logger.info(f"\nRunning {category_name} Tests:")
        tests_dir = os.path.join(current_dir, category_dir)
        
        if not os.path.exists(tests_dir):
            logger.info(f"No {category_name.lower()} test directory found at {tests_dir}")
            results[category_name] = unittest.TestResult()
            continue
        
        try:
            logger.info(f"{category_name} tests directory: {tests_dir}")
            logger.info(f"Directory content: {os.listdir(tests_dir)}")
            
            tests = loader.discover(start_dir=tests_dir, pattern='test_*.py')
            results[category_name] = unittest.TextTestRunner(verbosity=2).run(tests)
        except Exception as e:
            logger.error(f"Failed to run {category_name.lower()} tests: {e}")
            results[category_name] = unittest.TestResult()
    
    # Summarize results
    logger.info("\n" + "=" * 80)
    logger.info("Test Summary")
    logger.info("=" * 80)
    
    total_errors = 0
    total_failures = 0
    total_run = 0
    
    for category, result in results.items():
        tests_run = result.testsRun
        errors = len(result.errors)
        failures = len(result.failures)
        total_run += tests_run
        total_errors += errors
        total_failures += failures
        
        logger.info(f"{category} Tests: {tests_run} run, {errors} errors, {failures} failures")
        
        # Log details of errors and failures if any
        if errors > 0 or failures > 0:
            logger.info(f"  Details for {category} test issues:")
            
            for i, (test, error) in enumerate(result.errors, 1):
                logger.info(f"  Error {i}: {test}")
                logger.info(f"  {error}")
                logger.info("-" * 40)
                
            for i, (test, failure) in enumerate(result.failures, 1):
                logger.info(f"  Failure {i}: {test}")
                logger.info(f"  {failure}")
                logger.info("-" * 40)
    
    logger.info(f"\nOverall: {total_run} tests run, {total_errors} errors, {total_failures} failures")
    logger.info("=" * 80)
    
    # Return success if no tests failed
    return total_errors + total_failures == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)