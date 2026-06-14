/**
 * static/js/main.js
 * Shared utilities available on every page.
 */

// ── COPY TO CLIPBOARD ─────────────────────────────────
function copyTextToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    if (!btn) return;
    const orig = btn.textContent;
    btn.textContent = "✓ Copied!";
    btn.style.color = "#10b981";
    setTimeout(() => { btn.textContent = orig; btn.style.color = ""; }, 2200);
  });
}

// ── NUMBER FORMATTER ──────────────────────────────────
function fmtNum(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

// ── ANIMATE NUMBER COUNT-UP ───────────────────────────
function countUp(el, target, suffix = "", duration = 1200) {
  const start = performance.now();
  const isFloat = String(target).includes(".");
  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3); // cubic ease-out
    const val = isFloat
      ? (ease * target).toFixed(1)
      : Math.round(ease * target);
    el.textContent = fmtNum(Number(val)) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── TOAST NOTIFICATION ────────────────────────────────
function showToast(msg, type = "info") {
  const colors = { info: "#7c3aed", success: "#10b981", error: "#ef4444" };
  const t = document.createElement("div");
  t.textContent = msg;
  Object.assign(t.style, {
    position: "fixed", bottom: "28px", right: "28px", zIndex: "9999",
    background: colors[type] || colors.info,
    color: "#fff", padding: "12px 22px",
    borderRadius: "10px", fontSize: ".88rem", fontWeight: "600",
    boxShadow: "0 8px 32px rgba(0,0,0,.4)",
    animation: "fadeUp .3s ease",
    pointerEvents: "none",
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
