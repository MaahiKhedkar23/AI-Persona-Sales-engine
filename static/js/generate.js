/**
 * static/js/generate.js
 * Handles:
 *  - Single strategy generation
 *  - Compare mode (two personas side-by-side)
 *  - Rendering funnel stages, flowchart, tips
 *  - Copy full strategy + download as .txt
 */

// ── STAGE COLOURS ─────────────────────────────────────
const STAGE_COLORS = {
  "Awareness":     "#6c63ff",
  "Interest":      "#3ecf8e",
  "Consideration": "#f0c040",
  "Conversion":    "#ff6b6b",
  "Retention":     "#4f8ef7",
};

// Stores the last generated strategy for copy/download
let _lastStrategy = null;

// ── MODE TOGGLE ───────────────────────────────────────
function setMode(mode) {
  const isSingle = mode === "single";
  document.getElementById("single-mode").classList.toggle("hidden", !isSingle);
  document.getElementById("compare-mode").classList.toggle("hidden",  isSingle);
  document.getElementById("btn-single").classList.toggle("active",  isSingle);
  document.getElementById("btn-compare").classList.toggle("active", !isSingle);
}

// ── SINGLE GENERATE ───────────────────────────────────
async function generateSingle() {
  const product = document.getElementById("product").value.trim();
  const persona  = document.getElementById("persona").value;

  if (!product) { showError("single", "Please enter a product name."); return; }
  if (!persona)  { showError("single", "Please choose a persona."); return; }

  setLoadingSingle(true);
  hideError("single");
  document.getElementById("output-section").classList.add("hidden");

  const result = await callAPI(product, persona);

  setLoadingSingle(false);

  if (!result.success) { showError("single", result.error); return; }

  _lastStrategy = result.data;
  renderOutput(result.data);
}

function setLoadingSingle(on) {
  const btn     = document.querySelector("#single-mode .btn-primary");
  const text    = document.getElementById("btn-text");
  const spinner = document.getElementById("btn-spinner");
  btn.disabled = on;
  text.textContent = on ? "Generating…" : "⚡ Generate Strategy";
  spinner.classList.toggle("hidden", !on);
}

// ── COMPARE GENERATE ──────────────────────────────────
async function generateCompare() {
  const product   = document.getElementById("cmp-product").value.trim();
  const personaA  = document.getElementById("cmp-persona-a").value;
  const personaB  = document.getElementById("cmp-persona-b").value;

  if (!product)            { showError("compare", "Please enter a product name."); return; }
  if (!personaA)           { showError("compare", "Please choose Persona A."); return; }
  if (!personaB)           { showError("compare", "Please choose Persona B."); return; }
  if (personaA === personaB) { showError("compare", "Choose two different personas to compare."); return; }

  setLoadingCompare(true);
  hideError("compare");
  document.getElementById("compare-output").classList.add("hidden");

  // Fire both API calls in parallel for speed
  const [resultA, resultB] = await Promise.all([
    callAPI(product, personaA),
    callAPI(product, personaB),
  ]);

  setLoadingCompare(false);

  if (!resultA.success) { showError("compare", "Persona A error: " + resultA.error); return; }
  if (!resultB.success) { showError("compare", "Persona B error: " + resultB.error); return; }

  renderCompare(resultA.data, resultB.data);
}

function setLoadingCompare(on) {
  const btn     = document.getElementById("cmp-btn-text");
  const spinner = document.getElementById("cmp-spinner");
  document.querySelector("#compare-mode .btn-primary").disabled = on;
  btn.textContent = on ? "Generating both…" : "⚡ Compare Personas";
  spinner.classList.toggle("hidden", !on);
}

// ── API CALL ──────────────────────────────────────────
async function callAPI(product, persona) {
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product, persona }),
    });
    return await res.json();
  } catch {
    return { success: false, error: "Network error — is the server running?" };
  }
}

