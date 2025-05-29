
# Script Troubleshooting Guide

## Common Issues and Solutions

### 1. Migration Scripts Failing

**Error**: `ImportError: No module named 'main'`
**Solution**: Make sure you're running scripts from the project root directory:
```bash
cd /path/to/your/project
python scripts/check_migrations.py
```

**Error**: `alembic.util.exc.CommandError: Can't locate revision identified by 'head'`
**Solution**: Initialize Alembic or reset it:
```bash
python scripts/reset_alembic.py
```

### 2. Template Scripts Failing

**Error**: `templates/ directory not found`
**Solution**: Create the templates directory:
```bash
mkdir -p templates
```

**Error**: `UnicodeDecodeError`
**Solution**: Ensure all template files are UTF-8 encoded.

### 3. Database Connection Issues

**Error**: `sqlalchemy.exc.OperationalError`
**Solution**: 
1. Check your database configuration in `main.py`
2. Ensure database file exists or can be created
3. Check file permissions

### 4. Import Path Issues

**Error**: `ModuleNotFoundError: No module named 'common'`
**Solution**: Run scripts from project root and ensure Python path includes current directory:
```bash
export PYTHONPATH="${PYTHONPATH}:."
python scripts/your_script.py
```

## Running All Scripts Safely

Use the master runner to test all scripts:
```bash
python scripts/run_all_checks.py
```

## Individual Script Usage

### Migration Scripts
```bash
# Check migration status
python scripts/check_migrations.py

# Validate migrations work
python scripts/validate_migrations.py

# Reset Alembic (DESTRUCTIVE)
python scripts/reset_alembic.py
```

### Template Scripts
```bash
# Validate template format
python scripts/validate_templates.py

# Generate template documentation
python scripts/generate_template_registry.py

# Audit template usage
python scripts/template_audit.py
```

### Analysis Scripts
```bash
# Find code duplications
python scripts/duplication_scanner.py

# Check integration issues
python scripts/integration_checklist.py
```

## Exit Codes

- `0`: Success
- `1`: Critical failure (should stop deployment)
- `2`: Non-critical warnings (deployment can continue)

## Getting Help

If scripts continue to fail:
1. Run `python scripts/run_all_checks.py` for comprehensive diagnosis
2. Check the specific error messages in the output
3. Verify your project structure matches expected layout
4. Ensure all dependencies are installed
