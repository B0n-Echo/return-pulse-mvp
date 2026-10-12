// Return Pulse dashboard.
// Each section asks the server for its data. If that part of the server isn't
// built yet (or fails), it falls back to a sample file and says so on screen.

const REASON_LABELS = {
  too_small: "Too small",
  too_large: "Too large",
  colour_mismatch: "Colour mismatch",
  quality: "Quality",
  damaged: "Damaged",
  wrong_item: "Wrong item",
  changed_mind: "Changed mind",
  delivery_late: "Delivery late",
  unclear: "Unclear",
  failed: "Failed",
};
const REASONS_FOR_CORRECTION = Object.keys(REASON_LABELS).filter((r) => r !== "failed");

/** Turn a reason code like "too_small" into a label like "Too small". */
function label(reason) {
  return REASON_LABELS[reason] || reason;
}

/** Format a share like 0.6 as "60%". */
function pct(x) {
  return x == null ? "–" : `${Math.round(x * 100)}%`;
}

/** Create an element with optional class and text (text is never parsed as HTML). */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

/**
 * Fetch one section's data from the API; fall back to its sample file.
 * Marks the section "Sample" and shows the banner when the fallback is used.
 */
async function load(sectionId, url, mockName) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    const tag = document.querySelector(`#${sectionId} .tag`);
    if (tag) tag.hidden = false;
    document.getElementById("sample-banner").hidden = false;
    const res = await fetch(`/static/mock/${mockName}.json`);
    return res.json();
  }
}

// ── Status line ─────────────────────────────────────────────────────────────
async function loadHealth() {
  const box = document.getElementById("status");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.status === "ok") {
      const c = data.counts;
      box.textContent = `Database connected · ${c.returns.toLocaleString()} returns · ${c.classified.toLocaleString()} classified`;
    } else {
      box.classList.add("error");
      box.textContent = `Database problem: ${data.detail}`;
    }
  } catch (err) {
    box.classList.add("error");
    box.textContent = "Can't reach the server. Is uvicorn running?";
  }
}

// ── 1. Summary ──────────────────────────────────────────────────────────────
function renderSummary(s) {
  const tiles = document.getElementById("summary-tiles");
  const items = [
    [s.total_returns.toLocaleString(), "Returns"],
    [s.classified.toLocaleString(), "Classified"],
    [pct(s.known_share), "Reason known"],
    [s.unclear.toLocaleString(), "Unclear", true],
    [s.failed.toLocaleString(), "Failed", s.failed > 0],
    [s.evidence_flags.toLocaleString(), "Evidence flags", s.evidence_flags > 0],
  ];
  tiles.replaceChildren(...items.map(([value, name, warn]) => {
    const tile = el("div", warn ? "tile warn" : "tile");
    tile.append(el("div", "v", value), el("div", "l", name));
    return tile;
  }));
}

// ── 2. Drivers ──────────────────────────────────────────────────────────────
function renderDrivers(rows) {
  const box = document.getElementById("drivers-bars");
  const max = Math.max(...rows.map((r) => r.share), 0.01);
  box.replaceChildren(...rows.map((r) => {
    const bar = el("div", "bar");
    const track = el("div", "track");
    const fill = el("div", ["unclear", "failed"].includes(r.issue_type) ? "fill grey" : "fill");
    fill.style.width = `${(r.share / max) * 100}%`;
    track.append(fill);
    bar.append(el("span", null, label(r.issue_type)), track,
               el("span", "n", `${pct(r.share)} · ${r.returns.toLocaleString()}`));
    return bar;
  }));
}

