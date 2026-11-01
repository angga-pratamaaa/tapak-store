"""Panel admin (web, /panel): dashboard, CRUD produk + foto, pengguna, verifikasi pembayaran, laporan penjualan."""
import csv
import io
from datetime import datetime, time, timedelta
from functools import wraps

from flask import (Blueprint, Response, abort, flash, g, redirect, render_template, request, send_file, url_for)
from sqlalchemy import func
from werkzeug.datastructures import FileStorage

from tapak.extensions import db
from tapak.forms import ProductForm, ReportForm
from tapak.logs import L, client_ip
from tapak.models import Order, OrderItem, Product, User
from tapak.security import web_user
from tapak.uploads import remove_image, save_image

bp = Blueprint("panel", __name__, url_prefix="/panel")
STATUS_LABEL = {"pending": "Belum bayar", "waiting": "Menunggu verifikasi", "paid": "Lunas", "rejected": "Ditolak"}


def admin_required(f):
    """Hanya admin. Setiap akses dicatat (ADMIN_ACCESS GRANTED/DENIED), sama dengan API admin."""
    @wraps(f)
    def wrapper(*a, **k):
        u = web_user()
        base = dict(path=request.path, method=request.method, ip=client_ip())
        g.actor = u.username if u else "anonymous"
        if not u:
            L("WARNING", "ADMIN_ACCESS", **base, user=g.actor, result="DENIED", reason="unauthenticated")
            flash("Silakan masuk sebagai admin.", "err")
            return redirect(url_for("auth.login", next=request.path))
        if u.role != "admin":
            L("WARNING", "ADMIN_ACCESS", **base, user=u.username, result="DENIED", reason="not_admin")
            abort(403)
        L("INFO", "ADMIN_ACCESS", **base, user=u.username, result="GRANTED")
        return f(*a, **k)
    return wrapper


def fill_product(p, form):
    p.name, p.brand = form.name.data.strip(), (form.brand.data or "").strip()
    p.category, p.price, p.stock = form.category.data, form.price.data, form.stock.data or 0
    p.description = (form.description.data or "").strip() or None


def apply_image(p, form):
    """Simpan foto baru bila diunggah. Kembalikan False bila berkas ditolak."""
    if isinstance(form.image.data, FileStorage) and form.image.data.filename:
        name = save_image(form.image.data, "products")
        if not name:
            flash("Foto bukan gambar valid (JPG/PNG/WEBP) atau lebih dari 2 MB.", "err")
            return False
        remove_image("products", p.image)
        p.image = name
    return True


@bp.get("/")
@admin_required
def dashboard():
    n = lambda stmt: int(db.session.scalar(stmt) or 0)
    stats = dict(
        users=n(db.select(func.count(User.id))), products=n(db.select(func.count(Product.id))),
        orders=n(db.select(func.count(Order.id))), waiting=n(db.select(func.count(Order.id)).where(Order.status == "waiting")),
        low_stock=n(db.select(func.count(Product.id)).where(Product.stock < 10)),
        revenue=n(db.select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "paid")))
    recent = db.session.scalars(db.select(Order).order_by(Order.id.desc()).limit(5)).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent, labels=STATUS_LABEL)


# ---- produk ----
@bp.get("/products")
@admin_required
def products():
    rows = db.session.scalars(db.select(Product).order_by(Product.id.desc())).all()
    return render_template("admin/products.html", products=rows)


@bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    form = ProductForm()
    if form.validate_on_submit():
        p = Product()
        fill_product(p, form)
        if apply_image(p, form):
            db.session.add(p)
            db.session.commit()
            L("INFO", "PRODUCT_CREATE", id=p.id, name=p.name, by=g.actor, ip=client_ip())
            flash("Produk ditambahkan.", "ok")
            return redirect(url_for("panel.products"))
    return render_template("admin/product_form.html", form=form, p=None)


@bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(pid):
    p = db.get_or_404(Product, pid)
    form = ProductForm(obj=p)
    if form.validate_on_submit():
        fill_product(p, form)
        if apply_image(p, form):
            db.session.commit()
            L("INFO", "PRODUCT_UPDATE", id=p.id, name=p.name, price=p.price, by=g.actor, ip=client_ip())
            flash("Produk diperbarui.", "ok")
            return redirect(url_for("panel.products"))
        db.session.rollback()
    return render_template("admin/product_form.html", form=form, p=p)


@bp.post("/products/<int:pid>/delete")
@admin_required
def product_delete(pid):
    p = db.get_or_404(Product, pid)
    name, image = p.name, p.image
    db.session.delete(p)
    db.session.commit()
    remove_image("products", image)
    L("WARNING", "PRODUCT_DELETE", id=pid, name=name, by=g.actor, ip=client_ip())
    flash("Produk dihapus.", "ok")
    return redirect(url_for("panel.products"))


# ---- pengguna ----
@bp.get("/users")
@admin_required
def users():
    rows = db.session.scalars(db.select(User).order_by(User.id)).all()
    return render_template("admin/users.html", users=rows)


