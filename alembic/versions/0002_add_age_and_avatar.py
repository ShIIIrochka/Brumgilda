"""Add age and telegram_avatar_file_id columns

Revision ID: 0002_age_avatar
Revises: 5e150362c97d
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_age_avatar"
down_revision: Union[str, Sequence[str], None] = "5e150362c97d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("telegram_avatar_file_id", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_avatar_file_id")
    op.drop_column("users", "age")
