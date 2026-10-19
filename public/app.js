"use strict";
// Frontend TAPAK: HTML + CSS + JavaScript murni (tanpa framework, tanpa sumber eksternal).
const $ = (s) => document.querySelector(s);
const rupiah = (n) => "Rp " + Number(n).toLocaleString("id-ID");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* penyimpanan diblokir */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* abaikan */ } },
};
let session = store.get("session", null); // {token, role, username}
let cart = store.get("cart", []);         // [{id, name, brand, category, price, size, qty}]
let catalog = [];                          // seluruh produk
let shown = [];                            // hasil (semua atau hasil pencarian)
let state = { cat: "semua", query: "" };
let current = null;                        // produk di modal
let pickedSize = null;

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(session ? { Authorization: "Bearer " + session.token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Permintaan gagal (" + res.status + ")");
  return data;
}

let toastTimer;
function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = isErr ? "err" : ""; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 4000);
}
const guard = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

// ================== ilustrasi sepatu (SVG buatan sendiri) ==================
const PALETTE = {
  Langkah: ["#15151a", "#ff4b14", "#f1f1f1"], Rimba: ["#3f5b43", "#e8b04a", "#262626"],
  Bayu: ["#e8e2d6", "#2b50d8", "#ffffff"], Kilat: ["#1e40af", "#c6ff3d", "#f3f4f6"],
  Garuda: ["#b3121e", "#ffffff", "#171717"], Nusa: ["#d6a064", "#2d2823", "#f2e8d9"],
  Cakra: ["#222224", "#f6d11a", "#ececec"], Ombak: ["#0e8a8c", "#fbfbfb", "#1a2a36"],
};
const FALLBACK = ["#44464d", "#ff4b14", "#eeeeee"];
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const toHex = (a) => "#" + a.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
const mix = (a, b, t) => { const x = hex(a), y = hex(b); return toHex(x.map((v, i) => v + (y[i] - v) * t)); };
const shade = (h, t) => (t >= 0 ? mix(h, "#ffffff", t) : mix(h, "#000000", -t));
function colors(p) {
  let [up, ac, so] = PALETTE[p.brand] || FALLBACK;
  const v = Number(p.id) % 3;
  if (v === 1) [up, ac] = [ac, up];
  if (v === 2) up = mix(up, "#ffffff", 0.18);
  return { up, ac, so };
}
let uid = 0;
// Bentuk dasar sepatu digambar dalam koordinat (x, d), d = tinggi di atas sol; k = skala tinggi.
const BASE = "M30,0 L28,60 C26,86 30,104 40,110 C52,114 66,112 76,106 L92,96 C100,80 106,66 126,58 C160,50 198,46 232,32 C262,22 286,12 292,0 Z";
function shoeSVG(p) {
  const n = ++uid, { up, ac, so } = colors(p), cat = p.category;
  const dark = shade(up, -0.3), light = shade(up, 0.28);
  const G = 150, shadow = `<ellipse cx="156" cy="${G + 3}" rx="130" ry="7" fill="#000" opacity=".14"/>`;
  const defs = `<defs><linearGradient id="g${n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${light}"/><stop offset="1" stop-color="${up}"/></linearGradient>
    <pattern id="m${n}" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.1" fill="#fff" opacity=".4"/></pattern></defs>`;
  if (cat === "sandal") {
    const bed = mix(up, "#000000", 0.55), top = shade(bed, 0.22);
    return `<svg viewBox="0 40 300 130" role="img" aria-label="Ilustrasi sandal ${esc(p.name)}" xmlns="http://www.w3.org/2000/svg">${defs}${shadow}
      <path d="M22 134 C22 124 40 120 80 120 H218 C262 120 290 124 292 136 C292 148 272 152 240 152 H60 C34 152 22 146 22 134Z" fill="${bed}"/>
      <path d="M30 122 H282 C288 126 288 130 282 132 H34 C28 130 28 126 30 122Z" fill="${top}"/>
      <path d="M112 122 C118 80 152 72 176 122" fill="none" stroke="url(#g${n})" stroke-width="20" stroke-linecap="round"/>
      <path d="M196 122 C204 88 234 84 252 126" fill="none" stroke="${ac}" stroke-width="18" stroke-linecap="round"/>
      <path d="M40 124 C40 98 62 90 82 122" fill="none" stroke="${up}" stroke-width="14" stroke-linecap="round"/>
      <circle cx="146" cy="96" r="4" fill="${top}"/></svg>`;
  }
  const high = cat === "basket", boot = cat === "gunung";
  const k = high ? 1 : boot ? 0.82 : 0.62;
  const sole = { lari: 26, gunung: 24, basket: 22, kasual: 18, futsal: 10, skate: 22 }[cat] ?? 18;
  const S = G - sole;
  const teeth = boot ? "M36," + G + Array.from({ length: 15 }, (_, i) => ` L${44 + i * 16},${G + 7} L${52 + i * 16},${G}`).join("") + " Z" : "";
  const soleCol = cat === "skate" ? "#f4f1ea" : cat === "lari" ? shade(so, 0.1) : so;
  const view = high || boot ? "0 12 300 160" : "0 36 300 130";
  const solePath = `M22 ${S} H286 C296 ${S} 298 ${S + 4} 292 ${G - 3} C290 ${G} 284 ${G} 280 ${G} H40 C28 ${G} 22 ${G - 6} 22 ${G - 12} Z`;
  const laces = Array.from({ length: 5 }, (_, i) => { const x = 112 + i * 24, d = 72 - i * 8; return `M${x},${d} l9,-13`; }).join(" ");
  const body = `
    <path d="${BASE}" fill="url(#g${n})"/>
    ${cat === "lari" ? `<path d="${BASE}" fill="url(#m${n})"/>` : ""}
    <path d="M32,0 L32,26 C80,40 130,34 170,22 C210,10 250,12 292,0 Z" fill="${ac}"/>
    <path d="M30,0 L28,60 C26,80 30,96 38,104 L58,104 C52,80 52,40 56,0 Z" fill="${dark}" opacity=".5"/>
    <path d="M236,32 C262,22 286,12 292,0 L240,0 C246,12 244,24 236,32 Z" fill="#000" opacity=".22"/>
    <path d="M88,96 C94,114 112,118 122,104 L126,58 C112,62 100,76 88,96 Z" fill="${light}"/>
    <path d="M40,110 C52,114 66,112 76,106 L92,96 C100,80 106,66 126,58" fill="none" stroke="${shade(up, 0.55)}" stroke-width="3.5" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
    <path d="${laces}" stroke="#fff" stroke-width="4" stroke-linecap="round" fill="none" opacity=".9" vector-effect="non-scaling-stroke"/>`;
  return `<svg viewBox="${view}" role="img" aria-label="Ilustrasi sepatu ${esc(p.name)}" xmlns="http://www.w3.org/2000/svg">${defs}${shadow}
    <g transform="translate(0,${S}) scale(1,${-k})">${body}</g>
    ${boot ? `<path d="${teeth}" fill="${shade(so, -0.1)}"/>` : ""}
    <path d="${solePath}" fill="${soleCol}"/>
    ${cat === "lari" ? `<path d="M30 ${S + 12} Q60 ${S + 4} 90 ${S + 12} T150 ${S + 12} T210 ${S + 12} T270 ${S + 12}" stroke="${ac}" stroke-width="3" fill="none" opacity=".8"/>` : ""}
    ${cat === "skate" ? `<path d="M26 ${S + 8} H288" stroke="${ac}" stroke-width="4"/>` : ""}
    ${cat === "gunung" ? `<path d="M22 ${S + 6} H290" stroke="${ac}" stroke-width="5"/>` : ""}</svg>`;
}
const tint = (p) => colors(p).ac + "40";