// ── 3. Hotspots + comments ──────────────────────────────────────────────────
function renderHotspots(rows) {
  const body = document.getElementById("hotspots-body");
  if (!rows.length) {
    const tr = el("tr");
    const td = el("td", "empty", "No hotspots: no group is well above normal.");
    td.colSpan = 8;
    tr.append(td);
    body.replaceChildren(tr);
    return;
  }
  body.replaceChildren(...rows.map((h) => {
    const tr = el("tr", "clickable");
    tr.tabIndex = 0;
    const times = el("span", "times", `${h.times_normal.toFixed(1)}×`);
    const tdTimes = el("td", "num");
    tdTimes.append(times);
    tr.append(
      el("td", null, h.vendor_name),
      el("td", null, h.subcategory),
      el("td", null, h.size),
      el("td", null, label(h.issue_type)),
      el("td", "num", `${h.issue_returns} of ${h.group_returns}`),
      el("td", "num", pct(h.share)),
      el("td", "num", pct(h.normal_share)),
      tdTimes,
    );
    const open = () => {
      body.querySelectorAll("tr").forEach((row) => row.classList.remove("selected"));
      tr.classList.add("selected");
      openComments(h);
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") open(); });
    return tr;
  }));
}

async function openComments(h) {
  const panel = document.getElementById("comments");
  const list = document.getElementById("comments-list");
  document.getElementById("comments-title").textContent =
    `${h.vendor_name} · ${h.subcategory} · size ${h.size} · ${label(h.issue_type)}`;
  list.replaceChildren(el("li", "hint", "Loading comments…"));
  panel.hidden = false;

  const params = new URLSearchParams({
    vendor_id: h.vendor_id, subcategory: h.subcategory, size: h.size, issue_type: h.issue_type,
  });
  const rows = await load("hotspots", `/api/hotspots/comments?${params}`, "comments");
  list.replaceChildren(...rows.map(renderComment));
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderComment(c) {
  const li = el("li", "comment");
  li.append(el("div", "text", `"${c.other_text}"`));

  const meta = el("div", "meta");
  meta.append(el("span", "chip", label(c.issue_type)));
  if (c.confidence != null) meta.append(el("span", null, `confidence ${pct(c.confidence)}`));
  if (c.evidence_phrase) meta.append(el("span", null, `quote: "${c.evidence_phrase}"`));
  if (c.evidence_found === false) meta.append(el("span", "chip flag", "⚠ quote not found in comment, please check"));
  meta.append(el("span", null, c.source === "strong_model" ? "second opinion" : "AI"));

  const actions = el("div", "actions");
  const ok = el("button", "ok", "✓");
  ok.title = "The reason is right";
  const no = el("button", "no", "✗");
  no.title = "The reason is wrong";
  const status = el("span", "saved");
  actions.append(ok, no, status);
  meta.append(actions);

  ok.addEventListener("click", () => sendCorrection(c, true, null, status));
  no.addEventListener("click", () => {
    const pick = el("select");
    pick.append(el("option", null, "Correct reason…"));
    REASONS_FOR_CORRECTION.forEach((r) => {
      const opt = el("option", null, label(r));
      opt.value = r;
      pick.append(opt);
    });
    pick.addEventListener("change", () => {
      if (pick.value) sendCorrection(c, false, pick.value, status);
    });
    actions.replaceChildren(pick, status);
    pick.focus();
  });

  li.append(meta);
  return li;
}

async function sendCorrection(c, isCorrect, correctedIssue, statusEl) {
  statusEl.className = "saved";
  statusEl.textContent = "Saving…";
  try {
    const res = await fetch("/api/corrections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ return_id: c.return_id, is_correct: isCorrect, corrected_issue: correctedIssue }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    statusEl.className = "saved good";
    statusEl.textContent = isCorrect ? "Saved: right" : `Saved: ${label(correctedIssue)}`;
  } catch (err) {
    statusEl.className = "saved bad";
    statusEl.textContent = `Not saved (${err.message})`;
  }
}

document.getElementById("comments-close").addEventListener("click", () => {
  document.getElementById("comments").hidden = true;
  document.querySelectorAll("#hotspots-body tr").forEach((row) => row.classList.remove("selected"));
});

// ── 4. Locations ────────────────────────────────────────────────────────────
function renderLocations(rows) {
  const body = document.getElementById("locations-body");
  if (!rows.length) {
    const tr = el("tr");
    const td = el("td", "empty", "No city stands out.");
    td.colSpan = 6;
    tr.append(td);
    body.replaceChildren(tr);
    return;
  }
  body.replaceChildren(...rows.map((r) => {
    const tr = el("tr");
    const tdTimes = el("td", "num");
    tdTimes.append(el("span", "times", `${r.times_normal.toFixed(1)}×`));
    tr.append(
      el("td", null, r.ship_city),
      el("td", null, label(r.issue_type)),
      el("td", "num", `${r.issue_returns} of ${r.group_returns}`),
      el("td", "num", pct(r.share)),
      el("td", "num", pct(r.normal_share)),
      tdTimes,
    );
    return tr;
  }));
}

// ── 5. Trend ────────────────────────────────────────────────────────────────
let trendRows = [];

function setupTrend(rows) {
  trendRows = rows;
  const select = document.getElementById("trend-reason");
  const reasons = [...new Set(rows.map((r) => r.issue_type))];
  select.replaceChildren(...reasons.map((r) => {
    const opt = el("option", null, label(r));
    opt.value = r;
    return opt;
  }));
  select.addEventListener("change", () => drawTrend(select.value));
  if (reasons.length) drawTrend(reasons[0]);
}

/** Draw the last 52 weeks against the 52 weeks before, for one reason. */
function drawTrend(reason) {
  const svg = document.getElementById("trend-chart");
  const W = 720, H = 220, L = 36, R = 10, T = 10, B = 26;
  const weeks = trendRows.filter((r) => r.issue_type === reason)
    .sort((a, b) => a.week_start.localeCompare(b.week_start));
  const now = weeks.slice(-52);
  const prev = weeks.slice(-104, -52);
  const max = Math.max(1, ...now.map((w) => w.returns), ...prev.map((w) => w.returns));
  const x = (i) => L + (i / 51) * (W - L - R);
  const y = (v) => T + (1 - v / max) * (H - T - B);
  const path = (series) => series.map((w, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(w.returns).toFixed(1)}`).join(" ");

  const ns = "http://www.w3.org/2000/svg";
  const make = (tag, attrs, text) => {
    const n = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    if (text != null) n.textContent = text;
    return n;
  };
  const parts = [];
  [0, 0.5, 1].forEach((f) => {
    const v = Math.round(max * f);
    parts.push(make("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: "#e1e5ec" }));
    parts.push(make("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, v));
  });
  if (now.length) {
    parts.push(make("text", { x: L, y: H - 6 }, now[0].week_start));
    parts.push(make("text", { x: W - R, y: H - 6, "text-anchor": "end" }, now[now.length - 1].week_start));
  }
  if (prev.length) parts.push(make("path", { d: path(prev), fill: "none", stroke: "#9aa3b2", "stroke-width": 2 }));
  if (now.length) parts.push(make("path", { d: path(now), fill: "none", stroke: "#23598e", "stroke-width": 2.5 }));
  if (!weeks.length) parts.push(make("text", { x: W / 2, y: H / 2, "text-anchor": "middle" }, "No data yet"));
  svg.replaceChildren(...parts);
}

// ── Start ───────────────────────────────────────────────────────────────────
async function start() {
  loadHealth();
  const [summary, drivers, hotspots, locations, trend] = await Promise.all([
    load("summary", "/api/summary", "summary"),
    load("drivers", "/api/drivers", "drivers"),
    load("hotspots", "/api/hotspots", "hotspots"),
    load("locations", "/api/locations", "locations"),
    load("trend", "/api/trend", "trend"),
  ]);
  renderSummary(summary);
  renderDrivers(drivers);
  renderHotspots(hotspots);
  renderLocations(locations);
  setupTrend(trend);
}

start();
