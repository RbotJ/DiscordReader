"""Migrate data from setups to setup_messages and drop legacy table

Revision ID: 939cf5168241
Revises: 838fa798aa44
Create Date: 2025-05-23 20:27:25.829944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '939cf5168241'
down_revision: Union[str, None] = '838fa798aa44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if setups table exists before proceeding
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Check if setups table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'setups'
        )
    """))
    setups_exists = result.scalar()
    
    if setups_exists:
        # Copy all data from setups table to setup_messages table
        op.execute("""
            INSERT INTO setup_messages (date, raw_text, source, created_at)
            SELECT date, raw_text, COALESCE(source, 'unknown'), COALESCE(created_at, NOW())
            FROM setups
            WHERE NOT EXISTS (
                SELECT 1 FROM setup_messages sm 
                WHERE sm.date = setups.date 
                AND sm.raw_text = setups.raw_text
            )
        """)
        
        # Now we can safely drop the old setups table
        op.drop_table('setups')
    
    # Ensure all ticker_setups have valid setup_message_id references
    # Set any NULL setup_message_id to the first available setup_message
    op.execute("""
        UPDATE ticker_setups 
        SET setup_message_id = (
            SELECT MIN(id) FROM setup_messages 
            WHERE setup_messages.date <= CURRENT_DATE
        )
        WHERE setup_message_id IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
