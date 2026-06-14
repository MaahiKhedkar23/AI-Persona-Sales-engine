
// ── CHECKLIST ─────────────────────────────────────────
function updateChecklist() {
  const all     = document.querySelectorAll(".ck-box");
  const checked = document.querySelectorAll(".ck-box:checked");
  const pct     = all.length ? Math.round((checked.length / all.length) * 100) : 0;

  document.getElementById("ck-pct").textContent       = pct + "%";
  document.getElementById("ck-bar-fill").style.width  = pct + "%";

  // Style completed items
  all.forEach(box => {
    const item = box.closest(".ck-item");
    if (item) item.classList.toggle("ck-done", box.checked);
  });
}

// ── TIMELINE ANIMATION ────────────────────────────────
function animateTimeline() {
  const nodes = document.querySelectorAll(".tl-node");
  const line  = document.getElementById("timeline-line");

  nodes.forEach((node, i) => {
    setTimeout(() => {
      node.classList.add("tl-active");
      // Grow the progress line proportionally
      if (line) {
        const pct = ((i + 1) / nodes.length) * 100;
        line.style.width = pct + "%";
      }
    }, i * 300);
  });
}

// ── CONTENT STUDIO ────────────────────────────────────
function copyCard(elId, btn) {
  const el = document.getElementById(elId);
  if (!el) return;
  navigator.clipboard.writeText(el.innerText).then(() => {
    const orig = btn.textContent;
    btn.textContent = "✓ Copied!";
    btn.style.color = "#10b981";
    setTimeout(() => { btn.textContent = orig; btn.style.color = ""; }, 2000);
  });
}

function expandCard(btn) {
  const card    = btn.closest(".cs-card");
  const content = card.querySelector(".csc-content");
  const isExp   = card.classList.contains("expanded");
  card.classList.toggle("expanded", !isExp);
  btn.textContent = isExp ? "↕ Expand" : "↑ Collapse";
  content.style.webkitLineClamp = isExp ? "3" : "unset";
}

// ── STATUS BADGE ──────────────────────────────────────
function updateStatusBadge(status) {
  const colors = {
    draft:    "#64748b",
    ready:    "#f59e0b",
    launched: "#7c3aed",
    tracking: "#10b981",
  };
  const dot   = document.getElementById("esb-dot");
  const label = document.getElementById("esb-label");
  if (dot)   dot.style.background = colors[status] || "#64748b";
  if (label) label.textContent    = status.charAt(0).toUpperCase() + status.slice(1);
}

// ── LAUNCH CAMPAIGN ───────────────────────────────────
async function launchCampaign() {
  // 1. Mark as launched in DB
  await fetch(`/api/campaigns/${CAMPAIGN_ID}/launch`, { method: "POST" });
  updateStatusBadge("launched");

  // 2. Hide pre-launch, show tracking init
  document.getElementById("pre-launch").classList.add("hidden");
  const init = document.getElementById("tracking-init");
  init.classList.remove("hidden");

  // 3. Animate tracking steps
  const steps   = init.querySelectorAll(".ti-step");
  const delays  = [0, 1400, 2800, 4200, 5600];

  steps.forEach((step, i) => {
    setTimeout(() => {
      step.classList.add("ti-active");
      if (i === steps.length - 1) {
        // All done — start tracking
        setTimeout(() => startTracking(), 800);
      }
    }, delays[i]);
  });
}

// ── START TRACKING ────────────────────────────────────
async function startTracking() {
  updateStatusBadge("tracking");

  try {
    const res  = await fetch(`/api/campaigns/${CAMPAIGN_ID}/start-tracking`, { method: "POST" });
    const data = await res.json();

    if (!data.success) {
      console.error("Tracking start failed:", data.error);
      return;
    }

    // Transition: hide init, show analytics
    document.getElementById("tracking-init").classList.add("hidden");
    const reveal = document.getElementById("analytics-reveal");
    reveal.classList.remove("hidden");

    // Render metrics with count-up animation
    renderLiveMetrics(data.analytics);

    // Render opt tips after a delay
    setTimeout(() => {
      if (data.opt_tips && data.opt_tips.length) {
        renderLiveOptTips(data.opt_tips);
        document.getElementById("live-opt-tips").classList.remove("hidden");
      }
    }, 3000);

  } catch (e) {
    console.error("Failed to start tracking:", e);
  }
}

