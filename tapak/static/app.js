// Validasi sisi klien (menambah validasi server): pesan galat HTML5 dalam bahasa Indonesia,
// pencocokan kata sandi, dan konfirmasi sebelum menghapus.
(function () {
  function msg(el) {
    var v = el.validity;
    if (v.valueMissing) return "Kolom ini wajib diisi.";
    if (v.typeMismatch) return "Format tidak valid.";
    if (v.tooShort) return "Minimal " + el.getAttribute("minlength") + " karakter.";
    if (v.patternMismatch) return "Karakter tidak diizinkan.";
    if (v.rangeUnderflow || v.rangeOverflow) return "Nilai di luar rentang (" + (el.min || "") + " - " + (el.max || "") + ").";
    return "";
  }
  function check(el) {
    if (el.name === "confirm") {
      var pw = el.form.querySelector("[name=password]");
      el.setCustomValidity(pw && el.value !== pw.value ? "Kata sandi tidak sama." : "");
    }
    if (el.name === "password" && el.form.querySelector("[name=confirm]")) {
      var s = el.value;
      el.setCustomValidity(s && !(/[A-Za-z]/.test(s) && /\d/.test(s)) ? "Harus memuat huruf dan angka." : "");
    }
    var holder = el.closest(".field");
    if (!holder) return;
    var note = holder.querySelector(".js-err");
    if (!note) { note = document.createElement("small"); note.className = "err js-err"; holder.appendChild(note); }
    var m = el.validity.valid ? "" : (msg(el) || el.validationMessage);
    note.textContent = m;
    holder.classList.toggle("has-err", !!m);
  }
  document.querySelectorAll("form[data-validate]").forEach(function (f) {
    f.setAttribute("novalidate", "");
    f.addEventListener("input", function (e) { if (e.target.matches("input,select,textarea")) check(e.target); });
    f.addEventListener("submit", function (e) {
      var bad = false;
      f.querySelectorAll("input,select,textarea").forEach(function (el) { check(el); if (!el.validity.valid) bad = true; });
      if (bad) { e.preventDefault(); f.querySelector(".has-err input,.has-err select,.has-err textarea").focus(); }
    });
  });
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) { if (!window.confirm(f.dataset.confirm)) e.preventDefault(); });
  });
})();
