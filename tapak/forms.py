"""Form WTForms: validasi sisi server. Atribut HTML5 (required, minlength, pattern) menambah validasi sisi klien."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import DateField, IntegerField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp, ValidationError

from tapak.config import CATEGORIES

IMG = FileAllowed(["jpg", "jpeg", "png", "webp"], "Hanya JPG, PNG, atau WEBP.")
CAT_CHOICES = [(c, c.capitalize()) for c in CATEGORIES]


class LoginForm(FlaskForm):
    username = StringField("Username", [DataRequired("Username wajib diisi."), Length(max=50)],
                           render_kw={"autocomplete": "username", "maxlength": 50})
    password = PasswordField("Kata sandi", [DataRequired("Kata sandi wajib diisi.")], render_kw={"autocomplete": "current-password"})


class RegisterForm(FlaskForm):
    username = StringField("Username", [
        DataRequired("Username wajib diisi."), Length(3, 50, "Username 3-50 karakter."),
        Regexp(r"^[A-Za-z0-9_.-]+$", message="Hanya huruf, angka, titik, garis bawah, dan minus.")],
        render_kw={"minlength": 3, "maxlength": 50, "pattern": r"[A-Za-z0-9_.\-]+", "autocomplete": "username"})
    email = StringField("Email", [DataRequired("Email wajib diisi."), Email("Format email tidak valid."), Length(max=120)],
                        render_kw={"type": "email", "maxlength": 120, "autocomplete": "email"})
    password = PasswordField("Kata sandi", [DataRequired("Kata sandi wajib diisi."), Length(8, 128, "Minimal 8 karakter.")],
                             render_kw={"minlength": 8, "autocomplete": "new-password"})
    confirm = PasswordField("Ulangi kata sandi", [DataRequired("Ulangi kata sandi."), EqualTo("password", "Kata sandi tidak sama.")],
                            render_kw={"minlength": 8, "autocomplete": "new-password"})

    def validate_password(self, field):
        s = field.data or ""
        if not (any(c.isalpha() for c in s) and any(c.isdigit() for c in s)):
            raise ValidationError("Kata sandi harus memuat huruf dan angka.")


class ProductForm(FlaskForm):
    name = StringField("Nama produk", [DataRequired("Nama wajib diisi."), Length(max=120)], render_kw={"maxlength": 120})
    brand = StringField("Merek", [Length(max=60)], render_kw={"maxlength": 60})
    category = SelectField("Kategori", choices=CAT_CHOICES)
    price = IntegerField("Harga (Rp)", [DataRequired("Harga wajib diisi."), NumberRange(0, 100_000_000, "Harga 0 - 100.000.000.")],
                         render_kw={"type": "number", "min": 0, "max": 100000000, "step": 1})
    stock = IntegerField("Stok", [NumberRange(0, 100_000, "Stok 0 - 100.000.")], default=0,
                         render_kw={"type": "number", "min": 0, "max": 100000, "step": 1})
    description = TextAreaField("Deskripsi", [Length(max=2000)], render_kw={"rows": 4, "maxlength": 2000})
    image = FileField("Foto produk (JPG/PNG/WEBP, maks. 2 MB)", [Optional(), IMG], render_kw={"accept": "image/png,image/jpeg,image/webp"})


class FilterForm(FlaskForm):
    """Filter katalog (GET): kata kunci, kategori, rentang harga."""

    class Meta:
        csrf = False

    q = StringField("Cari", [Length(max=100)], render_kw={"maxlength": 100, "placeholder": "Cari sepatu atau merek"})
    category = SelectField("Kategori", choices=[("", "Semua kategori")] + CAT_CHOICES, default="")
    min_price = IntegerField("Harga min", [Optional(), NumberRange(0, 100_000_000)], render_kw={"type": "number", "min": 0, "placeholder": "0"})
    max_price = IntegerField("Harga maks", [Optional(), NumberRange(0, 100_000_000)], render_kw={"type": "number", "min": 0, "placeholder": "tanpa batas"})

    def validate_max_price(self, field):
        if field.data is not None and self.min_price.data is not None and field.data < self.min_price.data:
            raise ValidationError("Harga maks harus >= harga min.")


class CartAddForm(FlaskForm):
    product_id = IntegerField("Produk", [DataRequired()])
    size = IntegerField("Ukuran", [DataRequired("Pilih ukuran."), NumberRange(36, 46, "Ukuran 36-46.")],
                        render_kw={"type": "number", "min": 36, "max": 46})
    qty = IntegerField("Jumlah", [DataRequired(), NumberRange(1, 10, "Jumlah 1-10.")], default=1,
                       render_kw={"type": "number", "min": 1, "max": 10})


class ReviewForm(FlaskForm):
    rating = SelectField("Nilai", choices=[(str(i), f"{i} bintang") for i in (5, 4, 3, 2, 1)], default="5")
    comment = TextAreaField("Ulasan", [DataRequired("Ulasan wajib diisi."), Length(max=1000)], render_kw={"rows": 3, "maxlength": 1000})


class ProofForm(FlaskForm):
    proof = FileField("Bukti pembayaran (JPG/PNG/WEBP, maks. 2 MB)", [FileRequired("Pilih berkas bukti pembayaran."), IMG],
                      render_kw={"accept": "image/png,image/jpeg,image/webp"})


class ReportForm(FlaskForm):
    class Meta:
        csrf = False

    date_from = DateField("Dari tanggal", [Optional()], render_kw={"type": "date"})
    date_to = DateField("Sampai tanggal", [Optional()], render_kw={"type": "date"})

    def validate_date_to(self, field):
        if field.data and self.date_from.data and field.data < self.date_from.data:
            raise ValidationError("Tanggal akhir harus >= tanggal awal.")
