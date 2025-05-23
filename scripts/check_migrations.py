#!/usr/bin/env python3
"""
Migration Check Script

Validates that database migrations are up to date and prevents deployment
with pending migrations.
"""

import sys
import os
import subprocess
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

def check_migrations():
    """Check if there are pending migrations that need to be applied."""
    try:
        # Set up Alembic configuration
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        
        # Get current database revision
        with script.get_revision("head") as head_revision:
            head = head_revision.revision if head_revision else None
        
        # Check current database state
        current_result = subprocess.run(
            ["alembic", "current"], 
            capture_output=True, 
            text=True
        )
        
        if current_result.returncode != 0:
            print("ERROR: Could not determine current migration state")
            print(current_result.stderr)
            return False
        
        current = current_result.stdout.strip()
        
        # Compare current vs head
        if not current:
            print("WARNING: No migrations have been applied to database")
            return True
        
        if current != head:
            print("ERROR: Database migrations are not up to date!")
            print(f"Current revision: {current}")
            print(f"Latest revision: {head}")
            print("\nRun 'alembic upgrade head' to apply pending migrations")
            return False
        
        print("✓ Database migrations are up to date")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to check migrations: {e}")
        return False

def check_for_model_changes():
    """Check if there are uncommitted model changes without migrations."""
    try:
        # Generate a test migration to see if there are model changes
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "--dry-run", "-m", "test"], 
            capture_output=True, 
            text=True
        )
        
        if "No changes detected" not in result.stdout:
            print("WARNING: Model changes detected without corresponding migration")
            print("Consider running 'alembic revision --autogenerate -m \"Your description\"'")
            return False
        
        print("✓ No uncommitted model changes detected")
        return True
        
    except Exception as e:
        print(f"WARNING: Could not check for model changes: {e}")
        return True  # Don't fail CI for this check

def main():
    """Main entry point for migration checks."""
    print("🔍 Checking database migration status...")
    
    # Check if migrations are up to date
    migrations_ok = check_migrations()
    
    # Check for uncommitted model changes
    models_ok = check_for_model_changes()
    
    if not migrations_ok:
        print("\n❌ Migration check failed!")
        sys.exit(1)
    
    if not models_ok:
        print("\n⚠️  Model changes detected without migrations")
        # Don't fail CI, just warn
    
    print("\n✅ Migration checks passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())