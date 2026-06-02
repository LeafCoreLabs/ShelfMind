"""vendors and purchases + invoice GST columns

Revision ID: 005
Revises: 004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendors_store_id", "vendors", ["store_id"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ordered", nullable=False),
        sa.Column("subtotal", sa.Float(), server_default="0", nullable=False),
        sa.Column("tax", sa.Float(), server_default="0", nullable=False),
        sa.Column("total", sa.Float(), server_default="0", nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_store_id", "purchase_orders", ["store_id"])
    op.create_index("ix_purchase_orders_vendor_id", "purchase_orders", ["vendor_id"])

    op.create_table(
        "purchase_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("po_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("line_total", sa.Float(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_lines_po_id", "purchase_lines", ["po_id"])
    op.create_index("ix_purchase_lines_product_id", "purchase_lines", ["product_id"])

    op.add_column("invoices", sa.Column("cgst_amount", sa.Float(), server_default="0", nullable=False))
    op.add_column("invoices", sa.Column("sgst_amount", sa.Float(), server_default="0", nullable=False))
    op.add_column("invoices", sa.Column("igst_amount", sa.Float(), server_default="0", nullable=False))
    op.add_column("invoices", sa.Column("place_of_supply", sa.String(length=128), nullable=True))
    op.add_column("invoice_lines", sa.Column("hsn_code", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("invoice_lines", "hsn_code")
    op.drop_column("invoices", "place_of_supply")
    op.drop_column("invoices", "igst_amount")
    op.drop_column("invoices", "sgst_amount")
    op.drop_column("invoices", "cgst_amount")
    op.drop_table("purchase_lines")
    op.drop_table("purchase_orders")
    op.drop_table("vendors")
