"""Add accumulation scans/signals/rotation tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-01 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Idempoten: tabel bisa sudah ada via create_all."""
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "accumulation_scans" not in existing:
        op.create_table(
            "accumulation_scans",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scan_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("universe_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("stage_b_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("stage_c_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("requests_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quota_remaining", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scan_date", name="uq_accumulation_scans_date"),
        )
        op.create_index(
            "ix_accumulation_scans_scan_date", "accumulation_scans", ["scan_date"]
        )

    if "accumulation_signals" not in existing:
        op.create_table(
            "accumulation_signals",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scan_id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=16), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("depth", sa.String(length=16), nullable=False, server_default="hv"),
            sa.Column("components", sa.JSON(), nullable=True),
            sa.Column("reasons", sa.Text(), nullable=True),
            sa.Column("close", sa.Float(), nullable=True),
            sa.Column("foreign_net", sa.Float(), nullable=True),
            sa.Column("broker_net", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["scan_id"], ["accumulation_scans.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_accumulation_signals_scan_id", "accumulation_signals", ["scan_id"]
        )
        op.create_index(
            "ix_accum_signals_scan_score", "accumulation_signals", ["scan_id", "score"]
        )
        op.create_index(
            "ix_accum_signals_ticker_scan", "accumulation_signals", ["ticker", "scan_id"]
        )

    if "accumulation_rotation" not in existing:
        op.create_table(
            "accumulation_rotation",
            sa.Column("ticker", sa.String(length=16), nullable=False),
            sa.Column("stratum", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_checked_scan_id", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("ticker"),
            sa.UniqueConstraint("ticker", name="uq_accumulation_rotation_ticker"),
        )


def downgrade() -> None:
    """Downgrade schema. Hanya menyentuh tabel akumulasi."""
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "accumulation_signals" in existing:
        op.drop_table("accumulation_signals")
    if "accumulation_rotation" in existing:
        op.drop_table("accumulation_rotation")
    if "accumulation_scans" in existing:
        op.drop_table("accumulation_scans")
