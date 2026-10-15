// Runs after replay.js in the same script and uses its helpers (el, svg, clock, Viewer, ...).
(() => {
  const $ = (id) => document.getElementById(id);
  const data = JSON.parse($("report-data").textContent);
  const report = data.report;
  const synthetic = data.evidence_kind === "synthetic";
  const NOTICE =
    "SYNTHETIC DEMO: invented values that exercise the report; not benchmark evidence.";
  const PROMPTS = {
    llm: "tactics prompt",
    llm_rules: "rules-only prompt",
    commander: "commander with unit skills",
  };
  const SCRIPTED = {
    attack_nearest: [
      "Scripted: attack nearest, walking",
      "every able unit attacks the nearest visible enemy, walking.",
    ],
    rush_nearest: [
      "Scripted: attack nearest, running",
      "every able unit attacks the nearest visible enemy, running.",
    ],
    hold: ["Scripted: hold position", "no unit ever receives an order."],
  };
  const FEATURED = {
    selected: "Selected example",
    first_model_run: "First completed model run",
    first_run: "First recorded run",
  };
  const KINDS = {
    plan: "Plan",
    maneuver: "Maneuver",
    turning_point: "Turning point",
    trouble: "Trouble",
    outcome: "Outcome",
  };
  const STILLS = {
    opening: "Opening view",
    approach: "Closing in",
    incoming_fire: "Incoming fire",
    first_contact: "First melee",
    first_rout: "First rout",
    ending: "Battle ending",
  };
  const STATES = [
    ["destroyed", "#2b2b2b", "destroyed"],
    ["routing", "#7a4f9a", "fleeing"],
    ["wavering", "#cc79a7", "wavering"],
    ["melee", "#d55e00", "fighting"],
    ["under_fire", "#e8c547", "under fire"],
    ["moving", "#8fb3c9", "moving"],
    ["none", "#8a8f86", "no state flag"],
    ["idle", "#c9c4b5", "idle"],
  ];
  const entries = new Map();
  report.groups.forEach((group, g) =>
    group.trials.forEach((trial, t) => {
      const key = `g${g}-t${t}`;
      entries.set(key, { key, trial, group, g });
    }),
  );
  const cache = new Map();
  let scenario = null,
    openKey = null,
    payload = null,
    featured = null,
    cardSpans = [];

  // A rotation can name a model policy with its own model: llm_rules@gpt-6-luna/medium.
  // The card records the model and effort it played with; a trial without one (its
  // controller failed to build) takes them from that name, then from the job.
  const basePolicy = (trial) => trial.policy.split("@")[0];
  const isModel = (entry) =>
    entry.trial.card?.kind === "model" || data.model_policies.includes(basePolicy(entry.trial));
  function controllerName(entry) {
    const { trial, group } = entry,
      card = trial.card || {},
      [model, level] = (trial.policy.split("@")[1] || "").split("/");
    let name;
    if (isModel(entry)) {
      const effort = card.effort || level || group.definition.effort;
      name = [
        card.model || model || group.definition.model,
        effort && `${effort} reasoning`,
        PROMPTS[basePolicy(trial)] || trial.policy,
      ]
        .filter(Boolean)
        .join(" · ");
    } else name = SCRIPTED[trial.policy]?.[0] || trial.policy;
    return trial.delay_ms ? `${name} · +${trial.delay_ms / 1000} s added delay` : name;
  }
  function outcome(trial) {
    if (!trial.valid)
      return {
        text: `Did not finish${trial.error ? `: ${trial.error}` : ""}`,
        short: "Failed",
        tone: "failed",
      };
    const engine = trial.engine_outcome || trial.outcome,
      word = { won: "Won", lost: "Lost", draw: "Draw" }[engine] || capital(String(engine));
    // One clock for every duration: the battle's own milliseconds where recorded.
    const ms = trial.battle_ms ?? (trial.battle_s == null ? null : trial.battle_s * 1000),
      duration = ms == null ? null : clock(ms);
    const timeLimit = trial.ended_by === "time_limit";
    const text = timeLimit
      ? `${word} at the time limit${duration ? ` (${duration})` : ""}`
      : duration
        ? `${word} ${engine === "draw" ? "after" : "in"} ${duration}`
        : word;
    const short = `${duration ? `${word} ${duration}` : word}${timeLimit ? " (time limit)" : ""}`;
    return { text, short, tone: engine };
  }
  function context(entry) {
    const card = entry.trial.card || {},
      kind = isModel(entry) ? "model" : card.kind === "scripted" ? "scripted" : "other";
    const rule = SCRIPTED[entry.trial.policy]?.[1] || card.description?.split("\n")[0];
    const label = kind === "scripted" && rule ? `Scripted rule: ${rule}` : rule;
    return { kind, rule: label, synthetic };
  }
  function conditions(entry) {
    const track = entry.group.definition.track || "",
      kind = context(entry).kind;
    const text = /obs-v3/.test(track) && /live-1x/.test(track);
    let line;
    if (kind === "scripted")
      line = `${context(entry).rule}${text ? " It reads the same text observations as the model: enemy units are visible only while its army can see them" : ""}`;
    else if (text)
      line =
        "Reads a text description of the battlefield, not images · the battle keeps running at 1× while the model thinks · enemy units are visible only while its army can see them";
    else
      line = `${entry.trial.card?.description || "Controller"} · interface ${track || "not recorded"}`;
    if (entry.trial.delay_ms)
      line += ` · observations delayed by +${entry.trial.delay_ms / 1000} s`;
    return line;
  }
  function date(value) {
    if (!value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime())
      ? value && String(value).toLowerCase()
      : parsed.toLocaleDateString("en-GB", {
          day: "numeric",
          month: "short",
          year: "numeric",
          timeZone: "UTC",
        });
  }
  function rosterEntry(id) {
    return payload?.roster.find((entry) => entry.id === id);
  }
  function unitChip(entry) {
    const chip = button("", () => Viewer.select(entry.id, true), `unit-chip ${entry.side}`);
    chip.append(glyph(entry.glyph), entry.display);
    chip.title = `${entry.display} · ${entry.role}: select on the map`;
    chip.setAttribute("aria-label", `Select ${entry.display} on the map`);
    return chip;
  }

  async function decode(key) {
    const encoded = data.replays[key];
    if (!encoded) return null;
    if (!cache.has(key))
      cache.set(
        key,
        (async () => {
          const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
          const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
          return JSON.parse(await new Response(stream).text());
        })(),
      );
    return cache.get(key);
  }

  function scenarioKeys() {
    const groups = new Set(scenario.comparisons.flatMap((index) => data.comparisons[index].groups));
    return [...entries.values()].filter((entry) => groups.has(entry.g));
  }

  function renderScenario(index) {
    scenario = data.scenarios[index];
    $("question").textContent = scenario.question || scenario.title;
    $("challenge").textContent = scenario.challenge || "";
    document.title = `${synthetic ? "SYNTHETIC DEMO — " : ""}${scenario.title} · WH3 AI commander benchmark`;
    $("run-select").replaceChildren(
      ...scenarioKeys().map((entry) => {
        const view = data.comparisons.find((item) => item.groups.includes(entry.g));
        const option = el(
          "option",
          `${controllerName(entry)} — ${outcome(entry.trial).text} · ${date(view?.created_at) || "undated"}`,
        );
        option.value = entry.key;
        return option;
      }),
    );
    renderCompare();
    return openRun(scenario.featured, false);
  }

  function renderRunLine(entry) {
    const line = $("run-line");
    line.replaceChildren();
    if (synthetic) line.append(el("span", "SYNTHETIC DEMO", "tag synthetic"));
    if (entry.key === scenario.featured)
      line.append(el("span", FEATURED[scenario.featured_reason], "tag"));
    const result = outcome(entry.trial);
    const row = entry.group.controllers.find((item) => item.controller === entry.trial.controller);
    line.append(
      el("strong", controllerName(entry), "name"),
      el("span", result.text, `result ${result.tone}`),
    );
    if (row)
      line.append(
        el(
          "span",
          !entry.trial.valid
            ? "Not counted in battles won: it did not finish"
            : row.valid === 1
              ? "Single recorded battle"
              : `One of ${row.valid} recorded battles with this setup`,
          "sample",
        ),
      );
    const conditionsLine = $("conditions");
    conditionsLine.replaceChildren(
      `${conditions(entry).replace(/\.?$/, ".")} `,
      el(
        "span",
        `The animated map is a rendering of recorded state, not the ${isModel(entry) ? "model" : "controller"}'s input.`,
      ),
    );
  }

  async function openRun(key, scroll) {
    openKey = key;
    const entry = entries.get(key);
    $("run-select").value = key;
    renderRunLine(entry);
    markReplays();
    $("download-replay").disabled = true;
    $("watch-featured").hidden = true;
    let decoded = null,
      problem = null;
    try {
      decoded = await decode(key);
    } catch (error) {
      problem = `Replay unavailable: ${error.message}`;
    }
    if (openKey !== key) return;
    payload = decoded;
    if (payload?.frames?.length) Viewer.show(payload, context(entry));
    else
      Viewer.clear(
        problem || "No replay was recorded for this battle; its result is in the table below.",
      );
    const highlights = payload?.highlights || [];
    featured = highlights.find((h) => h.feature) || highlights[0] || null;
    $("watch-featured").hidden = !featured;
    $("watch-featured").textContent = featured?.feature
      ? "▶ Watch the featured maneuver"
      : "▶ Watch analyst note 1";
    $("watch-full").disabled = !payload?.frames?.length;
    $("download-replay").disabled = !payload;
    renderHappened();
    if (scroll) Viewer.reveal();
  }

  // Compare: one table per run set, one row per controller, one replay button per battle.
  function runSet(index, several) {
    const view = data.comparisons[index],
      figure = el("figure", null, "run-set"),
      caption = el("figcaption");
    caption.append(el("strong", ["Run set", date(view.created_at)].filter(Boolean).join(" · ")));
    const same =
      {
        true: "Controller code and prompts identical.",
        false: "Controller code or prompts differ.",
      }[view.same_controller] ?? "Controller code and prompts could not be compared.";
    if (view.reference) {
      if (several)
        caption.append(
          `The first set; it holds the ${FEATURED[scenario.featured_reason].toLowerCase()}.`,
        );
    } else if (view.differences.length)
      caption.append(`Differs from the first set: ${view.differences.join(", ")}. ${same}`);
    else caption.append(`Same recorded settings as the first set; a separate launch. ${same}`);
    const table = el("table", null, "results"),
      head = el("tr"),
      body = el("tbody");
    const columns = [
      "Model / setup",
      "Battles won",
      "Typical order delay",
      "Inference cost / battle",
      "Replays",
    ];
    for (const name of columns) {
      const th = el("th", name);
      th.scope = "col";
      head.append(th);
    }
    const rows = view.groups.flatMap((g) =>
      report.groups[g].controllers.map((summary) => {
        const items = [...entries.values()].filter(
          (entry) => entry.g === g && entry.trial.controller === summary.controller,
        );
        return { g, summary, items, name: controllerName(items[0]), model: isModel(items[0]) };
      }),
    );
    rows.sort((a, b) => b.model - a.model || a.name.localeCompare(b.name, "en", { numeric: true }));
    for (const row of rows) {
      const { summary, items } = row,
        tr = el("tr");
      tr.dataset.controller = summary.controller;
      tr.dataset.group = row.g;
      const cell = (label, ...content) => {
        const td = el("td");
        td.dataset.label = label;
        td.append(...content);
        tr.append(td);
        return td;
      };
      cell(columns[0], row.name).className = "name";
      const won = (summary.outcomes.won || 0) + (summary.time_limit_engine_outcomes?.won || 0);
      const extras = [];
      if (summary.outcomes.time_limit)
        extras.push(`(${summary.outcomes.time_limit} at the time limit)`);
      if (summary.trials > summary.valid) {
        const reasons = [
          ...new Set(
            items.filter((e) => !e.trial.valid).map((e) => e.trial.error || e.trial.outcome),
          ),
        ];
        extras.push(`+${summary.trials - summary.valid} failed: ${reasons.join("; ")}`);
      }
      // The interval leaves out time-limit wins, which Battles won counts.
      if (summary.win_ci95 && summary.valid >= 5 && !summary.outcomes.time_limit)
        extras.push(
          `95% interval ${Math.round(summary.win_ci95[0] * 100)}–${Math.round(summary.win_ci95[1] * 100)}%`,
        );
      cell(
        columns[1],
        el("span", `${won} of ${summary.valid}`, "won-count"),
        ...extras.map((text) => el("small", text, "extra")),
      );
      cell(
        columns[2],
        summary.order_age_median_s == null ? "not recorded" : seconds(summary.order_age_median_s),
      );
      const scripted = items.every((e) => e.trial.card?.kind === "scripted");
      const known = items.every((e) => e.trial.llm?.usd != null);
      cell(
        columns[3],
        scripted
          ? "$0 (scripted)"
          : known && summary.trials
            ? money(summary.usd / summary.trials)
            : "not recorded",
      );
      const replays = el("div", null, "replays");
      for (const entry of items) {
        const result = outcome(entry.trial);
        if (data.replays[entry.key]) {
          const watch = button(`${result.short} ▶`, () => openRun(entry.key, true));
          watch.dataset.key = entry.key;
          watch.setAttribute("aria-label", `Watch ${controllerName(entry)}: ${result.text}`);
          replays.append(watch);
        } else replays.append(el("span", `${result.short} · no replay`, "missing"));
      }
      cell(columns[4], replays);
      body.append(tr);
    }
    const thead = el("thead");
    thead.append(head);
    table.append(thead, body);
    figure.append(caption, table);
    return { figure, rows };
  }

  function renderCompare() {
    const box = $("run-sets");
    box.replaceChildren();
    // The set holding the featured run comes first; the others state how they differ from it.
    const order = [...scenario.comparisons].sort(
      (a, b) => data.comparisons[b].reference - data.comparisons[a].reference,
    );
    const all = [];
    for (const index of order) {
      const { figure, rows } = runSet(index, order.length > 1);
      box.append(figure);
      all.push(...rows);
    }
    const notes = [
      "Typical order delay: for each battle, the median age of the battlefield view behind each batch of new orders when the game acknowledged it (battle clock); across battles, the median of those medians. The model's reply time is one part of it.",
      "Inference cost / battle: recorded model API cost divided by battles started, failed ones included. Scripted controllers make no model calls.",
    ];
    const expect = scenario.expect || {};
    if (expect.time_limit_s)
      notes.push(
        `Battles won counts the engine's result; the ${expect.player_defends ? "defender wins" : "attacker loses"} at the time limit (${clock(expect.time_limit_s * 1000)}) in this scenario.`,
      );
    const largest = Math.max(0, ...all.map((row) => row.summary.valid));
    if (largest <= 1)
      notes.push("Each row is one recorded battle: an example, not a success rate.");
    else if (largest === 2)
      notes.push("Each row holds at most two recorded battles: examples, not success rates.");
    $("footnotes").replaceChildren(...notes.map((text) => el("li", text)));
    const lines = [];
    const own = scenario.setup_only_jobs.length;
    if (own)
      lines.push(
        `${own} launch${own > 1 ? "es" : ""} of this scenario stopped during setup before any battle`,
      );
    const others = new Map();
    for (const item of data.setup_only) others.set(item.title, (others.get(item.title) || 0) + 1);
    for (const [title, n] of others)
      lines.push(
        `${n} launch${n > 1 ? "es" : ""} of ${title} stopped during setup before any battle`,
      );
    $("setup-only").textContent = lines.length ? `Not shown: ${lines.join("; ")}.` : "";
    $("setup-only").hidden = !lines.length;
  }
  function markReplays() {
    for (const node of document.querySelectorAll(".replays button"))
      node.setAttribute("aria-current", String(node.dataset.key === openKey));
  }

  // What happened: analyst notes (or key events), game stills, all events, unit timelines.
  // A card plays from `from` and stops at `stop` (null: the end); `moment` is its window and
  // time. Watching note k emphasises its units; watching a key event emphasises none.
  function momentCard(index, label, title, text, units, from, stop, moment, k) {
    const item = el("li", null, "highlight"),
      head = el("p", null, "label");
    cardSpans[index] = moment;
    head.append(el("span", String(index + 1), "number"), label);
    item.append(head, el("h3", title));
    if (text) item.append(el("p", text));
    const chips = units.map(rosterEntry).filter(Boolean);
    if (chips.length) {
      const list = el("div", null, "chips");
      list.append(...chips.map(unitChip));
      item.append(list);
    }
    item.append(button(`▶ Watch from ${clock(from)}`, () => Viewer.watch(from, stop, k), "watch"));
    return item;
  }
  function renderHappened() {
    const list = $("highlights"),
      intro = $("happened-intro");
    list.replaceChildren();
    cardSpans = [];
    $("events").replaceChildren();
    $("lanes").replaceChildren();
    const ready = Boolean(payload?.frames?.length);
    for (const id of ["events-box", "lanes-box"]) $(id).hidden = !ready;
    $("stills-block").hidden = true;
    if (!ready) {
      intro.textContent = "No replay was recorded for this battle.";
      return;
    }
    const highlights = payload.highlights || [];
    if (highlights.length) {
      intro.textContent =
        "Analyst notes, written after reviewing this recording. Each opens the replay a little before the moment. The model's own words appear only inside quotation marks, attributed to it.";
      highlights.forEach((h, k) =>
        list.append(
          momentCard(
            k,
            `Analyst note · ${KINDS[h.kind] || "Moment"} · ${clock(h.time_ms)}`,
            h.title,
            h.text,
            h.units || [],
            span(h).from,
            h.end_ms ?? null,
            { ...span(h), at: h.time_ms },
            k,
          ),
        ),
      );
    } else {
      const key = payload.events.filter((e) => e.key);
      intro.textContent = key.length
        ? "Key moments recorded in this battle. No analyst notes have been written for this run."
        : "No analyst notes or key moments were recorded for this run.";
      key.forEach((e, k) => {
        const from = Math.max(0, e.time_ms - 10000),
          to = e.time_ms + 5000;
        list.append(
          momentCard(
            k,
            `Recorded event · ${clock(e.time_ms)}`,
            e.caption,
            null,
            e.unit ? [e.unit] : [],
            from,
            to,
            { from, to, at: e.time_ms },
          ),
        );
      });
    }
    const shots = (payload.stills || []).filter((shot) => shot.image && shot.status === "embedded");
    $("stills-block").hidden = !shots.length;
    $("stills").replaceChildren(
      ...shots.map((shot) => {
        const figure = el("figure"),
          image = el("img"),
          name = STILLS[shot.trigger] || "Game still";
        const caption = `${name} · spectator camera at ${clock(shot.time_ms)} · not what the model saw`;
        image.src = shot.image;
        image.alt = `${name}: game still at ${clock(shot.time_ms)}`;
        const thumb = button(
          "",
          () => {
            $("still-image").src = shot.image;
            $("still-image").alt = image.alt;
            $("still-caption").textContent = caption;
            $("still-dialog").showModal();
          },
          "thumb",
        );
        thumb.append(image);
        thumb.setAttribute("aria-label", `Enlarge: ${caption}`);
        const text = el("figcaption", caption);
        text.append(
          button(
            `Show ${clock(shot.time_ms)} on the map`,
            () => Viewer.jump(shot.time_ms, true),
            "link",
          ),
        );
        figure.append(thumb, text);
        return figure;
      }),
    );
    $("events-summary").textContent = `All recorded events (${payload.events.length})`;
    $("events").replaceChildren(
      ...payload.events.map((e) => {
        const item = el("li", null, e.key ? "key" : null),
          jump = button("", () => Viewer.jump(e.time_ms, true));
        jump.append(el("b", clock(e.time_ms)), el("span", e.caption));
        item.append(jump);
        return item;
      }),
    );
    renderLanes();
    markHighlights(Viewer.time);
  }
  // One card at most is marked: the note the map caption shows, else the latest key event
  // begun whose window holds the time.
  function markHighlights(time) {
    const marked = payload?.highlights?.length ? Viewer.note : markedAt(cardSpans, time);
    [...$("highlights").children].forEach((card, k) =>
      card.classList.toggle("active", k === marked),
    );
  }

  function unitState(u) {
    if (u.men === 0) return STATES[0];
    if (!u.state?.length) return STATES.find(([key]) => key === "none");
    return (
      STATES.find(
        ([key]) =>
          (u.state || []).includes(key) ||
          (key === "routing" && (u.state || []).includes("shattered")),
      ) || STATES.at(-1)
    );
  }
  // Unit timelines: one lane per unit, coloured by recorded state; blank where unobserved.
  function renderLanes() {
    const box = $("lanes");
    box.replaceChildren();
    if (!payload?.frames?.length || !$("lanes-box").open) return;
    const frames = payload.frames.filter((f) => f.friendly.length || f.enemy.length);
    if (!frames.length) return;
    const width = Math.max(300, Math.round(box.clientWidth)),
      label = Math.min(180, Math.round(width * 0.3)),
      row = 18;
    const t0 = frames[0].time_ms,
      t1 = frames.at(-1).time_ms,
      gap = 1.5 * (payload.sample_interval_ms || 1000);
    const x = (t) => label + ((width - label - 8) * (t - t0)) / Math.max(1, t1 - t0);
    const sides = [...new Set(frames.flatMap((f) => (f.mode?.tickets || []).map((t) => t.side)))];
    const resources = [
      ["Supplies", (f) => f.mode?.supplies],
      ["Army currency", (f) => f.army?.currency],
      ...sides.map((side) => [
        `Tickets (${side})`,
        (f) => f.mode?.tickets?.find((t) => t.side === side)?.tickets,
      ]),
    ].filter(([, pick]) => frames.some((f) => pick(f) != null));
    const lanes = payload.roster.length + resources.length,
      height = lanes * row + 24;
    const chart = svg("svg", {
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": "Recorded state of each unit over the battle",
    });
    chart.style.height = `${height}px`;
    payload.roster.forEach((entry, k) => {
      const y = k * row;
      chart.append(
        svg(
          "text",
          {
            x: 0,
            y: y + 12,
            "font-size": 12,
            fill: entry.side === "friendly" ? "#1c6a96" : "#8f5d00",
          },
          (entry.short === entry.display ? entry.display : `${entry.short} · ${entry.name}`).slice(
            0,
            Math.floor(label / 6.5),
          ),
        ),
      );
      frames.forEach((f, i) => {
        const u = (entry.side === "friendly" ? f.friendly : f.enemy).find(
          (item) => item.id === entry.id,
        );
        if (!u) return;
        const next = frames[i + 1]?.time_ms ?? f.time_ms + 1000,
          until = Math.min(next, f.time_ms + gap);
        chart.append(
          svg("rect", {
            x: x(f.time_ms),
            y: y + 3,
            width: Math.max(1, x(until) - x(f.time_ms)),
            height: row - 6,
            fill: unitState(u)[1],
          }),
        );
      });
      for (const d of payload.decisions)
        if (d.applied_ms != null && d.steps.some((s) => s.unit === entry.id))
          chart.append(
            svg("rect", {
              x: x(d.applied_ms) - 0.5,
              y: y + 1,
              width: 1,
              height: 3,
              fill: d.steps.some((s) => s.unit === entry.id && s.status === "rejected")
                ? "#ad3a2c"
                : "#1d2521",
            }),
          );
    });
    resources.forEach(([name, pick], k) => {
      const y = (payload.roster.length + k) * row,
        values = frames.map((f) => [f.time_ms, pick(f)]).filter(([, v]) => v != null);
      const top = Math.max(1, ...values.map(([, v]) => v));
      chart.append(
        svg("text", { x: 0, y: y + 12, "font-size": 12, fill: "#39423d" }, `${name} (0–${top})`),
        svg("polyline", {
          points: values
            .map(([t, v]) => `${x(t)},${y + row - 3 - ((row - 6) * v) / top}`)
            .join(" "),
          fill: "none",
          stroke: "#39423d",
          "stroke-width": 1.2,
        }),
      );
    });
    for (let m = Math.ceil(t0 / 60000); m * 60000 <= t1; m++)
      chart.append(
        svg(
          "text",
          {
            x: x(m * 60000),
            y: height - 6,
            "font-size": 10,
            fill: "#61675f",
            "text-anchor": "middle",
          },
          `${m}:00`,
        ),
      );
    chart.addEventListener("click", (event) => {
      const rect = chart.getBoundingClientRect(),
        at = ((event.clientX - rect.left) * width) / rect.width;
      if (at < label) return;
      Viewer.jump(t0 + ((at - label) / (width - label - 8)) * (t1 - t0), true);
    });
    const legend = el("p", null, "note");
    for (const [, colour, name] of STATES) {
      const swatch = svg("svg", {
        viewBox: "0 0 10 10",
        width: 10,
        height: 10,
        "aria-hidden": "true",
      });
      swatch.append(svg("rect", { width: 10, height: 10, fill: colour }));
      legend.append(swatch, ` ${name}  `);
    }
    legend.append(
      "· Blank: not observed. Ticks mark new orders (red: rejected). Click a lane to jump there.",
    );
    box.append(chart, legend);
  }

  // Run settings: everything about the run in the viewer that the main reading path omits.
  function openSettings() {
    const entry = entries.get(openKey);
    if (!entry) return;
    const { trial, group } = entry,
      definition = group.definition,
      declared = definition.scenario || {},
      expect = declared.expect || {};
    const role =
      declared.attacker === "player"
        ? "attacker"
        : declared.attacker === "enemy"
          ? "defender"
          : expect.player_defends == null
            ? null
            : expect.player_defends
              ? "defender"
              : "attacker";
    const recorder = definition.recorder,
      imagery = definition.imagery;
    const body = $("settings-body");
    body.replaceChildren(
      keyValues([
        ["Scenario", `${scenario.title} (${declared.name || scenario.name})`],
        ["Map", declared.map],
        ["Battle timer", expect.time_limit_s == null ? null : clock(expect.time_limit_s * 1000)],
        [
          "Enemy AI",
          [
            expect.difficulty && expect.difficulty.replace(/^ai_level_/, "").replaceAll("_", " "),
            expect.ai_stats_modifier && `stats ×${expect.ai_stats_modifier}`,
          ]
            .filter(Boolean)
            .join(" · "),
        ],
        ["Player role", role],
        [
          "Controller",
          [
            controllerName(entry),
            `policy ${trial.policy}`,
            trial.card?.timing === "blocking"
              ? "waits for each reply before reading the battle again; the battle keeps running at 1×"
              : trial.card?.timing,
          ]
            .filter(Boolean)
            .join(" · "),
        ],
        ["Added observation age", `${(trial.delay_ms || 0) / 1000} s`],
        ["Interface track", definition.track],
        [
          "Observation interval",
          definition.observe_ms == null
            ? null
            : `${definition.observe_ms} ms (mod tick ${definition.tick_ms ?? "?"} ms, wait after orders ${definition.interval_ms ?? "?"} ms)`,
        ],
        [
          "Replay recorder",
          recorder == null
            ? "not recorded"
            : recorder.enabled
              ? `on, every ${recorder.interval_ms} ms`
              : "off",
        ],
        [
          "Game stills",
          imagery == null
            ? "not recorded"
            : imagery.enabled
              ? `on (up to ${imagery.max_stills ?? "?"}; never shown to the controller)`
              : "off",
        ],
        ["Source revision", definition.source],
        ["Game build", definition.game?.steam_build_id],
        ["Job and episode", `${trial.instance} / ${trial.episode}`],
        ["Setup checked", trial.setup_checked == null ? null : trial.setup_checked ? "yes" : "no"],
        ["Recording warnings", payload ? payload.warnings.length : "no replay"],
      ]),
    );
    if (declared.brief)
      body.append(details("Scenario brief, as declared", el("p", declared.brief)));
    // Before c916e6c a single-policy job saved its one prompt as system_prompt.md.
    const files = data.prompts?.[trial.instance] || {},
      prompt = files[`${basePolicy(trial)}_prompt.md`] ?? files["system_prompt.md"];
    if (isModel(entry) && prompt != null)
      body.append(
        details(
          `Prompt the model received (${PROMPTS[basePolicy(trial)] || trial.policy})`,
          el("pre", prompt, "raw"),
        ),
      );
    $("settings-dialog").showModal();
  }

  function downloads() {
    $("download-report").addEventListener("click", () => {
      saveJSON(
        {
          ...(synthetic ? { notice: NOTICE } : {}),
          evidence_kind: data.evidence_kind,
          report,
          comparisons: data.comparisons,
          scenarios: data.scenarios,
          setup_only: data.setup_only,
        },
        `wh3-${synthetic ? "SYNTHETIC-DEMO-" : ""}report.json`,
      );
      $("export-status").textContent = "Report JSON download ready.";
    });
    $("download-replay").addEventListener("click", () => {
      const entry = entries.get(openKey);
      if (!payload || !entry) return;
      saveJSON(
        {
          ...(synthetic ? { notice: NOTICE } : {}),
          evidence_kind: data.evidence_kind,
          trial: entry.trial,
          replay: payload,
        },
        `wh3-${synthetic ? "SYNTHETIC-DEMO-" : ""}replay-${entry.trial.instance}-${entry.trial.episode}.json`,
      );
      $("export-status").textContent = "Replay JSON download ready.";
    });
  }

  function setup() {
    if (synthetic) $("demo-banner").hidden = false;
    $("watch-featured").addEventListener("click", () => {
      if (featured)
        Viewer.watch(
          span(featured).from,
          featured.end_ms ?? null,
          payload.highlights.indexOf(featured),
        );
    });
    $("watch-full").addEventListener("click", () => Viewer.watch(0));
    $("run-select").addEventListener("change", (e) => openRun(e.target.value, false));
    $("open-settings").addEventListener("click", openSettings);
    $("close-settings").addEventListener("click", () => $("settings-dialog").close());
    $("close-still").addEventListener("click", () => $("still-dialog").close());
    $("lanes-box").addEventListener("toggle", renderLanes);
    let laneWidth = 0;
    new ResizeObserver(() => {
      const width = Math.round($("lanes").clientWidth);
      if (width !== laneWidth) {
        laneWidth = width;
        renderLanes();
      }
    }).observe($("lanes"));
    Viewer.onTime(markHighlights);
    downloads();
    if (!data.scenarios.length) {
      $("question").textContent = "No recorded battles in this report";
      for (const id of ["viewer", "happened", "compare"]) $(id).hidden = true;
      for (const id of [
        "watch-featured",
        "watch-full",
        "run-select",
        "open-settings",
        "download-replay",
      ])
        $(id).disabled = true;
      return;
    }
    if (data.scenarios.length > 1) {
      $("scenario").replaceChildren(
        ...data.scenarios.map((item, index) => {
          const option = el("option", item.title);
          option.value = String(index);
          return option;
        }),
      );
      $("scenario").addEventListener("change", (e) => renderScenario(Number(e.target.value)));
      $("scenario-pick").hidden = false;
    }
    renderScenario(0);
  }
  setup();
})();
