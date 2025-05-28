# Alembic Database Migrations

Alembic provides database migration capabilities for the A+ Trading App, managing schema changes and database versioning.

## Overview

Alembic is configured to work with the PostgreSQL database and provides migration capabilities for schema evolution. The application uses both Alembic migrations and direct schema management depending on the feature requirements.

## Configuration

### Environment Configuration (`alembic.ini`)
- **Database URL**: Configured to use `DATABASE_URL` environment variable
- **Migration Directory**: Migrations stored in `alembic/versions/`
- **Script Location**: Migration scripts in `alembic/`
- **Output Encoding**: UTF-8 for proper character support

### Environment Setup (`env.py`)
- **SQLAlchemy integration**: Uses application's SQLAlchemy models
- **Automatic model detection**: Discovers models from application imports
- **Online/offline modes**: Supports both connected and SQL script generation
- **Transaction management**: Proper transaction handling for migrations

## Migration Strategy

### Current Approach
The application uses a hybrid approach to database management:

1. **Enhanced Event System**: Direct SQL schema creation for performance
2. **Feature Models**: Alembic migrations for traditional model changes
3. **Legacy Preservation**: Old tables renamed with "old_" prefix

### Schema Management
```sql
-- Enhanced event system (direct SQL)
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  channel VARCHAR(50) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  source VARCHAR(100),
  correlation_id UUID,
  data JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Feature models (Alembic managed)
-- Applied through standard migration files
```

## Usage Commands

### Generate New Migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration template
alembic revision -m "Description of manual changes"
```

### Apply Migrations
```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific revision
alembic upgrade +1              # Next revision
alembic upgrade revision_id     # Specific revision

# Downgrade migrations
alembic downgrade -1            # Previous revision
alembic downgrade base          # All the way down
```

### Migration Information
```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show

# Show revision details
alembic show revision_id
```

## Database Integration

### Model Registration
Models must be imported in `env.py` for auto-generation to work:

```python
# Import all models for autogenerate
from features.models.new_schema import discord_channels
from features.models.new_schema import discord_messages
from features.models.new_schema import trade_setups
from features.models.new_schema import parsed_levels
from features.models.new_schema import events
```

### Target Metadata
```python
# Set target metadata for autogenerate
target_metadata = Base.metadata
```

## Migration File Structure

### Version Directory (`versions/`)
- Migration files stored with timestamp and revision ID
- Naming pattern: `{revision_id}_{description}.py`
- Each file contains `upgrade()` and `downgrade()` functions

### Migration Template
```python
"""Description of changes

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2025-05-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None

def upgrade():
    # Migration code here
    pass

def downgrade():
    # Rollback code here
    pass
```

## Best Practices

### Migration Development
1. **Review generated migrations**: Always review auto-generated migrations before applying
2. **Test both directions**: Ensure both upgrade and downgrade work correctly
3. **Data migration**: Include data migration code when changing column types
4. **Backup first**: Always backup production database before applying migrations

### Schema Changes
1. **Additive changes**: Prefer adding columns over modifying existing ones
2. **Default values**: Provide default values for new non-nullable columns
3. **Index management**: Create indexes in separate migrations when possible
4. **Foreign keys**: Handle foreign key constraints carefully

### Production Deployment
1. **Staging testing**: Test migrations on staging environment first
2. **Maintenance windows**: Apply migrations during planned maintenance
3. **Rollback plan**: Always have a tested rollback procedure
4. **Monitor performance**: Watch for migration impact on database performance

## Integration with Application

### Startup Integration
The application automatically handles database initialization:

```python
# In main.py
from common.db import initialize_db

def create_app():
    # Database initialization
    initialize_db(app)
    
    # Import models for table creation
    from features.models.new_schema import events
```

### Development Workflow
1. **Model changes**: Modify SQLAlchemy models in feature directories
2. **Generate migration**: Run `alembic revision --autogenerate`
3. **Review migration**: Check generated migration for correctness
4. **Apply migration**: Run `alembic upgrade head`
5. **Test application**: Verify application works with new schema

## Current Schema Status

### Enhanced Tables (Direct SQL)
- `events` - Enhanced event bus with correlation tracking
- `discord_channels` - Discord channel management
- `discord_messages` - Message storage and processing
- `trade_setups` - Parsed trading setups
- `parsed_levels` - Price levels and targets

### Legacy Tables (Preserved)
- `old_setups` - Original setup data
- `old_setup_channels` - Original channel configuration
- `old_ingestion_status` - Original ingestion tracking
- `old_events` - Original event logging

### Migration History
Current migration state represents the transition from legacy schema to enhanced event system with preserved data integrity.

## Troubleshooting

### Common Issues

#### Migration Conflicts
```bash
# Resolve merge conflicts in migration history
alembic merge -m "Merge conflicting revisions" revision1 revision2
```

#### Schema Sync Issues
```bash
# Mark current state as baseline
alembic stamp head

# Force revision to specific state
alembic stamp revision_id
```

#### Failed Migrations
```bash
# Check current state
alembic current

# Manually fix database and mark as applied
alembic stamp revision_id
```

### Database Recovery
1. **Backup restoration**: Restore from backup if migration fails
2. **Manual fixes**: Apply manual schema fixes and stamp revision
3. **Rollback**: Use downgrade to previous working state
4. **Fresh start**: Drop and recreate database with current schema

## Monitoring & Maintenance

### Migration Tracking
```sql
-- Check alembic version table
SELECT * FROM alembic_version;

-- Verify table existence
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

### Performance Monitoring
- Monitor migration execution time
- Check for blocking operations during migrations
- Verify index creation doesn't impact production
- Watch for lock contention during schema changes

---

*Last updated: 2025-05-28*
*Current status: Hybrid approach with direct SQL for enhanced event system*