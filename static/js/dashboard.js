/**
 * dashboard.js — SalesAI Platform
 * Restructured: Setup Phase → Strategy Intelligence Phase
 *
 * Flow:
 *   pickCategory → pickPersona → pickBehavior → startGenerate()
 *   → AI thinking animation → renderStrategyIntelligence()
 *   → Interactive funnel expand → Launch Workspace button
 */

// ── CONSTANTS ─────────────────────────────────────────
const STAGE_COLORS = {
  Awareness:     "#7c3aed",
  Interest:      "#2563eb",
  Consideration: "#f59e0b",
  Conversion:    "#ef4444",
  Retention:     "#10b981",
};

const BEHAVIOR_DESCS = {
  "Budget Sensitive":  "Price-conscious — highlight value, savings & free trials.",
  "Premium Buyer":     "Quality-driven — use aspirational, exclusive language.",
  "Impulsive":         "Emotion-driven — urgency, FOMO & strong CTAs work best.",
  "Research-Oriented": "Data-first — provide comparisons, proof & trust signals.",
  "ROI-Focused":       "ROI-led — lead with numbers, efficiency gains, payback period.",
};

// ── APP STATE ──────────────────────────────────────────
const S = {
  category:   null,
  persona:    null,
  behavior:   null,
  campaignId: null,
  lastData:   null,
};

// ══════════════════════════════════════════════════════
// PHASE 1: PERSONA SELECTOR
// ══════════════════════════════════════════════════════

// L1: Category
function pickCategory(cat) {
  S.category = cat;
  S.persona  = null;
  S.behavior = null;

  document.querySelectorAll(".cpc").forEach(c =>
    c.classList.toggle("selected", c.dataset.cat === cat)
  );

  // Build L2 persona cards
  const grid = document.getElementById("persona-picker");
  grid.innerHTML = "";
  const personas = HIERARCHY[cat].personas;

  Object.entries(personas).forEach(([name, data]) => {
    const card = document.createElement("div");
    card.className = "ppc";
    card.dataset.persona = name;
    card.innerHTML = `
      <span class="ppc-icon">${data.icon}</span>
      <div class="ppc-body">
        <div class="ppc-name">${name}</div>
        <div class="ppc-desc">${data.desc}</div>
      </div>
      <span class="ppc-tick">✓</span>`;
    card.onclick = () => pickPersona(name, data, card);
    grid.appendChild(card);
  });

  showGroup("l2-group");
  hideGroup("l3-group");
  document.getElementById("persona-hint").textContent = "";
  syncProfilePill();
  syncGenBtn();
}

// L2: Persona
function pickPersona(name, data, cardEl) {
  S.persona  = name;
  S.behavior = null;

  document.querySelectorAll(".ppc").forEach(c => c.classList.remove("selected"));
  cardEl.classList.add("selected");
  document.getElementById("persona-hint").textContent = data.desc;

  // Build L3 behavior cards
  const grid = document.getElementById("behavior-grid");
  grid.innerHTML = "";

  data.behaviors.forEach(b => {
    const card = document.createElement("div");
    card.className = "beh-card";
    card.innerHTML = `
      <div class="bc-name">${b}</div>
      <div class="bc-desc">${BEHAVIOR_DESCS[b] || ""}</div>`;
    card.onclick = () => pickBehavior(b, card);
    grid.appendChild(card);
  });

  showGroup("l3-group");
  document.getElementById("beh-hint").textContent = "";
  syncProfilePill();
  syncGenBtn();
}

// L3: Behavior
function pickBehavior(beh, cardEl) {
  S.behavior = beh;
  document.querySelectorAll(".beh-card").forEach(c => c.classList.remove("selected"));
  cardEl.classList.add("selected");
  document.getElementById("beh-hint").textContent = BEHAVIOR_DESCS[beh] || "";
  syncProfilePill();
  syncGenBtn();
}

// Helpers
function showGroup(id) {
  const el = document.getElementById(id);
  el.style.display = "block";
  el.classList.add("fade-reveal");
}
function hideGroup(id) { document.getElementById(id).style.display = "none"; }

function syncProfilePill() {
  const pill = document.getElementById("profile-pill");
  const val  = document.getElementById("pp-value");
  if (S.category && S.persona && S.behavior) {
    val.textContent = `${S.category} → ${S.persona} → ${S.behavior}`;
    pill.style.display = "flex";
  } else {
    pill.style.display = "none";
  }
}

function syncGenBtn() {
  const product = (document.getElementById("inp-product").value || "").trim();
  document.getElementById("gen-btn").disabled =
    !(product && S.category && S.persona && S.behavior);
}

// ══════════════════════════════════════════════════════
// PHASE 1: GENERATE
// ══════════════════════════════════════════════════════

