"""add_stories_table

Revision ID: 3012669045a7
Revises: a198b6596716
Create Date: 2025-11-30 09:26:37.021871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3012669045a7'
down_revision: Union[str, Sequence[str], None] = 'a198b6596716'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('story_text', sa.Text(), nullable=False),
        sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('processing_attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stories_timestamp', 'stories', ['timestamp'], unique=False)
    op.create_index('idx_stories_user_id', 'stories', ['user_id'], unique=False)
    op.create_index('idx_stories_processing_status', 'stories', ['processing_status'], unique=False)
    op.create_index(op.f('ix_stories_id'), 'stories', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_stories_id'), table_name='stories')
    op.drop_index('idx_stories_processing_status', table_name='stories')
    op.drop_index('idx_stories_user_id', table_name='stories')
    op.drop_index('idx_stories_timestamp', table_name='stories')
    op.drop_table('stories')
