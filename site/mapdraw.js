/* Map drawing shared by the project page (site/template.html) and the local app (tools/app.py).
   MapDraw(domains) returns draw(map, element, "lanes"|"levels"), legendHTML() and layersHTML(map). */
function MapDraw(DOMS) {
  "use strict";
  const STATE_SHORT = { provisional_acceptance: "accept", validation: "validate", consultation: "consult", deferral: "defer" };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const domOf = (d) => DOMS[d.domain || "radiology"] || DOMS.radiology;
  // ---------- drawing
  const NODE_W = 196, LINE_H = 13.5;
  function wrap(text, max) {
    const words = String(text).split(/\s+/); const out = []; let cur = "";
    for (const w of words) { if ((cur + " " + w).trim().length > max) { if (cur) out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); }
    if (cur) out.push(cur); return out;
  }
  function nodeLines(n, D, tag) {
    const L = [];
    if (tag) { const s = D.systems[n.system]; L.push({ t: `${(s && s.short) || n.system} · ${n.lane}`, k: "tag" }); }
    L.push({ t: n.activity, k: "title" });
    if (n.detail) wrap(n.detail, 30).forEach((t) => L.push({ t, k: "detail" }));
    if (n.ai_output) wrap("shows: " + n.ai_output, 30).forEach((t) => L.push({ t, k: "out" }));
    L.push({ t: `(${n.system})` + (n.labor && n.labor.length ? "  " + n.labor.map((l) => `[${l}]`).join(" ") : ""), k: "sys" });
    return L;
  }
  function adjOf(d) { const a = {}; d.edges.forEach((e) => (a[e.from] = a[e.from] || []).push(e.to)); return a; }
  function bfsDepth(d) {
    const adj = adjOf(d), depth = {}; let fr = d.nodes.filter((n) => n.entry).map((n) => n.id);
    fr.forEach((id) => (depth[id] = 0));
    while (fr.length) { const nx = []; fr.forEach((id) => (adj[id] || []).forEach((t) => { if (!(t in depth)) { depth[t] = depth[id] + 1; nx.push(t); } })); fr = nx; }
    d.nodes.forEach((n) => { if (!(n.id in depth)) { const ts = (adj[n.id] || []).filter((t) => t in depth).map((t) => depth[t]); depth[n.id] = ts.length ? Math.max(Math.min(...ts) - 1, 0) : 0; } });
    return depth;
  }
  function boxes(d, D, tag) { const b = {}; d.nodes.forEach((n) => { const L = nodeLines(n, D, tag); b[n.id] = { lines: L, h: 14 + L.length * LINE_H, w: NODE_W }; }); return b; }
  function layoutLanes(d, D) {
    const LANES = Object.keys(D.lanes), LW = 224, LG = 10, PADX = 10, TOP = 40, GAP = 24;
    const depth = bfsDepth(d), B = boxes(d, D, false), used = new Set(), cell = {};
    [...d.nodes].sort((a, b) => depth[a.id] - depth[b.id]).forEach((n) => {
      let row = depth[n.id]; const col = Math.max(0, LANES.indexOf(n.lane));
      while (used.has(row + ":" + col)) row++; used.add(row + ":" + col); cell[n.id] = { row, col };
    });
    const nRows = Math.max(0, ...Object.values(cell).map((c) => c.row)) + 1, rowH = Array(nRows).fill(36);
    d.nodes.forEach((n) => (rowH[cell[n.id].row] = Math.max(rowH[cell[n.id].row], B[n.id].h)));
    const rowY = []; let y = TOP + 12; rowH.forEach((h, i) => { rowY[i] = y; y += h + GAP; });
    d.nodes.forEach((n) => { const c = cell[n.id], b = B[n.id]; b.x = PADX + c.col * (LW + LG) + (LW - b.w) / 2; b.y = rowY[c.row] + (rowH[c.row] - b.h) / 2; b.cx = b.x + b.w / 2; b.cy = b.y + b.h / 2; });
    const W = PADX * 2 + LANES.length * LW + (LANES.length - 1) * LG, H = y + 2;
    let bg = "";
    LANES.forEach((lane, i) => { const x = PADX + i * (LW + LG), L = D.lanes[lane];
      bg += `<rect x="${x}" y="6" width="${LW}" height="${H - 10}" fill="var(${L.role === "record" ? "--lane-b" : "--lane-a"})"/>`;
      bg += `<text x="${x + LW / 2}" y="22" text-anchor="middle" font-family="var(--sans)" font-size="11.5" font-weight="600" fill="var(--ink)">${esc(L.title)} (${esc(lane)})</text>`;
      bg += `<text x="${x + LW / 2}" y="36" text-anchor="middle" font-family="var(--sans)" font-size="10" fill="var(--muted)">${esc(L.role)}</text>`; });
    return { B, W, H, bg };
  }
  function layoutLevels(d, D) {
    // each escalation row starts under the step that raised the doubt
    const COL = 220, LABEL = 96, ROWGAP = 46, TOP = 14, B = boxes(d, D, true);
    const lv = (n) => n.level || 0, levels = [...new Set(d.nodes.map(lv))].sort((a, b) => a - b);
    const byId = Object.fromEntries(d.nodes.map((n) => [n.id, n])), preds = {};
    d.edges.forEach((e) => (preds[e.to] = preds[e.to] || []).push(e.from));
    const colOf = {};
    levels.forEach((l) => {
      let next = 0;
      d.nodes.filter((n) => lv(n) === l).forEach((n) => {
        const up = (preds[n.id] || []).filter((p) => lv(byId[p]) < l && p in colOf).map((p) => colOf[p]);
        const c = Math.max(next, up.length ? Math.max(...up) : 0); colOf[n.id] = c; next = c + 1;
      });
    });
    const rowH = levels.map((l) => Math.max(40, ...d.nodes.filter((n) => lv(n) === l).map((n) => B[n.id].h)));
    let y = TOP; const rowY = [];
    levels.forEach((l, i) => { rowY[i] = y; y += rowH[i] + ROWGAP; });
    d.nodes.forEach((n) => { const i = levels.indexOf(lv(n)), b = B[n.id]; b.x = LABEL + 12 + colOf[n.id] * COL; b.y = rowY[i] + (rowH[i] - b.h) / 2; b.cx = b.x + b.w / 2; b.cy = b.y + b.h / 2; });
    const W = LABEL + 12 + (Math.max(...Object.values(colOf)) + 1) * COL, H = y - ROWGAP + 16;
    let bg = "";
    levels.forEach((l, i) => {
      const cy = rowY[i] + rowH[i] / 2;
      bg += `<text x="6" y="${cy - 2}" font-family="var(--sans)" font-size="12" font-weight="600" fill="var(--ink)">Level ${l}</text>`;
      bg += `<text x="6" y="${cy + 13}" font-family="var(--sans)" font-size="11" fill="var(--muted)">${l === 0 ? "ordinary path" : "escalation " + l}</text>`;
      if (i) { const ly = rowY[i] - ROWGAP / 2;
        bg += `<line x1="${LABEL}" y1="${ly}" x2="${W - 4}" y2="${ly}" stroke="var(--rule)" stroke-width="1"/>`;
        bg += `<text x="6" y="${ly + 4}" font-family="var(--serif)" font-style="italic" font-size="12.5" fill="var(--doubt)">why?</text>`; }
    });
    return { B, W, H, bg };
  }
  function clip(b, tx, ty) {
    const dx = tx - b.cx, dy = ty - b.cy; if (!dx && !dy) return [b.cx, b.cy];
    const s = Math.min((b.w / 2 + 3) / Math.abs(dx || 1e-9), (b.h / 2 + 3) / Math.abs(dy || 1e-9));
    return [b.cx + dx * s, b.cy + dy * s];
  }
  let uid = 0;
  // marks from analysis layers: [{on:"node"|"edge", id|from,to, tag, level:"info"|"warn"}]
  const MARK = { info: "var(--good)", warn: "#d98a00", diff: "var(--inst)" };
  function draw(d, mount, mode, marks) {
    const ME = {}, MN = {};
    (marks || []).forEach((k) => {
      if (k.on === "edge") ME[k.from + ">" + k.to] = k;
      else if (k.on === "node") {   // several layers can mark one step: join their tags in one badge
        const o = MN[k.id];
        MN[k.id] = o ? { tag: [o.tag, k.tag].filter(Boolean).join(" · "), level: o.level === "warn" || k.level === "warn" ? "warn" : "info" } : k;
      }
    });
    const D = domOf(d), id = "g" + ++uid, L = mode === "levels" ? layoutLevels(d, D) : layoutLanes(d, D), { B, W, H } = L;
    const col = { action: "var(--muted)", doubt: "var(--doubt)", institutional: "var(--inst)" };
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(d.title)}" xmlns="http://www.w3.org/2000/svg" style="min-width:${Math.round(W * 0.66)}px"><defs>` +
      Object.entries(col).map(([k, c]) => `<marker id="${id}-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${c}"/></marker>`).join("") + "</defs>" + L.bg;
    d.edges.forEach((e) => {
      const a = B[e.from], b = B[e.to]; if (!a || !b) return;
      const back = b.cy < a.cy - 2 || (Math.abs(b.cy - a.cy) < 2 && b.cx < a.cx);
      const skip = mode === "levels" && Math.abs(b.cy - a.cy) < 2 && Math.abs(b.cx - a.cx) > 230;
      const [x1, y1] = clip(a, b.cx, b.cy), [x2, y2] = clip(b, a.cx, a.cy);
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, bend = back ? 44 : skip ? -40 : 0;
      const nx = -(y2 - y1), ny = x2 - x1, nl = Math.hypot(nx, ny) || 1, cx = mx + (nx / nl) * bend, cy = my + (ny / nl) * bend;
      const dash = e.type === "doubt" ? ' stroke-dasharray="6 4"' : e.type === "institutional" ? ' stroke-dasharray="2 4"' : "";
      const mk = ME[e.from + ">" + e.to];
      if (mk) s += `<path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}" fill="none" stroke="${MARK[mk.level] || MARK.warn}" stroke-width="8" stroke-opacity="0.35" stroke-linecap="round"/>`;
      s += `<path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}" fill="none" stroke="${col[e.type]}" stroke-width="1.4"${dash} marker-end="url(#${id}-${e.type})"/>`;
      if (e.label) { const lx = (x1 + 2 * cx + x2) / 4, ly = (y1 + 2 * cy + y2) / 4;
        s += `<text x="${lx + 4}" y="${ly - 4}" font-family="var(--sans)" font-size="10" fill="${col[e.type]}" paint-order="stroke" stroke="var(--sheet)" stroke-width="3">${esc(e.label)}</text>`; }
    });
    d.nodes.forEach((n) => {
      const b = B[n.id], stroke = n.is_ai ? "var(--ai)" : "var(--ink)", dash = n.is_ai ? ' stroke-dasharray="5 3"' : "";
      const rx = n.is_ai && D.lanes[n.lane] && D.lanes[n.lane].role === "queue" ? 1 : 7;
      if (n.closes_claim) s += `<rect x="${b.x - 3}" y="${b.y - 3}" width="${b.w + 6}" height="${b.h + 6}" rx="${rx + 2}" fill="none" stroke="${stroke}" stroke-width="1"/>`;
      s += `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="${rx}" fill="var(--sheet)" stroke="${stroke}" stroke-width="${n.entry ? 2.2 : 1.1}"${dash}/>`;
      b.lines.forEach((ln, i) => {
        const st = { tag: 'font-size="9.5" fill="var(--muted)" font-family="var(--mono)"', title: 'font-weight="600" font-size="12" fill="var(--ink)" font-family="var(--sans)"',
          detail: 'font-style="italic" font-size="10.5" fill="var(--ink)" font-family="var(--serif)"', out: 'font-size="10" fill="var(--ai)" font-family="var(--mono)"',
          sys: 'font-size="10" fill="var(--muted)" font-family="var(--sans)"' }[ln.k];
        s += `<text x="${b.cx}" y="${b.y + 16 + i * LINE_H}" text-anchor="middle" ${st}>${esc(ln.t)}</text>`;
      });
      const nm = MN[n.id];
      if (nm && nm.tag) { const tw = 8 + nm.tag.length * 5.6, c = MARK[nm.level] || MARK.info;
        s += `<rect x="${b.x + b.w - tw - 4}" y="${b.y - 8}" width="${tw}" height="15" rx="7.5" fill="${c}"/>`;
        s += `<text x="${b.x + b.w - 4 - tw / 2}" y="${b.y + 3}" text-anchor="middle" font-family="var(--sans)" font-size="9.5" font-weight="600" fill="var(--sheet)">${esc(nm.tag)}</text>`; }
    });
    mount.innerHTML = s + "</svg>";
  }

  // legend
  const sw = (inner) => `<svg width="40" height="18" viewBox="0 0 40 18" aria-hidden="true">${inner}</svg>`;
  const legendHTML = () => [
    [sw('<rect x="2" y="2" width="36" height="14" rx="4" fill="var(--sheet)" stroke="var(--ink)" stroke-width="2.2"/>'), "entry"],
    [sw('<rect x="1" y="1" width="38" height="16" rx="5" fill="none" stroke="var(--ink)"/><rect x="4" y="4" width="32" height="10" rx="3" fill="var(--sheet)" stroke="var(--ink)"/>'), "claim closes"],
    [sw('<rect x="2" y="2" width="36" height="14" rx="1" fill="var(--sheet)" stroke="var(--ai)" stroke-dasharray="4 3"/>'), "AI in a queue"],
    [sw('<rect x="2" y="2" width="36" height="14" rx="6" fill="var(--sheet)" stroke="var(--ai)" stroke-dasharray="4 3"/>'), "AI in the work"],
    [sw('<line x1="2" y1="9" x2="32" y2="9" stroke="var(--muted)" stroke-width="1.6"/><path d="M32 5 L38 9 L32 13 z" fill="var(--muted)"/>'), "action"],
    [sw('<line x1="2" y1="9" x2="32" y2="9" stroke="var(--doubt)" stroke-width="1.6" stroke-dasharray="5 3"/><path d="M32 5 L38 9 L32 13 z" fill="var(--doubt)"/>'), "doubt"],
    [sw('<line x1="2" y1="9" x2="32" y2="9" stroke="var(--inst)" stroke-width="1.6" stroke-dasharray="2 3"/><path d="M32 5 L38 9 L32 13 z" fill="var(--inst)"/>'), "institutional"],
    ['<span class="mono">[R][C][A][I]</span>', "argumentation labor"],
  ].map(([m, t]) => `<span>${m}${t}</span>`).join("");

  function layersHTML(d) {
    const claims = d.routing.map((c) => `<div class="claim"><div><b>${esc(c.claim)}</b> <span class="muted">(${esc(c.claim_source)})</span></div>
      <div class="path">${c.states.map((s) => `<span class="st-${s}">${STATE_SHORT[s] || esc(s)}</span>`).join(" → ")} <span class="muted">· ${c.closed ? "closed" : "left open"}</span></div>
      ${c.unexamined_agreement ? '<div class="flag">Closed on agreement, nothing independent checked</div>' : ""}</div>`).join("");
    const arg = (d.argument || []).length ? d.argument.map((b) => `<div class="claim"><div class="path">${esc(b.element)}: ${esc(b.status)} → ${b.labor.map((l) => `[${l}]`).join(" ")}</div></div>`).join("") : '<p class="muted">Not coded.</p>';
    return `<div><h3>Claims</h3>${claims}</div><div><h3>Argument</h3>${arg}</div>
      <div><h3>Source</h3><p>${esc((d.source || {}).origin || "Draft")}</p>${(d.source || {}).notes ? `<p class="muted" style="margin-top:6px">${esc(d.source.notes)}</p>` : ""}</div>`;
  }
  // comparison of two episodes (tools/compare_episodes.py): facts, verdicts, labor and plain sentences
  function compareHTML(r, collapse) {
    const cell = (v) => `<td>${esc(v === null || v === undefined || v === "" ? "–" : v)}</td>`;
    let h = `<div class="cmpsum"><p class="small muted">${esc(r.mode === "labor across settings"
      ? "Different settings: step names differ, so the comparison uses argumentation labor (argumentation lens), which both settings share."
      : "Same setting: steps are matched by activity and screen. Steps found in only one map are outlined.")}</p>`;
    if ((r.sentences || []).length) h += "<ul>" + r.sentences.map((x) => `<li>${esc(x)}</li>`).join("") + "</ul>";
    const top = h; h = "";
    if ((r.facts || []).length) h += `<div class="tablewrap"><table><thead><tr><th></th><th>A</th><th>B</th></tr></thead><tbody>` +
      r.facts.map((f) => `<tr><td>${esc(f[0])}</td>${cell(f[1])}${cell(f[2])}</tr>`).join("") + "</tbody></table></div>";
    if (r.reachability) {
      const side = (rows) => rows.length ? rows.map(([c, v]) => `<div>${esc(c)}: <b class="${/unchecked/.test(v) ? "verdict-warn" : /every/.test(v) ? "verdict-ok" : ""}">${esc(v)}</b></div>`).join("") : "–";
      h += `<div class="tablewrap"><table><thead><tr><th>Reachability</th><th>A</th><th>B</th></tr></thead><tbody><tr><td>Claims</td><td>${side(r.reachability.a)}</td><td>${side(r.reachability.b)}</td></tr></tbody></table></div>`;
    }
    const L = r.labor || {};
    if (L.a && L.b) {
      h += `<div class="tablewrap"><table><thead><tr><th>Argumentation labor</th><th>A</th><th>B</th></tr></thead><tbody>` +
        Object.entries(L.kinds).map(([k, name]) => `<tr><td>${esc(name)}</td>${cell(L.a.by_kind[k] || 0)}${cell(L.b.by_kind[k] || 0)}</tr>`).join("") +
        ["queue", "work", "record"].map((role) => `<tr><td>Placed on ${role} screens</td>${cell(L.a.by_role[role] || 0)}${cell(L.b.by_role[role] || 0)}</tr>`).join("") +
        `<tr><td>After an AI step</td>${cell(L.a.after_ai)}${cell(L.b.after_ai)}</tr></tbody></table></div>`;
    }
    if (collapse && h) return top + `<details class="cmpdetails"><summary>Details <span>steps, claims, reachability, argumentation labor</span></summary>${h}</details></div>`;
    return top + h + "</div>";
  }
  return { draw, legendHTML, layersHTML, compareHTML };
}