@bp.post("/users/<int:uid>/toggle")
@admin_required
def user_toggle(uid):
    u = db.get_or_404(User, uid)
    if u.id == web_user().id:
        flash("Anda tidak bisa menonaktifkan akun sendiri.", "err")
    else:
        u.is_active = not u.is_active
        db.session.commit()
        L("WARNING", "USER_STATUS", target=u.username, active=int(u.is_active), by=g.actor, ip=client_ip())
        flash(f"Akun {u.username} {'diaktifkan' if u.is_active else 'dinonaktifkan'}.", "ok")
    return redirect(url_for("panel.users"))


@bp.post("/users/<int:uid>/delete")
@admin_required
def user_delete(uid):
    u = db.get_or_404(User, uid)
    if u.id == web_user().id:
        flash("Anda tidak bisa menghapus akun sendiri.", "err")
    elif u.orders:
        flash("Pengguna punya riwayat pesanan. Nonaktifkan saja, jangan dihapus.", "err")
    else:
        name = u.username
        db.session.delete(u)
        db.session.commit()
        L("WARNING", "USER_DELETE", target=name, by=g.actor, ip=client_ip())
        flash(f"Akun {name} dihapus.", "ok")
    return redirect(url_for("panel.users"))


# ---- pesanan dan verifikasi pembayaran ----
@bp.get("/orders")
@admin_required
def orders():
    status = request.args.get("status", "")
    q = db.select(Order).order_by(Order.id.desc())
    if status in STATUS_LABEL:
        q = q.where(Order.status == status)
    return render_template("admin/orders.html", orders=db.session.scalars(q).all(), labels=STATUS_LABEL, status=status)


@bp.post("/orders/<int:oid>/<action>")
@admin_required
def order_decide(oid, action):
    o = db.get_or_404(Order, oid)
    if action not in ("approve", "reject"):
        abort(404)
    if o.status != "waiting":
        flash("Hanya pesanan berstatus 'Menunggu verifikasi' yang bisa diputuskan.", "err")
    else:
        o.status = "paid" if action == "approve" else "rejected"
        db.session.commit()
        L("INFO", "PAYMENT_DECISION", order=o.id, result=o.status, by=g.actor, ip=client_ip())
        flash(f"Pesanan #{o.id} {'disetujui (lunas)' if action == 'approve' else 'ditolak'}.", "ok")
    return redirect(url_for("panel.orders"))


# ---- laporan penjualan ----
def report_data(d_from, d_to):
    cond = [Order.status == "paid"]
    if d_from:
        cond.append(Order.created_at >= datetime.combine(d_from, time.min))
    if d_to:
        cond.append(Order.created_at < datetime.combine(d_to + timedelta(days=1), time.min))
    day = func.date(Order.created_at)
    daily = [dict(day=str(r[0]), orders=r[1], revenue=int(r[2] or 0))
             for r in db.session.execute(db.select(day, func.count(Order.id), func.sum(Order.total)).where(*cond).group_by(day).order_by(day))]
    top = [dict(name=r[0] or "(produk dihapus)", qty=int(r[1]), revenue=int(r[2]))
           for r in db.session.execute(
               db.select(Product.name, func.sum(OrderItem.qty), func.sum(OrderItem.qty * OrderItem.unit_price))
               .select_from(OrderItem).join(Order, Order.id == OrderItem.order_id)
               .outerjoin(Product, Product.id == OrderItem.product_id)
               .where(*cond).group_by(Product.name).order_by(func.sum(OrderItem.qty).desc()).limit(10))]
    return daily, top, sum(d["orders"] for d in daily), sum(d["revenue"] for d in daily)


@bp.get("/reports")
@admin_required
def reports():
    form = ReportForm(request.args)
    valid = form.validate()
    daily, top, n_orders, revenue = report_data(form.date_from.data, form.date_to.data) if valid else ([], [], 0, 0)
    return render_template("admin/report.html", form=form, daily=daily, top=top, n_orders=n_orders, revenue=revenue,
                           qs={k: v for k, v in request.args.items() if k in ("date_from", "date_to") and v})


@bp.get("/reports/export")
@admin_required
def reports_export():
    form = ReportForm(request.args)
    if not form.validate():
        abort(400)
    daily, top, n_orders, revenue = report_data(form.date_from.data, form.date_to.data)
    fmt = request.args.get("format", "csv")
    L("INFO", "REPORT_EXPORT", format=fmt, by=g.actor, ip=client_ip())
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Per hari"
        ws.append(["Tanggal", "Jumlah pesanan", "Pendapatan (Rp)"])
        for d in daily:
            ws.append([d["day"], d["orders"], d["revenue"]])
        ws.append(["TOTAL", n_orders, revenue])
        ws2 = wb.create_sheet("Produk terlaris")
        ws2.append(["Produk", "Terjual", "Pendapatan (Rp)"])
        for t in top:
            ws2.append([t["name"], t["qty"], t["revenue"]])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="laporan-penjualan.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Tanggal", "Jumlah pesanan", "Pendapatan (Rp)"])
    for d in daily:
        w.writerow([d["day"], d["orders"], d["revenue"]])
    w.writerow(["TOTAL", n_orders, revenue])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=laporan-penjualan.csv"})
