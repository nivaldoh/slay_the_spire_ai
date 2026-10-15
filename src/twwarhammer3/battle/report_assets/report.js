// Runs after replay.js in the same script and uses its helpers (el, svg, clock, Viewer, ...).
(() => {
  const $ = (id) => document.getElementById(id);
  const data = JSON.parse($("report-data").textContent);
  const report = data.report;
  const synthetic = data.evidence_kind === "synthetic";
  const NOTICE =
    "SYNTHETIC DEMO: invented values that exercise the report; not benchmark evidence.";
  // How each scenario's featured battle was chosen; curated picks show the commander's record.
  const FEATURED = {
    selected: "Selected for its analyst notes",
    first_model_run: "The first finished model battle",
    first_run: "The first recorded battle",
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
  const BATTLE_TYPES = {
    siege: "Siege",
    survival: "Survival",
    conquest: "Conquest",
    domination: "Domination",
    ambush: "Ambush",
    river_crossing_battle: "Chokepoint",
    unfortified_settlement: "Settlement",
    underground_intercept: "Subterranean",
    free_for_all: "Free-for-all",
  };
  const AGE_WINDOW_MS = 60000; // one minute of a battle in the real-time chart
  const entries = new Map();
  report.groups.forEach((group, g) =>
    group.trials.forEach((trial, t) => {
      const key = `g${g}-t${t}`;
      entries.set(key, { key, trial, group, g, battle: data.battles[key] });
    }),
  );
  const shown = new Set(data.scenarios.flatMap((item) => item.battles));
  const cache = new Map();
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let scenario = null,
    openKey = null,
    payload = null,
    featured = null;

  const who = (entry) => entry.battle.commander;
  const isModel = (entry) => who(entry).kind === "model";
  const fullName = (entry) => [who(entry).name, who(entry).detail].filter(Boolean).join(" · ");
  const percent = (share) => `${Math.round(share * 100)}%`;
  // Never round a loss up to the win line: 99.8% broken reads 99%.
  const broken = (share) =>
    share >= 1 ? "100%" : `${Math.min(99, Math.floor(Math.round(share * 1e4) / 100))}%`;
  const median = (values) => quantile(values, 0.5);
  function quantile(values, q) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b),
      at = (sorted.length - 1) * q,
      low = Math.floor(at);
    return sorted[low] + (sorted[Math.ceil(at)] - sorted[low]) * (at - low);
  }
  function wilson(k, n) {
    const z = 1.96,
      p = k / n,
      d = 1 + (z * z) / n;
    const centre = (p + (z * z) / (2 * n)) / d,
      half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
    return [Math.max(0, centre - half), Math.min(1, centre + half)];
  }
  function date(value, year = true) {
    const parsed = new Date(value);
    return value && !Number.isNaN(parsed.getTime())
      ? parsed.toLocaleDateString("en-GB", {
          day: "numeric",
          month: "short",
          ...(year ? { year: "numeric" } : {}),
          timeZone: "UTC",
        })
      : null;
  }
  const on = (entry, year = true) => {
    const day = date(entry.battle.date, year);
    return day ? ` · ${day}` : "";
  };
  // The prompt file a model trial's job saved; before c916e6c a single-policy job saved its
  // one prompt as system_prompt.md.
  const promptOf = (trial) => {
    const files = data.prompts?.[trial.instance] || {};
    return files[`${trial.policy.split("@")[0]}_prompt.md`] ?? files["system_prompt.md"];
  };
  // Always the engine's result, with the battle clock duration. A battle that reached the
  // scenario's timer ended there, whatever older jobs recorded as `ended_by`.
  function outcome(entry) {
    const trial = entry.trial;
    if (!trial.valid)
      return {
        text: `Did not finish${trial.error ? `: ${trial.error}` : ""}`,
        short: "Did not finish",
        tone: "failed",
      };
    const engine = trial.engine_outcome || trial.outcome,
      word = { won: "Won", lost: "Lost", draw: "Draw" }[engine] || capital(String(engine));
    const ms = trial.battle_ms ?? (trial.battle_s == null ? null : trial.battle_s * 1000),
      duration = ms == null ? null : clock(ms);
    const limit = entry.group.definition.scenario?.expect?.time_limit_s;
    const timeLimit = trial.ended_by === "time_limit" || Boolean(limit && ms >= limit * 1000);
    const text = timeLimit
      ? `${word} at the time limit${duration ? ` (${duration})` : ""}`
      : duration
        ? `${word} ${engine === "draw" ? "after" : "in"} ${duration}`
        : word;
    const short = `${word}${duration ? ` ${duration}` : ""}${timeLimit ? " (time limit)" : ""}`;
    return { text, short, tone: engine };
  }
  // "ai_level_very_hard" -> "very hard": the game's battle AI difficulty, where recorded.
  const level = (item) => item.difficulty?.replace(/^ai_level_/, "").replaceAll("_", " ");
  const won = (entry) =>
    entry.trial.valid && (entry.trial.engine_outcome || entry.trial.outcome) === "won";
  function context(entry) {
    return { kind: who(entry).kind, rule: who(entry).detail, synthetic };
  }
  function scenarioEntries(item = scenario) {
    return item.battles.map((key) => entries.get(key));
  }

  // A shared tooltip for chart marks; marks are buttons, so focus shows it too.
  function tip(node, lines) {
    const show = () => {
      const box = $("tip"),
        rect = node.getBoundingClientRect();
      box.replaceChildren(el("b", lines[0]), ...lines.slice(1).map((line) => el("div", line)));
      box.hidden = false;
      const width = box.offsetWidth,
        height = box.offsetHeight;
      box.style.left = `${Math.max(8, Math.min(innerWidth - width - 8, rect.left + rect.width / 2 - width / 2))}px`;
      box.style.top = `${rect.top - height - 8 < 8 ? rect.bottom + 8 : rect.top - height - 8}px`;
    };
    const hide = () => {
      $("tip").hidden = true;
    };
    node.addEventListener("mouseenter", show);
    node.addEventListener("focus", show);
    node.addEventListener("mouseleave", hide);
    node.addEventListener("blur", hide);
    node.setAttribute("aria-label", lines.join(". "));
  }
  // The battle's measures in a few words; absent ones are left out, never zeroed.
  function measures(entry) {
    const m = entry.trial.measures || {},
      b = entry.battle,
      out = [];
    if (b.progress != null) out.push(`enemy army broken ${broken(b.progress)}`);
    if (b.own_left != null) out.push(`own soldiers alive ${percent(b.own_left)}`);
    const units = m.units || {};
    if (units.friendly && units.enemy)
      out.push(
        `units still fighting: own ${units.friendly.active} of ${units.friendly.registered}, enemy ${units.enemy.active} of ${units.enemy.registered}`,
      );
    const points = m.objective_time?.points || [];
    if (points.length)
      out.push(
        `objectives held ${points.map((p) => (p.share == null ? "not recorded" : percent(p.share))).join(", ")} of the time observed`,
      );
    const r = m.resources || {};
    if (r.status === "available") {
      if (r.supplies_left != null) out.push(`${r.supplies_left} supplies left`);
      if (r.build) out.push(`${r.build} built`);
      if (r.reinforce) out.push(`${r.reinforce} reinforcements bought`);
    }
    // A battle that did not finish keeps its last observation, labelled so.
    if (out.length && m.basis === "last_observation") out[0] = `at failure: ${out[0]}`;
    return out;
  }
  // One mark per battle: filled won, hollow lost, half draw, a cross when it did not finish.
  function dot(entry, onTrack = false) {
    const result = outcome(entry),
      progress = entry.battle.progress;
    const node = button("", () => openRun(entry.key, true), `dot ${result.tone}`);
    if (onTrack && progress == null && entry.trial.valid) node.classList.add("unknown");
    node.dataset.key = entry.key;
    const plans = entry.battle.timing?.plans || [],
      ages = plans.length ? plans : entry.battle.timing?.ages || [];
    const soldiers = entry.trial.measures?.soldiers?.enemy;
    tip(
      node,
      [
        fullName(entry),
        `${result.text}${on(entry)}`,
        ...(progress == null && soldiers?.net_losses != null
          ? [
              `Enemy still fighting not recorded (${soldiers.net_losses} of ${soldiers.registered} soldiers lost)`,
            ]
          : measures(entry).slice(0, 2)),
        ages.length
          ? `Median ${plans.length ? "plan" : "order"} age ${seconds(median(ages))}`
          : null,
        data.replays[entry.key] ? "Click to watch" : "No replay recorded",
      ].filter(Boolean),
    );
    return node;
  }
  function markCurrent() {
    for (const node of document.querySelectorAll("[data-key]"))
      node.setAttribute("aria-current", String(node.dataset.key === openKey));
    for (const row of document.querySelectorAll("#matrix tr[data-scenario]"))
      row.setAttribute("aria-current", String(row.dataset.scenario === scenario?.id));
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

  function renderFacts() {
    const all = [...shown].map((key) => entries.get(key));
    const models = [...new Set(all.filter(isModel).map((entry) => who(entry).name))].sort();
    const scripted = new Set(
      all.filter((entry) => who(entry).kind === "scripted").map((e) => who(e).name),
    );
    const dated = all
      .map((entry) => entry.battle.date)
      .filter((value) => date(value))
      .sort();
    // "14–15 Oct 2026" within a month, else both dates in full.
    const [from, to] = [date(dated[0]), date(dated.at(-1))];
    const span =
      from === to
        ? from
        : from.split(" ").slice(1).join(" ") === to.split(" ").slice(1).join(" ")
          ? `${from.split(" ")[0]}–${to}`
          : `${from} – ${to}`;
    const fact = (strong, text) => {
      const node = el("span");
      node.append(el("b", strong), text ? ` ${text}` : "");
      return node;
    };
    $("facts").replaceChildren(
      fact(all.length, `battles in ${data.scenarios.length} scenarios`),
      fact(models.join(", ") || "no models"),
      ...(scripted.size ? [fact(scripted.size, "scripted baselines")] : []),
      ...(span ? [el("span", span)] : []),
    );
  }

  // Charts on a shared 0–100% axis; `pad` px at the left hold battles without a value.
  const along = (at, pad = 0) => `calc(${pad}px + (100% - ${pad}px) * ${at})`;
  function axis(ticks, pad = 0) {
    const node = el("div", null, "axis");
    if (pad) node.append(el("span", "n/a", "na"));
    for (const [at, label] of ticks) {
      const tick = el("span", label);
      tick.style.left = along(at, pad);
      node.append(tick);
    }
    return node;
  }
  const BROKEN_TICKS = [
    [0, "0%"],
    [0.5, "50%"],
    [1, "100%"],
  ];
  // Dots stack upward where battles land within 4% of each other.
  function track(items, pad, step = 16) {
    const node = el("div", null, "track"),
      levels = new Map();
    node.style.setProperty("--pad", `${pad}px`);
    let top = 0;
    for (const entry of [...items].sort(
      (a, b) => (a.battle.progress ?? -1) - (b.battle.progress ?? -1),
    )) {
      const x = entry.battle.progress,
        bin = x == null ? -1 : Math.round(x * 25),
        level = levels.get(bin) || 0;
      levels.set(bin, level + 1);
      top = Math.max(top, level);
      const mark = dot(entry, true);
      mark.style.left = x == null ? "7px" : along(x, pad);
      mark.style.bottom = `${10.5 + level * step}px`;
      node.append(mark);
    }
    node.style.height = `${22 + top * step}px`;
    return node;
  }
  function header(label, sub, extra) {
    const node = el("div");
    node.append(el("b", label));
    if (sub) node.append(el("small", sub));
    if (extra) node.append(extra);
    return node;
  }
  function whoCell(row, extra) {
    const cell = el("div", null, "who-cell");
    cell.append(el("strong", row.name), el("small", row.detail));
    if (row.harnesses > 1) {
      const mark = el("sup", "†", "versions");
      mark.title = `Battles from ${row.harnesses} harness versions (controller, interface or game code). Run settings names each battle's; the report JSON keeps per-version groups.`;
      cell.firstChild.append(mark);
    }
    if (extra) cell.append(el("small", extra));
    return cell;
  }

  // The hero: the first group's largest controlled comparison, battle by battle.
  function renderHeadline() {
    const group = data.scenarios[0]?.group;
    const item = data.scenarios
      .filter((s) => s.group === group && s.controlled)
      .sort((a, b) => b.controlled.launches - a.controlled.launches)[0];
    if (!item) return;
    const keys = new Set(item.controlled.battles),
      rows = item.rows
        .map((row) => ({
          row,
          items: row.battles.filter((k) => keys.has(k)).map((k) => entries.get(k)),
        }))
        .filter((r) => r.items.length);
    const box = $("scoreboard"),
      title = button(item.title, pick(data.scenarios.indexOf(item)), "scenario");
    box.replaceChildren(
      el("p", `Controlled comparison · ${item.controlled.launches} rounds`, "eyebrow"),
      title,
    );
    const pad = rows.some((r) => r.items.some((e) => e.battle.progress == null)) ? 30 : 0;
    const list = el("div", null, "headline");
    list.append(el("span"), axis(BROKEN_TICKS, pad), el("span"), el("span", "order age", "count"));
    for (const { row, items } of rows) {
      const valid = items.filter((e) => e.trial.valid),
        name = el("span", row.name, "name");
      name.title = row.detail;
      if (row.short) name.append(el("small", row.short));
      const stats = rowStats({ ...row, battles: items.map((e) => e.key) });
      list.append(
        name,
        track(items, pad, 5),
        el("span", `${valid.filter(won).length}/${valid.length} won`, "count"),
        el(
          "span",
          stats.ages.length ? seconds(stats.box[2]) : stats.timed ? "no orders" : "–",
          "count",
        ),
      );
    }
    box.append(
      list,
      el(
        "p",
        `Enemy army broken at the end (● won ○ lost) and median order age; each commander ${item.controlled.once ? "once " : ""}in every round (a fresh game launch), one harness${level(item) ? `, against the game's AI on ${level(item)}` : ""}${item.split === "development" ? "; a development scenario" : ""}.`,
        "note",
      ),
    );
    box.hidden = false;
  }

  function renderScenario(index, open = true) {
    scenario = data.scenarios[index];
    $("scenario").value = String(index);
    $("question").textContent = scenario.question || scenario.title;
    $("scenario-title").textContent = [
      scenario.question && scenario.title,
      level(scenario) && `enemy: the game's AI on ${level(scenario)}`,
    ]
      .filter(Boolean)
      .join(" · ");
    $("challenge").textContent = scenario.challenge || "";
    $("results-scenario").textContent = scenario.title;
    document.title = `${synthetic ? "SYNTHETIC DEMO — " : ""}${scenario.title} · WH3 Commander Bench`;
    $("run-select").replaceChildren(
      ...scenarioEntries().map((entry) => {
        const option = el(
          "option",
          `${who(entry).name}${who(entry).short ? ` (${who(entry).short})` : ""} · ${outcome(entry).short}${on(entry, false)}`,
        );
        option.value = entry.key;
        return option;
      }),
    );
    renderRoutes();
    renderRows();
    renderLatency();
    markCurrent();
    return open ? openRun(scenario.featured, false) : null;
  }

  function renderRunLine(entry) {
    const line = $("run-line"),
      row = scenario.rows.find((item) => item.battles.includes(entry.key));
    line.replaceChildren();
    if (synthetic) line.append(el("span", "SYNTHETIC DEMO", "tag synthetic"));
    else if (entry.key === scenario.featured) {
      const tag = el("span", "Featured battle", "tag");
      tag.title = FEATURED[scenario.featured_reason];
      line.append(tag);
    }
    const title = el("span", null, "title");
    title.append(el("strong", who(entry).name, "name"), el("span", who(entry).detail, "detail"));
    const result = outcome(entry),
      status = el("span", null, "result");
    status.append(el("span", result.text, result.tone));
    if (row) {
      const items = row.battles.map((key) => entries.get(key)),
        valid = items.filter((e) => e.trial.valid),
        failed = items.length - valid.length;
      status.append(
        el(
          "span",
          items.length === 1
            ? "its only battle here"
            : `won ${valid.filter(won).length} of its ${valid.length} here${failed ? ` (+${failed} did not finish)` : ""}`,
          "sample",
        ),
      );
    }
    line.append(title, status);
    const facts = measures(entry);
    if (entry.key === scenario.featured && scenario.featured_reason === "selected")
      facts.push("featured for its analyst notes, not as typical");
    if (facts.length) line.append(el("span", facts.join(" · "), "measures"));
  }

  async function openRun(key, scroll) {
    openKey = key;
    const entry = entries.get(key);
    if (scenario && !scenario.battles.includes(key))
      renderScenario(
        data.scenarios.findIndex((item) => item.battles.includes(key)),
        false,
      );
    $("run-select").value = key;
    renderRunLine(entry);
    markCurrent();
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
    else Viewer.clear(problem || "No replay was recorded for this battle.");
    $("map-army").textContent = `${who(entry).name}'s army`;
    const highlights = payload?.highlights || [];
    featured = highlights.find((h) => h.feature) || highlights[0] || null;
    $("watch-featured").hidden = !featured;
    $("watch-featured").textContent = featured?.feature ? "▶ Key maneuver" : "▶ Analyst note 1";
    $("watch-full").disabled = !payload?.frames?.length;
    $("download-replay").disabled = !payload;
    renderChapters();
    if (scroll) Viewer.reveal();
  }

  // Same battle, different plans: every friendly path over the whole battle, one framing.
  function renderRoutes() {
    const box = $("routes");
    box.replaceChildren();
    const routes = scenarioEntries().filter((entry) => entry.battle.route);
    const points = routes.flatMap((entry) => [
      ...entry.battle.route.friendly.flatMap((u) => u.path),
      ...entry.battle.route.enemy.map((u) => u.at),
    ]);
    if (!points.length) {
      box.append(el("p", "No positions were recorded for this scenario.", "caption"));
      return;
    }
    const xs = points.map((p) => p[0]),
      zs = points.map((p) => p[1]);
    let [x0, z0, x1, z1] = [Math.min(...xs), Math.min(...zs), Math.max(...xs), Math.max(...zs)];
    const margin = Math.max(30, 0.06 * Math.max(x1 - x0, z1 - z0));
    [x0, z0, x1, z1] = [x0 - margin, z0 - margin, x1 + margin, z1 + margin];
    const aspect = Math.max(0.5, Math.min(1.25, (z1 - z0) / (x1 - x0)));
    const w = 200,
      h = Math.round(w * aspect),
      scale = Math.min(w / (x1 - x0), h / (z1 - z0));
    const px = (x) => w / 2 + (x - (x0 + x1) / 2) * scale,
      py = (z) => h / 2 - (z - (z0 + z1) / 2) * scale;
    const ground = scenario.terrain ? blockedPath(scenario.terrain, px, py, scale) : "";
    for (const row of scenario.rows) {
      const items = row.battles.map((key) => entries.get(key)).filter((e) => e.battle.route);
      // An army that never moved (hold position) has no route to show.
      if (!items.some((e) => e.battle.route.friendly.some((u) => u.path.length > 2))) continue;
      const group = el("section", null, "route-group"),
        list = el("div", null, "route-list");
      for (const entry of items) {
        const map = svg("svg", { viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" });
        if (ground) map.append(svg("path", { d: ground, fill: "#33454f" }));
        for (const u of entry.battle.route.enemy)
          map.append(
            svg("path", {
              d: `M${px(u.at[0])} ${py(u.at[1]) - 3.2}l3.2 3.2-3.2 3.2-3.2-3.2z`,
              fill: TEAM.enemy,
              opacity: 0.9,
            }),
          );
        for (const u of entry.battle.route.friendly) {
          const line = u.path.map((p) => `${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}`).join(" ");
          const [sx, sz] = u.path[0],
            [ex, ez] = u.path.at(-1);
          map.append(
            svg("rect", {
              x: px(sx) - 2,
              y: py(sz) - 2,
              width: 4,
              height: 4,
              fill: "none",
              stroke: TEAM.friendly,
              "stroke-width": 1,
              opacity: 0.8,
            }),
            svg("polyline", {
              points: line,
              fill: "none",
              stroke: TEAM.friendly,
              "stroke-width": 1.4,
              "stroke-linejoin": "round",
              "stroke-linecap": "round",
              opacity: 0.85,
            }),
            u.end === "down"
              ? svg("path", {
                  d: `M${px(ex) - 2.6} ${py(ez) - 2.6}l5.2 5.2m0-5.2l-5.2 5.2`,
                  stroke: "#ffffff",
                  "stroke-width": 1.4,
                })
              : svg("circle", {
                  cx: px(ex),
                  cy: py(ez),
                  r: 2.6,
                  fill: u.end === "up" ? TEAM.friendly : "none",
                  stroke: TEAM.friendly,
                  "stroke-width": 1.2,
                }),
          );
        }
        const result = outcome(entry),
          label = el("span");
        label.append(el("b", result.short, result.tone));
        if (entry.battle.progress != null && !won(entry))
          label.append(` · ${broken(entry.battle.progress)} broken`);
        const card = button("", () => openRun(entry.key, true), `route ${result.tone}`);
        card.dataset.key = entry.key;
        card.setAttribute(
          "aria-label",
          `Watch ${fullName(entry)}: ${result.text}. Map of every path its army took.`,
        );
        card.append(map, label);
        list.append(card);
      }
      // Three maps per commander, in order; the rest behind a button.
      if (items.length > 3) {
        const more = button(
          `+${items.length - 3} more`,
          () => {
            list.classList.add("open");
            more.remove();
          },
          "more",
        );
        list.append(more);
      }
      group.append(whoCell(row), list);
      box.append(group);
    }
    if (!box.childElementCount)
      box.append(el("p", "No commander's army moved in this scenario.", "caption"));
  }

  // How far each commander got: rows of the scenario, every column a small chart.
  function rowStats(row) {
    const items = row.battles.map((key) => entries.get(key));
    const timings = items.map((entry) => entry.battle.timing).filter(Boolean);
    const valid = items.filter((entry) => entry.trial.valid);
    const instances = new Set(valid.map((entry) => entry.trial.instance));
    const plans = timings.flatMap((t) => t.plans);
    // A commander's model plans: their age is the model's latency, the executor's is not.
    const ages = plans.length ? plans : timings.flatMap((t) => t.ages);
    return {
      items,
      valid,
      timed: timings.length,
      won: valid.filter(won).length,
      ages,
      executor: plans.length ? median(timings.flatMap((t) => t.ages)) : null,
      box: [0.1, 0.25, 0.5, 0.75, 0.9].map((q) => quantile(ages, q)),
      // A 95% interval only for five or more finished battles from separate launches of one harness.
      interval:
        valid.length >= 5 && instances.size === valid.length && row.harnesses === 1
          ? wilson(valid.filter(won).length, valid.length)
          : null,
      usd: items.every((entry) => entry.trial.llm?.usd != null)
        ? items.reduce((sum, entry) => sum + entry.trial.llm.usd, 0) / items.length
        : null,
    };
  }
  const niceMax = (value, step) => Math.max(step, Math.ceil(value / step) * step);
  function renderRows() {
    const box = $("rows"),
      stats = scenario.rows.map((row) => ({ row, ...rowStats(row) }));
    const pad = scenarioEntries().some((entry) => entry.battle.progress == null) ? 30 : 0;
    const ageMax = niceMax(Math.max(0, ...stats.map((s) => s.box[4] ?? 0)), 5);
    const head = el("div", null, "rows-head");
    head.append(
      header("Commander"),
      header(
        "Enemy army broken when the battle ended",
        "dead or fleeing; each mark is one battle: ● won ○ lost × did not finish",
        axis(BROKEN_TICKS, pad),
      ),
      header("Won", "of finished"),
      header(
        "Order age",
        "how old its view of the battle was when orders reached the game",
        axis(
          [
            [0, "0 s"],
            [0.5, `${ageMax / 2} s`],
            [1, `${ageMax} s`],
          ],
          0,
        ),
      ),
      header("Cost", "per battle"),
    );
    box.replaceChildren(head);
    for (const s of stats) {
      const row = el("div", null, `row ${s.row.kind}`),
        trackCell = el("div", null, "track-cell");
      trackCell.dataset.label = "Enemy army broken";
      trackCell.append(track(s.items, pad));
      const wonCell = el("div", null, "won-cell"),
        count = el("b", String(s.won));
      count.append(el("span", ` / ${s.valid.length}`));
      wonCell.append(count);
      const failed = s.items.length - s.valid.length;
      if (failed) wonCell.append(el("small", `+${failed} did not finish`));
      if (s.interval)
        wonCell.append(el("small", `95% CI ${percent(s.interval[0])}–${percent(s.interval[1])}`));
      // A box plot: whiskers at the 10th and 90th percentiles, the middle half boxed.
      const ageCell = el("div", null, "age-cell");
      ageCell.dataset.label = s.executor != null ? "Plan age" : "Order age";
      if (!s.ages.length) ageCell.append(el("small", s.timed ? "no orders" : "not recorded"));
      else {
        const plot = el("div", null, "boxplot"),
          at = (v) => `${(Math.min(v, ageMax) / ageMax) * 100}%`;
        const whisker = el("i", null, "whisker"),
          iqr = el("i", null, "iqr"),
          mid = el("i", null, "mid");
        whisker.style.left = at(s.box[0]);
        whisker.style.width = `calc(${at(s.box[4])} - ${at(s.box[0])})`;
        iqr.style.left = at(s.box[1]);
        iqr.style.width = `calc(${at(s.box[3])} - ${at(s.box[1])})`;
        mid.style.left = at(s.box[2]);
        plot.append(whisker, iqr, mid);
        tip(plot, [
          `${s.executor != null ? "Plan" : "Order"} age, ${s.ages.length} batches in ${s.items.length} battles`,
          `median ${seconds(s.box[2])} · middle half ${seconds(s.box[1])}–${seconds(s.box[3])}`,
          `10th–90th percentile ${seconds(s.box[0])}–${seconds(s.box[4])}`,
        ]);
        plot.tabIndex = 0;
        ageCell.append(plot, el("span", seconds(s.box[2]), "value"));
        if (s.executor != null)
          ageCell.append(
            el("small", `model plans; unit skills act on ${seconds(s.executor)}-old views`),
          );
      }
      const cost = el(
        "div",
        s.row.kind !== "model" ? "$0" : s.usd == null ? "—" : money(s.usd),
        "cost-cell",
      );
      cost.dataset.label = "Cost / battle";
      row.append(whoCell(s.row), trackCell, wonCell, ageCell, cost);
      box.append(row);
    }
    const key = el("div", null, "phone-key");
    key.append(
      el("small", "Enemy army broken: ● won ○ lost × did not finish"),
      axis(BROKEN_TICKS, pad),
    );
    head.after(key);
    if (stats.some((s) => s.row.harnesses > 1))
      box.append(
        el(
          "p",
          "† Battles from more than one harness version; Run settings names each battle's.",
          "rows-foot",
        ),
      );
  }

  // The battle doesn't wait: how old each commander's latest view was, second by second.
  function renderLatency() {
    const box = $("latency"),
      lede = $("realtime-lede");
    box.replaceChildren();
    const stats = scenario.rows
      .map((row) => {
        const s = rowStats(row);
        // The commander's earliest finished battle with replies: never chosen by outcome.
        const sample = s.items.find((e) => e.trial.valid && e.battle.timing?.replies.length);
        return { row, ...s, sample };
      })
      .filter((s) => s.sample && s.ages.length);
    $("show-lag").hidden = !stats.length;
    if (!stats.length) {
      lede.textContent = "No orders with a measured age were recorded in this scenario.";
      return;
    }
    // The lede quotes age and movement from the same battles: those with the 1 Hz recorder.
    const model = stats
      .filter((s) => s.row.kind === "model" && s.executor == null)
      .map((s) => {
        const measured = s.items.filter((e) => e.battle.timing?.moved.length);
        return {
          ...s,
          measured,
          moved: measured.flatMap((e) => e.battle.timing.moved),
          measuredAges: measured.flatMap((e) => e.battle.timing.ages),
        };
      })
      .sort((a, b) => b.moved.length - a.moved.length || b.ages.length - a.ages.length)[0];
    lede.replaceChildren();
    const twin = model && stats.filter((s) => s.row.name === model.row.name).length > 1;
    if (model && twin)
      model.row = { ...model.row, name: `${model.row.name} (${model.row.detail})` };
    if (model?.moved.length) {
      const n = model.measured.length;
      lede.append(
        `The game runs at normal speed while a model thinks. In ${n === 1 ? "one battle" : `${n} battles`} here, orders from ${model.row.name} reached the game based on a view of the battle a median `,
        el("strong", seconds(median(model.measuredAges))),
        " old; by then the farthest-moving unit in view had moved a median ",
        el("strong", `${Math.round(median(model.moved))} m`),
        ".",
      );
    } else if (model) {
      lede.append(
        `The game runs at normal speed while a model thinks. Here orders from ${model.row.name} reached the game based on a view of the battle a median `,
        el("strong", seconds(median(model.ages))),
        ` old (${model.ages.length} batches of orders).`,
      );
    } else lede.textContent = "The game runs at normal speed while each commander decides.";
    const yMax = AGE_SCALE_S; // shared with the replay's view-age band; taller teeth get a caret
    const head = el("div", null, "lat-head");
    head.append(
      header("Commander"),
      header(
        "Age of the commander's latest view of the battle",
        `one minute of its first finished battle here, 0–${yMax} s; each drop is a reply, including replies that kept the current orders`,
        axis(
          [
            [0, "+0 s"],
            [0.5, "+30 s"],
            [1, "+60 s"],
          ],
          0,
        ),
      ),
      header("Typical order age", "replies with new orders"),
    );
    box.append(head, el("p", `One minute per row · 0–${yMax} s`, "phone-key"));
    for (const s of stats) {
      const row = el("div", null, "lat-row"),
        chart = svg("svg", {
          viewBox: "0 0 600 60",
          preserveAspectRatio: "none",
          role: "img",
          "aria-label": `${s.row.name}: age of its latest view over one minute, 0 to ${yMax} s`,
        });
      const [t0, t1] = windowOf(s.sample),
        x = (t) => ((t - t0) / (t1 - t0)) * 600,
        y = (age) => 60 - (Math.min(age, yMax) / yMax) * 56;
      for (let tick = yMax > 15 ? 10 : 5; tick < yMax; tick += yMax > 15 ? 10 : 5)
        chart.append(svg("line", { x1: 0, x2: 600, y1: y(tick), y2: y(tick), class: "grid" }));
      const series = ageSeries(s.sample.battle.timing.replies, [t0, t1]);
      chart.append(
        svg("path", {
          d: `M${x(t0)} 60${series.map(([t, a]) => `L${x(t).toFixed(1)} ${y(a).toFixed(1)}`).join("")}L${x(t1)} 60Z`,
          class: `age ${s.row.kind}`,
        }),
      );
      for (const [t, a] of series.filter(([, a]) => a > yMax))
        chart.append(svg("path", { d: `M${x(t) - 4} 0h8l-4 5z`, class: "clipped" }));
      const plot = el("div", null, "age-chart");
      plot.append(chart);
      const value = el("div", null, "age-value");
      value.append(
        el("b", seconds(s.box[2])),
        el("small", `median · 90th percentile ${seconds(s.box[4])}`),
        el(
          "small",
          s.executor != null
            ? "model plans; unit skills act on fresh views"
            : `${s.ages.length} replies with orders in ${s.items.length} battle${s.items.length > 1 ? "s" : ""}`,
        ),
      );
      row.append(whoCell(s.row), plot, value);
      box.append(row);
    }
    const ratios = scenarioEntries()
      .map((entry) => entry.trial.clock_ratio)
      .filter((value) => value != null);
    if (ratios.length)
      box.append(
        el(
          "p",
          `Battle clock against wall clock: ${Math.min(...ratios).toFixed(2)}–${Math.max(...ratios).toFixed(2)}× over ${ratios.length} battles here; the game never paused for a reply.`,
          "rows-foot",
        ),
      );
  }
  const windowOf = (entry) => {
    const first = entry.battle.timing.replies[0][1];
    return [first, first + AGE_WINDOW_MS];
  };

  // All scenarios: each battle's outcome by model, and the scripted baselines together.
  function families() {
    const all = [...shown].map((key) => entries.get(key));
    const names = [...new Set(all.filter(isModel).map((entry) => who(entry).family))].sort();
    if (all.some((entry) => who(entry).kind === "scripted")) names.push("Scripted");
    return names;
  }
  function outcomeCell(item, family) {
    const cell = el("div", null, "cell"),
      mine = scenarioEntries(item).filter((entry) => who(entry).family === family);
    if (!mine.length) {
      cell.append(el("span", family === "Scripted" ? "no baseline yet" : "–", "none"));
      return cell;
    }
    for (const entry of mine) cell.append(dot(entry));
    const valid = mine.filter((entry) => entry.trial.valid);
    cell.append(
      el(
        "span",
        valid.length ? `${valid.filter(won).length}/${valid.length}` : "did not finish",
        "count",
      ),
    );
    // A cell that pools several commanders or harness versions says so.
    const rows = item.rows.filter((row) => row.family === family);
    if (rows.length > 1 || rows.some((row) => row.harnesses > 1)) {
      const mark = el("span", "†", "pooled");
      mark.title = rows
        .map((row) => {
          const n = row.battles.filter((key) => entries.get(key).trial.valid);
          return `${row.name} · ${row.detail}: ${n.filter((key) => won(entries.get(key))).length}/${n.length}${row.harnesses > 1 ? `, ${row.harnesses} harness versions` : ""}`;
        })
        .join("\n");
      cell.append(mark);
    }
    return cell;
  }
  const pick = (index) => () => {
    renderScenario(index);
    $("watch").scrollIntoView();
  };
  function renderMatrix() {
    const all = families(),
      box = $("matrix");
    box.replaceChildren();
    const groups = [...new Set(data.scenarios.map((item) => item.group))];
    for (const group of groups) {
      const items = data.scenarios.filter((item) => item.group === group);
      // Pilots predate the benchmark's setup checks: folded away by default.
      const fold = details(`${group} · ${items.length}`);
      fold.open = groups.length === 1 || !/pilot/i.test(group);
      // Fixed column widths, so each model's column lines up across the groups.
      const table = el("table"),
        head = el("tr"),
        columns = el("colgroup");
      columns.append(el("col"), ...all.map(() => el("col")));
      columns.firstChild.style.width = "40%";
      for (const label of [
        "Scenario",
        ...all.map((f) => (f === "Scripted" ? "Scripted baselines" : f)),
      ]) {
        const th = el("th", label);
        th.scope = "col";
        head.append(th);
      }
      const thead = el("thead"),
        body = el("tbody");
      thead.append(head);
      for (const item of items) {
        const tr = el("tr"),
          name = el("td");
        tr.dataset.scenario = item.id;
        name.append(button(item.title, pick(data.scenarios.indexOf(item)), "scenario"));
        const sub = [
          BATTLE_TYPES[item.battle_type],
          [item.armies?.friendly, item.armies?.enemy].filter(Boolean).join(" vs "),
        ].filter(Boolean);
        if (sub.length) name.append(el("small", sub.join(" · ")));
        tr.append(name);
        for (const family of all) {
          const td = el("td");
          td.dataset.label = family === "Scripted" ? "Scripted baselines" : family;
          td.append(outcomeCell(item, family));
          tr.append(td);
        }
        body.append(tr);
      }
      table.append(columns, thead, body);
      fold.append(table);
      box.append(fold);
    }
    box.append(
      el(
        "p",
        "Each mark is one battle: ● won ○ lost × did not finish. † pools commanders with different settings or harness versions: not a controlled comparison.",
        "rows-foot",
      ),
    );
  }

  // Analyst notes: chapters that play their moment; the playing one shows its sentence.
  function renderChapters() {
    const list = $("highlights");
    list.replaceChildren();
    const shots = (payload?.stills || []).filter((s) => s.image && s.status === "embedded");
    $("stills-block").hidden = !shots.length;
    $("stills").replaceChildren(
      ...shots.slice(0, 4).map((shot) => {
        const name = STILLS[shot.trigger] || "Game still",
          caption = `${name} · spectator camera at ${clock(shot.time_ms)} · not what the model saw`;
        const thumb = button(
          "",
          () => {
            $("still-image").src = shot.image;
            $("still-image").alt = caption;
            $("still-caption").textContent = caption;
            $("still-dialog").showModal();
          },
          "thumb",
        );
        const image = el("img");
        image.src = shot.image;
        image.alt = `${name} at ${clock(shot.time_ms)}`;
        thumb.append(image);
        thumb.setAttribute("aria-label", `Enlarge: ${caption}`);
        return thumb;
      }),
    );
    const highlights = payload?.frames?.length ? payload.highlights || [] : [];
    $("chapters-head").hidden = !highlights.length;
    highlights.forEach((h, k) => {
      const window = span(h),
        item = el("li"),
        card = button("", () => Viewer.watch(window.from, h.end_ms ?? null, k), "chapter"),
        label = el("span", null, "label");
      label.append(
        el("span", String(k + 1), "number"),
        `${KINDS[h.kind] || "Moment"} · ${clock(h.time_ms)}`,
      );
      card.append(label, el("strong", h.title));
      if (h.text) card.append(el("span", h.text, "text"));
      card.setAttribute(
        "aria-label",
        `Analyst note ${k + 1}, ${clock(h.time_ms)}: ${h.title}. Watch it.`,
      );
      item.append(card);
      list.append(item);
    });
    markHighlights();
  }
  function markHighlights() {
    const marked = payload?.highlights?.length ? Viewer.note : -1;
    [...$("highlights").querySelectorAll(".chapter")].forEach((card, k) =>
      card.classList.toggle("active", k === marked),
    );
  }

  // What the model receives and sends back: verbatim lines of one message, abridged.
  // Preferred: the first reply with orders whose message reports its previous delay.
  function excerpt(prompt) {
    const out = [];
    let keep = 0;
    for (const line of prompt.split("\n")) {
      const head = line.match(
        /^(Battle notes:|Recent decisions|Your units:|Visible enemies:|Terrain samples:)/,
      );
      if (head) {
        if (out.length) out.push("");
        out.push(line);
        keep = head[1] === "Terrain samples:" ? 6 : 2;
      } else if (/^(Timing:|Enemy roster:|Battle:)/.test(line)) {
        out.push("", line);
        keep = 0;
      } else if (keep && line.trim()) {
        out.push(line);
        if (!--keep) out.push("⋯");
      }
    }
    return out.join("\n");
  }
  function renderInterface(entry, replay) {
    const candidates = (replay?.decisions || []).filter(
      (d) => d.prompt && d.steps?.length && d.attempts?.[0]?.text,
    );
    const d =
      candidates.find((item) => /Your last batch was issued/.test(item.prompt)) || candidates[0];
    $("interface").hidden = !d || !isModel(entry);
    if (!d || !isModel(entry)) return;
    let reply = d.attempts[0].text;
    try {
      const value = JSON.parse(reply);
      reply = [
        ...Object.entries(value)
          .filter(([key]) => key !== "orders")
          .map(([key, text]) => `"${key}": ${JSON.stringify(text)}`),
        `"orders": [`,
        ...(value.orders || []).map((order) => `  ${JSON.stringify(order).replace(/,"/g, ', "')}`),
        "]",
      ].join("\n");
    } catch {
      // Not JSON: shown as recorded.
    }
    const system = promptOf(entry.trial);
    $("interface-prompt").textContent = excerpt(d.prompt);
    $("interface-reply").textContent = reply;
    $("interface-caption").textContent =
      `Verbatim lines, abridged (⋯), of the message behind ${who(entry).name}'s orders accepted at ${clock(d.applied_ms)} in the featured battle of ${scenario.title}, and its reply, one order per line.${system ? ` A fixed system prompt (the rules and the order format, ${system.split(/\s+/).length} words) comes first in every call; Run settings shows it.` : ""} Each decision's details in the viewer hold its full message and reply.`;
  }

  // Development scenarios are the ones prompts and harness were tuned on: in-sample results.
  function status() {
    const held = data.scenarios.filter((s) => s.split === "held_out").length,
      tuned = data.scenarios.length - held;
    return held
      ? `${tuned} of ${data.scenarios.length} scenarios are development scenarios the prompts and harness were iterated on (in-sample results); ${held} ${held > 1 ? "are" : "is"} held out.`
      : "Every scenario is a development scenario: the prompts and harness were iterated on them and none is held out yet, so these results are in-sample and exploratory.";
  }
  function renderMethod() {
    const items = [
      [
        "What a model sees",
        "Text only, at every decision: its own units, the enemy units its army can see right now, the enemy roster shown on the custom-battle screen, a coarse passability grid where the interface provides one, its last orders, notes it wrote itself and how late its previous orders landed. Prompted models answer with orders per unit (move, attack, halt, change behaviour, use an ability; fly, build or reinforce where the battle allows); the commander answers with plans that scripted unit skills carry out.",
      ],
      [
        "Real time",
        "The battle runs at normal speed from start to finish and never waits for a reply. Order age is measured on the battle clock, from the observation to the game accepting the orders; accepted is not the same as carried out.",
      ],
      [
        "Opponent and baselines",
        "The game's own battle AI commands the enemy (difficulty in Run settings). Scripted baselines: attack nearest (walk), charge nearest (run), hold position, and per-unit skills with no model.",
      ],
      [
        "Enemy army broken",
        "The share of the enemy's soldiers dead, fleeing or otherwise out of the fight when the battle ended. Land attacks are won only at 100%; a defender at the timer or an objective battle can win without it. The engine decides every outcome.",
      ],
      ["Status", status()],
      [
        "Rows and versions",
        "A row holds every battle of one commander in a scenario; a row marked † spans several harness versions, and Run settings names each battle's. The report JSON keeps strict per-version groups and paired statistics.",
      ],
    ];
    const setup =
      data.setup_only.length + data.scenarios.reduce((n, s) => n + s.setup_only_jobs.length, 0);
    const hidden = [
      setup && `${setup} launch${setup > 1 ? "es" : ""} stopped during setup before any battle`,
      data.diagnostics.length &&
        `${data.diagnostics.length} diagnostic probe battle${data.diagnostics.length > 1 ? "s" : ""} (tooling tests, not commanders)`,
    ].filter(Boolean);
    if (hidden.length)
      items.push(["Not shown", `${hidden.join("; ")}. The report JSON lists them.`]);
    if (synthetic) items.unshift(["Synthetic demo", NOTICE]);
    $("method-notes").replaceChildren(
      ...items.map(([title, text]) => {
        const item = el("li");
        item.append(el("b", title), text);
        return item;
      }),
    );
  }

  // Run settings: everything about the battle in the viewer that the reading path omits.
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
        [
          "Scenario",
          scenario.name && scenario.name !== scenario.title
            ? `${scenario.title} (${scenario.name})`
            : scenario.title,
        ],
        [
          "Status",
          [scenario.split, scenario.status?.replaceAll("_", " ")].filter(Boolean).join(" · "),
        ],
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
          "Commander",
          [
            fullName(entry),
            `policy ${trial.policy}`,
            trial.card?.timing === "blocking"
              ? "waits for each reply before reading the battle again; the battle keeps running at 1×"
              : trial.card?.timing,
          ]
            .filter(Boolean)
            .join(" · "),
        ],
        ["Added observation age", `${(trial.delay_ms || 0) / 1000} s`],
        ["Harness version", entry.battle.harness],
        ["Interface track", definition.track],
        ["Controller version", trial.card?.version || "unrecorded; see source revision"],
        [
          "Evaluator version",
          trial.measures?.evaluator_version ?? definition.evaluator_version ?? "unversioned",
        ],
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
    const prompt = promptOf(trial);
    if (isModel(entry) && prompt != null)
      body.append(
        details(
          `Prompt the model received (${who(entry).prompt || trial.policy})`,
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
          battles: data.battles,
          scenarios: data.scenarios,
          setup_only: data.setup_only,
          diagnostics: data.diagnostics,
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
          // Evaluation belongs to the report, not the public replay export.
          trial: Object.fromEntries(
            [
              "instance",
              "episode",
              "policy",
              "outcome",
              "engine_outcome",
              "ended_by",
              "valid",
              "battle_ms",
              "battle_s",
            ].map((key) => [key, entry.trial[key]]),
          ),
          replay: payload,
        },
        `wh3-${synthetic ? "SYNTHETIC-DEMO-" : ""}replay-${entry.trial.instance}-${entry.trial.episode}.json`,
      );
      $("export-status").textContent = "Replay JSON download ready.";
    });
  }

  const watchFeatured = (intoView = true) => {
    if (featured)
      Viewer.watch(
        span(featured).from,
        featured.end_ms ?? null,
        payload.highlights.indexOf(featured),
        intoView,
      );
  };
  // One reply of the battle in the viewer, inspected: the median-age reply with orders, taken
  // from the key maneuver when there is one (the decisive phase), else from the whole battle.
  function showDelay() {
    const all = (payload?.decisions || [])
      .map((d, i) => ({ d, i }))
      .filter(
        ({ d }) =>
          d.steps.length && d.age_s != null && d.basis_frame != null && d.after_frame != null,
      );
    const moment = featured && span(featured),
      inside = moment
        ? all.filter(({ d }) => d.applied_ms >= moment.from && d.applied_ms <= moment.to)
        : [];
    const candidates = (inside.length ? inside : all).sort((a, b) => a.d.age_s - b.d.age_s);
    if (!candidates.length) return;
    Viewer.pin(candidates[Math.floor((candidates.length - 1) / 2)].i);
    Viewer.reveal();
  }
  async function setup() {
    if (synthetic) $("demo-banner").hidden = false;
    $("watch-featured").addEventListener("click", () => watchFeatured());
    $("watch-full").addEventListener("click", () => Viewer.watch(0));
    $("run-select").addEventListener("change", (e) => openRun(e.target.value, false));
    $("show-lag").addEventListener("click", showDelay);
    $("open-settings").addEventListener("click", openSettings);
    $("close-settings").addEventListener("click", () => $("settings-dialog").close());
    $("close-still").addEventListener("click", () => $("still-dialog").close());
    addEventListener("scroll", () => ($("tip").hidden = true), { passive: true });
    Viewer.onTime(markHighlights);
    downloads();
    renderFacts();
    renderMethod();
    if (!data.scenarios.length) {
      $("question").textContent = "No recorded battles in this report";
      for (const id of ["viewer", "results", "realtime", "all"]) $(id).hidden = true;
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
    renderHeadline();
    renderMatrix();
    await renderScenario(0);
    renderInterface(entries.get(scenario.featured), payload);
    // Open on the key maneuver itself (the army is mid-map there) and play it once the map is
    // half in view, unless the reader prefers less motion or has already moved the replay.
    // "Key maneuver" replays it with its lead-in.
    if (!featured || reduceMotion) return;
    const k = payload.highlights.indexOf(featured);
    Viewer.seek(featured.time_ms);
    const start = Viewer.time;
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        ([seen]) => {
          if (!seen.isIntersecting) return;
          observer.disconnect();
          if (Viewer.time === start && openKey === scenario.featured)
            Viewer.watch(start, featured.end_ms ?? null, k, false);
        },
        { threshold: 0.5 },
      );
      observer.observe($("map-wrap"));
    }
  }
  setup();
})();
