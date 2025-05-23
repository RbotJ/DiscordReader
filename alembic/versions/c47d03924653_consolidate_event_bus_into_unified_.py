"""Consolidate event_bus into unified events table

Revision ID: c47d03924653
Revises: 939cf5168241
Create Date: 2025-05-23 20:30:37.693552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c47d03924653'
down_revision: Union[str, None] = '939cf5168241'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add event_type column to events table to match event_bus structure
    op.add_column('events', sa.Column('event_type', sa.String(100), nullable=True))
    
    # Update events table to use JSONB for better performance (like event_bus)
    op.execute("ALTER TABLE events ALTER COLUMN data TYPE JSONB USING data::jsonb")
    
    # Add timezone support to created_at column to match event_bus
    op.execute("ALTER TABLE events ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Migrate data from event_bus to events table
    op.execute("""
        INSERT INTO events (event_type, channel, data, created_at)
        SELECT event_type, COALESCE(channel, 'default'), COALESCE(payload, '{}'::jsonb), COALESCE(created_at, NOW())
        FROM event_bus
        WHERE NOT EXISTS (
            SELECT 1 FROM events e 
            WHERE e.event_type = event_bus.event_type 
            AND e.channel = COALESCE(event_bus.channel, 'default')
            AND e.created_at = COALESCE(event_bus.created_at, NOW())
        )
    """)
    
    # Make event_type NOT NULL after migration
    op.alter_column('events', 'event_type', nullable=False)
    
    # Drop the old event_bus table
    op.drop_table('event_bus')


def downgrade() -> None:
    """Downgrade schema."""
    pass
