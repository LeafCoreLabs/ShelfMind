"""auth users onboarding

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("stores", sa.Column("business_type", sa.String(length=128), nullable=True))
    op.add_column("stores", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("preferences", postgresql.JSONB(), nullable=True))
    op.add_column("stores", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_store_id", "users", ["store_id"])

    op.create_table(
        "onboarding_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_onboarding_drafts_admin_id", "onboarding_drafts", ["admin_id"])


def downgrade() -> None:
    op.drop_table("onboarding_drafts")
    op.drop_table("users")
    op.drop_column("stores", "is_active")
    op.drop_column("stores", "preferences")
    op.drop_column("stores", "timezone")
    op.drop_column("stores", "business_type")
    op.drop_column("stores", "phone")
