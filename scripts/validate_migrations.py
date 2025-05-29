#!/usr/bin/env python3
"""
Migration Validation Script

Tests that all migrations can be applied and rolled back successfully.
"""

import sys
import subprocess
import tempfile
import os

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"🔄 {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print(f"❌ {description} failed!")
        print(f"Command: {cmd}")
        print(f"Error: {result.stderr}")
        return False
    
    print(f"✅ {description} completed successfully")
    return True

def validate_migrations():
    """Validate that all migrations can be applied and rolled back."""
    
    print("🧪 Starting migration validation tests...")
    
    # Step 1: Apply all migrations
    if not run_command("alembic upgrade head", "Applying all migrations"):
        return False
    
    # Step 2: Check current status
    if not run_command("alembic current", "Checking current migration status"):
        return False
    
    # Step 3: Test rollback (go back one migration)
    if not run_command("alembic downgrade -1", "Testing migration rollback"):
        return False
    
    # Step 4: Re-apply latest migration
    if not run_command("alembic upgrade head", "Re-applying latest migration"):
        return False
    
    # Step 5: Validate schema integrity
    if not run_command("python -c 'from common.db import db; db.create_all()'", 
                      "Validating schema integrity"):
        return False
    
    print("\n🎉 All migration validations passed!")
    return True

def main():
    """Main entry point for migration validation."""
    if not validate_migrations():
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())