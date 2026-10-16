"use strict";
// The exporter concatenates replay.js and report.js into one script; report.js uses these helpers.
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const svg = (tag, attrs = {}, text) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text != null) node.textContent = text;
  return node;
};
const json = (value) => JSON.stringify(value, null, 2);
// Battle clock as the engine counts it (6:22); tenths only where a sequence needs them.
const clock = (ms) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
const clockTenths = (ms) => {
  const tenths = Math.max(0, Math.floor(ms / 100));
  return `${clock(tenths * 100)}.${tenths % 10}`;
};
const seconds = (value) =>
  value == null ? "not recorded" : value < 0.05 ? "<0.1 s" : `${value.toFixed(1)} s`;
const money = (usd) =>
  usd == null ? "not recorded" : usd === 0 ? "$0" : usd < 0.01 ? "<$0.01" : `$${usd.toFixed(2)}`;
const capital = (text) => text.charAt(0).toUpperCase() + text.slice(1);
// The stretch of battle an analyst note covers: its lead-in, then at least 5 s after it.
const span = (h) => ({
  from: Math.max(0, h.time_ms - (h.lead_in_s || 0) * 1000),
  to: Math.max(h.end_ms ?? h.time_ms + 20000, h.time_ms + 5000),
});
// Of the moments ({from, to, at}) whose window holds t, the one to mark: the latest at or
// before t, else the next one after it; -1 when no window holds t.
function markedAt(moments, t) {
  let found = -1,
    best = -Infinity;
  moments.forEach((m, k) => {
    const score = m.at <= t ? m.at : t - m.at;
    if (m.from <= t && t <= m.to && score >= best) {
      found = k;
      best = score;
    }
  });
  return found;
}
const GLYPHS = [
  "general",
  "cavalry",
  "missile_cavalry",
  "infantry",
  "polearm_infantry",
  "missile_infantry",
  "artillery",
  "monster",
];
const glyphKey = (key) => (GLYPHS.includes(key) ? key : "unknown");
// The two armies' colours: they mean the armies everywhere and nothing else.
const TEAM = { friendly: "#56b4e9", enemy: "#e69f00" };
// One scale wherever a view's age is drawn (the replay strip, the real-time rows).
const AGE_SCALE_S = 15;
// The impassable terrain cells as one SVG path, through a projection's x and y.
function blockedPath(terrain, x, y, scale) {
  const cell = terrain.cell_m,
    size = (cell * scale).toFixed(1);
  let path = "";
  terrain.rows.forEach((row, j) =>
    [...row].forEach((value, i) => {
      if (value === "#")
        path += `M${x(terrain.x0 + i * cell - cell / 2).toFixed(1)} ${y(terrain.z0 + j * cell + cell / 2).toFixed(1)}h${size}v${size}h-${size}z`;
    }),
  );
  return path;
}
// Age of the newest view a controller has answered, over [t0, t1] on the battle clock:
// [view_ms, applied_ms] replies make a sawtooth that drops whenever a reply lands.
function ageSeries(replies, [t0, t1]) {
  const landed = [...replies].sort((a, b) => a[1] - b[1]),
    points = [];
  let basis = null;
  for (const [view, applied] of landed) {
    if (applied > t1) break;
    if (applied > t0 && basis != null) points.push([applied, applied - basis]);
    basis = basis == null ? view : Math.max(basis, view);
    if (applied >= t0) points.push([applied, applied - basis]);
  }
  if (basis != null) points.push([t1, t1 - basis]);
  return points.map(([t, age]) => [t, age / 1000]);
}
function button(text, action, className) {
  const node = el("button", text, className);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function details(summary, ...content) {
  const node = el("details");
  node.append(el("summary", summary), ...content);
  return node;
}
function keyValues(rows) {
  const list = el("dl", null, "kv");
  for (const [key, value] of rows)
    if (value != null && value !== "") list.append(el("dt", key), el("dd", String(value)));
  return list;
}
function glyph(key, className = "glyph") {
  const node = svg("svg", { viewBox: "0 0 24 24", class: className, "aria-hidden": "true" });
  node.append(svg("use", { href: `#glyph-${glyphKey(key)}` }));
  return node;
}
function saveJSON(value, name) {
  const a = el("a"),
    url = URL.createObjectURL(new Blob([json(value)], { type: "application/json" }));
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// The battle viewer: map, controls, timeline strip, roster and the moment panel.
// Positions come only from recorded frames; gaps stay gaps and nothing is interpolated.
const Viewer = (() => {
  const $ = (id) => document.getElementById(id);
  const MAP = "#13212a";
  const REJECTED = "#ff7b72";
  const ABILITY = "#ff6fd8"; // an ability or spell ordered: no army or model uses this hue
  const ABILITY_MS = 5000; // how long its ring stays, fading
  const FEW_UNITS = 12; // up to this many markers every unit keeps its label
  const TRAIL_MS = 20000; // observed movement shown behind each unit
  const ROUTE_MS = 20000; // how long a newly issued route stays drawn for unselected units
  const ARRIVED_M = 30; // a waypoint this close to a recorded position counts as reached
  const ACCEPTED = ["acknowledged", "queued"];
  const STRIP_H = 104;
  const STRIP_LEFT = 70; // a gutter for the rows' labels
  const AGE_TOP = 56,
    AGE_H = 32;
  // Bands kept clear of units: the caption on top, the scale bar and north arrow below.
  const TOP_BAND = 40,
    BOTTOM_BAND = 36;
  let r = null,
    run = {},
    roster = new Map(),
    tracks = new Map(),
    orderLog = new Map(),
    chips = new Map(),
    times = [];
  let time = 0,
    start = 0,
    end = 0,
    gapMs = 1500,
    playing = false,
    speed = 4,
    until = null,
    lastTick = null,
    loop = null;
  let selected = null,
    hovered = null,
    pinned = null,
    lag = false,
    proj = null,
    strip = { w: 0, marks: [] },
    keys = {},
    framed = null,
    extent = null,
    watching = null,
    mapWidth = 0;
  const listeners = [];

  const placed = (u) => u && Number.isFinite(u.x) && Number.isFinite(u.z);
  const requested = (d) => d.decision_time_ms ?? d.time_ms;
  const unitIn = (frame, id) =>
    frame?.friendly.find((u) => u.id === id) || frame?.enemy.find((u) => u.id === id);
  const sideOf = (id) =>
    roster.get(id)?.side || (String(id).startsWith("e") ? "enemy" : "friendly");
  const has = (u, state) => (u?.state || []).includes(state);
  // Index of the last item whose key is at or before t, or -1.
  function lastAtOrBefore(list, t, key = (item) => item) {
    let lo = 0,
      hi = list.length - 1,
      found = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (key(list[mid]) <= t) {
        found = mid;
        lo = mid + 1;
      } else hi = mid - 1;
    }
    return found;
  }
  const frameIndex = () => Math.max(0, lastAtOrBefore(times, time));

  // The latest decision applied by t, and a later one still waiting for its reply.
  function momentAt(t) {
    let current = -1,
      pending = -1;
    r.decisions.forEach((d, i) => {
      if (d.applied_ms != null && d.applied_ms <= t) {
        if (current < 0 || d.applied_ms >= r.decisions[current].applied_ms) current = i;
      } else if (requested(d) <= t) pending = i;
    });
    return { current, pending: pending > current ? pending : -1 };
  }

  function show(payload, context) {
    r = payload;
    r.highlights ||= [];
    run = context;
    playing = false;
    until = null;
    watching = null;
    selected = null;
    hovered = null;
    pinned = null;
    keys = {};
    extent = null;
    roster = new Map(r.roster.map((entry) => [entry.id, entry]));
    times = r.frames.map((frame) => frame.time_ms);
    gapMs = 1.5 * (r.sample_interval_ms || 1000);
    tracks = new Map();
    for (const frame of r.frames)
      for (const side of ["friendly", "enemy"])
        for (const u of frame[side]) {
          if (!placed(u)) continue;
          if (!tracks.has(u.id)) tracks.set(u.id, []);
          const track = tracks.get(u.id);
          if (track.at(-1)?.t !== frame.time_ms) track.push({ t: frame.time_ms, x: u.x, z: u.z });
        }
    orderLog = new Map();
    r.decisions.forEach((d, i) => {
      if (d.applied_ms == null) return;
      for (const id of new Set(d.steps.map((step) => step.unit))) {
        if (!orderLog.has(id)) orderLog.set(id, []);
        orderLog.get(id).push(i);
      }
    });
    const first = r.frames.find((frame) => frame.friendly.length || frame.enemy.length);
    start = (first || r.frames[0]).time_ms;
    end = r.frames.at(-1).time_ms;
    time = r.decisions.find((d) => d.applied_ms != null)?.applied_ms ?? start;
    $("scrubber").min = start / 1000;
    $("scrubber").max = end / 1000;
    setControls(true);
    $("whole").checked = false;
    $("whole").disabled = !r.terrain;
    $("map-synthetic").hidden = !run.synthetic;
    $("lag-toggle").disabled = !r.decisions.some((d) => d.basis_frame != null);
    $("map-empty").hidden = true;
    $("map-note").textContent = r.recorder_version
      ? ""
      : `No 1 Hz recorder in this run: positions and states update only when the controller observed the battle, about every ${Math.round(r.sample_interval_ms / 1000)} s; event times are when a change was first observed.`;
    renderRoster();
    updatePlay();
    mapWidth = 0;
    layout();
  }

  function clear(message) {
    r = null;
    playing = false;
    watching = null;
    selected = null;
    pinned = null;
    for (const id of [
      "map-ground",
      "map-lag-layer",
      "map-layer",
      "map-furniture",
      "strip-static",
      "roster",
    ])
      $(id).replaceChildren();
    $("map").setAttribute("viewBox", "0 0 640 280");
    $("map").style.height = "280px";
    $("map-empty").textContent = message;
    $("map-empty").hidden = false;
    for (const id of ["map-caption", "map-status", "map-selection", "map-synthetic", "map-lag"])
      $(id).hidden = true;
    $("map-note").textContent = "";
    $("strip-cursor").setAttribute("y2", 0);
    $("moment").replaceChildren(el("p", message, "muted"));
    $("clock").textContent = "–";
    setControls(false);
    updatePlay();
  }

  function setControls(enabled) {
    for (const node of document.querySelectorAll(
      ".controls button, #speed, #scrubber, #whole, #lag-toggle",
    ))
      node.disabled = !enabled;
  }

  // A box around points, at least `least` metres wide and tall, with a `margin`.
  function around(points, margin, least) {
    const xs = points.map((p) => p.x),
      zs = points.map((p) => p.z);
    const box = [Math.min(...xs), Math.min(...zs), Math.max(...xs), Math.max(...zs)];
    for (const [a, b] of [
      [0, 2],
      [1, 3],
    ]) {
      const grow = Math.max(margin, (least - (box[b] - box[a])) / 2);
      box[a] -= grow;
      box[b] += grow;
    }
    return box;
  }
  // Fixed framing per replay, where the fighting happened: the 5th to 95th percentile of every
  // recorded position over the battle (a unit that strays far off does not shrink the rest),
  // and where the units seen in the first 30 s started, with a margin. No camera moves; "Show the whole map" frames
  // the terrain instead.
  function bounds() {
    const terrain = r.terrain?.bounds;
    if ($("whole").checked && terrain)
      return [terrain.min_x, terrain.min_z, terrain.max_x, terrain.max_z];
    const all = [...tracks.values()].flat(),
      xs = all.map((p) => p.x).sort((a, b) => a - b),
      zs = all.map((p) => p.z).sort((a, b) => a - b),
      at = (list, q) => list[Math.round((list.length - 1) * q)];
    const points = all.length
      ? [
          { x: at(xs, 0.05), z: at(zs, 0.05) },
          { x: at(xs, 0.95), z: at(zs, 0.95) },
          ...[...tracks.values()].map((track) => track[0]).filter((p) => p.t <= start + 30000),
        ]
      : [];
    for (const frame of r.frames) {
      const zone = frame.mode?.custom?.zone;
      if (zone) {
        points.push(
          { x: zone.x - zone.radius, z: zone.z - zone.radius },
          { x: zone.x + zone.radius, z: zone.z + zone.radius },
        );
        break;
      }
    }
    extent ??= points.length ? around(points, 50, 220) : [-256, -256, 256, 256];
    return extent;
  }

  function layout() {
    if (!r) return;
    const map = $("map"),
      w = Math.max(260, Math.round($("map-wrap").clientWidth));
    mapWidth = w;
    const b = bounds(),
      aspect = (b[3] - b[1]) / (b[2] - b[0]);
    const tallest = Math.max(320, Math.min(innerHeight - 150, 980));
    const h = Math.round(Math.max(260, Math.min(w * aspect + TOP_BAND + BOTTOM_BAND, tallest)));
    map.setAttribute("viewBox", `0 0 ${w} ${h}`);
    map.style.height = `${h}px`;
    proj = { w, h };
    reframe();
    drawStrip();
    keys = {};
    render();
  }

  // The projection: the battle's fixed framing, or, while a decision is pinned for
  // inspection, a closer frame around the units it involves.
  function reframe() {
    const { w, h } = proj,
      b = pinned == null ? bounds() : inspectBounds(r.decisions[pinned]);
    // The inspect caption wraps on narrow maps: its band grows to fit it.
    const top = pinned == null ? TOP_BAND : Math.max(TOP_BAND, $("map-caption").offsetHeight + 10);
    const bottom = BOTTOM_BAND;
    const scale = Math.min((w - 28) / (b[2] - b[0]), (h - 28 - top - bottom) / (b[3] - b[1]));
    const cx = (b[0] + b[2]) / 2,
      cz = (b[1] + b[3]) / 2,
      middle = top + (h - top - bottom) / 2;
    // Markers shrink a little on narrow maps; labels keep their size.
    const k = Math.max(0.72, Math.min(1, w / 760));
    proj = {
      w,
      h,
      scale,
      k,
      cx,
      cz,
      x: (x) => w / 2 + (x - cx) * scale,
      y: (z) => middle - (z - cz) * scale,
    };
    framed = pinned;
    drawGround();
    drawFurniture();
    keys.map = null;
  }
  // Frames the units drawn in inspect mode, as placed in either of its two frames.
  function inspectBounds(d) {
    const ids = [...inspectUnits(d)];
    const points = [d.basis_frame, d.after_frame].flatMap((i) =>
      ids.map((id) => unitIn(r.frames[i], id)).filter(placed),
    );
    return points.length ? around(points, 50, 240) : bounds();
  }

  function drawGround() {
    const ground = $("map-ground"),
      terrain = r.terrain;
    ground.replaceChildren(svg("rect", { width: proj.w, height: proj.h, fill: "#0d171d" }));
    if (terrain) {
      const t = terrain.bounds,
        x = proj.x(t.min_x),
        y = proj.y(t.max_z);
      ground.append(
        svg("rect", {
          x,
          y,
          width: proj.x(t.max_x) - x,
          height: proj.y(t.min_z) - y,
          fill: MAP,
        }),
      );
      ground.append(
        svg("path", { d: blockedPath(terrain, proj.x, proj.y, proj.scale), fill: "#33454f" }),
      );
    } else ground.append(svg("rect", { width: proj.w, height: proj.h, fill: MAP }));
    // A faint 100 m grid helps judge distances without competing with the units.
    const grid = svg("g", { stroke: "#ffffff", "stroke-opacity": 0.045 });
    const halfW = proj.w / 2 / proj.scale,
      halfH = proj.h / 2 / proj.scale;
    for (let x = Math.ceil((proj.cx - halfW) / 100) * 100; x <= proj.cx + halfW; x += 100)
      grid.append(svg("line", { x1: proj.x(x), x2: proj.x(x), y1: 0, y2: proj.h }));
    for (let z = Math.ceil((proj.cz - halfH) / 100) * 100; z <= proj.cz + halfH; z += 100)
      grid.append(svg("line", { x1: 0, x2: proj.w, y1: proj.y(z), y2: proj.y(z) }));
    ground.append(grid);
  }

  function drawFurniture() {
    const g = $("map-furniture");
    g.replaceChildren();
    const metres = [50, 100, 200, 500].find((m) => m * proj.scale >= 60) || 500;
    const length = metres * proj.scale,
      x = proj.w - 40 - length,
      y = proj.h - 14;
    g.append(
      svg("path", {
        d: `M${x} ${y - 4}v4h${length}v-4`,
        fill: "none",
        stroke: "#cfdbe1",
        "stroke-width": 1.5,
      }),
      svg(
        "text",
        { x: x + length / 2, y: y - 7, class: "tiny", fill: "#cfdbe1", "text-anchor": "middle" },
        `${metres} m`,
      ),
      svg("path", { d: `M${proj.w - 20} ${y - 26}l6 14h-12z`, fill: "#cfdbe1" }),
      svg(
        "text",
        { x: proj.w - 20, y: y + 1, class: "tiny", fill: "#cfdbe1", "text-anchor": "middle" },
        "N",
      ),
    );
  }

  // Observed movement, split wherever two samples are further apart than the recording interval.
  function pieces(track, from, to) {
    const out = [];
    let piece = [];
    for (const p of track.slice(
      Math.max(
        0,
        lastAtOrBefore(track, from, (q) => q.t),
      ),
    )) {
      if (p.t > to) break;
      if (p.t < from) continue;
      if (piece.length && p.t - piece.at(-1).t > gapMs) {
        out.push(piece);
        piece = [];
      }
      piece.push(p);
    }
    if (piece.length) out.push(piece);
    return out;
  }
  const points = (list) =>
    list.map((p) => `${proj.x(p.x).toFixed(1)},${proj.y(p.z).toFixed(1)}`).join(" ");
  const polyline = (list, stroke, attrs = {}) =>
    svg("polyline", {
      points: points(list),
      fill: "none",
      stroke,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      ...attrs,
    });

  function drawTrails(layer, frameTime, focus) {
    for (const [id, track] of tracks) {
      const mine = id === selected,
        colour = TEAM[sideOf(id)];
      const opacity = mine ? 0.95 : focus && !focus.has(id) ? 0.1 : 0.45;
      for (const piece of pieces(track, mine ? -Infinity : frameTime - TRAIL_MS, frameTime)) {
        if (piece.length > 1)
          layer.append(polyline(piece, colour, { "stroke-width": mine ? 2.5 : 1.5, opacity }));
        else
          layer.append(
            svg("circle", {
              cx: proj.x(piece[0].x),
              cy: proj.y(piece[0].z),
              r: mine ? 2.2 : 1.6,
              fill: colour,
              opacity,
            }),
          );
      }
    }
  }

  // Where an attack target is drawn: its current position, else where it was last seen.
  function targetAt(id, fi) {
    const visible = unitIn(r.frames[fi], id);
    if (placed(visible)) return visible;
    const track = tracks.get(id) || [];
    return track[lastAtOrBefore(track, r.frames[fi].time_ms, (p) => p.t)] || null;
  }

  // The unit's newest decision with route steps applied by t; optionally accepted ones only.
  function latestOrders(id, t, accepted = false) {
    const log = orderLog.get(id) || [];
    for (let k = log.length - 1; k >= 0; k--) {
      const d = r.decisions[log[k]];
      if (d.applied_ms > t) continue;
      const own = d.steps.filter(
        (s) => s.unit === id && ["move", "attack", "halt"].includes(s.kind),
      );
      if (own.length && (!accepted || own.some((s) => ACCEPTED.includes(s.status)))) return log[k];
    }
    return null;
  }

  // One dashed route through the issued waypoints; attack targets as rings, never as arrows.
  // A rejected move rejects the steps queued after it, so a route turns red at most once.
  // A strong route starts where the model saw the unit. A faint route starts where the unit
  // is now and runs through the waypoints it has not yet come within ARRIVED_M of; a unit out
  // of view gets none.
  function drawRoute(layer, d, id, fi, strong) {
    const steps = d.steps.filter((s) => s.unit === id && ["move", "attack"].includes(s.kind));
    if (!steps.length) return;
    const moves = steps.filter((s) => s.kind === "move"),
      ok = moves.filter((s) => s.status !== "rejected"),
      bad = moves.filter((s) => s.status === "rejected");
    let lead = [],
      ahead = ok;
    if (strong) {
      const basis = d.basis_frame != null ? unitIn(r.frames[d.basis_frame], id) : null;
      if (placed(basis)) lead = [basis];
    } else {
      // Only the waypoints the unit has not yet come within ARRIVED_M of, from where it is.
      const u = unitIn(r.frames[fi], id);
      let reached = 0;
      for (let i = d.after_frame ?? fi; i <= fi && reached < ok.length; i++) {
        const p = unitIn(r.frames[i], id);
        if (placed(p) && Math.hypot(p.x - ok[reached].x, p.z - ok[reached].z) < ARRIVED_M)
          reached++;
      }
      lead = placed(u) ? [u] : [];
      ahead = placed(u) ? ok.slice(reached) : [];
    }
    const g = svg("g", { opacity: strong ? 1 : 0.3, "pointer-events": "none" }),
      dashed = { "stroke-width": strong ? 2.2 : 1, "stroke-dasharray": "7 5" };
    if (lead.length + ahead.length > 1)
      g.append(polyline([...lead, ...ahead], TEAM.friendly, dashed));
    const turn = ahead.length ? [ahead.at(-1)] : lead;
    if (bad.length && turn.length + bad.length > 1)
      g.append(polyline([...turn, ...bad], REJECTED, dashed));
    moves.forEach((step, k) => {
      const x = proj.x(step.x),
        y = proj.y(step.z);
      if (step.status === "rejected")
        g.append(
          svg("path", {
            d: `M${x - 6} ${y - 6}l12 12m0-12l-12 12`,
            stroke: REJECTED,
            "stroke-width": 2.5,
          }),
        );
      else if (!strong) {
        if (ahead.includes(step))
          g.append(svg("circle", { cx: x, cy: y, r: 2.6, fill: TEAM.friendly }));
      } else
        g.append(
          svg("circle", {
            cx: x,
            cy: y,
            r: 8,
            fill: MAP,
            stroke: TEAM.friendly,
            "stroke-width": 1.5,
          }),
          svg(
            "text",
            { x, y: y + 3.5, class: "tiny", fill: "#fff", "text-anchor": "middle" },
            k + 1,
          ),
        );
    });
    for (const step of steps.filter((s) => s.kind === "attack" && s.target)) {
      const target = targetAt(step.target, fi),
        colour = step.status === "rejected" ? REJECTED : TEAM.friendly;
      if (!target) continue;
      // The dotted connector says "this target", not "this path": the route is the dashes.
      const origin = moves.length ? moves.at(-1) : unitIn(r.frames[fi], id);
      if (strong && placed(origin))
        g.append(
          polyline([origin, target], colour, {
            "stroke-width": 1.2,
            "stroke-dasharray": "1.5 4",
            opacity: 0.8,
          }),
        );
      g.append(
        svg("circle", {
          cx: proj.x(target.x),
          cy: proj.y(target.z),
          r: 19,
          fill: "none",
          stroke: colour,
          "stroke-width": strong ? 2 : 1,
        }),
      );
    }
    layer.append(g);
  }

  function drawUnit(layer, u, side, { dim = false, ghost = false, seen = null, note = null } = {}) {
    if (!placed(u)) return;
    const entry = roster.get(u.id) || {},
      colour = TEAM[side];
    const down = u.men === 0,
      fleeing = has(u, "routing") || has(u, "shattered"),
      hollow = ghost || seen != null;
    const g = svg("g", {
      class: "unit",
      "data-unit": u.id,
      transform: `translate(${proj.x(u.x).toFixed(1)} ${proj.y(u.z).toFixed(1)}) scale(${proj.k})`,
      opacity: dim ? 0.25 : seen != null ? 0.6 : ghost ? 0.75 : down ? 0.45 : 1,
    });
    g.append(svg("circle", { r: 18, class: "hit" }));
    if (u.id === selected && !ghost)
      g.append(svg("circle", { r: 20, fill: "none", stroke: "#fff", "stroke-width": 2 }));
    if (u.bearing != null && !down && !hollow)
      g.append(
        svg("path", {
          d: "M0 -19L-4.5 -12.5H4.5Z",
          fill: colour,
          transform: `rotate(${u.bearing})`,
        }),
      );
    const body =
      side === "friendly"
        ? svg("circle", { r: 11.5 })
        : svg("path", { d: "M0 -13.5L13.5 0 0 13.5-13.5 0Z" });
    body.setAttribute("fill", hollow ? "none" : MAP);
    body.setAttribute("stroke", colour);
    body.setAttribute("stroke-width", 2);
    if (hollow || fleeing) body.setAttribute("stroke-dasharray", "3 2.5");
    g.append(body);
    g.append(
      svg("use", {
        href: `#glyph-${glyphKey(entry.glyph)}`,
        x: -8,
        y: -8,
        width: 16,
        height: 16,
        color: colour,
      }),
    );
    if (!hollow) {
      const share = u.men0 > 1 ? u.men / u.men0 : u.hp;
      if (Number.isFinite(share)) {
        g.append(
          svg("rect", { x: -11, y: 16, width: 22, height: 3, fill: "#ffffff", opacity: 0.18 }),
        );
        g.append(
          svg("rect", {
            x: -11,
            y: 16,
            width: 22 * Math.max(0, Math.min(1, share)),
            height: 3,
            fill: colour,
          }),
        );
      }
    }
    // An outline takes no label but keeps other labels off its marker; on a crowded map only the
    // selected, hovered or emphasised units are named.
    const named = !quiet || u.id === selected || u.id === hovered || focus?.has(u.id);
    labels.push({
      x: proj.x(u.x),
      y: proj.y(u.z),
      text:
        ghost || !named
          ? null
          : `${entry.short || u.id}${seen != null ? `, seen ${clock(seen)}` : ""}`,
      note: [fleeing && !down && "fleeing", note].filter(Boolean).join(" ") || null,
      colour,
      rank: u.id === selected ? 0 : dim || hollow ? 2 : 1,
      opacity: g.getAttribute("opacity"),
    });
    if (has(u, "melee") && !down && !hollow) {
      g.append(
        svg("circle", { cx: -14, cy: -12, r: 7.5, fill: MAP, stroke: "#fff", "stroke-width": 1 }),
      );
      g.append(
        svg("use", { href: "#glyph-melee", x: -19, y: -17, width: 10, height: 10, color: "#fff" }),
      );
    }
    if (down)
      g.append(svg("path", { d: "M-8 -8l16 16m0-16l-16 16", stroke: "#fff", "stroke-width": 2 }));
    g.append(svg("title", {}, `${entry.display || u.id}, ${entry.role || "unit"}`));
    layer.append(g);
  }

  // Short labels go beside their marker where they overlap no other marker or label;
  // faded units lose theirs when nothing fits.
  let labels = [],
    quiet = false,
    focus = null;
  function placeLabels(layer) {
    const radius = 14 * proj.k,
      taken = labels.map((l) => [l.x - radius, l.y - radius, l.x + radius, l.y + radius]);
    const overlap = (a, b) =>
      Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) *
      Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
    for (const l of labels.sort((a, b) => a.rank - b.rank)) {
      if (!l.text) continue;
      const w = (l.text.length + (l.note ? l.note.length + 1 : 0)) * 7.4,
        h = 12,
        d = radius + 3;
      const options = [
        [l.x + d, l.y - h - 1],
        [l.x + d, l.y + 1],
        [l.x - d - w, l.y - h - 1],
        [l.x - d - w, l.y + 1],
        [l.x - w / 2, l.y - d - h - 5],
        [l.x - w / 2, l.y + d + 7],
      ].map(([x, y]) => [x, y, x + w, y + h]);
      const cost = (box) => taken.reduce((sum, other) => sum + overlap(box, other), 0);
      const box =
        options.find((option) => !cost(option)) ||
        (l.rank === 0 && options.sort((a, b) => cost(a) - cost(b))[0]);
      if (!box) continue;
      taken.push(box);
      const text = svg(
        "text",
        {
          x: box[0],
          y: box[3] - 2,
          class: "label",
          fill: l.colour,
          "font-size": 11,
          opacity: l.opacity,
        },
        l.text,
      );
      if (l.note) text.append(svg("tspan", { fill: "#ffd27a" }, ` ${l.note}`));
      layer.append(text);
    }
    labels = [];
  }

  function drawLastSeen(layer, fi, focus) {
    const frame = r.frames[fi],
      visible = new Set(frame.enemy.map((u) => u.id));
    const dead = new Set(frame.enemy_roster.filter((u) => u.dead).map((u) => u.id));
    for (const entry of r.roster) {
      if (entry.side !== "enemy" || visible.has(entry.id) || dead.has(entry.id)) continue;
      const point = targetAt(entry.id, fi);
      if (point)
        drawUnit(layer, { id: entry.id, x: point.x, z: point.z }, "enemy", {
          seen: point.t,
          dim: focus && !focus.has(entry.id),
        });
    }
  }

  // A watched note stays emphasised over its own window until the time is moved by hand.
  const watched = () => watching != null && watching.from <= time && time <= watching.to;
  // Bright: the selected unit and its standing and current targets, else a watched note's units.
  function focusSet(fi) {
    if (!selected) return watched() && watching.ids.size ? watching.ids : null;
    const ids = new Set([selected]);
    const u = unitIn(r.frames[fi], selected);
    if (u?.target) ids.add(u.target);
    const standing = latestOrders(selected, time, true);
    if (standing != null)
      for (const step of r.decisions[standing].steps)
        if (step.unit === selected && step.target) ids.add(step.target);
    return ids;
  }

  function inspectUnits(d) {
    const ids = new Set();
    for (const step of d.steps) {
      if (step.unit !== "army") ids.add(step.unit);
      if (step.target) ids.add(step.target);
    }
    for (const m of d.displacements) if (m.metres >= (ids.size ? 5 : 1)) ids.add(m.unit);
    return ids;
  }

  // Inspect mode: the observation the model saw (outlines) and the first recorded state at or
  // after its orders were applied (solid), joined by straight lines between the two samples.
  function drawInspect(layer, d) {
    const basis = r.frames[d.basis_frame],
      after = r.frames[d.after_frame],
      ids = inspectUnits(d);
    const moved = new Map();
    for (const m of d.displacements) {
      if (!ids.has(m.unit)) continue;
      const a = { x: m.from[0], z: m.from[1] },
        b = { x: m.to[0], z: m.to[1] };
      layer.append(polyline([a, b], TEAM[m.side], { "stroke-width": 1.5 }));
      if (m.metres >= 1) moved.set(m.unit, `${Math.round(m.metres)} m`);
    }
    for (const side of ["friendly", "enemy"]) {
      for (const u of basis[side]) if (ids.has(u.id)) drawUnit(layer, u, side, { ghost: true });
      for (const u of after[side])
        if (ids.has(u.id)) drawUnit(layer, u, side, { note: moved.get(u.id) });
    }
    placeLabels(layer);
  }

  // Replies whose view the overlay and strip follow: every applied decision, or for the
  // asynchronous commander only its plan adoptions (its executor follows the latest plan).
  const planned = () => r.decisions.some((d) => d.plan_age_s != null);
  const answers = (d) => d.applied_ms != null && (!planned() || d.plan_age_s != null);
  // The model's view: the observation behind the latest reply that reached the game (for the
  // asynchronous commander, its plan's older one), drawn as outlines joined to where each
  // unit is now.
  function viewOf(now) {
    if (now.current < 0) return null;
    let i = now.current;
    while (i >= 0 && !(answers(r.decisions[i]) && r.decisions[i].applied_ms <= time)) i--;
    if (i < 0) return null;
    const d = r.decisions[i];
    if (d.plan_age_s != null) {
      const at = d.time_ms - d.plan_age_s * 1000;
      return { d, at, frame: Math.max(0, lastAtOrBefore(times, at)) };
    }
    return d.basis_frame == null ? null : { d, at: d.time_ms, frame: d.basis_frame };
  }
  function drawLag(layer, fi, now) {
    const view = viewOf(now);
    if (!lag || pinned != null || !view) return;
    const frame = r.frames[fi];
    for (const side of ["friendly", "enemy"])
      for (const u of r.frames[view.frame][side]) {
        const current = frame[side].find((item) => item.id === u.id);
        if (placed(u) && placed(current) && Math.hypot(u.x - current.x, u.z - current.z) >= 3)
          layer.append(polyline([u, current], TEAM[side], { "stroke-width": 1.5, opacity: 0.8 }));
        drawUnit(layer, u, side, { ghost: true });
      }
  }

  // Units given an ability or spell in the last ABILITY_MS, with the whole seconds since.
  function abilityRings() {
    const rings = [];
    for (const d of r.decisions) {
      if (d.applied_ms == null || d.applied_ms > time || d.applied_ms <= time - ABILITY_MS)
        continue;
      for (const step of d.steps)
        if (step.kind === "ability" && ACCEPTED.includes(step.status) && step.unit !== "army")
          rings.push({ id: step.unit, age: Math.floor((time - d.applied_ms) / 1000) });
    }
    return rings;
  }

  function renderMap(fi, now) {
    const lagKey = lag && pinned == null ? now.current : "";
    const rings = pinned == null ? abilityRings() : [];
    const key = [
      fi,
      now.current,
      selected,
      hovered,
      pinned,
      proj.w,
      proj.h,
      watched(),
      lagKey,
      rings.map((ring) => `${ring.id}:${ring.age}`).join(","),
    ].join("|");
    if (key === keys.map) return;
    keys.map = key;
    const layer = $("map-layer");
    layer.replaceChildren();
    $("map-lag-layer").replaceChildren();
    quiet = false;
    focus = null;
    if (pinned != null) return drawInspect(layer, r.decisions[pinned]);
    drawLag($("map-lag-layer"), fi, now);
    const frame = r.frames[fi];
    focus = focusSet(fi);
    const unseen = r.roster.filter(
      (entry) => entry.side === "enemy" && !frame.enemy.some((u) => u.id === entry.id),
    ).length;
    quiet = frame.friendly.length + frame.enemy.length + unseen > FEW_UNITS;
    drawTrails(layer, frame.time_ms, focus);
    // Routes issued in the last 20 s, faint; the selected unit's standing orders, strong.
    if (!selected)
      for (const entry of r.roster.filter((item) => item.side === "friendly")) {
        if (focus && !focus.has(entry.id)) continue;
        const i = latestOrders(entry.id, time);
        if (i != null && r.decisions[i].applied_ms >= time - ROUTE_MS)
          drawRoute(layer, r.decisions[i], entry.id, fi, false);
      }
    if (selected) {
      const standing = latestOrders(selected, time, true),
        newest = latestOrders(selected, time);
      if (standing != null) drawRoute(layer, r.decisions[standing], selected, fi, true);
      if (newest != null && newest !== standing)
        drawRoute(layer, r.decisions[newest], selected, fi, true);
    }
    // Objectives as small diamonds filled by their holder's colour, larger for victory points;
    // their names and holders are in the tooltip.
    for (const point of frame.mode?.capture_points || [])
      if (placed(point)) {
        const colour = { us: TEAM.friendly, enemy: TEAM.enemy }[point.holder],
          s = point.victory ? 8 : 5.5;
        const mark = svg("path", {
          d: `M${proj.x(point.x).toFixed(1)} ${(proj.y(point.z) - s).toFixed(1)}l${s} ${s}-${s} ${s}-${s}-${s}z`,
          class: "objective",
          fill: colour || "none",
          "fill-opacity": 0.6,
          stroke: colour || "#cfdbe1",
          "stroke-width": point.victory ? 2 : 1.4,
        });
        const holder = { us: "held by the model's army", enemy: "held by the enemy" }[point.holder];
        mark.append(
          svg(
            "title",
            {},
            `${point.name || point.id}${point.victory ? " (victory point)" : ""}: ${holder || "not held"}`,
          ),
        );
        layer.append(mark);
      }
    const extraction = frame.mode?.custom?.zone;
    if (extraction && placed(extraction)) {
      layer.append(
        svg("circle", {
          cx: proj.x(extraction.x),
          cy: proj.y(extraction.z),
          r: extraction.radius * proj.scale,
          fill: "#7dd3a722",
          stroke: "#7dd3a7",
          "stroke-width": 2,
          "stroke-dasharray": "5 3",
        }),
        svg(
          "text",
          { x: proj.x(extraction.x), y: proj.y(extraction.z), class: "tiny", fill: "#7dd3a7" },
          "Extraction",
        ),
      );
    }
    drawLastSeen(layer, fi, focus);
    for (const side of ["friendly", "enemy"])
      for (const u of frame[side]) drawUnit(layer, u, side, { dim: focus && !focus.has(u.id) });
    // A ring around a unit just ordered to use an ability or spell, fading over ABILITY_MS.
    for (const ring of rings) {
      const u = unitIn(frame, ring.id);
      if (!placed(u)) continue;
      const circle = svg("circle", {
        cx: proj.x(u.x),
        cy: proj.y(u.z),
        r: 23 * proj.k,
        class: "ability-ring",
        fill: "none",
        stroke: ABILITY,
        "stroke-width": 2.5,
        opacity: (1 - ring.age / (ABILITY_MS / 1000 + 1)).toFixed(2),
      });
      circle.append(
        svg("title", {}, `${roster.get(ring.id)?.display || ring.id}: ability ordered`),
      );
      layer.append(circle);
    }
    placeLabels(layer);
  }

  // Timeline strip: decisions with orders, decisions keeping orders, rejections, analyst
  // notes and key events. Its marks are click targets; the scrubber and buttons do the same.
  const stripX = (t) =>
    STRIP_LEFT + ((strip.w - STRIP_LEFT - 10) * (t - start)) / Math.max(1, end - start);
  function drawStrip() {
    const node = $("strip"),
      w = Math.max(200, Math.round(node.clientWidth));
    node.setAttribute("viewBox", `0 0 ${w} ${STRIP_H}`);
    strip = { w, marks: [] };
    const g = $("strip-static");
    g.replaceChildren();
    for (let m = Math.ceil(start / 60000); m * 60000 <= end; m++) {
      const x = stripX(m * 60000);
      g.append(svg("line", { x1: x, x2: x, y1: 90, y2: 94, stroke: "#5f7380" }));
      if (w > 420 || m % 2 === 0)
        g.append(
          svg(
            "text",
            { x, y: 103, fill: "#8fa3ad", "font-size": 10, "text-anchor": "middle" },
            `${m}:00`,
          ),
        );
    }
    // How old the view behind the latest reply is, second by second: drops when replies land.
    const replies = r.decisions
      .filter(answers)
      .map((d) => [d.time_ms - (d.plan_age_s || 0) * 1000, d.applied_ms]);
    const series = ageSeries(replies, [start, end]);
    const top = AGE_SCALE_S;
    const ageY = (age) => AGE_TOP + AGE_H - (Math.min(age, top) / top) * AGE_H;
    const label = (y, text) => svg("text", { x: 8, y, fill: "#8fa3ad", "font-size": 11 }, text);
    g.append(
      label(15, "Notes"),
      label(36, "Replies"),
      label(50, "Events"),
      label(AGE_TOP + 10, "View age"),
      label(AGE_TOP + 22, `0–${top} s, line 5 s`),
      svg("line", {
        x1: STRIP_LEFT,
        x2: w - 10,
        y1: ageY(5),
        y2: ageY(5),
        stroke: "#ffffff",
        "stroke-opacity": 0.25,
        "stroke-dasharray": "2 3",
      }),
    );
    if (series.length)
      g.append(
        svg("path", {
          d: `M${stripX(series[0][0])} ${AGE_TOP + AGE_H}${series.map(([t, a]) => `L${stripX(t).toFixed(1)} ${ageY(a).toFixed(1)}`).join("")}L${stripX(series.at(-1)[0])} ${AGE_TOP + AGE_H}Z`,
          fill: "#8fa3ad",
          "fill-opacity": 0.65,
        }),
      );
    r.highlights.forEach((h, k) => {
      const { from, to } = span(h);
      g.append(
        svg("rect", {
          x: stripX(from),
          y: 3,
          width: Math.max(2, stripX(to) - stripX(from)),
          height: 16,
          fill: "#ffffff",
          opacity: 0.08,
          rx: 3,
        }),
      );
      const x = stripX(h.time_ms);
      g.append(
        svg("circle", { cx: x, cy: 11, r: 7, fill: "#f3efe4" }),
        svg(
          "text",
          { x, y: 14.5, "font-size": 10, "font-weight": 700, fill: MAP, "text-anchor": "middle" },
          k + 1,
        ),
      );
      strip.marks.push({ row: 0, x, t: from });
    });
    r.decisions.forEach((d, i) => {
      if (d.applied_ms == null) return;
      const x = stripX(d.applied_ms),
        rejected = d.invalid || d.steps.some((s) => s.status === "rejected");
      if (rejected)
        g.append(svg("rect", { x: x - 1.25, y: 22, width: 2.5, height: 20, fill: REJECTED }));
      else if (d.steps.length)
        g.append(svg("rect", { x: x - 1, y: 25, width: 2, height: 14, fill: TEAM.friendly }));
      else g.append(svg("circle", { cx: x, cy: 32, r: 1.6, fill: "#7f929c" }));
      strip.marks.push({ row: 1, x, i });
    });
    for (const e of r.events.filter((e) => e.key)) {
      const x = stripX(e.time_ms),
        colour = e.unit ? TEAM[sideOf(e.unit)] : "#ffffff";
      g.append(svg("path", { d: `M${x} 41.5l4.5 4.5-4.5 4.5-4.5-4.5z`, fill: colour }));
      strip.marks.push({ row: 2, x, t: e.time_ms });
    }
    $("strip-cursor").setAttribute("y2", STRIP_H);
  }
  let dragging = false;
  function stripPointer(event, snap) {
    const box = $("strip").getBoundingClientRect();
    const x = ((event.clientX - box.left) * strip.w) / box.width,
      y = ((event.clientY - box.top) * STRIP_H) / box.height;
    const row = y < 21 ? 0 : y < 41 ? 1 : y < 53 ? 2 : 3;
    const near = snap
      ? strip.marks
          .filter((m) => m.row === row && Math.abs(m.x - x) <= 7)
          .sort((a, b) => Math.abs(a.x - x) - Math.abs(b.x - x))[0]
      : null;
    if (near?.i != null) return goDecision(near.i);
    jump(near ? near.t : start + ((x - STRIP_LEFT) / (strip.w - STRIP_LEFT - 10)) * (end - start));
  }

  const waiting = (now) => {
    const s = (time - requested(r.decisions[now.pending])) / 1000,
      reply = `${run.kind === "model" ? "the model's" : "the controller's"} ${now.current < 0 ? "first" : "next"} reply`;
    return s < 0.1 ? `Asking for ${reply}` : `Waiting ${s.toFixed(1)} s for ${reply}`;
  };
  function statusLine(now) {
    // A commander's unit skills reply every fraction of a second; its plans carry the timing.
    if (now.pending < 0 || planned()) return null;
    const d = r.decisions[now.pending],
      line = el("p", null, "status-line");
    if (d.applied_ms == null && time >= end)
      line.append(
        `The battle ended before the reply requested at ${clock(requested(d))} was applied.`,
      );
    else line.append(el("span", waiting(now), "waiting"));
    return line;
  }

  function unitButton(entry) {
    const node = button(entry.display, () => select(entry.id), "who");
    node.title = `Select ${entry.display} on the map`;
    return node;
  }
  function jumpButton(t) {
    const node = button(clock(t), () => jump(t), "jump");
    node.setAttribute("aria-label", `Jump to ${clock(t)}`);
    return node;
  }
  const pre = (text) => el("pre", text, "raw");

  // Panel folds stay as the reader left them when the next decision is shown.
  const openFolds = new Set();
  function fold(summary, ...content) {
    const node = details(summary, ...content);
    node.open = openFolds.has(summary);
    node.addEventListener("toggle", () =>
      node.open ? openFolds.add(summary) : openFolds.delete(summary),
    );
    return node;
  }

  function explanation(d) {
    const section = el("section");
    if (d.reason) {
      section.append(el("blockquote", `“${d.reason}”`));
      // The model names units by their raw ids; the quotation stays verbatim.
      const named = [...new Set(d.reason.match(/\b[ef]\d+\b/g))]
        .map((id) => roster.get(id))
        .filter(Boolean)
        .map((u) => `${u.id} = ${u.display}${u.short !== u.display ? ` (${u.short})` : ""}`);
      if (named.length) section.append(el("p", `In this quotation: ${named.join(", ")}`, "note"));
      if (d.notes_changed)
        section.append(
          fold(
            "Its battle notes changed",
            el("p", "Before", "note"),
            pre(d.notes_before ?? "(none)"),
            el("p", "After", "note"),
            pre(d.notes ?? "(none)"),
          ),
        );
    } else if (run.kind === "model")
      section.append(el("p", "No reason was recorded with this reply.", "muted"));
    else
      section.append(
        el("h4", "The controller's rule"),
        el("p", run.rule || "A scripted rule; it states no reasons."),
      );
    return section;
  }

  function ordersSection(d) {
    const section = el("section");
    section.append(el("h4", "Orders given"));
    if (d.invalid) {
      const list = el("ul", null, "orders");
      list.append(
        el("li", `Refused by validation before reaching the game: ${d.invalid.error}`, "rejected"),
      );
      section.append(list, el("p", "No orders reached the game; earlier orders continue.", "note"));
      return section;
    }
    const list = el("ul", null, "orders");
    for (const line of d.summary) {
      const ability = d.steps.some(
        (s) => s.unit === line.unit && s.kind === "ability" && ACCEPTED.includes(s.status),
      );
      const item = el("li", null, `${line.status}${ability ? " ability" : ""}`),
        entry = roster.get(line.unit);
      const prefix = entry ? `${entry.display}: ` : null;
      if (prefix && line.text.startsWith(prefix))
        item.append(unitButton(entry), `: ${line.text.slice(prefix.length)}`);
      else item.append(line.text);
      if (line.status === "unacknowledged")
        item.append(el("span", "No acknowledgement recorded.", "status"));
      list.append(item);
    }
    section.append(list);
    return section;
  }

  // Folded: facts from the frames after the orders, with the one caveat they need.
  function nextSection(d) {
    const list = el("ul", null, "facts");
    for (const fact of d.next) {
      const item = el("li");
      item.append(jumpButton(fact.time_ms), el("span", fact.text));
      list.append(item);
    }
    if (d.next_truncated)
      list.append(
        el(
          "li",
          `${d.next_truncated} more observation${d.next_truncated > 1 ? "s" : ""} not listed.`,
          "muted",
        ),
      );
    return fold(
      "What happened next",
      list,
      el(
        "p",
        "Observed in the recorded frames; timing alone does not show the order caused it.",
        "note",
      ),
    );
  }

  function ageSection(d, i) {
    const section = el("section");
    if (d.age_s == null) {
      section.append(el("p", "Not measured: no acknowledgement was recorded for this reply."));
      return section;
    }
    const sentence = el("p", null, "age-sentence");
    if (d.plan_age_s != null)
      sentence.append(
        "Plan made from a view ",
        el("strong", `${seconds(d.plan_age_s)} old`),
        `; unit skills act on fresh views (${seconds(d.age_s)}).`,
      );
    else if (planned())
      sentence.append(
        "Unit skills, from a view ",
        el("strong", `${seconds(d.age_s)} old`),
        ", follow the model's latest plan.",
      );
    else
      sentence.append(
        "Acted on a view ",
        el("strong", `${seconds(d.age_s)} old`),
        ` when the game accepted ${d.steps.length ? "these orders" : "this reply"}.`,
      );
    section.append(sentence);
    // What moved while it waited: for a commander, Model's view shows its plan's view instead.
    if (!planned() && d.basis_frame != null && d.after_frame != null) {
      if (pinned === i) {
        const moved = d.displacements
          .filter((m) => inspectUnits(d).has(m.unit))
          .sort((a, b) => b.metres - a.metres);
        const list = el("ul", null, "displacements");
        for (const m of moved)
          list.append(
            el("li", `${roster.get(m.unit)?.display || m.unit} moved ${Math.round(m.metres)} m`),
          );
        section.append(
          el("p", "While the reply was being generated:", "note"),
          list,
          el(
            "p",
            "Lines join two recorded positions; the path between them is not recorded.",
            "note",
          ),
        );
      } else section.append(button("See what moved while it waited", () => pin(i), "inspect"));
    }
    return section;
  }

  const signed = (value) => `${value < 0 ? "−" : ""}${Math.abs(value).toFixed(2)} s`;
  function technical(d) {
    const out = [];
    if (d.prompt || d.attempts.some((a) => a.text)) {
      const replies = d.attempts.flatMap((a, k) => [
        el("p", d.attempts.length > 1 ? `Reply, attempt ${k + 1}` : "Reply", "note"),
        pre(a.text ?? "Not recorded"),
      ]);
      out.push(
        fold(
          "Exact message and reply",
          el("p", "Prompt", "note"),
          pre(d.prompt ?? "Not recorded"),
          ...replies,
        ),
      );
    }
    const parts = d.latency_parts || {},
      usage = d.attempts.map((a) => a.usage || {});
    const sum = (pick) =>
      usage.length && usage.every((u) => pick(u) != null)
        ? usage.reduce((n, u) => n + pick(u), 0).toLocaleString("en")
        : null;
    const usd =
      d.attempts.length && d.attempts.every((a) => a.usd != null)
        ? d.attempts.reduce((n, a) => n + a.usd, 0)
        : null;
    out.push(
      fold(
        "Technical timing and cost",
        keyValues([
          ["View seen (battle clock)", clockTenths(d.time_ms)],
          ["Accepted (battle clock)", d.applied_ms == null ? null : clockTenths(d.applied_ms)],
          ["Reply (wall clock)", d.reply_s == null ? null : seconds(d.reply_s)],
          ["Provider processing", parts.provider_s == null ? null : seconds(parts.provider_s)],
          [
            "Call minus provider",
            parts.transport_residual_s == null
              ? null
              : `${signed(parts.transport_residual_s)} (${parts.transport_residual_s < 0 ? "provider-reported time exceeds the measured call" : "residual: transport and client overhead, not measured network time"})`,
          ],
          [
            "Round trip minus reply",
            parts.harness_roundtrip_residual_s == null
              ? null
              : `${signed(parts.harness_roundtrip_residual_s)} (residual: game tick, mailbox and polling)`,
          ],
          ["Attempts", d.attempts.length || null],
          ["Input tokens", sum((u) => u.input_tokens)],
          ["Cached input tokens", sum((u) => u.input_tokens_details?.cached_tokens)],
          ["Output tokens", sum((u) => u.output_tokens)],
          ["Reasoning tokens", sum((u) => u.output_tokens_details?.reasoning_tokens)],
          ["Cost", usd == null ? null : money(usd)],
          [
            "Model reported",
            [...new Set(d.attempts.map((a) => a.actual_model).filter(Boolean))].join(", "),
          ],
        ]),
      ),
    );
    if (d.invalid)
      out.push(
        fold(
          "Validation refused these orders",
          el("p", "The harness refused this reply's orders before they reached the game.", "note"),
          pre(json(d.invalid)),
        ),
      );
    return out;
  }

  function decisionView(i) {
    const d = r.decisions[i],
      head = el("div", null, "decision-head");
    head.append(
      el(
        "h3",
        d.invalid
          ? `Reply at ${clock(d.applied_ms)}: orders refused by validation`
          : d.steps.length
            ? `Orders issued at ${clock(d.applied_ms)}`
            : `Reply at ${clock(d.applied_ms)}: no new orders`,
      ),
    );
    if (!d.invalid && !d.summary.length)
      head.title = "Earlier orders, queued steps included, continue.";
    // What it ordered and why first; how old its information was after. A commander's unit
    // skill ticks carry no reasons of their own.
    const parts = [head];
    if (!(planned() && d.plan_age_s == null && !d.reason)) parts.push(explanation(d));
    if (d.invalid || d.summary.length) parts.push(ordersSection(d));
    if (d.next?.length) parts.push(nextSection(d));
    parts.push(ageSection(d, i), ...technical(d));
    return parts;
  }

  function stateWords(u) {
    if (u.men === 0) return "destroyed";
    const words = [];
    if (has(u, "shattered")) words.push("shattered (will not rally)");
    else if (has(u, "routing")) words.push("fleeing");
    else if (has(u, "wavering")) words.push("wavering");
    if (has(u, "melee")) words.push("fighting in melee");
    if (has(u, "under_fire")) words.push("under fire");
    if (!words.length)
      words.push(
        has(u, "running")
          ? "running"
          : has(u, "moving")
            ? "moving"
            : has(u, "idle")
              ? "idle"
              : !u.state
                ? "no state recorded"
                : u.state.join(", ") || "no state flag reported",
      );
    return words.join(", ");
  }
  const STATS = [
    ["speed", "Speed"],
    ["armour", "Armour"],
    ["charge_bonus", "Charge bonus"],
    ["melee_attack", "Melee attack"],
    ["melee_defence", "Melee defence"],
    ["weapon_damage", "Weapon damage"],
    ["morale", "Leadership"],
    ["ammo", "Ammunition per soldier"],
    ["range_m", "Range (m)"],
  ];

  function unitCard(id, fi) {
    const entry = roster.get(id),
      frame = r.frames[fi],
      u = unitIn(frame, id);
    const card = el("section", null, `unit-card ${entry.side}`),
      head = el("header"),
      title = el("div");
    title.append(
      el("h3", entry.display),
      el("p", `${entry.role}, ${entry.side === "friendly" ? "friendly" : "enemy"}, ${entry.short}`),
    );
    head.append(
      glyph(entry.glyph),
      title,
      button("Clear selection", () => select(null)),
    );
    card.append(head);
    if (entry.about) card.append(el("p", entry.about, "about"));
    const tags = [
      entry.commander && "Army general",
      entry.protected && "Protected unit: the scenario tracks its survival",
    ].filter(Boolean);
    if (tags.length) card.append(el("p", tags.join(", "), "note"));
    const now = el("p", null, "now");
    const dead = frame.enemy_roster.some((item) => item.id === id && item.dead);
    if (u) {
      const parts = [capital(stateWords(u))];
      if (u.men0 > 1) parts.push(`${u.men} of ${u.men0} soldiers`);
      if (Number.isFinite(u.hp)) parts.push(`health ${Math.round(u.hp * 100)}%`);
      if (u.ammo0 > 0)
        parts.push(`ammunition left ${Math.round((100 * u.ammo) / u.ammo0)}% of starting supply`);
      now.append(el("strong", `At ${clock(frame.time_ms)}: `), parts.join(", "));
    } else {
      const point = targetAt(id, fi);
      now.append(
        el("strong", `At ${clock(frame.time_ms)}: `),
        dead
          ? "destroyed"
          : point
            ? `not visible to the army; last seen at ${clock(point.t)}`
            : "not observed yet",
      );
    }
    card.append(now);
    if (entry.side === "friendly") {
      const i = latestOrders(id, time, true),
        line = i != null && r.decisions[i].summary.find((item) => item.unit === id);
      const text = line ? line.text.replace(`${entry.display}: `, "") : null;
      const orders = el("p", null, "now");
      orders.append(
        el("strong", "Standing orders: "),
        text ? `${text} (issued ${clock(r.decisions[i].applied_ms)})` : "none issued yet",
      );
      card.append(orders);
    } else card.append(el("p", "Commanded by the game's AI.", "note"));
    if (entry.stats) {
      const stats = el("dl", null, "stats");
      for (const [key, label] of STATS)
        if (entry.stats[key] != null) {
          const item = el("div");
          item.append(el("dt", label), el("dd", String(entry.stats[key])));
          stats.append(item);
        }
      card.append(stats, el("p", "Base values recorded from the game at battle setup.", "note"));
    }
    return card;
  }

  function renderPanel(fi, now) {
    const shown = pinned ?? (now.current >= 0 ? now.current : null);
    const key = [shown, now.pending, pinned, selected, selected ? fi : "", time >= end].join("|");
    // Between decisions only the waiting counter changes: update it in place, so the panel's
    // buttons and folds keep working during playback.
    if (key === keys.panel) {
      const counter = $("moment").querySelector(".waiting");
      if (counter && now.pending >= 0) counter.textContent = waiting(now);
      return;
    }
    keys.panel = key;
    const box = $("moment");
    box.replaceChildren();
    if (selected) box.append(unitCard(selected, fi));
    if (pinned != null) {
      const line = el("div", null, "pinned-line");
      line.append(
        el("span", `Pinned: decision issued at ${clock(r.decisions[pinned].applied_ms)}`),
        button("Back to playback", () => unpin()),
      );
      box.append(line);
    } else {
      const line = statusLine(now);
      if (line) box.append(line);
    }
    if (shown == null) {
      box.append(
        el(
          "p",
          now.pending >= 0
            ? "No orders have reached the game yet. The battle keeps running while the first reply is generated."
            : "The armies are deploying; no decision has been requested yet.",
          "muted",
        ),
      );
      return;
    }
    box.append(...decisionView(shown));
  }

  // Order of battle under the map: one line per unit type with its role; duplicates are
  // grouped, and each regiment stays selectable by its map label.
  function renderRoster() {
    const box = $("roster");
    box.replaceChildren();
    chips = new Map();
    const role = r.frames.find((f) => f.mode?.role)?.mode.role;
    const chip = (entry, className, ...content) => {
      const node = button(
        "",
        () => select(entry.id === selected ? null : entry.id, true),
        className,
      );
      node.append(...content);
      node.title = `${entry.display}, ${entry.role}`;
      node.setAttribute("aria-label", `${entry.display}, ${entry.role}`);
      chips.set(entry.id, node);
      return node;
    };
    for (const side of ["friendly", "enemy"]) {
      const units = r.roster.filter((entry) => entry.side === side);
      if (!units.length) continue;
      const column = el("section", null, `roster-side ${side}`),
        heading = el("h3"),
        list = el("ul");
      const sideRole =
        role && (side === "friendly" ? role : role === "attacker" ? "defender" : "attacker");
      heading.append(
        el("span", null, `swatch ${side}`),
        `${side === "friendly" ? "Friendly" : "Enemy"} army${sideRole ? `, ${sideRole}` : ""}`,
      );
      const groups = new Map();
      for (const entry of units) groups.set(entry.name, [...(groups.get(entry.name) || []), entry]);
      for (const [name, group] of groups) {
        const [first] = group,
          item = el("li"),
          names = el("span", null, "names"),
          title = el("span", group.length > 1 ? `${name} ×${group.length}` : first.display);
        if (group.length === 1 && first.short !== first.display)
          title.append(" ", el("span", first.short, "code"));
        names.append(title, el("small", first.role));
        if (group.length > 1) {
          const label = el("span", null, "group");
          label.append(glyph(first.glyph), names);
          item.append(label, ...group.map((entry) => chip(entry, "code-chip", entry.short)));
        } else item.append(chip(first, "unit-chip", glyph(first.glyph), names));
        list.append(item);
      }
      column.append(heading, list);
      box.append(column);
    }
  }

  function updateRoster(fi) {
    const frame = r.frames[fi];
    for (const [id, chip] of chips) {
      const u = unitIn(frame, id),
        dead = u?.men === 0 || frame.enemy_roster.some((item) => item.id === id && item.dead);
      chip.classList.toggle("down", Boolean(dead));
      chip.classList.toggle("fleeing", !dead && (has(u, "routing") || has(u, "shattered")));
      chip.setAttribute("aria-pressed", String(id === selected));
    }
  }

  // The note marked now: the watched one, else the latest begun one whose window holds the time.
  const activeHighlight = () =>
    watched()
      ? watching.k
      : markedAt(
          r.highlights.map((h) => ({ ...span(h), at: h.time_ms })),
          time,
        );

  // How old the view behind the latest reply is now, on the battle clock.
  function lagLine(now) {
    if (!lag || pinned != null) return null;
    const view = viewOf(now);
    if (!view) return "No reply has reached the game yet.";
    const age = ((time - view.at) / 1000).toFixed(1);
    return view.d.plan_age_s != null
      ? `Outlines: where units stood ${age} s ago, in the view behind the model's current plan.`
      : `Outlines: where units stood ${age} s ago, in the view behind the latest reply.`;
  }

  function renderOverlays(fi, now) {
    const caption = $("map-caption"),
      status = $("map-status"),
      frame = r.frames[fi];
    caption.classList.toggle("pinned", pinned != null);
    if (pinned != null) {
      const d = r.decisions[pinned];
      caption.textContent = `The reply applied at ${clockTenths(d.applied_ms)}: outlines where the model saw units (${clockTenths(r.frames[d.basis_frame].time_ms)}), solid where they were next recorded (${clockTenths(r.frames[d.after_frame].time_ms)})`;
      caption.hidden = false;
    } else {
      const k = activeHighlight();
      caption.textContent = k >= 0 ? `Note ${k + 1}: ${r.highlights[k].title}` : "";
      caption.hidden = k < 0;
    }
    const gap = pinned == null && time - frame.time_ms > gapMs;
    status.textContent = gap
      ? `No observation recorded during this interval; showing ${clockTenths(frame.time_ms)}`
      : "";
    status.hidden = !gap;
    const line = lagLine(now);
    $("map-lag").textContent = line || "";
    $("map-lag").hidden = !line;
    $("lag-toggle").setAttribute("aria-pressed", String(lag));
    $("map").classList.toggle("lagging", lag && pinned == null);
    const chip = $("map-selection");
    if (keys.selection !== selected) {
      keys.selection = selected;
      chip.replaceChildren();
      const entry = selected && roster.get(selected);
      if (entry) {
        const text = el("span");
        text.append(el("strong", entry.display), el("span", `, ${entry.role}`, "role"));
        chip.append(
          glyph(entry.glyph),
          text,
          button("Clear", () => select(null)),
        );
        chip.querySelector("svg").style.color = TEAM[entry.side];
      }
      chip.hidden = !entry;
    }
  }

  function render() {
    if (!r || !proj) return;
    const fi = frameIndex(),
      now = momentAt(time);
    renderOverlays(fi, now); // first: the inspect framing depends on its caption's height
    if (framed !== pinned) reframe();
    renderMap(fi, now);
    renderPanel(fi, now);
    updateRoster(fi);
    $("scrubber").value = time / 1000;
    $("clock").textContent = `${clock(time)} / ${clock(end)}`;
    const x = stripX(time);
    $("strip-cursor").setAttribute("x1", x);
    $("strip-cursor").setAttribute("x2", x);
    for (const listener of listeners) listener(time);
  }

  // The one button with an icon.
  function updatePlay() {
    const icon = svg("svg", { viewBox: "0 0 16 16", class: "play-icon", "aria-hidden": "true" });
    icon.append(
      svg("path", { d: playing ? "M3 2h3.6v12H3zM9.4 2H13v12H9.4z" : "M4 2l10 6-10 6z" }),
    );
    $("play").replaceChildren(icon, playing ? "Pause" : "Play");
    $("play").setAttribute("aria-label", playing ? "Pause" : "Play");
  }
  function play() {
    if (!r) return;
    if (time >= end) {
      time = start;
      watching = null;
    }
    pinned = null;
    if (!playing) lastTick = null;
    playing = true;
    loop ??= requestAnimationFrame(tick); // animation frames run only while playing
    updatePlay();
    render();
  }
  function pause() {
    playing = false;
    until = null;
    updatePlay();
  }
  function toggle() {
    if (playing) pause();
    else play();
  }
  // Every move of the time by hand (scrubber, timeline strip, buttons, keys, lists) ends a watch.
  function seek(t) {
    if (!r) return;
    time = Math.max(start, Math.min(end, t));
    until = null;
    pinned = null;
    watching = null;
    render();
  }
  const reveal = () => $("map-wrap").scrollIntoView({ block: "start" }); // the panel follows
  function jump(t, intoView = false) {
    pause();
    seek(t);
    if (intoView) reveal();
  }
  const goDecision = (i) => jump(r.decisions[i].applied_ms);
  function stepDecision(direction) {
    if (!r) return;
    const applied = r.decisions.map((d, i) => [d.applied_ms, i]).filter(([t]) => t != null);
    const target =
      direction > 0 ? applied.find(([t]) => t > time + 1) : applied.findLast(([t]) => t < time - 1);
    if (target) goDecision(target[1]);
  }
  function stepEvent(direction) {
    if (!r) return;
    const e =
      direction > 0
        ? r.events.find((item) => item.time_ms > time + 1)
        : r.events.findLast((item) => item.time_ms < time - 1);
    if (e) jump(e.time_ms);
  }
  function pin(i) {
    pause();
    time = r.decisions[i].applied_ms;
    pinned = i;
    watching = null;
    render();
    $("moment").scrollTop = 0;
    $("map-wrap").scrollIntoView({ block: "nearest" });
  }
  function unpin() {
    pinned = null;
    render();
  }
  // Roster and note chips bring the selection into view; map clicks do not.
  function select(id, intoView = false) {
    selected = id && roster.has(id) ? id : null;
    keys.map = keys.panel = null;
    render();
    if (selected) $("moment").scrollTop = 0;
    if (selected && intoView) reveal();
  }
  function setLag(on) {
    lag = Boolean(on) && !$("lag-toggle").disabled;
    keys.map = null;
    render();
  }
  // Play from `from` at 4× and stop at `to` when given: the battle itself ran at 1×. Watching
  // analyst note k keeps its units bright and its caption shown; a key event dims nothing.
  function watch(from, to = null, k = null, intoView = true) {
    if (!r) return;
    pinned = null;
    speed = 4;
    $("speed").value = "4";
    time = Math.max(start, Math.min(end, from));
    const note = k != null ? r.highlights[k] : null;
    watching = note && { k, ids: new Set(note.units || []), from: time, to: span(note).to };
    keys.map = null;
    play();
    until = to;
    if (intoView) reveal();
  }
  function tick(now) {
    loop = null;
    if (!playing || !r) return;
    if (lastTick != null) {
      time += (now - lastTick) * speed;
      const stop = Math.min(end, until ?? Infinity);
      if (time >= stop) {
        time = stop;
        pause();
      }
      render();
    }
    lastTick = now;
    if (playing) loop = requestAnimationFrame(tick);
  }

  function setup() {
    $("play").addEventListener("click", toggle);
    $("prev-decision").addEventListener("click", () => stepDecision(-1));
    $("next-decision").addEventListener("click", () => stepDecision(1));
    $("prev-event").addEventListener("click", () => stepEvent(-1));
    $("next-event").addEventListener("click", () => stepEvent(1));
    $("speed").addEventListener("change", (e) => {
      speed = Number(e.target.value);
    });
    $("whole").addEventListener("change", layout);
    $("lag-toggle").addEventListener("click", () => setLag(!lag));
    $("scrubber").addEventListener("input", (e) => seek(Number(e.target.value) * 1000));
    $("map").addEventListener("click", (e) => {
      const node = e.target.closest?.("[data-unit]");
      if (node && pinned == null) select(node.dataset.unit === selected ? null : node.dataset.unit);
    });
    // Hovering a marker names it on a crowded map.
    const hover = (id) => {
      if (id === hovered) return;
      hovered = id;
      keys.map = null;
      if (r) render();
    };
    $("map").addEventListener("pointerover", (e) =>
      hover(e.target.closest?.("[data-unit]")?.dataset.unit ?? null),
    );
    $("map").addEventListener("pointerleave", () => hover(null));
    const node = $("strip");
    node.addEventListener("pointerdown", (e) => {
      if (!r) return;
      dragging = true;
      node.setPointerCapture(e.pointerId);
      stripPointer(e, true);
    });
    node.addEventListener("pointermove", (e) => {
      if (dragging) stripPointer(e, false);
    });
    for (const type of ["pointerup", "pointercancel"])
      node.addEventListener(type, () => {
        dragging = false;
      });
    document.addEventListener("keydown", (e) => {
      if (!r || e.altKey || e.ctrlKey || e.metaKey || document.querySelector("dialog[open]"))
        return;
      const target = e.target,
        tag = target.tagName;
      if (["INPUT", "SELECT", "TEXTAREA"].includes(tag)) return;
      if (target !== document.body && !$("watch").contains(target)) return;
      if (e.key === " " && ["BUTTON", "SUMMARY", "A"].includes(tag)) return;
      const action = {
        " ": toggle,
        ArrowLeft: () => stepDecision(-1),
        ArrowRight: () => stepDecision(1),
        "[": () => stepEvent(-1),
        "]": () => stepEvent(1),
      }[e.key];
      if (action) {
        e.preventDefault();
        action();
      }
    });
    new ResizeObserver(() => {
      if (r && Math.round($("map-wrap").clientWidth) !== mapWidth) layout();
    }).observe($("map-wrap"));
    addEventListener("resize", () => r && layout());
  }
  setup();
  return {
    show,
    clear,
    seek,
    reveal,
    watch,
    setLag,
    onTime: (listener) => listeners.push(listener),
    get time() {
      return time;
    },
    // The analyst note the map caption shows, or -1.
    get note() {
      return r ? activeHighlight() : -1;
    },
  };
})();
