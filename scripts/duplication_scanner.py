#!/usr/bin/env python3
"""
Comprehensive Duplication Scanner

Identifies specific duplications across the trading application codebase
for systematic elimination and consolidation.
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import ast

def scan_import_duplications():
    """Find duplicate import statements across files."""
    imports_map = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find import statements
            import_patterns = [
                r'^import\s+([^\s]+)',
                r'^from\s+([^\s]+)\s+import',
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches:
                    imports_map[match].append(str(py_file))
                    
        except (UnicodeDecodeError, PermissionError, FileNotFoundError):
            continue
    
    # Find commonly duplicated imports
    duplicated_imports = []
    for import_name, files in imports_map.items():
        if len(files) >= 3:  # Used in 3+ files
            duplicated_imports.append((import_name, len(files), files[:5]))  # Limit to 5 examples
    
    return sorted(duplicated_imports, key=lambda x: x[1], reverse=True)

def scan_function_duplications():
    """Find duplicate or very similar function names."""
    function_map = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Find function definitions
            functions = re.findall(r'def\s+(\w+)\s*\(', content)
            
            for func_name in functions:
                if not func_name.startswith('_'):  # Skip private functions
                    function_map[func_name].append(str(py_file))
                    
        except Exception:
            continue
    
    # Find duplicate function names
    duplicated_functions = []
    for func_name, files in function_map.items():
        if len(files) > 1:
            duplicated_functions.append((func_name, files))
    
    return duplicated_functions

def scan_database_query_patterns():
    """Find duplicate database query patterns."""
    query_patterns = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Common database query patterns
            patterns = [
                r'\.query\(["\']([^"\']+)["\']',
                r'SELECT\s+([^FROM]+)\s+FROM',
                r'INSERT\s+INTO\s+(\w+)',
                r'UPDATE\s+(\w+)\s+SET',
                r'DELETE\s+FROM\s+(\w+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    query_patterns[match.strip()].append(str(py_file))
                    
        except Exception:
            continue
    
    # Find repeated query patterns
    duplicated_queries = []
    for pattern, files in query_patterns.items():
        if len(files) > 1:
            duplicated_queries.append((pattern, files))
    
    return duplicated_queries

def scan_error_handling_patterns():
    """Find duplicate error handling code."""
    error_patterns = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Common error handling patterns
            patterns = [
                r'except\s+(\w+Exception)',
                r'raise\s+(\w+Exception)',
                r'try:\s*\n.*?except.*?:',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    if isinstance(match, str) and len(match) < 100:  # Avoid huge matches
                        error_patterns[match].append(str(py_file))
                    
        except Exception:
            continue
    
    # Find repeated error patterns
    duplicated_errors = []
    for pattern, files in error_patterns.items():
        if len(files) > 1:
            duplicated_errors.append((pattern, files))
    
    return duplicated_errors

def scan_api_endpoint_patterns():
    """Find similar API endpoint patterns."""
    route_patterns = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Find route definitions
            routes = re.findall(r'@\w*\.route\(["\']([^"\']+)["\']', content)
            
            for route in routes:
                route_patterns[route].append(str(py_file))
                    
        except Exception:
            continue
    
    # Find duplicate routes
    duplicated_routes = []
    for route, files in route_patterns.items():
        if len(files) > 1:
            duplicated_routes.append((route, files))
    
    return duplicated_routes

def scan_configuration_duplications():
    """Find duplicate configuration patterns."""
    config_patterns = defaultdict(list)
    
    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".cache", ".pythonlibs"]):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Configuration patterns
            patterns = [
                r'os\.environ\.get\(["\']([^"\']+)["\']',
                r'config\[["\']([^"\']+)["\']',
                r'DATABASE_URL',
                r'API_KEY',
                r'SECRET_KEY',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    config_patterns[match].append(str(py_file))
                    
        except Exception:
            continue
    
    # Find repeated config patterns
    duplicated_configs = []
    for pattern, files in config_patterns.items():
        if len(files) > 2:  # Used in 3+ files
            duplicated_configs.append((pattern, files))
    
    return duplicated_configs

def main():
    """Run comprehensive duplication analysis."""
    print("🔍 Scanning for Duplications Across Trading Application...\n")
    
    # 1. Import Duplications
    print("📦 IMPORT DUPLICATIONS:")
    import_dups = scan_import_duplications()
    for import_name, count, files in import_dups[:10]:  # Top 10
        print(f"   • {import_name}: used in {count} files")
        for file in files[:3]:  # Show first 3 files
            print(f"     - {file}")
        if len(files) > 3:
            print(f"     ... and {len(files) - 3} more")
        print()
    
    # 2. Function Duplications
    print("\n🔧 FUNCTION NAME DUPLICATIONS:")
    func_dups = scan_function_duplications()
    for func_name, files in func_dups[:10]:
        print(f"   • {func_name}: found in {len(files)} files")
        for file in files:
            print(f"     - {file}")
        print()
    
    # 3. Database Query Duplications
    print("\n🗃️ DATABASE QUERY PATTERN DUPLICATIONS:")
    query_dups = scan_database_query_patterns()
    for pattern, files in query_dups[:5]:
        print(f"   • '{pattern}': found in {len(files)} files")
        for file in files:
            print(f"     - {file}")
        print()
    
    # 4. API Route Duplications
    print("\n🌐 API ROUTE DUPLICATIONS:")
    route_dups = scan_api_endpoint_patterns()
    for route, files in route_dups:
        print(f"   🚨 CRITICAL: Route '{route}' defined in multiple files:")
        for file in files:
            print(f"     - {file}")
        print()
    
    # 5. Configuration Duplications
    print("\n⚙️ CONFIGURATION DUPLICATIONS:")
    config_dups = scan_configuration_duplications()
    for config, files in config_dups[:5]:
        print(f"   • {config}: used in {len(files)} files")
        for file in files[:3]:
            print(f"     - {file}")
        if len(files) > 3:
            print(f"     ... and {len(files) - 3} more")
        print()
    
    # 6. Error Handling Duplications
    print("\n❌ ERROR HANDLING DUPLICATIONS:")
    error_dups = scan_error_handling_patterns()
    for pattern, files in error_dups[:5]:
        print(f"   • {pattern}: found in {len(files)} files")
        for file in files[:2]:
            print(f"     - {file}")
        if len(files) > 2:
            print(f"     ... and {len(files) - 2} more")
        print()
    
    # Summary
    total_duplications = (len(import_dups) + len(func_dups) + len(query_dups) + 
                         len(route_dups) + len(config_dups) + len(error_dups))
    
    print(f"\n📊 SUMMARY:")
    print(f"   • Import duplications: {len(import_dups)}")
    print(f"   • Function duplications: {len(func_dups)}")
    print(f"   • Database query duplications: {len(query_dups)}")
    print(f"   • Route duplications: {len(route_dups)} ⚠️")
    print(f"   • Configuration duplications: {len(config_dups)}")
    print(f"   • Error handling duplications: {len(error_dups)}")
    print(f"   • Total duplications found: {total_duplications}")
    
    if route_dups:
        print(f"\n🚨 CRITICAL: {len(route_dups)} duplicate routes found - these need immediate attention!")
    
    return 0

if __name__ == "__main__":
    exit(main())