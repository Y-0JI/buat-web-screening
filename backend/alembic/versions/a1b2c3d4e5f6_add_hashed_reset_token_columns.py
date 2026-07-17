"""Add hashed reset token columns for password reset

Revision ID: a1b2c3d4e5f6
Revises: 9a317bebb481
Create Date: 2026-07-17 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9a317bebb481'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns() -> set:
    bind = op.get_bind()
    return {c["name"] for c in inspect(bind).get_columns("users")}


def upgrade() -> None:
    """Upgrade schema."""
    cols = _user_columns()
    with op.batch_alter_table("users") as batch_op:
        # Kolom lama (plaintext) diganti dengan hash agar DB aman bila bocor.
        if "reset_token" in cols:
            batch_op.drop_column("reset_token")
        if "reset_token_hash" not in cols:
            batch_op.add_column(
                sa.Column("reset_token_hash", sa.String(255), nullable=True)
            )
        if "reset_token_expiry" not in cols:
            batch_op.add_column(
                sa.Column("reset_token_expiry", sa.DateTime(timezone=True), nullable=True)
            )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_reset_token_hash", ["reset_token_hash"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    cols = _user_columns()
    with op.batch_alter_table("users") as batch_op:
        if "reset_token_hash" in cols:
            batch_op.drop_index("ix_users_reset_token_hash")
            batch_op.drop_column("reset_token_hash")
        if "reset_token_expiry" in cols:
            batch_op.drop_column("reset_token_expiry")
