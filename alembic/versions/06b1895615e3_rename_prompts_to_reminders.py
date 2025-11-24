"""rename prompts to reminders

Revision ID: 06b1895615e3
Revises: cad2f99ab1ba
Create Date: 2025-11-23 18:16:56.268738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06b1895615e3'
down_revision: Union[str, Sequence[str], None] = 'cad2f99ab1ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename prompts table to reminders
    op.rename_table('prompts', 'reminders')

    # Rename prompt_id column to reminder_id in responses table
    op.alter_column('responses', 'prompt_id', new_column_name='reminder_id')

    # Rename indexes
    op.execute('ALTER INDEX idx_prompts_scheduled_time RENAME TO idx_reminders_scheduled_time')
    op.execute('ALTER INDEX idx_prompts_status RENAME TO idx_reminders_status')
    op.execute('ALTER INDEX idx_prompts_user_id RENAME TO idx_reminders_user_id')
    op.execute('ALTER INDEX idx_responses_prompt_id RENAME TO idx_responses_reminder_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename reminders table back to prompts
    op.rename_table('reminders', 'prompts')

    # Rename reminder_id column back to prompt_id
    op.alter_column('responses', 'reminder_id', new_column_name='prompt_id')

    # Rename indexes back
    op.execute('ALTER INDEX idx_reminders_scheduled_time RENAME TO idx_prompts_scheduled_time')
    op.execute('ALTER INDEX idx_reminders_status RENAME TO idx_reminders_status')
    op.execute('ALTER INDEX idx_reminders_user_id RENAME TO idx_prompts_user_id')
    op.execute('ALTER INDEX idx_responses_reminder_id RENAME TO idx_responses_prompt_id')
