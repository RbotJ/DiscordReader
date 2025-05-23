# Database Migration Strategy

## Overview

This document outlines our robust migration strategy using Alembic for the A+ Trading App database schema management. The strategy ensures safe, trackable, and reversible database changes while maintaining data integrity across environments.

## Architecture

Our migration system follows a **feature-based approach** that aligns with our vertical slice architecture:

```
migrations/
├── common/          # Shared infrastructure migrations
├── events/          # Event system migrations  
├── setups/          # Setup and ticker setup migrations
├── strategy/        # Signal and bias migrations
├── execution/       # Trade execution migrations
└── discord/         # Discord integration migrations
```

## Migration Workflow

### 1. Creating New Migrations

```bash
# Create a new migration after making model changes
alembic revision --autogenerate -m "Description of changes"

# Create an empty migration for data operations
alembic revision -m "Data migration description"
```

### 2. Reviewing Migrations

Before applying any migration:
1. Review the generated SQL in the migration file
2. Verify the upgrade and downgrade functions
3. Test on a development database first
4. Ensure data migration scripts preserve existing data

### 3. Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback to previous version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>
```

### 4. Checking Migration Status

```bash
# Show current migration status
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show <revision_id>
```

## CI/CD Integration

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-migrations
        name: Check for pending migrations
        entry: python scripts/check_migrations.py
        language: system
        pass_filenames: false
```

### CI Pipeline Steps

1. **Migration Check**: Fail if there are uncommitted model changes without migrations
2. **Migration Test**: Apply migrations to test database
3. **Schema Validation**: Verify schema matches model definitions
4. **Rollback Test**: Test that downgrade migrations work correctly

## Safety Guidelines

### Before Production Deployment

1. **Backup Database**: Always create a backup before applying migrations
2. **Test Migrations**: Run on staging environment identical to production
3. **Rollback Plan**: Prepare rollback strategy for each migration
4. **Downtime Assessment**: Evaluate if migration requires maintenance window

### Data Migration Best Practices

1. **Preserve Data**: Never delete data without explicit backup
2. **Batch Processing**: Process large datasets in chunks
3. **Progress Tracking**: Log migration progress for monitoring
4. **Validation**: Verify data integrity after migration

## Migration Scripts

### Check for Pending Migrations

```python
# scripts/check_migrations.py
import sys
from alembic import command
from alembic.config import Config

def check_migrations():
    alembic_cfg = Config("alembic.ini")
    
    # Get current revision
    current = command.current(alembic_cfg)
    
    # Get head revision
    head = command.heads(alembic_cfg)
    
    if current != head:
        print("ERROR: There are pending migrations!")
        print(f"Current: {current}")
        print(f"Head: {head}")
        sys.exit(1)
    
    print("✓ Database is up to date")

if __name__ == "__main__":
    check_migrations()
```

### Migration Validation

```python
# scripts/validate_migrations.py
import subprocess
import sys

def validate_migrations():
    """Validate that all migrations can be applied and rolled back."""
    
    # Apply all migrations
    result = subprocess.run(["alembic", "upgrade", "head"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Migration upgrade failed: {result.stderr}")
        sys.exit(1)
    
    # Test rollback
    result = subprocess.run(["alembic", "downgrade", "-1"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Migration downgrade failed: {result.stderr}")
        sys.exit(1)
    
    # Re-apply latest
    result = subprocess.run(["alembic", "upgrade", "head"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Re-applying migration failed: {result.stderr}")
        sys.exit(1)
    
    print("✓ All migrations validated successfully")

if __name__ == "__main__":
    validate_migrations()
```

## Environment-Specific Considerations

### Development
- Auto-generate migrations for model changes
- Test migration rollbacks regularly
- Use `--sql` flag to review generated SQL

### Staging
- Mirror production environment exactly
- Test full deployment pipeline including migrations
- Validate data migration results

### Production
- Schedule migrations during maintenance windows
- Monitor migration performance
- Have rollback plan ready
- Log all migration activities

## Troubleshooting

### Common Issues

1. **Conflicting Migrations**: Use `alembic merge` to resolve
2. **Failed Migration**: Check logs, fix issue, mark as resolved with `alembic stamp`
3. **Schema Drift**: Regenerate migration with `--autogenerate`
4. **Data Loss**: Restore from backup, review migration script

### Recovery Procedures

```bash
# Mark migration as applied without running it
alembic stamp <revision_id>

# Generate SQL without applying
alembic upgrade head --sql

# Show differences between model and database
alembic revision --autogenerate -m "Fix schema drift"
```

## Monitoring and Alerting

### Key Metrics
- Migration execution time
- Migration success/failure rate
- Schema drift detection
- Database size changes

### Alerts
- Failed migrations in CI/CD
- Long-running migrations
- Schema inconsistencies
- Rollback operations

## Documentation Standards

### Migration Descriptions
- Use clear, descriptive messages
- Include ticket/issue numbers
- Explain data impact if applicable
- Note any special requirements

### Code Comments
- Document complex migration logic
- Explain data transformation steps
- Note performance considerations
- Include rollback instructions

This migration strategy ensures reliable, safe, and trackable database changes while maintaining the integrity of our trading application data.