"use strict";
const data = JSON.parse(document.getElementById("graph-data").textContent);
const $ = (id) => document.getElementById(id);
const skillOps = new Set(["engage", "charge", "shoot", "move", "hold"]);
const labels = {
  owned: "Find available units",
  select_target: "Choose visible enemy",
  contact: "Observe melee contact",
  engage: "Engage selected enemy",
  charge: "Charge selected enemy",
  shoot: "Shoot selected enemy",
  move: "Move to point",
  hold: "Hold near point",
  end: "End graph",
};
const clock = (ms) =>
  `${Math.floor(ms / 60000)}:${((Math.floor(ms / 100) / 10) % 60).toFixed(1).padStart(4, "0")}`;
const ns = "http://www.w3.org/2000/svg";
function svg(tag, attrs, text) {
  const el = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs || {})) el.setAttribute(key, value);
  if (text !== undefined) el.textContent = text;
  return el;
}
function options(element, values) {
  element.replaceChildren(...values.map(([value, text]) => new Option(text, value)));
}
let episode,
  member,
  selected = -1,
  visible = [],
  time = 0,
  cutoff = Infinity,
  animation = null,
  previousTick;
function caption(e) {
  const name = labels[e.op] || labels[episode.graphs[e.member].nodes[e.node]?.op] || e.node;
  if (e.kind === "orders")
    return `${e.orders.length} order${e.orders.length === 1 ? "" : "s"} dispatched`;
  if (e.kind === "ack") {
    if (e.ack.accepted === false || e.ack.validation_error || e.ack.results.some((r) => !r.ok))
      return "Order refused";
    if (e.missing_result_indexes?.length)
      return `Partial acknowledgement: ${e.ack.results.length} of ${e.orders_expected} order results`;
    return e.ack.results.length
      ? "Order accepted by engine"
      : "Acknowledgement has no per-order result";
  }
  if (e.kind === "started") return `${name} started`;
  if (e.kind === "transition") {
    if (e.op === "contact")
      return e.status === "yes" ? "Visible melee contact observed" : "No visible melee contact";
    if (skillOps.has(e.op))
      return `${name}: ${e.status === "succeeded" ? "graph reported completion" : e.status}`;
    if (e.op === "owned") return `Available units: ${(e.outputs.units || []).join(", ") || "none"}`;
    if (e.op === "select_target") return `Selected enemy: ${e.outputs.target || "none"}`;
    return `${name}: ${e.status}`;
  }
  if (e.kind === "cancelled") return "Graph cancelled locally; no halt order sent";
  if (e.kind === "exhausted") return "Graph visit limit reached";
  return "Graph closed";
}
function before(e) {
  return e.time_ms < time || (e.time_ms === time && e.line <= cutoff);
}
function stateAt() {
  let state = { status: "waiting", node: null },
    last = null;
  for (const e of episode.events) {
    if (e.member !== member || !before(e)) continue;
    if (e.kind === "started")
      state = { status: "running", node: e.node, run: e.node_run, event: e };
    if (e.kind === "transition") {
      state = { status: "ready", node: e.successor, event: e };
      last = e;
    }
    if (["closed", "cancelled", "exhausted"].includes(e.kind))
      state = { status: e.kind, node: e.node, event: e };
  }
  return { ...state, last };
}
function graph(state) {
  const spec = episode.graphs[member],
    names = [],
    positions = {};
  function visit(name) {
    if (names.includes(name)) return;
    names.push(name);
    const exits = spec.nodes[name].next;
    for (const key of ["succeeded", "yes", ...Object.keys(exits)])
      if (exits[key]) visit(exits[key]);
  }
  visit(spec.entry);
  names.forEach((name, i) => {
    positions[name] = [(i % 2) * 290 + 25, Math.floor(i / 2) * 80 + 25];
  });
  const canvas = $("graph"),
    height = Math.max(210, Math.ceil(names.length / 2) * 80 + 25);
  canvas.setAttribute("viewBox", `0 0 620 ${height}`);
  canvas.style.height = `${Math.max(245, height)}px`;
  canvas.replaceChildren();
  const defs = svg("defs"),
    marker = svg("marker", {
      id: "arrow",
      viewBox: "0 0 10 10",
      refX: 9,
      refY: 5,
      markerWidth: 5,
      markerHeight: 5,
      orient: "auto-start-reverse",
    });
  marker.append(svg("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#a5b6a4" }));
  defs.append(marker);
  canvas.append(defs);
  for (const name of names) {
    const [x, y] = positions[name];
    for (const next of new Set(Object.values(spec.nodes[name].next))) {
      const exit = Object.keys(spec.nodes[name].next)
        .filter((key) => spec.nodes[name].next[key] === next)
        .join("/");
      const [nx, ny] = positions[next],
        right = nx > x,
        same = name === next;
      const ax = x + (right || same ? 245 : 0),
        bx = nx + (right ? 0 : 245);
      const path = same
        ? `M${x + 245},${y + 12} C${x + 285},${y - 15} ${x + 285},${y + 65} ${x + 245},${y + 36}`
        : `M${ax},${y + 24} C${ax + (right ? 22 : -22)},${y + 24} ${bx + (right ? -22 : 22)},${ny + 24} ${bx},${ny + 24}`;
      const active = state.last?.node === name && state.last.successor === next;
      canvas.append(
        svg("path", {
          d: path,
          class: "edge",
          "marker-end": "url(#arrow)",
          style: active ? "stroke:#26765f;stroke-width:2.2" : "",
        }),
      );
      if (same)
        canvas.append(
          svg("text", { x: x + 285, y: y + 55, class: "edge-label", "text-anchor": "end" }, exit),
        );
    }
  }
  for (const name of names) {
    const [x, y] = positions[name],
      node = spec.nodes[name];
    const status = state.node === name ? (state.status === "ready" ? "next" : state.status) : "";
    const ended =
      state.last?.node === name ? (state.last.status === "failed" ? "failed" : "finished") : "";
    const g = svg("g", {
      class: `node ${status} ${ended}`,
      "data-node": name,
      "data-state": status,
    });
    g.append(svg("rect", { x, y, width: 245, height: 48, rx: 7 }));
    g.append(svg("text", { x: x + 12, y: y + 20 }, labels[node.op] || node.op));
    const full = `${name} · ${Object.entries(node.next)
      .map(([exit, next]) => `${exit} → ${next}`)
      .join("; ")}`;
    const note = svg("text", { x: x + 12, y: y + 37, class: "id" }, full);
    g.append(svg("title", {}, full));
    g.append(note);
    canvas.append(g);
    let short = full;
    while (note.getComputedTextLength() > 221 && short.length > 1) {
      short = short.slice(0, -1);
      note.textContent = `${short}…`;
    }
  }
  $("state").dataset.status = state.status;
  $("state").dataset.node = state.node || "";
  $("state").textContent =
    state.status === "waiting"
      ? "No graph start recorded yet."
      : state.status === "ready"
        ? `${labels[spec.nodes[state.last.node].op]}: ${state.last.status}. Next: ${state.node}; not started yet.`
        : state.status === "running"
          ? `${labels[spec.nodes[state.node].op]} is running (node run ${state.run}).`
          : `${state.status}. This graph state does not mean its units have stopped.`;
}
function frameAt() {
  return episode.frames
    .filter((f) => f.time_ms < time || (f.time_ms === time && f.source.line <= cutoff))
    .at(-1);
}
function isOwned(unit) {
  const kinds = episode.ownership[member];
  return kinds
    ? kinds.includes(unit.type)
    : !Object.values(episode.ownership).some((ks) => ks?.includes(unit.type));
}
function map() {
  const canvas = $("map"),
    frame = frameAt();
  canvas.replaceChildren();
  if (!frame) {
    $("frame-time").textContent = "No public frame collected yet.";
    return;
  }
  $("frame-time").textContent =
    `Observation ${frame.seq} at ${clock(frame.time_ms)} · trace row ${frame.source.line}. View fits the current units; no interpolation.`;
  const units = [...frame.friendly, ...frame.enemy].filter(
    (u) => Number.isFinite(u.x) && Number.isFinite(u.z),
  );
  const xs = units.map((u) => u.x),
    zs = units.map((u) => u.z);
  const minX = Math.min(0, ...xs) - 25,
    maxX = Math.max(0, ...xs) + 25;
  const minZ = Math.min(0, ...zs) - 25,
    maxZ = Math.max(0, ...zs) + 25;
  const scale = Math.min(240 / (maxX - minX), 290 / (maxZ - minZ));
  const point = (u) => [
    170 + (u.x - (minX + maxX) / 2) * scale,
    185 - (u.z - (minZ + maxZ) / 2) * scale,
  ];
  const event = episode.events[selected];
  if (event?.kind === "orders")
    for (const order of event.orders) {
      const from = frame.friendly.find((u) => u.id === order.unit);
      const to = order.type === "move" ? order : frame.enemy.find((u) => u.id === order.target);
      if (from && to && [from.x, from.z, to.x, to.z].every(Number.isFinite)) {
        const [x1, y1] = point(from),
          [x2, y2] = point(to);
        canvas.append(
          svg("line", {
            x1,
            y1,
            x2,
            y2,
            stroke: "#a6b592",
            "stroke-dasharray": "5 4",
            "stroke-width": 1.5,
          }),
        );
      }
    }
  let legendRow = 0;
  for (const side of ["friendly", "enemy"]) {
    const sideUnits = frame[side]
      .filter((u) => [u.x, u.z].every(Number.isFinite))
      .sort((a, b) => point(a)[1] - point(b)[1]);
    const labelY = [];
    for (const u of sideUnits) labelY.push(Math.max(point(u)[1], (labelY.at(-1) ?? 10) + 24));
    for (let i = labelY.length - 1; i >= 0; i--)
      labelY[i] = Math.min(labelY[i], i === labelY.length - 1 ? 340 : labelY[i + 1] - 24);
    for (const [i, u] of sideUnits.entries()) {
      const [x, y] = point(u),
        owned = side === "friendly" && isOwned(u);
      const color = side === "enemy" ? "#ad6053" : "#26765f";
      const group = svg("g", {
        transform: `translate(${x},${y})`,
        "data-unit": u.id,
        "data-x": u.x,
        "data-z": u.z,
      });
      group.append(
        svg(
          "title",
          {},
          `${u.name} (${u.id}) · ${u.men ?? "?"} soldiers · ${(u.state || []).join(", ")}`,
        ),
      );
      group.append(
        side === "enemy"
          ? svg("path", { d: "M0,-8 l8,8 l-8,8 l-8,-8z", fill: color })
          : svg("circle", {
              cx: 0,
              cy: 0,
              r: 7,
              fill: owned ? color : "#fff",
              stroke: color,
              "stroke-width": 2,
            }),
      );
      const labelX = side === "friendly" ? 22 : 310;
      canvas.append(
        svg("line", {
          x1: x,
          y1: y,
          x2: labelX + (side === "friendly" ? 20 : -10),
          y2: labelY[i] - 3,
          stroke: color,
          "stroke-opacity": 0.4,
        }),
      );
      canvas.append(svg("text", { x: labelX, y: labelY[i], class: "map-label" }, u.id));
      canvas.append(group);
      const rowY = 45 + legendRow++ * 57;
      canvas.append(
        svg(
          "text",
          { x: 350, y: rowY, class: "map-label", style: `fill:${color}` },
          `${u.id} · ${u.name}`,
        ),
      );
      canvas.append(
        svg(
          "text",
          { x: 350, y: rowY + 17, class: "map-label map-state" },
          `${u.men ?? "?"} soldiers`,
        ),
      );
      canvas.append(
        svg(
          "text",
          { x: 350, y: rowY + 32, class: "map-label map-state" },
          (u.state || []).join(", ") || "state unavailable",
        ),
      );
    }
  }
}
function fillEvents() {
  visible = episode.events
    .map((e, i) => [e, i])
    .filter(
      ([e]) =>
        e.member === member &&
        ($("filter").value === "all" ||
          ["orders", "ack", "closed", "cancelled", "exhausted"].includes(e.kind) ||
          (e.kind === "transition" &&
            (skillOps.has(e.op) || (e.op === "contact" && e.status === "yes")))),
    )
    .map(([, i]) => i);
  options(
    $("events"),
    visible.map((i) => [i, `${clock(episode.events[i].time_ms)} · ${caption(episode.events[i])}`]),
  );
  Array.from($("events").options).forEach((option) => {
    option.dataset.line = episode.events[Number(option.value)].line;
  });
}
function seek(value, eventIndex = null) {
  time = Math.max(Number($("time").min), Math.min(Number($("time").max), Number(value)));
  cutoff = eventIndex === null ? Infinity : episode.events[eventIndex].line;
  selected = eventIndex ?? visible.filter((i) => episode.events[i].time_ms <= time).at(-1) ?? -1;
  $("time").value = time;
  $("clock").textContent = clock(time);
  $("events").value = selected;
  const e = episode.events[selected];
  $("caption").textContent = e ? caption(e) : "No selected event yet";
  $("event-time").textContent = e
    ? `Shown at ${clock(e.time_ms)} · source observation ${e.source.seq} at ${clock(e.source.time_ms)} · trace row ${e.line}`
    : "";
  $("evidence").textContent = e
    ? e.kind === "ack"
      ? `Engine acknowledgement only. This does not complete the skill.${e.missing_result_indexes?.length ? ` Missing results for order indexes ${e.missing_result_indexes.join(", ")}.` : ""}`
      : e.kind === "transition"
        ? e.witness ||
          (skillOps.has(e.op)
            ? "No completion witness recorded."
            : "Public branch/selection result; no engine order required.")
        : e.kind === "orders"
          ? e.orders
              .map(
                (o) =>
                  `${o.unit}: ${o.type} ${o.target || (o.x !== undefined ? `to (${o.x}, ${o.z})` : "")}`,
              )
              .join("; ")
          : e.reason || "The node record is shown below."
    : "Use the time slider or event arrows.";
  if (e?.selection) {
    const { preference, used, goal_line } = e.selection;
    $("evidence").textContent +=
      ` Model preference ${preference.target}: ${used ? "used within this node's eligible targets" : "ineligible here; graph fallback used"}.` +
      ` Goal ${preference.source.node_run}, observation ${preference.source.seq} at ${clock(preference.source.time_ms)}, trace row ${goal_line}.`;
  }
  $("record").textContent = e ? JSON.stringify(e, null, 2) : "";
  graph(stateAt());
  map();
}
function stop() {
  if (animation !== null) cancelAnimationFrame(animation);
  animation = null;
  $("play").textContent = "Play replay";
}
function chooseMember() {
  member = $("member").value;
  fillEvents();
  seek(time);
}
function chooseEpisode() {
  stop();
  episode = data.episodes[Number($("episode").value)];
  options(
    $("member"),
    Object.keys(episode.graphs).map((name) => [name, name]),
  );
  $("time").min = episode.frames[0].time_ms;
  $("time").max = Math.max(episode.frames.at(-1).time_ms, ...episode.events.map((e) => e.time_ms));
  time = Number($("time").min);
  chooseMember();
  const ending = episode.result.engine_ending;
  $("outcome").textContent =
    `Recorded result: ${ending?.result || episode.result.status || "unavailable"}${ending?.battle_ms !== undefined ? ` at ${clock(ending.battle_ms)}` : ""}. No strength or learning comparison is established.`;
  $("provenance").textContent = JSON.stringify(
    {
      battle: episode.battle,
      source_revision: episode.source_revision,
      graph_sha256: episode.graph_sha256,
      evidence: episode.evidence,
    },
    null,
    2,
  );
}
options(
  $("episode"),
  data.episodes.map((e, i) => [i, e.episode]),
);
$("episode").onchange = chooseEpisode;
$("member").onchange = chooseMember;
$("filter").onchange = () => {
  fillEvents();
  seek(time);
};
$("events").onchange = () => {
  stop();
  const i = Number($("events").value);
  seek(episode.events[i].time_ms, i);
};
$("time").oninput = () => {
  stop();
  seek($("time").value);
};
for (const [id, direction] of [
  ["previous", -1],
  ["next", 1],
])
  $(id).onclick = () => {
    stop();
    const at = visible.indexOf(selected);
    const target = visible[Math.max(0, Math.min(visible.length - 1, at + direction))];
    if (target !== undefined) seek(episode.events[target].time_ms, target);
  };
$("play").onclick = () => {
  if (animation !== null) {
    stop();
    return;
  }
  if (time >= Number($("time").max)) seek($("time").min);
  previousTick = performance.now();
  $("play").textContent = "Pause replay";
  function tick(now) {
    seek(time + (now - previousTick) * Number($("speed").value));
    previousTick = now;
    if (time >= Number($("time").max)) stop();
    else animation = requestAnimationFrame(tick);
  }
  animation = requestAnimationFrame(tick);
};
chooseEpisode();
