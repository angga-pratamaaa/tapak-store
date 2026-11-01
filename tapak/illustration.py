"""Ilustrasi sepatu (SVG buatan sendiri, tanpa berkas gambar). Dipakai bila produk belum punya foto unggahan.
Port dari generator JavaScript versi awal; warna ditentukan oleh merek dan id produk."""
import itertools

from markupsafe import Markup, escape

PALETTE = {
    "Langkah": ("#15151a", "#ff4b14", "#f1f1f1"), "Rimba": ("#3f5b43", "#e8b04a", "#262626"),
    "Bayu": ("#e8e2d6", "#2b50d8", "#ffffff"), "Kilat": ("#1e40af", "#c6ff3d", "#f3f4f6"),
    "Garuda": ("#b3121e", "#ffffff", "#171717"), "Nusa": ("#d6a064", "#2d2823", "#f2e8d9"),
    "Cakra": ("#222224", "#f6d11a", "#ececec"), "Ombak": ("#0e8a8c", "#fbfbfb", "#1a2a36"),
}
FALLBACK = ("#44464d", "#ff4b14", "#eeeeee")
BASE = "M30,0 L28,60 C26,86 30,104 40,110 C52,114 66,112 76,106 L92,96 C100,80 106,66 126,58 C160,50 198,46 232,32 C262,22 286,12 292,0 Z"
SOLE = {"lari": 26, "gunung": 24, "basket": 22, "kasual": 18, "futsal": 10, "skate": 22}
_uid = itertools.count(1)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _hex(a):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in a)


def mix(a, b, t):
    x, y = _rgb(a), _rgb(b)
    return _hex([v + (y[i] - v) * t for i, v in enumerate(x)])


def shade(h, t):
    return mix(h, "#ffffff", t) if t >= 0 else mix(h, "#000000", -t)


def colors(p):
    up, ac, so = PALETTE.get(p.brand, FALLBACK)
    v = int(p.id or 0) % 3
    if v == 1:
        up, ac = ac, up
    elif v == 2:
        up = mix(up, "#ffffff", 0.18)
    return up, ac, so


def tint(p):
    return colors(p)[1] + "40"


def shoe_svg(p):
    n = next(_uid)
    up, ac, so = colors(p)
    cat = p.category
    name = escape(p.name)
    dark, light = shade(up, -0.3), shade(up, 0.28)
    G = 150
    shadow = f'<ellipse cx="156" cy="{G + 3}" rx="130" ry="7" fill="#000" opacity=".14"/>'
    defs = (f'<defs><linearGradient id="g{n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{up}"/></linearGradient>'
            f'<pattern id="m{n}" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.1" fill="#fff" opacity=".4"/></pattern></defs>')
    if cat == "sandal":
        bed = mix(up, "#000000", 0.55)
        top = shade(bed, 0.22)
        return Markup(
            f'<svg viewBox="0 40 300 130" role="img" aria-label="Ilustrasi sandal {name}" xmlns="http://www.w3.org/2000/svg">{defs}{shadow}'
            f'<path d="M22 134 C22 124 40 120 80 120 H218 C262 120 290 124 292 136 C292 148 272 152 240 152 H60 C34 152 22 146 22 134Z" fill="{bed}"/>'
            f'<path d="M30 122 H282 C288 126 288 130 282 132 H34 C28 130 28 126 30 122Z" fill="{top}"/>'
            f'<path d="M112 122 C118 80 152 72 176 122" fill="none" stroke="url(#g{n})" stroke-width="20" stroke-linecap="round"/>'
            f'<path d="M196 122 C204 88 234 84 252 126" fill="none" stroke="{ac}" stroke-width="18" stroke-linecap="round"/>'
            f'<path d="M40 124 C40 98 62 90 82 122" fill="none" stroke="{up}" stroke-width="14" stroke-linecap="round"/>'
            f'<circle cx="146" cy="96" r="4" fill="{top}"/></svg>')
    high, boot = cat == "basket", cat == "gunung"
    k = 1 if high else 0.82 if boot else 0.62
    S = G - SOLE.get(cat, 18)
    teeth = ""
    if boot:
        teeth = f"M36,{G}" + "".join(f" L{44 + i * 16},{G + 7} L{52 + i * 16},{G}" for i in range(15)) + " Z"
    sole_col = "#f4f1ea" if cat == "skate" else shade(so, 0.1) if cat == "lari" else so
    view = "0 12 300 160" if high or boot else "0 36 300 130"
    sole_path = f"M22 {S} H286 C296 {S} 298 {S + 4} 292 {G - 3} C290 {G} 284 {G} 280 {G} H40 C28 {G} 22 {G - 6} 22 {G - 12} Z"
    laces = " ".join(f"M{112 + i * 24},{72 - i * 8} l9,-13" for i in range(5))
    body = (
        f'<path d="{BASE}" fill="url(#g{n})"/>'
        + (f'<path d="{BASE}" fill="url(#m{n})"/>' if cat == "lari" else "")
        + f'<path d="M32,0 L32,26 C80,40 130,34 170,22 C210,10 250,12 292,0 Z" fill="{ac}"/>'
        f'<path d="M30,0 L28,60 C26,80 30,96 38,104 L58,104 C52,80 52,40 56,0 Z" fill="{dark}" opacity=".5"/>'
        '<path d="M236,32 C262,22 286,12 292,0 L240,0 C246,12 244,24 236,32 Z" fill="#000" opacity=".22"/>'
        f'<path d="M88,96 C94,114 112,118 122,104 L126,58 C112,62 100,76 88,96 Z" fill="{light}"/>'
        f'<path d="M40,110 C52,114 66,112 76,106 L92,96 C100,80 106,66 126,58" fill="none" stroke="{shade(up, 0.55)}" stroke-width="3.5" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'<path d="{laces}" stroke="#fff" stroke-width="4" stroke-linecap="round" fill="none" opacity=".9" vector-effect="non-scaling-stroke"/>')
    extra = ""
    if cat == "lari":
        extra = f'<path d="M30 {S + 12} Q60 {S + 4} 90 {S + 12} T150 {S + 12} T210 {S + 12} T270 {S + 12}" stroke="{ac}" stroke-width="3" fill="none" opacity=".8"/>'
    elif cat == "skate":
        extra = f'<path d="M26 {S + 8} H288" stroke="{ac}" stroke-width="4"/>'
    elif cat == "gunung":
        extra = f'<path d="M22 {S + 6} H290" stroke="{ac}" stroke-width="5"/>'
    return Markup(
        f'<svg viewBox="{view}" role="img" aria-label="Ilustrasi sepatu {name}" xmlns="http://www.w3.org/2000/svg">{defs}{shadow}'
        f'<g transform="translate(0,{S}) scale(1,{-k})">{body}</g>'
        + (f'<path d="{teeth}" fill="{shade(so, -0.1)}"/>' if boot else "")
        + f'<path d="{sole_path}" fill="{sole_col}"/>{extra}</svg>')
