"use strict";
window.wh3Replay = (() => {
  const $ = (id) => document.getElementById(`replay-${id}`);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text != null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const svg = (tag, attrs = {}, text) => {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs))
      n.setAttribute(key, value);
    if (text != null) n.textContent = text;
    return n;
  };
  const json = (value) => JSON.stringify(value, null, 2);
  const fmt = (value, digits = 1) =>
    value == null ? "Unavailable" : Number(value).toFixed(digits);
  const seconds = (ms) => `${fmt(ms / 1000)} s`;
  const colours = { friendly: "#56b4e9", enemy: "#e69f00" };
  const symbols = {
    lord: "♔",
    hero: "♔",
    cavalry: "♞",
    missile_cavalry: "♞",
    infantry: "▰",
    missile: "↗",
    artillery: "⊕",
    monster: "◆",
  };
  const laneColours = {
    dead: "#555",
    routing: "#cc79a7",
    wavering: "#f0e442",
    under_fire: "#e69f00",
    melee: "#d55e00",
    moving: "#56b4e9",
    idle: "#999",
  };
  let dataset,
    trials = [],
    current,
    replay,
    time = 0,
    selected = 0,
    playing = false,
    lastTick;
  let generation = 0,
    selectionGeneration = 0,
    compareFrames = true;
  const cache = new Map();
  const label = (t) =>
    [t.card?.model, t.card?.effort, t.policy, t.instance, t.episode]
      .filter(Boolean)
      .join(" · ");
  const evidence = (source) =>
    source
      ? `${source.file}${source.line ? `:${source.line}` : ""}`
      : "Source unavailable";
  const states = (u) =>
    u.men === 0
      ? "dead"
      : Object.keys(laneColours).find((s) => u.state?.includes(s)) || "unknown";
  const allUnits = (frame) => [
    ...frame.friendly.map((u) => ({ ...u, side: "friendly" })),
    ...frame.enemy.map((u) => ({ ...u, side: "enemy" })),
  ];
  const unitsAt = (frame) => new Map(allUnits(frame).map((u) => [u.id, u]));
  const position = (u) => u && Number.isFinite(u.x) && Number.isFinite(u.z);
  function disclosure(title, value) {
    const d = node("details");
    d.append(node("summary", title), node("pre", value, "replay-raw"));
    return d;
  }
  function button(text, action) {
    const b = node("button", text);
    b.addEventListener("click", action);
    return b;
  }
  async function decode(key) {
    if (!dataset.replays[key]) return null;
    const encoded = dataset.replays[key];
    if (!cache.has(encoded))
      cache.set(
        encoded,
        (async () => {
          const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
          const stream = new Blob([bytes])
            .stream()
            .pipeThrough(new DecompressionStream("gzip"));
          return JSON.parse(await new Response(stream).text());
        })(),
      );
    return cache.get(encoded);
  }
  async function load(data, view, status) {
    const ownGeneration = ++generation;
    ++selectionGeneration;
    playing = false;
    replay = null;
    dataset = data;
    trials = view.groups.flatMap((g) =>
      data.report.groups[g].trials.map((trial, t) => ({
        ...trial,
        key: `g${g}-t${t}`,
      })),
    );
    $("trial").replaceChildren(
      ...trials.map((t, i) => {
        const option = node("option", label(t));
        option.value = i;
        return option;
      }),
    );
    $("content").hidden = true;
    $("availability").textContent = trials.length
      ? "Loading embedded replay evidence…"
      : "No started trial in this comparison.";
    $("verdict").replaceChildren(node("p", status, "banner"));
    $("multiples").replaceChildren();
    $("forces").replaceChildren();
    $("stills").replaceChildren();
    $("prompts").replaceChildren(
      ...Object.entries(data.prompts).map(([job, prompts]) => {
        const section = node("div");
        section.append(node("h3", job));
        for (const [name, prompt] of Object.entries(prompts))
          section.append(disclosure(name, prompt));
        return section;
      }),
    );
    if (!trials.length) {
      $("download").disabled = true;
      return;
    }
    try {
      const payloads = await Promise.all(trials.map((t) => decode(t.key)));
      if (ownGeneration !== generation) return;
      trials.forEach((t, i) => {
        t.replay = payloads[i];
      });
      const featured =
        trials.find((t) => t.key === data.featured[view.id]) || trials[0];
      await open(trials.indexOf(featured), status);
      if (ownGeneration !== generation) return;
      multiples();
    } catch (error) {
      if (ownGeneration === generation)
        $("availability").textContent =
          `Replay unavailable: ${error.message}. Statistical evidence remains available below.`;
    }
  }
  async function open(index, status) {
    const ownSelection = ++selectionGeneration;
    playing = false;
    $("play").textContent = "Play";
    const next = trials[index];
    const loaded = next?.replay || (await decode(next?.key));
    if (ownSelection !== selectionGeneration) return;
    current = next;
    replay = loaded;
    compareFrames = true;
    $("trial").value = index;
    $("content").hidden = !replay?.frames.length;
    $("download").disabled = !replay;
    const summary = replay?.summary;
    const verdict = $("verdict");
    if (status) verdict.dataset.status = status;
    verdict.replaceChildren(
      node("p", verdict.dataset.status || dataset.evidence_kind, "banner"),
      node("h2", label(current)),
      node(
        "p",
        `${current.outcome}${current.ended_by === "time_limit" ? ` (engine ${current.engine_outcome})` : ""} · ${fmt(current.battle_s)} s · active-strength margin ${fmt(current.metrics?.margin, 3)} · ${summary?.decisions ?? "Unavailable"} logged decisions · ${summary?.orders ?? "Unavailable"} submitted / ${summary?.acknowledged_orders ?? "Unavailable"} acknowledged orders · median information age ${fmt(summary?.age_s?.p50)} s · $${fmt(current.llm?.usd ?? (current.card?.kind === "scripted" ? 0 : null), 5)}`,
      ),
      node(
        "p",
        "Featured-trial rule: earliest completed model trial in recorded job-start / episode order, irrespective of outcome. If none completed, first supplied trial. The selector opens every trial.",
        "note",
      ),
    );
    if (!replay?.frames.length) {
      $("forces").replaceChildren();
      $("stills").replaceChildren();
      $("availability").textContent =
        "No recorded replay frames for this trial. Summary evidence is retained below.";
      return;
    }
    $("availability").textContent =
      `${replay.evidence_kind === "synthetic" ? "SYNTHETIC DEMO · invented frames · " : ""}${replay.frame_source}. ${replay.warnings.length} incomplete evidence records. Exact historical frame timing is retained.`;
    selected = 0;
    time = replay.decisions[0]?.time_ms ?? replay.frames[0].time_ms;
    $("time").min = replay.frames[0].time_ms / 1000;
    $("time").max = replay.frames.at(-1).time_ms / 1000;
    forces();
    stills();
    events();
    timeline();
    lanes("friendly");
    lanes("enemy");
    inspector();
    draw();
  }
  function forces() {
    const first =
      replay.frames.find((f) => f.friendly.length) || replay.frames[0];
    const section = $("forces");
    section.replaceChildren();
    const description = node("div");
    description.append(
      node("h3", "Recorded briefing"),
      node(
        "p",
        [
          first.mode?.type,
          first.mode?.role,
          first.remaining_ms != null
            ? `Timer ${seconds(first.remaining_ms)}`
            : "Timer unrecorded",
        ]
          .filter(Boolean)
          .join(" · "),
      ),
      node("p", first.mode?.objectives || "Objectives not recorded"),
    );
    section.append(description);
    for (const side of ["friendly", "enemy"]) {
      const box = node("div");
      box.append(
        node(
          "h3",
          `${side === "friendly" ? "Friendly" : "Enemy roster"} · ${replay.armies?.[side === "friendly" ? "player" : "enemy"]?.faction || "Faction unrecorded"}`,
        ),
      );
      const list = node("ul");
      for (const u of replay.roster.filter((u) => u.side === side))
        list.append(
          node(
            "li",
            `${symbols[u.class] || "◇"} ${u.id} ${u.name}${u.men0 != null ? ` · ${u.men0} men` : ""}${u.protected ? " · protected" : ""}${u.commander ? " · general" : ""}`,
          ),
        );
      box.append(list);
      section.append(box);
    }
  }
  function stills() {
    const firstImage = (replay.stills || []).findIndex((shot) => shot.image);
    $("background").querySelector('[value="game"]').textContent =
      replay.stills?.some((shot) => shot.image)
        ? "Game stills above · no registered map background"
        : "Game imagery · not recorded";
    $("stills").replaceChildren(
      ...(replay.stills || []).map((shot, index) => {
        const figure = node("figure");
        if (index === firstImage) figure.className = "featured-still";
        const title =
          {
            opening: "Opening view",
            approach: "Closing formations",
            incoming_fire: "Incoming fire",
            first_contact: "First observed melee",
            first_rout: "First observed rout",
            ending: "Battle ending",
          }[shot.trigger] || "Game still";
        if (shot.image) {
          const img = node("img");
          img.src = shot.image;
          img.alt = `${title} at ${seconds(shot.time_ms)}`;
          figure.append(img);
        }
        figure.append(
          node(
            "figcaption",
            `${title} · ${shot.time_ms != null ? seconds(shot.time_ms) : "time unavailable"} · ${shot.image ? "Presentation only; never policy input." : shot.status?.replaceAll("_", " ") || "Capture missing"} ${shot.caption || ""} ${shot.visibility || "Visibility not audited: the image may include information hidden from the controller."} ${shot.error || ""}`,
          ),
        );
        figure.append(
          disclosure("Capture evidence", json({ ...shot, image: undefined })),
        );
        return figure;
      }),
    );
  }
  function bounds(whole, frames = replay.frames) {
    const b = replay.terrain?.bounds;
    if (whole && b) return [b.min_x, b.min_z, b.max_x, b.max_z];
    const points = frames.flatMap(allUnits).filter(position);
    if (!points.length) return [-512, -512, 512, 512];
    return [
      Math.min(...points.map((p) => p.x)) - 45,
      Math.min(...points.map((p) => p.z)) - 45,
      Math.max(...points.map((p) => p.x)) + 45,
      Math.max(...points.map((p) => p.z)) + 45,
    ];
  }
  function projection(b, width = 700, height = 560) {
    const scale = Math.min(
      (width - 30) / (b[2] - b[0]),
      (height - 30) / (b[3] - b[1]),
    );
    return {
      scale,
      x: (x) => width / 2 + (x - (b[0] + b[2]) / 2) * scale,
      y: (z) => height / 2 - (z - (b[1] + b[3]) / 2) * scale,
    };
  }
  function ground(target, p) {
    target.append(
      svg("rect", { width: "100%", height: "100%", fill: "#15232b" }),
    );
    const terrain = replay.terrain;
    if (!terrain) {
      target.append(
        svg("text", { x: 15, y: 25, fill: "#ddd" }, "Terrain was not recorded"),
      );
      return;
    }
    const step = terrain.cell_m;
    terrain.rows.forEach((row, j) =>
      [...row].forEach((value, i) => {
        target.append(
          svg("rect", {
            x: p.x(terrain.x0 + i * step - step / 2),
            y: p.y(terrain.z0 + j * step + step / 2),
            width: step * p.scale,
            height: step * p.scale,
            fill: value === "#" ? "#52616a" : "#1c3039",
            stroke: "#31414a",
            "stroke-width": 0.35,
          }),
        );
      }),
    );
  }
  function glyph(target, unit, p, { ghost = false, seen } = {}) {
    if (!position(unit)) return;
    const colour = colours[unit.side],
      x = p.x(unit.x),
      y = p.y(unit.z);
    const g = svg("g", {
      opacity: ghost ? 0.28 : seen != null ? 0.55 : 1,
      class: seen != null ? "last-seen" : "unit-glyph",
    });
    const marker =
      unit.side === "friendly"
        ? svg("circle", { cx: x, cy: y, r: 10 })
        : svg("path", {
            d: `M${x} ${y - 11}L${x + 11} ${y}L${x} ${y + 11}L${x - 11} ${y}Z`,
          });
    marker.setAttribute("fill", seen != null || ghost ? "none" : "#15232b");
    marker.setAttribute("stroke", colour);
    marker.setAttribute("stroke-width", 2);
    g.append(marker);
    if (unit.bearing != null)
      g.append(
        svg("path", {
          d: `M${x} ${y - 13}l-3 5h6Z`,
          fill: colour,
          transform: `rotate(${unit.bearing} ${x} ${y})`,
        }),
      );
    g.append(
      svg(
        "text",
        { x, y: y + 4, "text-anchor": "middle", fill: colour, "font-size": 12 },
        symbols[unit.class] || "◇",
      ),
    );
    g.append(
      svg(
        "text",
        { x: x + 13, y: y - 6, fill: colour, "font-size": 10 },
        `${unit.id}${seen != null ? ` seen ${seconds(seen)}` : ""}`,
      ),
    );
    if (unit.men0)
      g.append(
        svg("rect", {
          x: x - 10,
          y: y + 14,
          width: 20 * Math.max(0, Math.min(1, unit.men / unit.men0)),
          height: 3,
          fill: colour,
        }),
      );
    if (Number.isFinite(unit.hp))
      g.append(
        svg("rect", {
          x: x - 10,
          y: y + 19,
          width: 20 * Math.max(0, Math.min(1, unit.hp)),
          height: 2,
          fill: colour,
          opacity: 0.65,
        }),
      );
    const badges = (unit.state || [])
      .filter((s) => ["melee", "under_fire", "wavering", "routing"].includes(s))
      .map(
        (s) =>
          ({ melee: "M", under_fire: "F", wavering: "W", routing: "R" })[s],
      )
      .join("");
    g.append(
      svg(
        "text",
        { x, y: y + 28, fill: "#fff", "font-size": 9, "text-anchor": "middle" },
        badges,
      ),
    );
    g.append(
      svg(
        "title",
        {},
        `${unit.id} · ${unit.name || unit.type} · ${unit.men}/${unit.men0} men · HP ${fmt(unit.hp * 100)}% · ${unit.state?.join(", ")} · ${unit.morale?.effect || "morale effect unrecorded"} · target ${unit.target || "none"}`,
      ),
    );
    target.append(g);
  }
  function frameIndex() {
    let index = 0;
    replay.frames.forEach((f, i) => {
      if (f.time_ms <= time) index = i;
    });
    return index;
  }
  function draw() {
    if (!replay?.frames.length) return;
    const index = frameIndex(),
      frame = replay.frames[index],
      decision = replay.decisions[selected];
    const after =
      decision?.after_frame != null
        ? replay.frames[decision.after_frame]
        : null;
    const basis =
      decision?.basis_frame != null
        ? replay.frames[decision.basis_frame]
        : null;
    const inspecting = compareFrames && decision && time === decision.time_ms;
    const displayed = inspecting && after ? after : frame;
    const p = projection(
      bounds($("whole").checked, [
        displayed,
        ...(inspecting && basis ? [basis] : []),
      ]),
    );
    const map = $("map");
    map.replaceChildren();
    ground(map, p);
    const defs = svg("defs"),
      marker = svg("marker", {
        id: "replay-arrow",
        viewBox: "0 0 10 10",
        refX: 9,
        refY: 5,
        markerWidth: 5,
        markerHeight: 5,
        orient: "auto-start-reverse",
      });
    marker.append(
      svg("path", { d: "M0 0L10 5L0 10Z", fill: "context-stroke" }),
    );
    defs.append(marker);
    map.append(defs);
    // Trail dots are samples, not interpolated movement or a reconstructed route.
    for (const f of replay.frames.filter(
      (f) => f.time_ms <= time && f.time_ms >= time - 20000,
    ))
      for (const u of allUnits(f).filter(position))
        map.append(
          svg("circle", {
            cx: p.x(u.x),
            cy: p.y(u.z),
            r: 1.8,
            fill: colours[u.side],
            opacity: 0.35,
          }),
        );
    if (inspecting && basis) {
      for (const u of allUnits(basis)) glyph(map, u, p, { ghost: true });
      for (const d of decision.displacements)
        map.append(
          svg("line", {
            x1: p.x(d.from[0]),
            y1: p.y(d.from[1]),
            x2: p.x(d.to[0]),
            y2: p.y(d.to[1]),
            stroke: colours[d.side],
            "stroke-width": 1,
            opacity: 0.5,
          }),
        );
    }
    const visible = unitsAt(displayed),
      lastSeen = new Map();
    const displayedIndex = replay.frames.indexOf(displayed);
    for (const f of replay.frames.slice(0, displayedIndex + 1))
      for (const u of f.enemy)
        lastSeen.set(u.id, { ...u, seen: f.time_ms, side: "enemy" });
    const dead = new Set(
      displayed.enemy_roster.filter((u) => u.dead).map((u) => u.id),
    );
    for (const [id, u] of lastSeen)
      if (!visible.has(id) && !dead.has(id)) glyph(map, u, p, { seen: u.seen });
    for (const u of allUnits(displayed)) glyph(map, u, p);
    for (const point of displayed.mode?.capture_points || [])
      if (position(point)) {
        map.append(
          svg("rect", {
            x: p.x(point.x) - 8,
            y: p.y(point.z) - 8,
            width: 16,
            height: 16,
            fill: "none",
            stroke: "#fff",
          }),
        );
        map.append(
          svg(
            "text",
            {
              x: p.x(point.x) + 10,
              y: p.y(point.z),
              fill: "#fff",
              "font-size": 10,
            },
            `${point.id} ${point.holder || "unheld"}`,
          ),
        );
      }
    if (decision && basis) {
      const origins = unitsAt(basis);
      for (const item of decision.orders) {
        const o = item.order,
          start = origins.get(o.unit),
          end = o.x != null ? o : origins.get(o.target);
        if (!position(start) || !position(end)) continue;
        const applied =
          decision.applied_ms != null && time >= decision.applied_ms;
        const colour =
          item.status === "rejected" && applied ? "#ff7777" : colours.friendly;
        const line = svg("line", {
          x1: p.x(start.x),
          y1: p.y(start.z),
          x2: p.x(end.x),
          y2: p.y(end.z),
          stroke: colour,
          "stroke-width": 2,
          "stroke-dasharray": applied ? "none" : "6 5",
          "marker-end": "url(#replay-arrow)",
        });
        line.append(
          svg(
            "title",
            {},
            `${o.unit} ${o.type}: ${applied ? item.status : "issued; awaiting application"} · ${item.ack?.error || ""}`,
          ),
        );
        map.append(line);
        if (applied)
          map.append(
            svg(
              "text",
              {
                x: p.x(end.x) + 4,
                y: p.y(end.z) - 4,
                fill: colour,
                "font-size": 10,
              },
              item.ack?.error || (item.status === "queued" ? "queued" : ""),
            ),
          );
      }
    }
    const gap = time - frame.time_ms > replay.sample_interval_ms * 1.5;
    $("frame").textContent = inspecting
      ? `Basis ${seconds(basis?.time_ms ?? time)} (ghost) → ${decision.after_label}: ${after ? seconds(after.time_ms) : "unavailable"} (solid). Displacement joins two recorded samples. ${evidence(displayed.source)}`
      : `Cursor ${seconds(time)} · showing recorded frame ${seconds(frame.time_ms)} · ${evidence(frame.source)}${gap ? " · GAP: no recorded frame at the cursor; positions are stale" : ""}`;
    $("frame").classList.toggle("gap", gap);
    $("time").value = time / 1000;
    for (const cursor of document.querySelectorAll(".replay-cursor")) {
      cursor.setAttribute("x1", tx(time));
      cursor.setAttribute("x2", tx(time));
    }
  }
  function tx(ms) {
    const a = replay.frames[0].time_ms,
      b = replay.frames.at(-1).time_ms;
    return 125 + (560 * (ms - a)) / Math.max(1, b - a);
  }
  function baseTimeline(target, height) {
    target.replaceChildren(
      svg("rect", { width: 700, height, fill: "#15232b" }),
    );
    target.append(
      svg("line", {
        x1: tx(time),
        x2: tx(time),
        y1: 0,
        y2: height,
        stroke: "#fff",
        opacity: 0.7,
        class: "replay-cursor",
      }),
    );
  }
  function choose(index) {
    compareFrames = true;
    selected = Math.max(0, Math.min(replay.decisions.length - 1, index));
    if (replay.decisions[selected]) time = replay.decisions[selected].time_ms;
    inspector();
    draw();
  }
  function timeline() {
    baseTimeline($("timeline"), 90);
    $("timeline").append(
      svg(
        "text",
        { x: 8, y: 20, fill: "#eee", "font-size": 12 },
        "Decision age",
      ),
    );
    replay.decisions.forEach((d, i) => {
      const bar = svg("rect", {
        x: tx(d.time_ms),
        y: 28 + (i % 2) * 18,
        width: Math.max(2, tx(d.applied_ms ?? d.time_ms) - tx(d.time_ms)),
        height: 14,
        fill: d.applied_ms == null ? "#aaa" : colours.friendly,
        tabindex: 0,
        role: "button",
        "aria-label": `Decision ${i + 1}, basis ${seconds(d.time_ms)}, application ${d.applied_ms == null ? "missing" : seconds(d.applied_ms)}`,
      });
      bar.append(svg("title", {}, bar.getAttribute("aria-label")));
      bar.addEventListener("click", () => choose(i));
      bar.addEventListener("keydown", (e) => {
        if (e.key === "Enter") choose(i);
      });
      $("timeline").append(bar);
    });
    $("timeline").append(
      svg(
        "text",
        { x: 125, y: 80, fill: "#ccc", "font-size": 10 },
        `${seconds(replay.frames[0].time_ms)} — ${seconds(replay.frames.at(-1).time_ms)} · bar: basis → application`,
      ),
    );
    const series = [
      ["Winds", (f) => f.magic?.current, "#56b4e9"],
      ["Reserve", (f) => f.magic?.reserve, "#009e73"],
      ["Supplies", (f) => f.mode?.supplies, "#e69f00"],
    ];
    if (replay.frames.some((f) => f.army?.currency != null))
      series.push(["Army currency", (f) => f.army?.currency, colours.friendly]);
    for (const side of new Set(
      replay.frames.flatMap((f) => (f.mode?.tickets || []).map((t) => t.side)),
    )) {
      series.push([
        `${side} tickets`,
        (f) => f.mode?.tickets?.find((t) => t.side === side)?.tickets,
        side === "us" ? colours.friendly : colours.enemy,
      ]);
    }
    const height = series.length * 28 + 16;
    $("resources").setAttribute("viewBox", `0 0 700 ${height}`);
    baseTimeline($("resources"), height);
    series.forEach(([name, value, colour], i) => {
      const values = replay.frames.map(value).filter((v) => v != null),
        max = Math.max(1, ...values);
      $("resources").append(
        svg(
          "text",
          { x: 8, y: 15 + i * 28, fill: colour, "font-size": 11 },
          `${name} · ${values.length ? `0–${max}` : "unrecorded"}`,
        ),
      );
      for (const f of replay.frames)
        if (value(f) != null) {
          const dot = svg("circle", {
            cx: tx(f.time_ms),
            cy: 24 + i * 28 - (value(f) / max) * 15,
            r: 1.8,
            fill: colour,
          });
          dot.append(
            svg("title", {}, `${seconds(f.time_ms)} ${name}: ${value(f)}`),
          );
          $("resources").append(dot);
        }
    });
    for (const e of replay.events.filter((e) => e.kind === "ability")) {
      const mark = svg(
        "text",
        { x: tx(e.time_ms), y: height - 4, fill: "#fff", "font-size": 10 },
        "✦",
      );
      mark.append(svg("title", {}, e.caption));
      $("resources").append(mark);
    }
  }
  function lanes(side) {
    const target = side === "friendly" ? $("lanes") : $("enemy-lanes");
    target.replaceChildren();
    const roster = replay.roster.filter((u) => u.side === side),
      height = roster.length * 30 + 30;
    const canvas = svg("svg", {
      viewBox: `0 0 700 ${height}`,
      role: "img",
      "aria-label": `${side} unit states and order attention`,
    });
    baseTimeline(canvas, height);
    roster.forEach((u, row) => {
      const y = row * 30 + 16;
      canvas.append(
        svg(
          "text",
          { x: 8, y, fill: colours[side], "font-size": 11 },
          `${u.id} ${u.name.slice(0, 14)}`,
        ),
      );
      replay.frames.forEach((f, index) => {
        const unit = f[side].find((unit) => unit.id === u.id);
        if (!unit) return;
        const end = Math.min(
          replay.frames[index + 1]?.time_ms ?? f.time_ms + 1000,
          f.time_ms + replay.sample_interval_ms,
        );
        const block = svg("rect", {
          x: tx(f.time_ms),
          y: y - 10,
          width: Math.max(1, tx(end) - tx(f.time_ms)),
          height: 10,
          fill: laneColours[states(unit)] || "#ddd",
        });
        const last = replay.decisions
          .filter((d) => d.applied_ms <= f.time_ms)
          .flatMap((d) =>
            d.orders
              .filter((o) => o.order.unit === u.id && o.ack?.ok)
              .map((o) => ({ ...o, time: d.applied_ms })),
          )
          .at(-1);
        block.append(
          svg(
            "title",
            {},
            `${seconds(f.time_ms)} ${u.id}: ${unit.state?.join(", ") || "unknown"}; ${unit.morale?.effect || ""}; last accepted order ${last ? `${last.order.type} at ${seconds(last.time)}` : "none recorded"}`,
          ),
        );
        block.addEventListener("click", () => {
          time = f.time_ms;
          draw();
        });
        canvas.append(block);
      });
      replay.decisions.forEach((d, index) =>
        d.orders
          .filter((o) => o.order.unit === u.id)
          .forEach((o) => {
            const mark = svg(
              "text",
              {
                x: tx(d.applied_ms ?? d.time_ms),
                y: y + 10,
                fill: o.status === "rejected" ? "#ff7777" : "#fff",
                "font-size": 10,
              },
              o.order.type === "ability" ? "✦" : "│",
            );
            mark.append(svg("title", {}, `${o.order.type}: ${o.status}`));
            mark.addEventListener("click", () => choose(index));
            canvas.append(mark);
          }),
      );
    });
    target.append(
      canvas,
      node(
        "p",
        "State: grey idle · blue moving · vermilion melee · orange under fire · yellow wavering · purple routing · dark grey dead. Blank intervals are unsampled. │ order · ✦ ability · red rejection. Hover for all flags and last accepted order.",
        "note",
      ),
    );
  }
  function inspector() {
    const box = $("inspector"),
      d = replay.decisions[selected];
    box.replaceChildren();
    if (!d) {
      box.append(node("p", "No logged decisions"));
      return;
    }
    box.append(
      node("h4", `Decision ${selected + 1} · ${d.request}`),
      node(
        "p",
        `Basis ${seconds(d.time_ms)} → applied ${d.applied_ms == null ? "unavailable" : seconds(d.applied_ms)} · information age ${d.applied_ms == null ? "unavailable" : seconds(d.applied_ms - d.time_ms)}`,
      ),
      node("p", evidence(d.source), "mono"),
    );
    box.append(
      node("h4", "Stated rationale"),
      node("blockquote", d.reason || "No reason recorded"),
    );
    box.append(
      disclosure(
        d.notes_changed
          ? "Battle notes changed · before / after"
          : "Battle notes unchanged",
        `BEFORE\n${d.notes_before ?? "(none)"}\n\nAFTER\n${d.notes ?? "(none)"}`,
      ),
    );
    if (d.plan) box.append(disclosure("Recorded commander plan", json(d.plan)));
    const orders = node("ol");
    for (const o of d.orders)
      orders.append(
        node(
          "li",
          `${json(o.order)} — ${o.status}${o.ack?.error ? `: ${o.ack.error}` : ""}`,
        ),
      );
    box.append(node("h4", "Orders and engine acknowledgements"), orders);
    if (!d.orders.length)
      box.append(node("p", "No new orders in this decision."));
    if (d.invalid)
      box.append(
        disclosure("Validation refused these orders", json(d.invalid)),
      );
    box.append(
      node(
        "p",
        `Acknowledgement: ${evidence(d.ack_source)}. Queued and acknowledged orders do not prove execution.`,
        "note",
      ),
    );
    const p = d.latency_parts;
    box.append(
      node("h4", "Latency and cost"),
      node(
        "p",
        `Provider ${fmt(p.provider_s, 3)} s · call minus provider ${fmt(p.transport_residual_s, 3)} s · roundtrip minus think ${fmt(p.harness_roundtrip_residual_s, 3)} s`,
      ),
      node("p", p.note, "note"),
    );
    for (const [i, a] of d.attempts.entries())
      box.append(
        node(
          "p",
          `Attempt ${i + 1}: $${fmt(a.usd, 5)} · input ${a.usage?.input_tokens ?? "?"} · output ${a.usage?.output_tokens ?? "?"} · reasoning ${a.usage?.output_tokens_details?.reasoning_tokens ?? "?"} · ${a.actual_model || "model unrecorded"}`,
        ),
      );
    box.append(
      disclosure(
        "Exact recorded prompt and raw replies",
        `PROMPT\n${d.prompt ?? "Not recorded"}\n\n${d.attempts.map((a, i) => `RAW REPLY ${i + 1}\n${a.text ?? "Not recorded"}`).join("\n\n")}`,
      ),
    );
    box.append(
      disclosure(
        "Recorded basis and first state after application",
        json({
          basis: replay.frames[d.basis_frame] ?? null,
          after: replay.frames[d.after_frame] ?? null,
        }),
      ),
    );
    box.append(
      disclosure(
        "Observed displacement · metres",
        d.displacements
          .map((m) => `${m.unit}: ${fmt(m.metres)} m`)
          .join("\n") || "No comparable positions recorded",
      ),
    );
    const f = replay.frames[d.after_frame ?? d.basis_frame];
    if (f)
      box.append(
        disclosure(
          "Resources and abilities left ready · first recorded state after application",
          json({
            magic: f.magic,
            supplies: f.mode?.supplies,
            army: f.army,
            ready: f.friendly
              .map((u) => ({
                unit: u.id,
                abilities: u.abilities?.filter((a) => a.ready),
              }))
              .filter((u) => u.abilities?.length),
          }),
        ),
      );
  }
  function eventAt(event) {
    if (event.decision != null) {
      selected = event.decision;
      inspector();
    }
    compareFrames = false;
    time = event.time_ms;
    draw();
  }
  function events() {
    $("events").replaceChildren(
      ...replay.events.map((event) => {
        const b = button(`${seconds(event.time_ms)} · ${event.caption}`, () =>
          eventAt(event),
        );
        b.title = evidence(event.source);
        b.dataset.kind = event.kind;
        return b;
      }),
    );
  }
  function multiples() {
    const payloads = trials.filter((t) => t.replay?.frames.length);
    const shared = payloads
      .flatMap((t) => t.replay.frames.flatMap(allUnits))
      .filter(position);
    const b = shared.length
      ? [
          Math.min(...shared.map((p) => p.x)) - 30,
          Math.min(...shared.map((p) => p.z)) - 30,
          Math.max(...shared.map((p) => p.x)) + 30,
          Math.max(...shared.map((p) => p.z)) + 30,
        ]
      : [-512, -512, 512, 512];
    $("multiples").replaceChildren(
      ...trials.map((t, i) => {
        const card = node("article");
        card.append(
          button(label(t), () => open(i)),
          node(
            "p",
            `${t.outcome} · ${fmt(t.battle_s)} s · margin ${fmt(t.metrics?.margin, 3)}`,
          ),
        );
        if (t.replay?.frames.length) {
          const map = svg("svg", {
              viewBox: "0 0 320 240",
              role: "img",
              "aria-label": `Recorded tracks for ${label(t)}`,
            }),
            p = projection(b, 320, 240);
          map.append(svg("rect", { width: 320, height: 240, fill: "#15232b" }));
          for (const f of t.replay.frames)
            for (const u of allUnits(f).filter(position))
              map.append(
                svg("circle", {
                  cx: p.x(u.x),
                  cy: p.y(u.z),
                  r: 1,
                  fill: colours[u.side],
                  opacity: 0.35,
                }),
              );
          card.append(map);
        } else card.append(node("p", "Replay not recorded"));
        return card;
      }),
    );
  }
  function stepEvent(direction) {
    const items = replay?.events || [];
    const event =
      direction > 0
        ? items.find((e) => e.time_ms > time)
        : items.findLast((e) => e.time_ms < time);
    if (event) eventAt(event);
  }
  function stepDecision(direction) {
    if (!replay) return;
    const index =
      direction > 0
        ? replay.decisions.findIndex((d) => d.time_ms > time)
        : replay.decisions.findLastIndex((d) => d.time_ms < time);
    if (index >= 0) choose(index);
  }
  function toggle() {
    if (!replay) return;
    compareFrames = false;
    playing = !playing;
    lastTick = null;
    $("play").textContent = playing ? "Pause" : "Play";
  }
  function tick(now) {
    if (playing && replay) {
      if (lastTick != null) {
        time = Math.min(
          time + (now - lastTick) * Number($("speed").value),
          replay.frames.at(-1).time_ms,
        );
        const index = replay.decisions.findLastIndex((d) => d.time_ms <= time);
        if (index >= 0 && selected !== index) {
          selected = index;
          inspector();
        }
        draw();
        if (time === replay.frames.at(-1).time_ms) toggle();
      }
      lastTick = now;
    }
    requestAnimationFrame(tick);
  }
  function setup() {
    $("trial").addEventListener("change", (e) => open(Number(e.target.value)));
    $("whole").addEventListener("change", draw);
    $("play").addEventListener("click", toggle);
    $("prev").addEventListener("click", () => stepDecision(-1));
    $("next").addEventListener("click", () => stepDecision(1));
    $("prev-event").addEventListener("click", () => stepEvent(-1));
    $("next-event").addEventListener("click", () => stepEvent(1));
    $("time").addEventListener("input", (e) => {
      compareFrames = false;
      time = Number(e.target.value) * 1000;
      const index = replay.decisions.findLastIndex((d) => d.time_ms <= time);
      if (index >= 0) selected = index;
      inspector();
      draw();
    });
    $("section").addEventListener("keydown", (e) => {
      if (
        ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "SUMMARY"].includes(
          e.target.tagName,
        )
      )
        return;
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
    $("map").setAttribute("tabindex", "0");
    $("download").addEventListener("click", () => {
      if (!replay) return;
      const blob = new Blob(
        [
          json({
            evidence_kind: dataset.evidence_kind,
            trial: { ...current, replay: undefined },
            replay,
          }),
        ],
        { type: "application/json" },
      );
      const url = URL.createObjectURL(blob),
        a = node("a");
      a.href = url;
      a.download = `wh3-${dataset.evidence_kind}-${current.episode}-replay.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    requestAnimationFrame(tick);
  }
  setup();
  return { load };
})();