async function startGenerate() {
  const product = (document.getElementById("inp-product").value || "").trim();
  if (!product || !S.category || !S.persona || !S.behavior) return;

  // Reset strategy phase
  document.getElementById("phase-strategy").classList.add("hidden");
  setEngine("think");
  runThinkingAnim();
  advanceWorkflow(1); // Step 1 → active

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product:  product,
        category: S.category,
        persona:  S.persona,
        behavior: S.behavior,
      }),
    });
    const result = await res.json();

    if (!result.success) {
      setEngine("err");
      document.getElementById("err-msg").textContent = result.error;
      return;
    }

    S.lastData   = result.data;
    S.campaignId = result.campaign_id;

    // Update done state
    document.getElementById("done-sub").textContent =
      `${S.persona} · ${S.behavior} · 5 stages generated`;
    setEngine("done");
    advanceWorkflow(2); // Move to Strategy step

    // Render the strategy intelligence phase
    renderStrategyIntelligence(result.data, result.campaign_id);

  } catch (e) {
    setEngine("err");
    document.getElementById("err-msg").textContent =
      "Network error — is the server running? " + e.message;
  }
}

// ══════════════════════════════════════════════════════
// ENGINE ANIMATION
// ══════════════════════════════════════════════════════

function setEngine(state) {
  ["idle", "think", "done", "err"].forEach(s =>
    document.getElementById(`state-${s}`).classList.add("hidden")
  );
  document.getElementById(`state-${state}`).classList.remove("hidden");
}

function resetEngine() { setEngine("idle"); }

function runThinkingAnim() {
  const steps  = document.querySelectorAll(".ts");
  const delays = [0, 1600, 3200, 4800, 6400, 8000];
  steps.forEach((s, i) => {
    s.classList.remove("active", "done");
    const fill = s.querySelector(".ts-fill");
    if (fill) fill.style.width = "0%";
  });
  steps.forEach((step, i) => {
    setTimeout(() => {
      step.classList.add("active");
      const fill = step.querySelector(".ts-fill");
      if (fill) setTimeout(() => { fill.style.width = "100%"; }, 60);
      if (i > 0) steps[i - 1].classList.replace("active", "done");
    }, delays[i]);
  });
}

// ══════════════════════════════════════════════════════
// WORKFLOW PROGRESS BAR
// ══════════════════════════════════════════════════════

function advanceWorkflow(step) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`wb-${i}`);
    const cn = document.getElementById(`wbc-${i}`);
    if (!el) continue;
    el.classList.remove("wb-active", "wb-done");
    if (i < step)      { el.classList.add("wb-done"); if (cn) cn.classList.add("wbc-done"); }
    else if (i === step) el.classList.add("wb-active");
  }
}

// ══════════════════════════════════════════════════════
// PHASE 2: STRATEGY INTELLIGENCE
// ══════════════════════════════════════════════════════

