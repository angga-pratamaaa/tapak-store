"""Kolom tambahan untuk fitur web: email/aktif/tanggal (users), deskripsi/foto/tanggal (products),
tanggal/bukti bayar (orders). Idempoten: kolom yang sudah ada dilewati.

Catatan MySQL: perintah ini memakai ALTER TABLE, jadi user aplikasi ('toko') perlu hak ALTER
(dan CREATE/INDEX) saat migrasi dijalankan. Cabut kembali setelah selesai (lihat README).

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

COLUMNS = {
    "users": [
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, nullable=True)],
    "products": [
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True)],
    "orders": [
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("payment_proof", sa.String(255), nullable=True)],
}


def upgrade():
    insp = sa.inspect(op.get_bind())
    for table, cols in COLUMNS.items():
        have = {c["name"] for c in insp.get_columns(table)}
        for col in cols:
            if col.name not in have:
                op.add_column(table, sa.Column(col.name, col.type, nullable=col.nullable, server_default=col.server_default))


def downgrade():
    for table, cols in COLUMNS.items():
        with op.batch_alter_table(table) as b:
            for col in cols:
                b.drop_column(col.name)
