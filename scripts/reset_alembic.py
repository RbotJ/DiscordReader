
#!/usr/bin/env python3
"""
Alembic Reset Script

Resets Alembic to use the current database state as the baseline,
removing all existing migration history and creating a fresh initial migration.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description, allow_failure=False):
    """Run a shell command and handle errors."""
    print(f"🔄 {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0 and not allow_failure:
        print(f"❌ {description} failed!")
        print(f"Command: {cmd}")
        print(f"Error: {result.stderr}")
        return False
    
    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
    else:
        print(f"⚠️ {description} completed with warnings")
    return True

def reset_alembic():
    """Reset Alembic migration history and create fresh baseline."""
    
    print("🔄 Starting Alembic reset process...")
    
    # Step 1: Mark current database as up-to-date (if migrations exist)
    if not run_command("alembic stamp head", "Marking current database state", allow_failure=True):
        print("ℹ️  No existing migrations to stamp")
    
    # Step 2: Backup existing migrations (optional safety measure)
    versions_dir = Path("alembic/versions")
    if versions_dir.exists() and any(versions_dir.iterdir()):
        backup_dir = Path("alembic/versions_backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(versions_dir, backup_dir)
        print("📦 Backed up existing migrations to alembic/versions_backup")
    
    # Step 3: Remove all existing migration files
    if versions_dir.exists():
        for file in versions_dir.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
        print("🗑️  Removed existing migration files")
    
    # Step 4: Create new initial migration from current database state
    if not run_command(
        "alembic revision --autogenerate -m 'Initial migration from existing database'",
        "Creating new initial migration"
    ):
        return False
    
    # Step 5: Mark the new migration as applied
    if not run_command("alembic stamp head", "Marking new migration as applied"):
        return False
    
    # Step 6: Verify the reset
    if not run_command("alembic current", "Verifying current migration state"):
        return False
    
    print("\n🎉 Alembic reset completed successfully!")
    print("📝 Your database schema is now the baseline for future migrations")
    return True

def main():
    """Main entry point for Alembic reset."""
    if not reset_alembic():
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