// ── RENDER SINGLE ─────────────────────────────────────
function renderOutput(data) {
  document.getElementById("out-product").textContent = data.product;
  document.getElementById("out-persona").textContent = data.persona;
  renderFlowchart("funnel-flow", data.funnel);
  renderStages("funnel-stages", data.funnel);
  renderTips(data.quick_tips);
  buildStrategyText(data);

  const out = document.getElementById("output-section");
  out.classList.remove("hidden");
  out.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── RENDER COMPARE ────────────────────────────────────
function renderCompare(dataA, dataB) {
  const cols = document.getElementById("compare-columns");
  cols.innerHTML = "";

  [dataA, dataB].forEach((data) => {
    const col = document.createElement("div");
    col.innerHTML = `
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:0">
        <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;margin-bottom:4px;">${data.product}</div>
        <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:16px;">${data.persona}</div>
        <div id="cflow-${data.persona.replace(/\s/g,'')}" class="funnel-flow" style="flex-direction:column;gap:6px;margin-bottom:18px;"></div>
        <div id="cstages-${data.persona.replace(/\s/g,'')}"></div>
      </div>`;
    cols.appendChild(col);

    const safeId = data.persona.replace(/\s/g, "");
    renderFlowchart(`cflow-${safeId}`, data.funnel, true);
    renderStages(`cstages-${safeId}`, data.funnel, true);
  });

  document.getElementById("compare-output").classList.remove("hidden");
  document.getElementById("compare-output").scrollIntoView({ behavior: "smooth" });
}

// ── FLOWCHART ─────────────────────────────────────────
function renderFlowchart(containerId, funnel, compact = false) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  funnel.forEach((stage, i) => {
    const color = STAGE_COLORS[stage.stage] || "#888";

    if (compact) {
      // Vertical compact version for compare mode
      const row = document.createElement("div");
      row.style.cssText = "display:flex;align-items:center;gap:8px;";
      row.innerHTML = `
        <div style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;"></div>
        <span style="font-size:.8rem;font-weight:700;color:${color};">${stage.stage}</span>
        <span style="font-size:.75rem;color:var(--text-muted);flex:1;">${stage.goal}</span>`;
      container.appendChild(row);
    } else {
      const node = document.createElement("div");
      node.className = "flow-node";

      const box = document.createElement("div");
      box.className = "flow-box";
      box.style.background = color;
      box.textContent = stage.stage;
      // Click flowchart box to scroll to that stage card
      box.onclick = () => {
        const card = document.getElementById(`stage-${i}`);
        if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
      };

      const goal = document.createElement("div");
      goal.className = "flow-goal";
      goal.textContent = stage.goal;

      node.appendChild(box);
      node.appendChild(goal);
      container.appendChild(node);

      if (i < funnel.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "flow-arrow";
        arrow.textContent = "→";
        container.appendChild(arrow);
      }
    }
  });
}

// ── STAGE ACCORDION CARDS ─────────────────────────────
function renderStages(containerId, funnel, compact = false) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  funnel.forEach((stage, index) => {
    const color  = STAGE_COLORS[stage.stage] || "#888";
    const cardId = `${containerId}-stage-${index}`;

    // First stage open by default on main view
    const defaultOpen = !compact && index === 0;

    const card = document.createElement("div");
    card.className = "stage-card";
    card.id = `stage-${index}`;
    card.style.animationDelay = `${index * 70}ms`;

    card.innerHTML = `
      <div class="stage-header" onclick="toggleStage('${cardId}')">
        <span class="stage-badge" style="background:${color}"></span>
        <span class="stage-name">${stage.stage}</span>
        ${!compact ? `<span class="stage-goal-preview">${stage.goal}</span>` : ""}
        <span class="stage-toggle ${defaultOpen ? 'open' : ''}" id="toggle-${cardId}">▶</span>
      </div>
      <div class="stage-body ${defaultOpen ? 'open' : ''}" id="body-${cardId}">

        <p class="tactics-heading">Tactics</p>
        <ul class="tactics-list">
          ${stage.tactics.map(t => `<li>${escHtml(t)}</li>`).join("")}
        </ul>

        <div class="content-tabs">
          <button class="tab-btn active" onclick="switchTab(event,'${cardId}','sales')">Sales Message</button>
          <button class="tab-btn"        onclick="switchTab(event,'${cardId}','email')">Email</button>
          <button class="tab-btn"        onclick="switchTab(event,'${cardId}','mktg')">Marketing</button>
        </div>

        <div class="tab-panel active" id="${cardId}-sales">
          <div class="content-block" id="cb-${cardId}-sales">${escHtml(stage.content.sales_message)}</div>
          <button class="copy-btn" onclick="copyCb('cb-${cardId}-sales', this)">⎘ Copy</button>
        </div>

        <div class="tab-panel" id="${cardId}-email">
          <div class="content-block">
            <div class="email-subject">Subject: ${escHtml(stage.content.email.subject)}</div>
            <div id="cb-${cardId}-email">${escHtml(stage.content.email.body)}</div>
          </div>
          <button class="copy-btn" onclick="copyEmail('${cardId}','${escAttr(stage.content.email.subject)}',this)">⎘ Copy</button>
        </div>

        <div class="tab-panel" id="${cardId}-mktg">
          <div class="content-block" id="cb-${cardId}-mktg">${escHtml(stage.content.marketing_text)}</div>
          <button class="copy-btn" onclick="copyCb('cb-${cardId}-mktg', this)">⎘ Copy</button>
        </div>
      </div>`;

    container.appendChild(card);
  });
}

