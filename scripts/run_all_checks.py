
#!/usr/bin/env python3
"""
Master Script Runner

Runs all validation and check scripts in the correct order and reports results.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_script(script_name, description, required=True):
    """Run a script and handle the result."""
    script_path = Path("scripts") / script_name
    
    if not script_path.exists():
        print(f"⚠️  {description}: Script not found ({script_path})")
        return not required
    
    print(f"🔄 Running {description}...")
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ {description}: PASSED")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}...")
            return True
        else:
            print(f"❌ {description}: FAILED (exit code {result.returncode})")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()[:200]}...")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description}: TIMEOUT (>60s)")
        return False
    except Exception as e:
        print(f"💥 {description}: EXCEPTION ({e})")
        return False

def main():
    """Run all validation scripts."""
    print("🚀 Running All Validation Scripts\n")
    
    # Define scripts to run in order
    scripts = [
        ("check_migrations.py", "Migration Status Check", True),
        ("validate_migrations.py", "Migration Validation", False),
        ("validate_templates.py", "Template Validation", False),
        ("integration_checklist.py", "Integration Checklist", False),
        ("duplication_scanner.py", "Duplication Scanner", False),
        ("template_audit.py", "Template Audit", False),
        ("generate_template_registry.py", "Template Registry Generation", False),
    ]
    
    results = []
    
    for script_file, description, required in scripts:
        success = run_script(script_file, description, required)
        results.append((description, success, required))
        print()  # Add spacing
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    critical_failed = 0
    
    for description, success, required in results:
        status = "✅ PASS" if success else "❌ FAIL"
        importance = " (CRITICAL)" if required else " (optional)"
        print(f"{status} {description}{importance}")
        
        if success:
            passed += 1
        else:
            failed += 1
            if required:
                critical_failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if critical_failed > 0:
        print(f"🚨 {critical_failed} critical failures detected!")
        return 1
    elif failed > 0:
        print(f"⚠️  {failed} optional checks failed")
        return 0
    else:
        print("🎉 All checks passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
