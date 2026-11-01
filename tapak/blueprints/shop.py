"""Halaman web pelanggan: beranda, katalog + filter harga, detail, keranjang, pesanan, bukti bayar."""
import os

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory,
                   session, url_for)
from sqlalchemy import or_

from tapak.blueprints.api import store_review
from tapak.blueprints.auth import login_required
from tapak.errors import ApiError
from tapak.extensions import db
from tapak.forms import CartAddForm, FilterForm, ProofForm, ReviewForm
from tapak.logs import L, client_ip
from tapak.models import Order, Product, Review
from tapak.security import web_user
from tapak.services import create_order
from tapak.uploads import remove_image, save_image

bp = Blueprint("shop", __name__)


@bp.get("/")
def home():
    featured = db.session.scalars(db.select(Product).order_by(Product.created_at.desc(), Product.id.desc()).limit(8)).all()
    return render_template("home.html", featured=featured)


@bp.get("/products")
def catalog():
    form = FilterForm(request.args)
    form.validate()  # GET: tampilkan galat bila rentang harga tidak valid
    q = db.select(Product)
    if not form.errors:
        term = (form.q.data or "").strip()
        if term:
            q = q.where(or_(Product.name.like(f"%{term}%"), Product.brand.like(f"%{term}%")))
        if form.category.data:
            q = q.where(Product.category == form.category.data)
        if form.min_price.data is not None:
            q = q.where(Product.price >= form.min_price.data)
        if form.max_price.data is not None:
            q = q.where(Product.price <= form.max_price.data)
        L("INFO", "SEARCH", q=term, ip=client_ip())
    else:
        q = q.where(db.false())
    page = db.paginate(q.order_by(Product.id), page=request.args.get("page", 1, type=int), per_page=current_app.config["PER_PAGE"], error_out=False)
    args = {k: v for k, v in request.args.items() if k != "page" and v}
    return render_template("catalog.html", form=form, page=page, args=args)


@bp.get("/products/<int:pid>")
def product(pid):
    p = db.get_or_404(Product, pid)
    reviews = db.session.scalars(db.select(Review).where(Review.product_id == pid).order_by(Review.id.desc())).all()
    return render_template("product.html", p=p, reviews=reviews, cart_form=CartAddForm(product_id=pid, qty=1), review_form=ReviewForm())


@bp.post("/products/<int:pid>/reviews")
@login_required
def add_review(pid):
    db.get_or_404(Product, pid)
    form = ReviewForm()
    if form.validate_on_submit():
        store_review(pid, web_user(), form.rating.data, form.comment.data)
        flash("Ulasan terkirim.", "ok")
    else:
        flash("Ulasan tidak valid: " + "; ".join(m for e in form.errors.values() for m in e), "err")
    return redirect(url_for("shop.product", pid=pid))


# ---- keranjang (disimpan di sesi) ----
def cart_items():
    out = []
    for i, (pid, size, qty) in enumerate(session.get("cart", [])):
        p = db.session.get(Product, pid)
        if p:
            out.append(dict(idx=i, p=p, size=size, qty=qty, sub=p.price * qty))
    return out


@bp.post("/cart/add")
def cart_add():
    form = CartAddForm()
    if not form.validate_on_submit() or not db.session.get(Product, form.product_id.data):
        flash("Pilih ukuran 36-46 dan jumlah 1-10.", "err")
        return redirect(request.referrer or url_for("shop.catalog"))
    cart = session.get("cart", [])
    cart.append([form.product_id.data, form.size.data, form.qty.data])
    session["cart"] = cart
    flash("Ditambahkan ke keranjang.", "ok")
    return redirect(url_for("shop.cart"))


@bp.get("/cart")
def cart():
    items = cart_items()
    return render_template("cart.html", items=items, total=sum(i["sub"] for i in items))


@bp.post("/cart/remove/<int:idx>")
def cart_remove(idx):
    c = session.get("cart", [])
    if 0 <= idx < len(c):
        c.pop(idx)
        session["cart"] = c
    return redirect(url_for("shop.cart"))


@bp.post("/checkout")
@login_required
def checkout():
    items = [dict(product_id=pid, size=size, qty=qty) for pid, size, qty in session.get("cart", [])]
    try:
        o = create_order(web_user(), items, status="pending")
    except ApiError as e:
        flash(e.msg, "err")
        return redirect(url_for("shop.cart"))
    session.pop("cart", None)
    flash("Pesanan dibuat. Unggah bukti pembayaran agar diverifikasi admin.", "ok")
    return redirect(url_for("shop.order_detail", oid=o.id))


# ---- pesanan ----
def own_order_or_404(oid):
    o = db.get_or_404(Order, oid)
    u = web_user()
    if o.user_id != u.id and u.role != "admin":
        L("WARNING", "ORDER_ACCESS_DENIED", order=o.id, user=u.username, ip=client_ip())
        abort(403)
    return o


@bp.get("/orders")
@login_required
def orders():
    rows = db.session.scalars(db.select(Order).where(Order.user_id == web_user().id).order_by(Order.id.desc())).all()
    return render_template("orders.html", orders=rows)


@bp.get("/orders/<int:oid>")
@login_required
def order_detail(oid):
    return render_template("order_detail.html", o=own_order_or_404(oid), form=ProofForm())


@bp.post("/orders/<int:oid>/proof")
@login_required
def upload_proof(oid):
    o = own_order_or_404(oid)
    form = ProofForm()
    if o.status not in ("pending", "rejected"):
        flash("Pesanan ini tidak menerima bukti pembayaran lagi.", "err")
    elif form.validate_on_submit():
        name = save_image(form.proof.data, "proofs")
        if not name:
            flash("Berkas bukan gambar valid atau lebih dari 2 MB.", "err")
        else:
            remove_image("proofs", o.payment_proof)
            o.payment_proof, o.status = name, "waiting"
            db.session.commit()
            L("INFO", "PAYMENT_PROOF_UPLOADED", order=o.id, user=web_user().username, ip=client_ip())
            flash("Bukti pembayaran terkirim. Menunggu verifikasi admin.", "ok")
    else:
        flash("; ".join(m for e in form.errors.values() for m in e), "err")
    return redirect(url_for("shop.order_detail", oid=oid))


@bp.get("/orders/<int:oid>/proof")
@login_required
def proof_file(oid):
    o = own_order_or_404(oid)
    if not o.payment_proof:
        abort(404)
    return send_from_directory(os.path.join(current_app.config["UPLOAD_DIR"], "proofs"), o.payment_proof)


@bp.get("/uploads/products/<path:name>")
def product_image(name):
    return send_from_directory(os.path.join(current_app.config["UPLOAD_DIR"], "products"), name)
