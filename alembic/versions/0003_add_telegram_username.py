"""Add telegram_username, drop avatar_url

Revision ID: 0003_tg_username
Revises: 0002_age_avatar
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_tg_username"
down_revision: Union[str, Sequence[str], None] = "0002_age_avatar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_username", sa.String(length=255), nullable=True))
    # avatar_url may or may not exist depending on migration state
    try:
        op.drop_column("users", "avatar_url")
    except Exception:
        pass


def downgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=1024), nullable=True))
    op.drop_column("users", "telegram_username")