// ── TIPS ──────────────────────────────────────────────
function renderTips(tips) {
  const list = document.getElementById("tips-list");
  if (!list) return;
  list.innerHTML = tips.map(t => `<li>${escHtml(t)}</li>`).join("");
  document.getElementById("tips-card").classList.remove("hidden");
}

// ── ACCORDION & TABS ──────────────────────────────────
function toggleStage(cardId) {
  const body   = document.getElementById(`body-${cardId}`);
  const toggle = document.getElementById(`toggle-${cardId}`);
  const isOpen = body.classList.contains("open");
  body.classList.toggle("open",  !isOpen);
  toggle.classList.toggle("open", !isOpen);
}

function switchTab(event, cardId, tab) {
  const card = event.target.closest(".stage-card");
  card.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  card.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById(`${cardId}-${tab}`).classList.add("active");
}

// ── COPY HELPERS ──────────────────────────────────────
function copyCb(elId, btn) {
  copyTextToClipboard(document.getElementById(elId).innerText, btn);
}
function copyEmail(cardId, subject, btn) {
  const body = document.getElementById(`cb-${cardId}-email`).innerText;
  copyTextToClipboard(`Subject: ${subject}\n\n${body}`, btn);
}

// ── COPY / DOWNLOAD FULL STRATEGY ─────────────────────
function buildStrategyText(data) {
  let text = `SALES STRATEGY REPORT\n`;
  text += `${"=".repeat(50)}\n`;
  text += `Product : ${data.product}\n`;
  text += `Persona : ${data.persona}\n\n`;

  data.funnel.forEach(stage => {
    text += `\n── ${stage.stage.toUpperCase()} ──\n`;
    text += `Goal: ${stage.goal}\n`;
    text += `Tactics:\n${stage.tactics.map(t => `  • ${t}`).join("\n")}\n`;
    text += `Sales Message: ${stage.content.sales_message}\n`;
    text += `Email Subject: ${stage.content.email.subject}\n`;
    text += `Email Body:\n${stage.content.email.body}\n`;
    text += `Marketing Text: ${stage.content.marketing_text}\n`;
  });

  text += `\n── QUICK TIPS ──\n`;
  data.quick_tips.forEach(t => { text += `  ✦ ${t}\n`; });

  document.getElementById("strategy-text-store").value = text;
}

function copyFullStrategy() {
  const text = document.getElementById("strategy-text-store").value;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => alert("Full strategy copied to clipboard!"));
}

function downloadStrategy() {
  const text    = document.getElementById("strategy-text-store").value;
  if (!text) return;
  const product = _lastStrategy?.product || "strategy";
  const blob    = new Blob([text], { type: "text/plain" });
  const a       = document.createElement("a");
  a.href        = URL.createObjectURL(blob);
  a.download    = `${product.replace(/\s+/g, "-").toLowerCase()}-strategy.txt`;
  a.click();
}

// ── ERROR HELPERS ─────────────────────────────────────
function showError(mode, msg) {
  const id = mode === "compare" ? "cmp-error" : "error-banner";
  const el = document.getElementById(id);
  el.textContent = "⚠ " + msg;
  el.classList.remove("hidden");
}
function hideError(mode) {
  const id = mode === "compare" ? "cmp-error" : "error-banner";
  document.getElementById(id).classList.add("hidden");
}

// ── UTILS ─────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function escAttr(s) { return String(s).replace(/'/g, "\\'"); }

// Enter key support
document.addEventListener("DOMContentLoaded", () => {
  const p = document.getElementById("product");
  if (p) p.addEventListener("keydown", e => { if (e.key === "Enter") generateSingle(); });
});
