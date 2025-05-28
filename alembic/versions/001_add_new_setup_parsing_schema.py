"""Add new setup parsing schema - discord channels, messages, trade setups, parsed levels

Revision ID: 001_new_schema
Revises: 
Create Date: 2025-05-28 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_new_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new discord_channels table (new schema)
    op.create_table('new_discord_channels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guild_id', sa.String(length=50), nullable=False),
    sa.Column('channel_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('channel_type', sa.String(length=50), nullable=False),
    sa.Column('is_listen', sa.Boolean(), nullable=True),
    sa.Column('is_announce', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('channel_id')
    )

    # Create new discord_messages table (new schema)
    op.create_table('new_discord_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.String(length=50), nullable=False),
    sa.Column('channel_id', sa.String(length=50), nullable=False),
    sa.Column('author_id', sa.String(length=50), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('message_date', sa.Date(), nullable=True),
    sa.Column('message_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['new_discord_channels.channel_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('message_id')
    )

    # Create new trade_setups table (new schema)
    op.create_table('new_trade_setups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=10), nullable=False),
    sa.Column('trade_date', sa.Date(), nullable=False),
    sa.Column('message_id', sa.String(length=50), nullable=False),
    sa.Column('parsed_at', sa.DateTime(), nullable=True),
    sa.Column('bias_note', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['message_id'], ['new_discord_messages.message_id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create new parsed_levels table (new schema)
    op.create_table('new_parsed_levels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('setup_id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('direction', sa.String(), nullable=False),
    sa.Column('strategy_type', sa.String(), nullable=True),
    sa.Column('trigger_relation', sa.String(), nullable=False),
    sa.Column('trigger_price', sa.Float(), nullable=False),
    sa.Column('target_1', sa.Float(), nullable=True),
    sa.Column('target_2', sa.Float(), nullable=True),
    sa.Column('target_3', sa.Float(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['setup_id'], ['new_trade_setups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Set default values for boolean columns
    op.execute("ALTER TABLE new_discord_channels ALTER COLUMN is_listen SET DEFAULT false")
    op.execute("ALTER TABLE new_discord_channels ALTER COLUMN is_announce SET DEFAULT false")
    op.execute("ALTER TABLE new_discord_channels ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE new_discord_messages ALTER COLUMN processed SET DEFAULT false")
    op.execute("ALTER TABLE new_trade_setups ALTER COLUMN is_active SET DEFAULT true")


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('new_parsed_levels')
    op.drop_table('new_trade_setups')
    op.drop_table('new_discord_messages')
    op.drop_table('new_discord_channels')