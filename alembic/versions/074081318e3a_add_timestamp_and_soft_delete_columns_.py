"""Add timestamp and soft delete columns to responses

Revision ID: 074081318e3a
Revises: 8ec5d21c3589
Create Date: 2025-11-23 22:51:24.557756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '074081318e3a'
down_revision: Union[str, Sequence[str], None] = '8ec5d21c3589'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns as nullable first
    op.add_column('responses', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('responses', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('responses', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # Update existing rows: copy timestamp to created_at and updated_at
    op.execute("UPDATE responses SET created_at = timestamp, updated_at = timestamp WHERE created_at IS NULL")

    # Make created_at and updated_at non-nullable
    op.alter_column('responses', 'created_at', nullable=False)
    op.alter_column('responses', 'updated_at', nullable=False)

    # Update timestamp column to have timezone
    op.alter_column('responses', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('responses', 'timestamp',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.drop_column('responses', 'deleted_at')
    op.drop_column('responses', 'updated_at')
    op.drop_column('responses', 'created_at')