// ================== sesi dan navigasi ==================
function renderSession() {
  $("#nav-login").hidden = !!session;
  $("#nav-logout").hidden = !session;
  $("#who").textContent = session ? session.username : "";
  document.querySelectorAll("[data-auth]").forEach((e) => { e.hidden = !session; });
  document.querySelectorAll("[data-admin]").forEach((e) => { e.hidden = !(session && session.role === "admin"); });
  $("#cart-count").textContent = cart.reduce((n, i) => n + i.qty, 0);
  $("#cart-count").hidden = cart.length === 0;
}

const views = ["produk", "pesanan", "admin", "masuk"];
function route() {
  const h = location.hash.slice(1);
  const name = h === "koleksi" ? "produk" : views.includes(h) ? h : "produk";
  views.forEach((v) => { $("#v-" + v).hidden = v !== name; });
  document.querySelectorAll(".tools a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + name));
  if (name === "produk") guard(loadProducts)().then(() => { if (h === "koleksi") $("#koleksi").scrollIntoView(); });
  if (name === "pesanan") guard(loadOrders)();
  if (name === "admin") guard(loadAdmin)();
  if (name !== "masuk") closeAll();
  window.scrollTo({ top: 0 });
}

// ================== katalog ==================
const CATS = [["semua", "Semua"], ["lari", "Lari"], ["gunung", "Gunung"], ["basket", "Basket"], ["kasual", "Kasual"],
              ["sandal", "Sandal"], ["futsal", "Futsal"], ["skate", "Skate"]];
const label = (c) => (CATS.find((x) => x[0] === c) || [c, c])[1];

function renderCatNav() {
  $("#cat-nav").innerHTML = CATS.map(([k, v]) => `<button data-cat="${k}" class="${state.cat === k ? "on" : ""}">${v}</button>`).join("");
}
function renderTiles() {
  $("#tiles").innerHTML = CATS.slice(1).map(([k, v]) => {
    const items = catalog.filter((p) => p.category === k);
    if (!items.length) return "";
    return `<button class="tile" data-cat-go="${k}"><b>${v}</b><span>${items.length} model</span>${shoeSVG(items[0])}</button>`;
  }).join("");
}
function renderBrands() {
  const sel = $("#f-brand"), keep = sel.value;
  const brands = [...new Set(catalog.map((p) => p.brand).filter(Boolean))].sort();
  sel.innerHTML = '<option value="">Semua merek</option>' + brands.map((b) => `<option>${esc(b)}</option>`).join("");
  sel.value = brands.includes(keep) ? keep : "";
}

function applyFilters() {
  let list = shown.slice();
  if (state.cat !== "semua") list = list.filter((p) => p.category === state.cat);
  const brand = $("#f-brand").value; if (brand) list = list.filter((p) => p.brand === brand);
  const pr = $("#f-price").value;
  if (pr) { const [lo, hi] = pr.split("-").map(Number); list = list.filter((p) => p.price >= lo && p.price < hi); }
  const sort = $("#f-sort").value;
  if (sort === "low") list.sort((a, b) => a.price - b.price);
  if (sort === "high") list.sort((a, b) => b.price - a.price);
  if (sort === "name") list.sort((a, b) => String(a.name).localeCompare(String(b.name)));

  const plain = !state.query && state.cat === "semua";
  $("#hero").hidden = !plain; $("#tiles").hidden = !plain;
  $("#shelf-title").textContent = state.query ? "Hasil untuk “" + state.query + "”" : state.cat === "semua" ? "Semua sepatu" : "Sepatu " + label(state.cat).toLowerCase();
  $("#shelf-count").textContent = list.length + " produk";
  $("#products").innerHTML = list.length ? list.map((p) => {
    const low = Number(p.stock) > 0 && Number(p.stock) < 20, out = Number(p.stock) === 0;
    return `<article class="card" data-open="${Number(p.id)}" tabindex="0" aria-label="${esc(p.name)}">
      <div class="media" style="--tint:${tint(p)}">${shoeSVG(p)}
        ${out ? '<span class="tag">Habis</span>' : low ? '<span class="tag hot">Stok tipis</span>' : ""}</div>
      <div class="info"><div class="price">${rupiah(p.price)}</div><h3>${esc(p.name)}</h3>
      <p class="sub">${esc(p.brand || "")}${p.category ? " · " + esc(p.category) : ""}</p></div></article>`;
  }).join("") : '<p class="empty">Sepatu tidak ditemukan. Coba kata kunci atau filter lain.</p>';
  renderCatNav();
}

async function loadProducts() {
  catalog = await api("/api/products");
  shown = state.query ? await api("/api/products/search?q=" + encodeURIComponent(state.query)) : catalog;
  if (!$("#hero-art").innerHTML) {
    const hero = catalog.find((p) => p.category === "lari") || catalog[0];
    if (hero) { $("#hero-art").innerHTML = shoeSVG({ ...hero, id: 3, brand: "Langkah", category: "basket" }); $("#auth-art").innerHTML = shoeSVG({ ...hero, id: 1, brand: "Garuda", category: "basket" }); }
  }
  renderTiles(); renderBrands(); applyFilters();
}

$("#search-form").addEventListener("submit", guard(async (e) => {
  e.preventDefault();
  state.query = $("#q").value.trim();
  if (location.hash !== "#produk" && location.hash !== "#koleksi") { location.hash = "#produk"; return; }
  await loadProducts(); $("#koleksi").scrollIntoView({ behavior: "smooth" });
}));
for (const id of ["#f-brand", "#f-price", "#f-sort"]) $(id).addEventListener("change", applyFilters);
document.addEventListener("click", guard(async (e) => {
  const c = e.target.closest("[data-cat],[data-cat-go]");
  if (c) {
    state.cat = c.dataset.cat || c.dataset.catGo;
    if (location.hash !== "#produk" && location.hash !== "#koleksi") { location.hash = "#produk"; return; }
    applyFilters(); $("#koleksi").scrollIntoView({ behavior: "smooth" });
  }
}));
$("#products").addEventListener("click", (e) => { const c = e.target.closest("[data-open]"); if (c) guard(openProduct)(Number(c.dataset.open)); });
$("#products").addEventListener("keydown", (e) => { if (e.key === "Enter") { const c = e.target.closest("[data-open]"); if (c) guard(openProduct)(Number(c.dataset.open)); } });

// ================== detail produk dan ulasan ==================
const SIZES = [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46];
async function openProduct(id) {
  current = catalog.find((x) => x.id === id) || shown.find((x) => x.id === id);
  if (!current) return;
  pickedSize = null;
  $("#m-media").style.setProperty("--tint", tint(current));
  $("#m-media").innerHTML = shoeSVG(current);
  $("#m-brand").textContent = current.brand || "";
  $("#m-name").textContent = current.name;
  $("#m-price").textContent = rupiah(current.price);
  $("#m-meta").textContent = (current.category ? "Kategori " + current.category : "") + (current.stock !== undefined ? " · Stok " + current.stock : "");
  $("#m-size-grid").innerHTML = SIZES.map((s) => `<button data-size="${s}">${s}</button>`).join("");
  $("#modal").hidden = false; document.body.style.overflow = "hidden";
  await loadReviews();
}
$("#m-size-grid").addEventListener("click", (e) => {
  const b = e.target.closest("[data-size]"); if (!b) return;
  pickedSize = Number(b.dataset.size);
  document.querySelectorAll("#m-size-grid button").forEach((x) => x.classList.toggle("on", x === b));
});
$("#m-add").addEventListener("click", () => {
  if (!current) return;
  if (!pickedSize) { toast("Pilih ukuran dulu", true); return; }
  const line = cart.find((i) => i.id === current.id && i.size === pickedSize);
  if (line) line.qty += 1;
  else cart.push({ id: current.id, name: current.name, brand: current.brand, category: current.category, price: current.price, size: pickedSize, qty: 1 });
  store.set("cart", cart); renderSession(); closeAll(); openDrawer();
});

async function loadReviews() {
  $("#reviews-title").textContent = "Ulasan";
  const list = await api("/api/products/" + current.id + "/reviews");
  // Komentar ditampilkan sebagai HTML. Aman bila server meng-escape (VULN_XSS=0),
  // rentan XSS tersimpan bila server menyimpan HTML mentah (VULN_XSS=1).
  $("#reviews-list").innerHTML = list.length
    ? list.map((r) => `<div class="review"><b>${esc(r.username)}</b> · ${esc(r.rating)}/5<div>${r.comment}</div></div>`).join("")
    : '<p class="muted">Belum ada ulasan.</p>';
  $("#review-form").hidden = !session; $("#rv-login").hidden = !!session;
}
$("#review-form").addEventListener("submit", guard(async (e) => {
  e.preventDefault();
  await api("/api/products/" + current.id + "/reviews", { method: "POST", body: { rating: Number($("#rv-rating").value), comment: $("#rv-comment").value } });
  $("#rv-comment").value = ""; toast("Ulasan terkirim"); await loadReviews();
}));

// ================== keranjang (laci) dan pesanan ==================
function openDrawer() { renderCart(); $("#drawer-wrap").hidden = false; document.body.style.overflow = "hidden"; }
function closeAll() { $("#modal").hidden = true; $("#drawer-wrap").hidden = true; document.body.style.overflow = ""; }
$("#cart-btn").addEventListener("click", openDrawer);
$("#d-close").addEventListener("click", closeAll);
$("#m-close").addEventListener("click", closeAll);
for (const id of ["#modal", "#drawer-wrap"]) $(id).addEventListener("mousedown", (e) => { if (e.target.id === id.slice(1)) closeAll(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAll(); });

function renderCart() {
  const box = $("#cart");
  if (!cart.length) { box.innerHTML = '<p class="muted" style="padding:24px 0">Keranjang masih kosong.</p><button class="btn solid" data-close>Mulai belanja</button>'; return; }
  const total = cart.reduce((n, i) => n + i.price * i.qty, 0);
  box.innerHTML = cart.map((i) => `<div class="line-item"><div class="thumb">${shoeSVG({ id: i.id, brand: i.brand, category: i.category, name: i.name })}</div>
    <div><h4>${esc(i.name)}</h4><div class="muted">Ukuran ${esc(i.size)} · ${rupiah(i.price)}</div>
      <div><span class="qty"><button data-dec="${i.id}:${i.size}" aria-label="Kurangi">−</button><span>${i.qty}</span><button data-inc="${i.id}:${i.size}" aria-label="Tambah">+</button></span>
      <button class="rm" data-del="${i.id}:${i.size}">Hapus</button></div></div></div>`).join("") +
    `<div class="cart-total"><span>Total</span><span>${rupiah(total)}</span></div><button class="btn solid wide" id="checkout" style="margin-top:14px">Bayar</button>`;
}
$("#cart").addEventListener("click", guard(async (e) => {
  const t = e.target;
  if (t.closest("[data-close]")) { closeAll(); return; }
  const key = (a) => t.closest(`[${a}]`)?.getAttribute(a);
  const find = (k) => cart.find((i) => `${i.id}:${i.size}` === k);
  if (key("data-inc")) find(key("data-inc")).qty += 1;
  else if (key("data-dec")) { const l = find(key("data-dec")); l.qty = Math.max(1, l.qty - 1); }
  else if (key("data-del")) cart = cart.filter((i) => `${i.id}:${i.size}` !== key("data-del"));
  else if (t.id === "checkout") {
    if (!session) { closeAll(); location.hash = "#masuk"; toast("Masuk dulu untuk membayar", true); return; }
    // Harga ikut dikirim di badan permintaan (dipakai pada skenario manipulasi harga).
    const r = await api("/api/orders", { method: "POST", body: { items: cart.map((i) => ({ product_id: i.id, qty: i.qty, size: i.size, price: i.price })) } });
    cart = []; store.set("cart", cart); renderSession(); closeAll(); toast("Pesanan #" + r.id + " berhasil, total " + rupiah(r.total));
    location.hash = "#pesanan"; return;
  } else return;
  store.set("cart", cart); renderSession(); renderCart();
}));

function table(cols, rows) {
  return `<table><thead><tr>${cols.map((c) => `<th>${esc(c[1])}</th>`).join("")}</tr></thead><tbody>` +
    rows.map((r) => `<tr>${cols.map((c) => `<td>${c[2] ? c[2](r) : esc(r[c[0]])}</td>`).join("")}</tr>`).join("") + "</tbody></table>";
}
async function loadOrders() {
  $("#order-detail").hidden = true;
  if (!session) { $("#orders").innerHTML = '<p class="muted">Masuk untuk melihat pesanan.</p>'; return; }
  const rows = await api("/api/orders");
  $("#orders").innerHTML = rows.length ? '<div class="tablewrap">' + table([["id", "No."], ["total", "Total", (r) => rupiah(r.total)], ["status", "Status"],
    ["", "", (r) => `<button class="btn line sm" data-order="${Number(r.id)}">Detail</button>`]], rows) + "</div>" : '<p class="muted">Belum ada pesanan.</p>';
}
$("#orders").addEventListener("click", guard(async (e) => {
  const b = e.target.closest("[data-order]"); if (!b) return;
  const o = await api("/api/orders/" + b.dataset.order);
  const d = $("#order-detail");
  d.innerHTML = `<h2>Pesanan #${Number(o.id)}</h2><p>Total ${rupiah(o.total)} · ${esc(o.status)}</p>` +
    table([["product_id", "Produk ID"], ["size", "Ukuran"], ["qty", "Jumlah"], ["unit_price", "Harga satuan", (r) => rupiah(r.unit_price)]], o.items);
  d.hidden = false;
}));

// ================== dashboard admin dan CRUD produk ==================
let editingId = null, adminProducts = [];
function resetProductForm() {
  editingId = null; $("#product-form").reset(); $("#pf-title").textContent = "Tambah sepatu"; $("#pf-cancel").hidden = true;
}
async function loadAdmin() {
  $("#admin-badge").hidden = !(session && session.role === "admin");
  try {
    const [stats, prods, users, orders] = await Promise.all([api("/admin/stats"), api("/api/products"), api("/admin/users"), api("/admin/orders")]);
    $("#admin-denied").hidden = true; $("#admin-body").hidden = false;
    $("#stats").innerHTML = [["Pengguna", stats.users], ["Produk", stats.products], ["Pesanan", stats.orders],
      ["Stok menipis (<10)", stats.low_stock], ["Pendapatan", rupiah(stats.revenue)]]
      .map(([k, v]) => `<div class="stat"><div class="muted">${esc(k)}</div><div class="num">${esc(v)}</div></div>`).join("");
    adminProducts = prods;
    $("#admin-products").innerHTML = table([["id", "ID"], ["name", "Nama"], ["brand", "Merek"], ["category", "Kategori"],
      ["price", "Harga", (r) => rupiah(r.price)], ["stock", "Stok"],
      ["", "", (r) => `<button class="btn line sm" data-edit="${Number(r.id)}">Ubah</button> <button class="btn line sm danger" data-delp="${Number(r.id)}">Hapus</button>`]], prods);
    $("#admin-users").innerHTML = table([["id", "ID"], ["username", "Username"], ["role", "Peran"]], users);
    $("#admin-orders").innerHTML = table([["id", "No."], ["user_id", "User"], ["total", "Total", (r) => rupiah(r.total)], ["status", "Status"]], orders);
  } catch (e) {
    $("#admin-body").hidden = true; $("#admin-denied").hidden = false;
  }
}
$("#product-form").addEventListener("submit", guard(async (e) => {
  e.preventDefault();
  const body = { name: $("#pf-name").value, brand: $("#pf-brand").value, category: $("#pf-category").value,
                 price: Number($("#pf-price").value), stock: Number($("#pf-stock").value) };
  if (editingId) await api("/admin/products/" + editingId, { method: "PUT", body });
  else await api("/admin/products", { method: "POST", body });
  toast(editingId ? "Produk diperbarui" : "Produk ditambahkan"); resetProductForm(); await loadAdmin();
}));
$("#pf-cancel").addEventListener("click", resetProductForm);
$("#admin-products").addEventListener("click", guard(async (e) => {
  const ed = e.target.closest("[data-edit]"), del = e.target.closest("[data-delp]");
  if (ed) {
    const p = adminProducts.find((x) => x.id === Number(ed.dataset.edit)); if (!p) return;
    editingId = p.id; $("#pf-title").textContent = "Ubah sepatu #" + p.id;
    $("#pf-name").value = p.name; $("#pf-brand").value = p.brand || ""; $("#pf-category").value = p.category;
    $("#pf-price").value = p.price; $("#pf-stock").value = p.stock; $("#pf-cancel").hidden = false;
    $("#product-form").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  if (del) {
    if (del.dataset.arm !== "1") { del.dataset.arm = "1"; del.textContent = "Yakin hapus?"; return; } // konfirmasi dua langkah
    await api("/admin/products/" + del.dataset.delp, { method: "DELETE" });
    toast("Produk dihapus"); await loadAdmin();
  }
}));

// ================== masuk, daftar, keluar ==================
$("#login-form").addEventListener("submit", guard(async (e) => {
  e.preventDefault();
  const r = await api("/api/login", { method: "POST", body: { username: $("#l-user").value, password: $("#l-pass").value } });
  session = { token: r.token, role: r.role, username: r.username }; store.set("session", session);
  $("#l-pass").value = ""; renderSession(); toast("Selamat datang, " + r.username); location.hash = "#produk";
}));
$("#register-form").addEventListener("submit", guard(async (e) => {
  e.preventDefault();
  await api("/api/register", { method: "POST", body: { username: $("#r-user").value, password: $("#r-pass").value } });
  toast("Akun dibuat, silakan masuk"); $("#register-form").reset();
}));
$("#nav-logout").addEventListener("click", () => { session = null; store.del("session"); renderSession(); location.hash = "#produk"; });

window.addEventListener("hashchange", route);
renderSession(); renderCatNav();
route();