function scrollToStrategy() {
  document.getElementById("phase-strategy")
    .scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderStrategyIntelligence(data, campaignId) {
  // AI Reasoning bubble
  document.getElementById("arc-text").textContent =
    data.agent_intro ||
    `Here's exactly how I would sell "${data.product}" to a ${data.behavior} ${data.persona}.`;

  document.getElementById("arc-profile").innerHTML =
    `<span class="arc-tag">${data.category}</span>` +
    `<span class="arc-tag">${data.persona}</span>` +
    `<span class="arc-tag">${data.behavior}</span>`;

  // Summary strip
  document.getElementById("ss-product").textContent  = data.product;
  document.getElementById("ss-category").textContent = data.category;
  document.getElementById("ss-persona").textContent  = data.persona;
  document.getElementById("ss-behavior").textContent = data.behavior;

  // Funnel
  renderFunnel(data.funnel || []);

  // Quick wins
  renderQuickWins(data.quick_wins || []);

  // Avoid
  renderAvoid(data.avoid || []);

  // Launch button
  document.getElementById("launch-btn").href = `/execution/${campaignId}`;

  // Build copy/download text
  buildStrategyText(data);

  // Show strategy phase
  const phase = document.getElementById("phase-strategy");
  phase.classList.remove("hidden");
  setTimeout(() => phase.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
}

// ── FUNNEL FLOW ───────────────────────────────────────
let activeStageIdx = null;

function renderFunnel(funnel) {
  const container = document.getElementById("funnel-flow");
  container.innerHTML = "";
  activeStageIdx = null;

  funnel.forEach((stage, i) => {
    const color = STAGE_COLORS[stage.stage] || "#7c3aed";

    const node = document.createElement("div");
    node.className = "f-node";
    node.id = `fnode-${i}`;
    node.innerHTML = `
      <div class="f-box" style="background:${color};box-shadow:0 0 20px ${color}55"
           onclick="expandStage(${i})">
        ${stage.stage}
      </div>
      <div class="f-goal">${(stage.goal || "").slice(0, 52)}…</div>`;
    container.appendChild(node);

    if (i < funnel.length - 1) {
      const arr = document.createElement("div");
      arr.className = "f-arrow";
      arr.innerHTML = "→";
      container.appendChild(arr);
    }
  });

  // Auto-open first stage
  setTimeout(() => expandStage(0), 400);
}

function expandStage(i) {
  const funnel = S.lastData?.funnel || [];
  const stage  = funnel[i];
  if (!stage) return;

  // Highlight active node
  document.querySelectorAll(".f-node").forEach((n, idx) => {
    n.classList.toggle("f-active", idx === i);
  });
  activeStageIdx = i;

  const color   = STAGE_COLORS[stage.stage] || "#7c3aed";
  const tactics = stage.tactics || [];
  const content = stage.content || {};
  const pid     = `sip-${i}`;
  const panel   = document.getElementById("stage-intel-panel");

  const tacticsHtml = tactics.map(t => {
    if (typeof t === "object") return `
      <div class="tac-block">
        <div class="tac-name">📌 ${esc(t.name)}</div>
        <div class="tac-desc">${esc(t.description || "")}</div>
        <ul class="tac-impl">
          ${(t.implementation || []).map(s => `<li>${esc(s)}</li>`).join("")}
        </ul>
        <div class="tac-meta">
          ${t.timing   ? `<span class="tac-meta-item">⏰ ${esc(t.timing)}</span>`   : ""}
          ${t.platform ? `<span class="tac-meta-item">📍 ${esc(t.platform)}</span>` : ""}
        </div>
      </div>`;
    return `<div class="tac-block"><div class="tac-name">→ ${esc(t)}</div></div>`;
  }).join("");

  panel.innerHTML = `
    <!-- Stage Header -->
    <div class="sip-header" style="border-left:4px solid ${color}">
      <div>
        <div class="sip-stage" style="color:${color}">${stage.stage}</div>
        <div class="sip-goal">${esc(stage.goal || "")}</div>
      </div>
      <button class="sip-close" onclick="closeStagePanel()">✕</button>
    </div>

    ${stage.insight
      ? `<div class="sip-insight">💡 <em>${esc(stage.insight)}</em></div>`
      : ""}

    <div class="sip-grid">
      <!-- LEFT: Tactics -->
      <div>
        <div class="sip-section-label">Tactics & Implementation</div>
        ${tacticsHtml || "<p style='color:var(--muted);font-size:.85rem'>No tactics generated.</p>"}
        ${(stage.kpis||[]).length ? `
        <div class="sip-section-label" style="margin-top:18px">KPIs to Track</div>
        <div class="kpi-row">
          ${stage.kpis.map(k => `<span class="kpi-chip">📈 ${esc(k)}</span>`).join("")}
        </div>` : ""}
      </div>

      <!-- RIGHT: Generated Content -->
      <div>
        <div class="sip-section-label">Generated Content</div>
        <div class="content-tabs">
          <button class="ctab active" onclick="switchTab(event,'${pid}','msg')">Message</button>
          <button class="ctab"        onclick="switchTab(event,'${pid}','email')">Email</button>
          <button class="ctab"        onclick="switchTab(event,'${pid}','mktg')">Ad Copy</button>
          ${content.hook ? `<button class="ctab" onclick="switchTab(event,'${pid}','hook')">Hook</button>` : ""}
        </div>

        <div id="${pid}-msg" class="ctab-panel active">
          <div class="content-box">${esc(content.sales_message || "—")}</div>
          <button class="csc-copy" onclick="copyTextToClipboard(${JSON.stringify(content.sales_message||"")}, this)">⎘ Copy</button>
        </div>
        <div id="${pid}-email" class="ctab-panel">
          <div class="content-box">
            ${content.email?.subject
              ? `<div class="email-subj">Subject: ${esc(content.email.subject)}</div>` : ""}
            ${esc(content.email?.body || "—")}
          </div>
          <button class="csc-copy" onclick="copyTextToClipboard(${JSON.stringify((content.email?.subject ? 'Subject: '+content.email.subject+'\n\n' : '')+(content.email?.body||''))}, this)">⎘ Copy</button>
        </div>
        <div id="${pid}-mktg" class="ctab-panel">
          <div class="content-box">${esc(content.marketing_text || "—")}</div>
          <button class="csc-copy" onclick="copyTextToClipboard(${JSON.stringify(content.marketing_text||"")}, this)">⎘ Copy</button>
        </div>
        ${content.hook ? `
        <div id="${pid}-hook" class="ctab-panel">
          <div class="content-box hook-text">${esc(content.hook)}</div>
          <button class="csc-copy" onclick="copyTextToClipboard(${JSON.stringify(content.hook)}, this)">⎘ Copy</button>
        </div>` : ""}
      </div>
    </div>`;

  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeStagePanel() {
  document.getElementById("stage-intel-panel").classList.add("hidden");
  document.querySelectorAll(".f-node").forEach(n => n.classList.remove("f-active"));
  activeStageIdx = null;
}

function switchTab(e, prefix, tab) {
  const panel = e.target.closest(".stage-intel-panel") ||
                e.target.closest(".stage-full-card")   ||
                e.target.closest(".glass-card");
  panel.querySelectorAll(".ctab").forEach(b => b.classList.remove("active"));
  panel.querySelectorAll(".ctab-panel").forEach(p => p.classList.remove("active"));
  e.target.classList.add("active");
  const tp = document.getElementById(`${prefix}-${tab}`);
  if (tp) tp.classList.add("active");
}

// ── QUICK WINS ────────────────────────────────────────
function renderQuickWins(wins) {
  document.getElementById("quickwins-body").innerHTML =
    wins.slice(0, 3).map(w => `
      <div class="dual-item">
        <span class="di-badge effort-${(typeof w==='object'?w.effort:'Low').toLowerCase()}">
          ${typeof w === "object" ? w.effort : "Low"}
        </span>
        <div class="di-body">
          <div class="di-title">${esc(typeof w==="object" ? w.action : w)}</div>
          ${typeof w==="object" && w.impact
            ? `<div class="di-sub">${esc(w.impact)}</div>` : ""}
        </div>
      </div>`).join("");
}

// ── AVOID ─────────────────────────────────────────────
function renderAvoid(avoids) {
  document.getElementById("avoid-body").innerHTML =
    avoids.slice(0, 3).map(a => `
      <div class="dual-item">
        <span class="di-x">✗</span>
        <div class="di-body">
          <div class="di-title">${esc(typeof a==="object" ? a.mistake : a)}</div>
          ${typeof a==="object" && a.reason
            ? `<div class="di-sub">${esc(a.reason)}</div>` : ""}
        </div>
      </div>`).join("");
}

// ── COPY / DOWNLOAD ───────────────────────────────────
function buildStrategyText(data) {
  let t = `SALESAI STRATEGY REPORT\n${"═".repeat(50)}\n`;
  t += `Product  : ${data.product}\nPersona  : ${data.persona}\nBehavior : ${data.behavior}\n\n`;
  t += `${data.agent_intro || ""}\n\n`;
  t += `PROFILE\n${data.profile_summary || ""}\n`;

  (data.funnel || []).forEach(stage => {
    t += `\n── ${stage.stage.toUpperCase()} ──\nGoal: ${stage.goal}\n`;
    (stage.tactics || []).forEach(tac => {
      if (typeof tac === "object") {
        t += `\nTactic: ${tac.name}\n${tac.description || ""}\n`;
        (tac.implementation || []).forEach(s => { t += `  → ${s}\n`; });
        if (tac.timing)   t += `  Timing: ${tac.timing}\n`;
        if (tac.platform) t += `  Platform: ${tac.platform}\n`;
      } else { t += `  → ${tac}\n`; }
    });
    const c = stage.content || {};
    t += `\nSales Message: ${c.sales_message || ""}\n`;
    if (c.email) t += `Email Subject: ${c.email.subject}\nEmail:\n${c.email.body}\n`;
    t += `Ad Copy: ${c.marketing_text || ""}\n`;
    if (c.hook) t += `Hook: ${c.hook}\n`;
  });

  t += `\nQUICK WINS\n`;
  (data.quick_wins || []).forEach(w => {
    t += `  ✦ ${typeof w==="object" ? w.action+" — "+(w.impact||"") : w}\n`;
  });
  document.getElementById("strategy-store").value = t;
}

function copyAll() {
  const txt = document.getElementById("strategy-store").value;
  if (!txt) { showToast("Generate a strategy first!", "error"); return; }
  navigator.clipboard.writeText(txt).then(() => showToast("Strategy copied! ✓", "success"));
}

function downloadTxt() {
  const txt = document.getElementById("strategy-store").value;
  if (!txt) { showToast("Generate a strategy first!", "error"); return; }
  const product = S.lastData?.product || "strategy";
  const blob = new Blob([txt], { type: "text/plain" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = `${product.replace(/\s+/g,"-").toLowerCase()}-strategy.txt`;
  a.click();
}

// ── UTIL ──────────────────────────────────────────────
function esc(s) {
  return String(s||"")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── INIT ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const p = document.getElementById("inp-product");
  if (p) {
    p.addEventListener("input", syncGenBtn);
    p.addEventListener("keydown", e => { if (e.key === "Enter") startGenerate(); });
  }
});
