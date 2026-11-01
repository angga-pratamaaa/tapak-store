from tapak.extensions import db
from tapak.models import Product, User
from tapak.security import hash_password

# Kata sandi sengaja lemah untuk uji brute force (hanya lab).
USERS = [("admin", "Admin#2026", "admin"), ("budi", "password123", "client"),
         ("sari", "qwerty123", "client"), ("andi", "123456", "client")]
# Merek fiktif (bukan merek dagang nyata).
PRODUCTS = [
    ("Langkah Runner Pro", "Langkah", "lari", 549000, 40), ("Rimba Trail X", "Rimba", "gunung", 699000, 25),
    ("Bayu Street Low", "Bayu", "kasual", 399000, 60), ("Langkah Court Elite", "Langkah", "basket", 799000, 20),
    ("Bayu Classic Canvas", "Bayu", "kasual", 289000, 80), ("Rimba Hiker Mid", "Rimba", "gunung", 850000, 15),
    ("Langkah Sprint Lite", "Langkah", "lari", 459000, 35), ("Bayu Sandal Pantai", "Bayu", "sandal", 149000, 100),
    ("Kilat Aero Racer", "Kilat", "lari", 629000, 30), ("Kilat Tempo Flow", "Kilat", "lari", 749000, 22),
    ("Garuda Slam High", "Garuda", "basket", 899000, 18), ("Garuda Court Low", "Garuda", "basket", 649000, 26),
    ("Garuda Futsal Strike", "Garuda", "futsal", 479000, 45), ("Nusa Pasir Slide", "Nusa", "sandal", 179000, 90),
    ("Nusa Kampung Loafer", "Nusa", "kasual", 349000, 50), ("Nusa Batik Sneaker", "Nusa", "kasual", 429000, 40),
    ("Cakra Deck Pro", "Cakra", "skate", 559000, 28), ("Cakra Ollie Mid", "Cakra", "skate", 519000, 24),
    ("Cakra Street Vulc", "Cakra", "skate", 459000, 33), ("Ombak Aqua Trail", "Ombak", "gunung", 599000, 20),
    ("Ombak Wave Slide", "Ombak", "sandal", 199000, 70), ("Ombak Marathon Elite", "Ombak", "lari", 1199000, 12),
    ("Kilat Futsal Turbo", "Kilat", "futsal", 519000, 38), ("Bayu Retro 90", "Bayu", "kasual", 479000, 55),
]


def seed():
    """Isi data awal bila tabel users kosong. Mengembalikan True bila data dibuat."""
    if db.session.scalars(db.select(User.id).limit(1)).first():
        return False
    for u, p, r in USERS:
        db.session.add(User(username=u, email=f"{u}@tapak.local", password_hash=hash_password(p), role=r))
    for n, br, cat, pr, st in PRODUCTS:
        db.session.add(Product(name=n, brand=br, category=cat, price=pr, stock=st))
    db.session.commit()
    return True