// ── RENDER LIVE METRICS ───────────────────────────────
function renderLiveMetrics(analytics) {
  if (!analytics) return;

  // Metric cards
  const metricsEl = document.getElementById("live-metrics");
  const metrics   = [
    { val: analytics.reach,            suffix: "",  label: "Est. Reach",    id: "lm-reach" },
    { val: analytics.engagement,       suffix: "%", label: "Engagement",    id: "lm-eng" },
    { val: analytics.clicks,           suffix: "",  label: "Clicks",        id: "lm-clicks" },
    { val: analytics.conversion_score, suffix: "",  label: "Conv. Score",   id: "lm-conv" },
  ];

  metricsEl.innerHTML = metrics.map(m => `
    <div class="metric-card large">
      <div class="mc-val" id="${m.id}">0</div>
      <div class="mc-lbl">${m.label}</div>
    </div>`).join("");

  // Animate after paint
  setTimeout(() => {
    metrics.forEach(m => {
      countUp(document.getElementById(m.id), m.val, m.suffix, 1800);
    });
  }, 200);

  // Progress bar
  const pct = analytics.progress || 0;
  setTimeout(() => {
    document.getElementById("live-prog-bar").style.width = pct + "%";
    document.getElementById("live-prog-pct").textContent = pct + "%";
  }, 400);

  // Tactic table
  const tbody = document.getElementById("live-tactic-tbody");
  if (tbody && analytics.tactic_data) {
    tbody.innerHTML = analytics.tactic_data.map(t => {
      const scoreColor = t.score >= 75 ? "#10b981" : t.score >= 50 ? "#f59e0b" : "#ef4444";
      const trendClass = t.trend === "↑" ? "trend-up" : t.trend === "↓" ? "trend-down" : "trend-flat";
      return `<tr>
        <td style="font-size:.82rem">${t.tactic}</td>
        <td><span class="status-${(t.status||"").toLowerCase()}">${t.status}</span></td>
        <td>
          <div class="score-bar-wrap">
            <div class="score-bar" style="width:${t.score}%;background:${scoreColor};max-width:70px"></div>
            <span class="score-num">${t.score}%</span>
          </div>
        </td>
        <td class="${trendClass}">${t.trend}</td>
      </tr>`;
    }).join("");
  }
}

// ── RENDER OPT TIPS ───────────────────────────────────
function renderLiveOptTips(tips) {
  const grid = document.getElementById("live-recs-grid");
  if (!grid) return;
  grid.innerHTML = tips.map(t => `
    <div class="rec-card glass-card priority-${t.priority}" style="animation:fadeUp .4s ease">
      <div class="rc-icon">${t.icon || "💡"}</div>
      <div class="rc-body">
        <div class="rc-title">${t.title}</div>
        <div class="rc-text">${t.text}</div>
      </div>
      <span class="rc-pri pri-${t.priority}">${t.priority}</span>
    </div>`).join("");
}

// ── INIT ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Animate timeline on load
  setTimeout(animateTimeline, 400);

  // Init checklist progress
  updateChecklist();

  // Set status badge from server-rendered status
  updateStatusBadge(EXEC_STATUS);

  // If already tracking, show analytics immediately
  if (EXEC_STATUS === "tracking") {
    document.getElementById("pre-launch").innerHTML = `
      <div style="text-align:center;padding:24px 0">
        <div style="font-size:2rem;margin-bottom:10px">📊</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem;margin-bottom:8px">
          Campaign is Live & Tracking
        </div>
        <div style="color:var(--muted2);font-size:.9rem">
          Analytics are being collected. 
          <a href="/campaigns/${CAMPAIGN_ID}" style="color:var(--purple-l)">View full report →</a>
        </div>
      </div>`;
  }
});