"""Remove embedded flip columns from biases table

Revision ID: 1695769576fb
Revises: ff7e49b64175
Create Date: 2025-05-23 20:40:50.073851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1695769576fb'
down_revision: Union[str, None] = 'ff7e49b64175'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: The biases table schema is already clean without embedded flip columns
    # This migration ensures all code references use bias_flips table exclusively
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
