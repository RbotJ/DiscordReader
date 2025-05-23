"""Fix ticker_setups FK to reference setup_messages

Revision ID: ff7e49b64175
Revises: c47d03924653
Create Date: 2025-05-23 20:33:28.950920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff7e49b64175'
down_revision: Union[str, None] = 'c47d03924653'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The ticker_setups table already has setup_message_id column and FK constraint
    # This migration ensures the schema is consistent with our models
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
