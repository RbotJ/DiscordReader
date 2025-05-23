"""Fix signals table schema alignment

Revision ID: 1a94e26cd7d9
Revises: cf433146f2a6
Create Date: 2025-05-23 20:24:58.432651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a94e26cd7d9'
down_revision: Union[str, None] = 'cf433146f2a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename trigger_value to trigger to match model
    op.alter_column('signals', 'trigger_value', new_column_name='trigger')
    
    # Create enum types only if they don't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE signalcategoryenum AS ENUM ('BREAKOUT', 'BREAKDOWN', 'REJECTION', 'BOUNCE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE aggressivenessenum AS ENUM ('NONE', 'LOW', 'MEDIUM', 'HIGH', 'AGGRESSIVE', 'CONSERVATIVE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE comparisontypeenum AS ENUM ('ABOVE', 'BELOW', 'NEAR', 'RANGE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # First, update existing data to match enum case
    op.execute("UPDATE signals SET category = UPPER(category)")
    op.execute("UPDATE signals SET aggressiveness = UPPER(aggressiveness) WHERE aggressiveness IS NOT NULL")
    op.execute("UPDATE signals SET comparison = UPPER(comparison)")
    
    # Update columns to use enums (keeping data)
    op.execute("ALTER TABLE signals ALTER COLUMN category TYPE signalcategoryenum USING category::signalcategoryenum")
    op.execute("ALTER TABLE signals ALTER COLUMN aggressiveness TYPE aggressivenessenum USING COALESCE(aggressiveness::aggressivenessenum, 'NONE')")
    op.execute("ALTER TABLE signals ALTER COLUMN comparison TYPE comparisontypeenum USING comparison::comparisontypeenum")
    
    # Make required fields NOT NULL and set defaults
    op.alter_column('signals', 'created_at', nullable=False)
    op.alter_column('signals', 'aggressiveness', nullable=False, server_default='NONE')
    
    # Remove unused columns that don't match our models
    op.drop_column('signals', 'active')
    op.drop_column('signals', 'triggered_at')


def downgrade() -> None:
    """Downgrade schema."""
    pass
