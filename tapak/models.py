"""Model ORM (SQLAlchemy). Skema dikelola oleh Flask-Migrate (folder migrations/)."""
from datetime import datetime, timezone

import sqlalchemy as sa

from tapak.extensions import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client", server_default="client")
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.text("1"))
    created_at = db.Column(db.DateTime, default=now)

    orders = db.relationship("Order", back_populates="user")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60), nullable=False, default="", server_default="")
    category = db.Column(db.String(30), nullable=False, default="", server_default="")
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=now)

    def to_dict(self):
        return dict(id=self.id, name=self.name, brand=self.brand, category=self.category, price=self.price, stock=self.stock)


class Order(db.Model):
    """status: pending (belum bayar) -> waiting (bukti diunggah) -> paid | rejected."""
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", server_default="paid")
    created_at = db.Column(db.DateTime, default=now)
    payment_proof = db.Column(db.String(255))

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", order_by="OrderItem.id")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    # Tanpa FK: produk boleh dihapus tanpa menghapus riwayat pesanan (sama seperti skema awal).
    product_id = db.Column(db.Integer, nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    unit_price = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", primaryjoin="foreign(OrderItem.product_id) == Product.id", viewonly=True)


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)

    user = db.relationship("User")
