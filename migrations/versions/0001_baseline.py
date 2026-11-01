"""Skema awal (users, products, orders, order_items, reviews). Idempoten.

Basis data lab sudah punya tabel ini (dibuat oleh versi sebelum Flask-Migrate), jadi tabel yang
sudah ada DILEWATI dan data tidak disentuh. Hanya basis data kosong yang dibuat dari nol.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("username", sa.String(50), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="client"))
    if "products" not in existing:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("brand", sa.String(60), nullable=False, server_default=""),
            sa.Column("category", sa.String(30), nullable=False, server_default=""),
            sa.Column("price", sa.Integer, nullable=False),
            sa.Column("stock", sa.Integer, nullable=False, server_default="0"))
    if "orders" not in existing:
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, nullable=False),
            sa.Column("total", sa.Integer, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="paid"))
    if "order_items" not in existing:
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("order_id", sa.Integer, nullable=False),
            sa.Column("product_id", sa.Integer, nullable=False),
            sa.Column("qty", sa.Integer, nullable=False),
            sa.Column("size", sa.Integer, nullable=False, server_default="0"),
            sa.Column("unit_price", sa.Integer, nullable=False))
    if "reviews" not in existing:
        op.create_table(
            "reviews",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("product_id", sa.Integer, nullable=False),
            sa.Column("user_id", sa.Integer, nullable=False),
            sa.Column("rating", sa.Integer, nullable=False),
            sa.Column("comment", sa.Text, nullable=False))


def downgrade():
    for t in ("reviews", "order_items", "orders", "products", "users"):
        op.drop_table(t)
