"""store commerce models

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("list_price", sa.Float(), server_default="0", nullable=False))
    op.add_column("products", sa.Column("cost_price", sa.Float(), server_default="0", nullable=False))
    op.add_column("products", sa.Column("stock_on_hand", sa.Integer(), server_default="0", nullable=False))
    op.add_column("products", sa.Column("reorder_level", sa.Integer(), server_default="5", nullable=False))

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("segment", sa.String(length=64), server_default="Regular", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_spent", sa.Float(), server_default="0", nullable=False),
        sa.Column("last_purchase_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_store_id", "customers", ["store_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Float(), server_default="0", nullable=False),
        sa.Column("tax_rate", sa.Float(), server_default="0.18", nullable=False),
        sa.Column("tax_amount", sa.Float(), server_default="0", nullable=False),
        sa.Column("total", sa.Float(), server_default="0", nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_store_id", "invoices", ["store_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Float(), server_default="0", nullable=False),
        sa.Column("line_total", sa.Float(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=32), server_default="cash", nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])

    op.add_column("transactions", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_transactions_customer_id", "transactions", "customers", ["customer_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_transactions_customer_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "customer_id")
    op.drop_table("payments")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("customers")
    op.drop_column("products", "reorder_level")
    op.drop_column("products", "stock_on_hand")
    op.drop_column("products", "cost_price")
    op.drop_column("products", "list_price")
