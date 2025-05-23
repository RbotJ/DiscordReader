"""Align biases table with separate bias_flips relationship

Revision ID: 838fa798aa44
Revises: 1a94e26cd7d9
Create Date: 2025-05-23 20:26:21.955320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '838fa798aa44'
down_revision: Union[str, None] = '1a94e26cd7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types for biases table
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE biasdirectionenum AS ENUM ('BULLISH', 'BEARISH');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Migrate existing flip data to separate bias_flips table
    op.execute("""
        INSERT INTO bias_flips (bias_id, direction, price_level)
        SELECT id, flip_direction::biasdirectionenum, flip_price_level
        FROM biases 
        WHERE flip_direction IS NOT NULL AND flip_price_level IS NOT NULL
    """)
    
    # Update biases table structure
    op.execute("UPDATE biases SET direction = UPPER(direction)")
    op.execute("UPDATE biases SET condition = UPPER(condition)")
    
    # Convert columns to enums
    op.execute("ALTER TABLE biases ALTER COLUMN direction TYPE biasdirectionenum USING direction::biasdirectionenum")
    op.execute("ALTER TABLE biases ALTER COLUMN condition TYPE comparisontypeenum USING condition::comparisontypeenum")
    
    # Make created_at NOT NULL
    op.alter_column('biases', 'created_at', nullable=False)
    
    # Remove the embedded flip columns (data already migrated)
    op.drop_column('biases', 'flip_direction')
    op.drop_column('biases', 'flip_price_level')


def downgrade() -> None:
    """Downgrade schema."""
    pass
