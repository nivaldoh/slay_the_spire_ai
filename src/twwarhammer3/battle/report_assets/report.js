// Runs after replay.js in the same script and uses its helpers (el, svg, clock, Viewer, ...).
(() => {
  const $ = (id) => document.getElementById(id);
  const data = JSON.parse($("report-data").textContent);
  const report = data.report;
  const synthetic = data.evidence_kind === "synthetic";
  const NOTICE =
    "SYNTHETIC DEMO: invented values that exercise the report; not benchmark evidence.";
  const STILLS = {
    opening: "Opening view",
    approach: "Closing in",
    incoming_fire: "Incoming fire",
    first_contact: "First melee",
    first_rout: "First rout",
    ending: "Battle ending",
  };
  const ORDERS = [
    ["move", "Move"],
    ["attack", "Attack"],
    ["ability", "Ability"],
    ["build", "Build"],
    ["reinforce", "Reinforce"],
    ["other", "Other"],
  ];
  // Each model keeps one hue across the page (light paper, dark map), in name order; scripted
  // rules are neutral. The first two pass the colour-vision checks against each other; names
  // always sit beside the marks.
  const HUES = [
    ["#5b45c9", "#9085e9"],
    ["#0e8a5f", "#199e70"],
    ["#b64a86", "#d55181"],
    ["#8a6a12", "#c09a3a"],
    ["#176aa6", "#64b5ed"],
    ["#986044", "#d9a27a"],
    ["#157f87", "#52c6ca"],
  ];
  const NEUTRAL = ["#7f898f", "#a3afb5"];
  const ENEMY_INK = "#b86f00"; // the enemy's orange, a step darker for the paper
  const entries = new Map();
  report.groups.forEach((group, g) =>
    group.trials.forEach((trial, t) => {
      const key = `g${g}-t${t}`;
      entries.set(key, { key, trial, group, g, battle: data.battles[key] });
    }),
  );
  // The battles on the page: the completed battles of its scenarios.
  const shown = new Set(data.scenarios.flatMap((item) => item.battles));
  const cache = new Map();
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let scenario = null,
    openKey = null,
    payload = null,
    featured = null;

  const who = (entry) => entry.battle.commander;
  const isModel = (entry) => who(entry).kind === "model";
  const fullName = (entry) => [who(entry).name, who(entry).detail].filter(Boolean).join(", ");
  const percent = (share) => `${Math.round(share * 100)}%`;
  const median = (values) => quantile(values, 0.5);
  function quantile(values, q) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b),
      at = (sorted.length - 1) * q,
      low = Math.floor(at);
    return sorted[low] + (sorted[Math.ceil(at)] - sorted[low]) * (at - low);
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
  const models = [
    ...new Set(
      [...shown]
        .map((key) => entries.get(key))
        .filter(isModel)
        .map((entry) => who(entry).family),
    ),
  ].sort();
  // A commander's hue: its model's, or neutral for a scripted rule; `dark` for the map stage.
  const hue = (row, dark = false) => {
    const k = row.kind === "model" ? models.indexOf(row.family) : -1;
    return (HUES[k] || NEUTRAL)[dark ? 1 : 0];
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
    return { text, short };
  }
  // "ai_level_very_hard" -> "very hard": the game's battle AI difficulty, where recorded.
  const level = (item) => item.difficulty?.replace(/^ai_level_/, "").replaceAll("_", " ");
  const won = (entry) => (entry.trial.engine_outcome || entry.trial.outcome) === "won";
  const draw = (entry) => (entry.trial.engine_outcome || entry.trial.outcome) === "draw";
  // A commander's record beside its score: "won 1 of 6", "lost its only battle".
  const record = (s) =>
    s.items.length === 1
      ? `${s.won ? "won" : s.items.some(draw) ? "drew" : "lost"} its only battle`
      : `won ${s.won} of ${s.items.length}`;
  // Battles from several test-setup versions or settings, said concretely.
  function pooledNote(rows) {
    const versions = new Set(rows.flatMap((row) => row.battles.map((k) => data.battles[k].harness)))
      .size;
    const parts = rows.map(
      (row) =>
        `${row.detail || row.name}: ${row.battles.length} battle${row.battles.length === 1 ? "" : "s"}`,
    );
    return `${parts.join("; ")}${versions > 1 ? `; from ${versions} test-setup versions (controller, interface or game code changed between them)` : ""}`;
  }
  const pooled = (rows) =>
    rows.length > 1 ||
    new Set(rows.flatMap((row) => row.battles.map((k) => data.battles[k].harness))).size > 1;
  function dagger(rows, className = "versions") {
    const mark = el("sup", "†", className);
    mark.title = pooledNote(rows);
    return mark;
  }
  // A battle's score: 100 for a win, else the share of the enemy army broken at the end (or
  // the scenario's objective measure). A battle without the measure has none.
  const scoreOf = (entry) =>
    (
      entry.battle.objective_outcome != null
        ? entry.battle.objective_outcome === "success"
        : won(entry)
    )
      ? 100
      : entry.battle.progress == null
        ? null
        : Math.min(99.99, 100 * entry.battle.progress);
  const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length;
  // A score as printed: never rounded up to a win's 100 (a 99.8% loss reads 99).
  const points = (value) => (value >= 100 ? "100" : String(Math.min(99, Math.round(value))));
  // A scenario's game mode, as data.modes names it ("land battle"), and its icon.
  const modeOf = (item) => data.modes.find((mode) => mode.key === item.mode);
  const ICONS = ["land", "siege_defence", "survival"];
  function modeIcon(key) {
    const node = svg("svg", { viewBox: "0 0 24 24", class: "mode-icon", "aria-hidden": "true" });
    node.append(svg("use", { href: `#mode-${ICONS.includes(key) ? key : "other"}` }));
    return node;
  }
  function context(entry) {
    return { kind: who(entry).kind, rule: who(entry).detail, synthetic };
  }

  // The battle's measures in a few words; absent ones are left out, never zeroed.
  function measures(entry) {
    const m = entry.trial.measures || {},
      b = entry.battle,
      out = [];
    const score = scoreOf(entry);
    const basis = {
      tickets: "ticket progress",
      objective_time: "objective ownership time",
      evacuation: "batteries in extraction zone",
      duration: "survival duration",
    }[b.progress_basis];
    if (score != null)
      out.push(
        `score ${points(score)}${won(entry) ? " (a win)" : ` in a ${draw(entry) ? "drawn" : "lost"} battle${basis ? ` (${basis})` : ""}`}`,
      );
    if (b.progress_basis === "duration" && m.duration_s != null)
      out.push(`survived ${clock(m.duration_s * 1000)}`);
    if (m.custom_objective) {
      const goal = m.custom_objective;
      out.push(
        `evacuation ${goal.status}: ${goal.extracted} of ${goal.assets.length} batteries in zone`,
      );
      if (goal.reason) out.push(goal.reason.replaceAll("_", " "));
    }
    if (b.own_left != null) out.push(`own soldiers alive ${percent(b.own_left)}`);
    const units = m.units || {};
    if (units.friendly && units.enemy)
      out.push(
        `units still fighting: own ${units.friendly.active} of ${units.friendly.registered}, enemy ${units.enemy.active} of ${units.enemy.registered}`,
      );
    const held = new Map();
    for (const p of m.objective_time?.points || []) {
      const name = /key_building/.test(p.key)
        ? "key building"
        : /suppl/.test(p.key)
          ? "supply points"
          : "";
      held.set(name, [
        ...(held.get(name) || []),
        p.share == null ? "not recorded" : percent(p.share),
      ]);
    }
    if (held.size)
      out.push(
        `objectives held ${[...held].map(([name, shares]) => `${name ? `${name} ` : ""}${shares.join(", ")}`).join("; ")} of the time observed`,
      );
    const r = m.resources || {};
    if (r.status === "available") {
      if (r.tickets && b.progress_basis === "tickets")
        out.push(
          `tickets: own ${r.tickets.us ?? "?"}, enemy ${r.tickets.enemy ?? "?"}${r.tickets_goal ? `; goal ${r.tickets_goal}` : ""}`,
        );
      if (r.supplies_left != null) out.push(`${r.supplies_left} supplies left`);
      if (r.build) out.push(`${r.build} built`);
      if (r.reinforce) out.push(`${r.reinforce} reinforcements bought`);
    }
    return out;
  }
  function markCurrent() {
    for (const node of document.querySelectorAll("[data-keys]"))
      node.setAttribute("aria-current", String(node.dataset.keys.split(" ").includes(openKey)));
    for (const node of document.querySelectorAll("[data-scenario]"))
      node.setAttribute("aria-current", String(node.dataset.scenario === scenario?.id));
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

  // A projection of points into a w × h box, with a margin and at least `least` metres across.
  function frameOf(points, w, h, least, margin) {
    const xs = points.map((p) => p[0]),
      zs = points.map((p) => p[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2,
      cz = (Math.min(...zs) + Math.max(...zs)) / 2;
    const spanX = Math.max(least, Math.max(...xs) - Math.min(...xs) + 2 * margin),
      spanZ = Math.max(least * (h / w), Math.max(...zs) - Math.min(...zs) + 2 * margin);
    const scale = Math.min(w / spanX, h / spanZ);
    return {
      scale,
      x: (x) => w / 2 + (x - cx) * scale,
      y: (z) => h / 2 - (z - cz) * scale,
    };
  }
  // A scenario's comparison, as Figure 3 and the index draw it: each model's score pooled over
  // its battles (seconds survived in survival) and the best scripted rule's, when any ran.
  const anyRule = data.scenarios.some((s) => s.rows.some((r) => r.kind === "scripted"));
  function cells(item) {
    const metric = item.mode === "survival" ? "duration" : "score";
    const out = models.map((family) => {
      const rows = item.rows.filter((row) => row.family === family);
      return {
        kind: "model",
        family,
        label: family,
        rows,
        metric,
        s: rows.length ? rowStats({ battles: rows.flatMap((row) => row.battles) }) : null,
      };
    });
    if (anyRule) {
      const best = item.rows
        .filter((row) => row.kind === "scripted")
        .map((row) => ({ row, ...rowStats(row) }))
        .filter((s) => s[metric] != null)
        .sort((a, b) => b[metric] - a[metric])[0];
      out.push({
        kind: "scripted",
        label: best ? best.row.name : "Best rule",
        rows: best ? [best.row] : [],
        metric,
        s: best || null,
      });
    }
    return out;
  }
  const cellHue = (cell) => (cell.kind === "model" ? hue(cell) : NEUTRAL[0]);
  const cellValue = (cell) =>
    cell.s?.[cell.metric] == null
      ? null
      : cell.metric === "duration"
        ? `${Math.round(cell.s.duration)} s`
        : points(cell.s.score);
  const topOf = (items) =>
    items.some((item) => item.mode === "survival")
      ? nice(Math.max(1, ...items.flatMap((item) => cells(item).map((c) => c.s?.duration || 0))))
      : 100;

  // The masthead's index: one small map per scenario (its terrain and both armies where they
  // began), its game mode, short name and a tiny bar per model and for the best rule. It picks
  // the scenario in the replay below.
  function renderIndex() {
    const nav = $("index");
    nav.replaceChildren();
    if (data.scenarios.length < 2) return;
    data.scenarios.forEach((item, index) => {
      const w = 180,
        h = 112,
        start = item.start || { friendly: [], enemy: [] },
        points = [...start.friendly, ...start.enemy];
      const map = svg("svg", {
        viewBox: `0 0 ${w} ${h}`,
        class: "index-map",
        "aria-hidden": "true",
      });
      map.append(svg("rect", { width: w, height: h, class: "off-map" }));
      if (points.length) {
        const p = frameOf(points, w, h, 180, 45);
        const t = item.terrain;
        if (t) {
          const x0 = p.x(t.bounds.min_x),
            y0 = p.y(t.bounds.max_z);
          map.append(
            svg("rect", {
              x: x0,
              y: y0,
              width: p.x(t.bounds.max_x) - x0,
              height: p.y(t.bounds.min_z) - y0,
              class: "on-map",
            }),
            svg("path", { d: blockedPath(t, p.x, p.y, p.scale), class: "blocked" }),
          );
        }
        for (const [x, z] of start.friendly)
          map.append(svg("circle", { cx: p.x(x), cy: p.y(z), r: 2.6, fill: TEAM.friendly }));
        for (const [x, z] of start.enemy)
          map.append(
            svg("path", {
              d: `M${p.x(x).toFixed(1)} ${(p.y(z) - 3).toFixed(1)}l3 3-3 3-3-3z`,
              fill: TEAM.enemy,
            }),
          );
      }
      const name = el("span", null, "index-name");
      name.append(modeIcon(item.mode), el("span", item.short));
      const row = cells(item),
        top = topOf([item]);
      const bars = el("span", null, "index-bars");
      for (const cell of row) {
        const track = el("i"),
          fill = el("b"),
          value = cell.s?.[cell.metric];
        fill.style.width = value == null ? "0" : `${(100 * Math.min(value, top)) / top}%`;
        fill.style.background = cellHue(cell);
        track.append(fill);
        bars.append(track);
      }
      const node = button("", () => pick(index)(), "index-item");
      node.append(map, name, bars);
      node.dataset.scenario = item.id;
      node.title = `${item.title}, ${modeOf(item)?.name || "battle"}: ${row
        .map(
          (cell) =>
            `${cell.kind === "model" ? cell.label : `best rule${cell.s ? ` (${cell.label})` : ""}`} ${cellValue(cell) ?? "no battles yet"}`,
        )
        .join(", ")}`;
      nav.append(node);
    });
  }

  // The benchmark in a few sentences: its size and dates; the wins of every model in the
  // scenarios where each model that played has at least three battles under one test setup;
  // how many battles the others have; how old the models' information was; that it is in-sample.
  const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
  const number = (n) => WORDS[n] || String(n);
  const MATCHED = 3;
  const list = (items, word = "and") =>
    items.length > 1 ? `${items.slice(0, -1).join(", ")} ${word} ${items.at(-1)}` : items[0];
  // A model's battles in a scenario from its largest group under one test setup.
  function groupOf(keys) {
    const groups = new Map();
    for (const key of keys)
      groups.set(data.battles[key].harness, [
        ...(groups.get(data.battles[key].harness) || []),
        key,
      ]);
    return [...groups.values()].sort((a, b) => b.length - a.length)[0] || [];
  }
  const noun = (item, plural = false) =>
    `${item.noun || `${item.short} battle`}${plural ? "s" : ""}`;
  function finding() {
    const all = [...shown].map((key) => entries.get(key));
    const dated = all
      .map((entry) => entry.battle.date)
      .filter((value) => date(value))
      .sort();
    // "14–15 Oct 2026" within a month, else both dates in full.
    const [from, to] = [date(dated[0]), date(dated.at(-1))];
    const days = !from
      ? null
      : from === to
        ? from
        : from.split(" ").slice(1).join(" ") === to.split(" ").slice(1).join(" ")
          ? `${from.split(" ")[0]}–${to}`
          : `${from} – ${to}`;
    const n = data.scenarios.length;
    const out = [
      `Early results${days ? ` from ${days}` : ""}: ${all.length} battles in ${number(n)} scenario${n === 1 ? "" : "s"}. `,
    ];
    // The scenarios where every model that played has a group of at least MATCHED battles.
    const matched = data.scenarios
      .map((item) => ({
        item,
        groups: models
          .filter((family) => item.rows.some((row) => row.family === family))
          .map((family) => {
            const keys = groupOf(
              item.rows.filter((row) => row.family === family).flatMap((row) => row.battles),
            );
            return { family, n: keys.length, won: keys.filter((k) => won(entries.get(k))).length };
          }),
      }))
      .filter((m) => m.groups.length && m.groups.every((g) => g.n >= MATCHED));
    if (matched.length) {
      const winning = matched.filter((m) => m.groups.some((g) => g.won)),
        losing = matched.filter((m) => !m.groups.some((g) => g.won));
      const total = (family) =>
        matched.reduce((k, m) => k + (m.groups.find((g) => g.family === family)?.won || 0), 0);
      const names = [...new Set(matched.flatMap((m) => m.groups.map((g) => g.family)))].sort(
        (a, b) => total(b) - total(a) || a.localeCompare(b),
      );
      // The first model's wins name their scenarios; a later model with the same scenarios and
      // battle counts gives its wins only ("won 0, 0 and 1").
      const lines = names
        .map((family) =>
          winning
            .map((m) => ({ m, g: m.groups.find((g) => g.family === family) }))
            .filter((x) => x.g),
        )
        .map((own, i, every) => {
          if (!own.length) return null;
          const first = every.find((x) => x.length);
          const same =
            own !== first &&
            own.length === first.length &&
            own.every((x, k) => x.m === first[k].m && x.g.n === first[k].g.n);
          return [
            el("span", names[i], "nowrap"),
            ` won ${same ? list(own.map((x) => String(x.g.won))) : list(own.map((x) => `${x.g.won} of ${x.g.n} ${noun(x.m.item, x.g.n !== 1)}`))}`,
          ];
        })
        .filter(Boolean);
      out.push(`With ${number(MATCHED)} or more battles per model under one test setup, `);
      lines.forEach((line, i) => out.push(i ? "; " : "", ...line));
      if (losing.length) {
        const nobody = names.length === 1 ? null : names.length === 2 ? "Neither" : "No model";
        const scenarios = list(
          losing.map((m) => noun(m.item)),
          "or",
        );
        out.push(
          lines.length ? ". " : "",
          nobody
            ? `${lines.length ? nobody : nobody.toLowerCase()} won any ${scenarios}`
            : `${lines.length ? "" : `${names[0]} `}won no ${scenarios}`,
        );
      }
      out.push(". ");
    }
    const counts = data.scenarios
      .filter((item) => !matched.some((m) => m.item === item))
      .flatMap((item) =>
        models.map((family) =>
          item.rows.filter((r) => r.family === family).reduce((k, r) => k + r.battles.length, 0),
        ),
      )
      .filter(Boolean);
    if (counts.length) {
      const [low, high] = [Math.min(...counts), Math.max(...counts)];
      const others = n - matched.length;
      out.push(
        `${matched.length ? `The other ${number(others)}` : others === 1 ? "The" : `All ${number(others)}`} scenario${others === 1 ? " has" : "s have"} ${low === high ? low : `${low}–${high}`} battle${high === 1 ? "" : "s"} per model so far. `,
      );
    }
    const ages = (kind) => {
      const values = [
        ...new Set(
          data.scenarios.flatMap((s) => s.rows.filter((r) => r.kind === kind)).map((r) => r.family),
        ),
      ]
        .map((family) =>
          rowStats({
            battles: data.scenarios.flatMap((s) =>
              s.rows.filter((r) => r.family === family).flatMap((r) => r.battles),
            ),
          }),
        )
        .filter((s) => s.ages.length)
        .map((s) => s.box[2]);
      if (!values.length) return null;
      return Math.min(...values) === Math.max(...values)
        ? seconds(values[0])
        : `${Math.min(...values).toFixed(1)}–${seconds(Math.max(...values))}`;
    };
    const [modelAge, ruleAge] = [ages("model"), ages("scripted")];
    if (modelAge)
      out.push(
        `The models' orders act on views of the battle ${modelAge} old${ruleAge ? `, the rules' on ${ruleAge}` : ""}. `,
      );
    const held = data.scenarios.filter((s) => s.split === "held_out").length;
    out.push(
      held
        ? `Prompts were developed on ${number(n - held)} of these scenarios.`
        : "Prompts were developed on these scenarios, so every result is in-sample.",
    );
    $("finding").replaceChildren(...out);
  }

  // The score scale, 0 to 100 (or seconds), shared by every bar of a figure.
  function scale(top = 100, unit = "") {
    const node = el("div", null, "scale");
    for (const value of [0, top / 2, top]) {
      const tick = el("span", `${value}${unit && value === top ? ` ${unit}` : ""}`);
      tick.style.left = `${(100 * value) / top}%`;
      node.append(tick);
    }
    return node;
  }
  // A commander's score: the bar reaches its mean, the line spans its worst to its best
  // battle; `rule` marks the best scripted rule's score.
  function scoreBar(s, colour, rule = null) {
    const node = el("div", null, "score");
    if (s.score == null) {
      node.append(el("span", "no score recorded", "none"));
      return node;
    }
    const bar = el("span", null, "bar"),
      fill = el("i", null, "fill");
    fill.style.width = `${s.score}%`;
    fill.style.background = colour;
    bar.append(fill);
    if (s.scores.length > 1) {
      const range = el("i", null, "range"),
        low = Math.min(...s.scores);
      range.style.left = `${low}%`;
      range.style.width = `${Math.max(...s.scores) - low}%`;
      bar.append(range);
    }
    if (rule != null) {
      const tick = el("i", null, "rule-tick");
      tick.style.left = `${rule}%`;
      bar.append(tick);
    }
    node.append(el("b", points(s.score)), bar);
    return node;
  }
  function swatch(row, dark = false) {
    const node = el("i", null, "swatch-hue");
    node.style.background = hue(row, dark);
    return node;
  }
  function whoCell(row, short = false) {
    const cell = el("div", null, "who-cell");
    const name = el("strong");
    name.append(swatch(row), row.name);
    cell.append(name);
    if (short ? row.short : row.detail) cell.append(el("small", short ? row.short : row.detail));
    if (pooled([row])) name.append(dagger([row]));
    return cell;
  }
  const ageText = (s) => (s.ages.length ? seconds(s.box[2]) : s.timed ? "no orders" : "–");
  const costText = (s) => (s.row.kind !== "model" ? "$0" : s.usd == null ? "–" : money(s.usd));

  // Figure 1's scenario: the largest controlled comparison anywhere. The page opens on it.
  const headline = data.scenarios
    .filter((s) => s.controlled)
    .sort((a, b) => b.controlled.launches - a.controlled.launches)[0];
  // Figure 1: one score per commander in that comparison; definitions as its footnotes.
  function renderHeadline() {
    const item = headline;
    if (!item) return;
    const keys = new Set(item.controlled.battles);
    // The controlled subset is one harness by construction.
    const all = item.rows
      .map((row) => ({ ...row, battles: row.battles.filter((key) => keys.has(key)), harnesses: 1 }))
      .filter((row) => row.battles.length)
      .map((row) => ({ row, ...rowStats(row) }));
    const rules = all.filter((s) => s.row.kind === "scripted" && s.score != null);
    const best = rules.length ? Math.max(...rules.map((s) => s.score)) : null;
    const table = $("headline-table");
    table.replaceChildren();
    const head = el("div", null, "board-head");
    const axis = el("div", null, "score");
    axis.append(el("span", "Score"), scale());
    head.append(
      el("span"),
      axis,
      el("span", "Outcome"),
      el("span", "Order age"),
      el("span", "Cost"),
    );
    table.append(head);
    for (const s of all) {
      const line = el("div", null, `board-row ${s.row.kind}`);
      line.append(
        whoCell(s.row, true),
        scoreBar(s, hue(s.row), s.row.kind === "model" ? best : null),
        el("span", record(s)),
        el("span", ageText(s)),
        el("span", costText(s)),
      );
      table.append(line);
    }
    const title = button(item.title, pick(data.scenarios.indexOf(item)), "inline");
    $("headline-caption").replaceChildren(
      el("b", "Figure 1. "),
      title,
      item.footnote ? "*" : "",
      `, a ${modeOf(item)?.name || "battle"}: ${item.controlled.launches} game launches, each commander ${item.controlled.once ? "once " : ""}per launch with the same test setup${level(item) ? `, against the game's AI on ${level(item)}` : ""}.${best != null ? " The tick marks the best scripted rule." : ""} Figure 3 pools every completed battle in this scenario, other launches included.`,
    );
    // Reasoning efforts on the page, defined once: "low reasoning" is a model setting.
    const efforts = [
      ...new Set(
        [...shown].map(
          (key) => /^(\w+) reasoning/.exec(data.battles[key].commander.short || "")?.[1],
        ),
      ),
    ].filter(Boolean);
    $("headline-foot").replaceChildren(
      ...[
        item.footnote && `* ${item.footnote}`,
        scoreNote(),
        efforts.length &&
          `${capital(efforts.join(" and "))} reasoning: the model's ${efforts.join(" or ")} reasoning-effort setting.`,
        "Order age: how old the battle state behind a reply's orders was when the game accepted them (median). Cost: mean API cost per completed battle.",
      ]
        .filter(Boolean)
        .map((text) => el("span", text)),
    );
    $("headline").hidden = false;
  }
  // The score, defined for the kinds of battle on the page only.
  function scoreNote() {
    const bases = new Set([...shown].map((key) => data.battles[key].progress_basis ?? "strength"));
    const modes = new Set(data.scenarios.map((s) => s.mode));
    // The modes scored by the enemy broken: land battles and siege defences.
    const broken = data.modes
      .filter((mode) =>
        data.scenarios.some(
          (s) =>
            s.mode === mode.key &&
            s.battles.some((k) =>
              [null, undefined, "killed"].includes(data.battles[k].progress_basis),
            ),
        ),
      )
      .map((mode) => (mode.key === "land" ? "land battles" : `${mode.name}s`));
    const parts = [
      (bases.has("strength") || bases.has("killed")) &&
        `of the enemy's soldiers dead, fleeing or out of the fight (${list(broken) || "land battles"})`,
      bases.has("objective_time") &&
        `of the time the objectives were held (${list([modes.has("siege_attack") && "siege attacks", modes.has("settlement") && "settlements"].filter(Boolean)) || "sieges"})`,
      bases.has("tickets") && "of the ticket goal reached (conquest and domination)",
      bases.has("evacuation") && "of the batteries in the extraction zone (evacuation)",
    ].filter(Boolean);
    return `Score: 100 for a win${parts.length ? `; otherwise the percentage ${parts.join(" or ")}` : ""}.${bases.has("duration") ? " Survival battles score seconds survived." : ""} Bars are means over completed battles; lines span the worst to the best.`;
  }
  // Cumulative API spend per model over every attempt in the report's input.
  function renderSpend() {
    const spend = new Map();
    for (const entry of entries.values())
      if (isModel(entry) && entry.trial.llm?.usd != null)
        spend.set(who(entry).family, (spend.get(who(entry).family) || 0) + entry.trial.llm.usd);
    if (!spend.size) return;
    const parts = [...spend].sort().flatMap(([family, usd], i) => {
      const name = el("span", null, "nowrap");
      name.append(swatch({ kind: "model", family }), `${family} ${money(usd)}`);
      return [i ? ", " : "", name];
    });
    $("spend").replaceChildren(
      "API spend over every attempt in this report, incomplete ones included: ",
      ...parts,
      ".",
    );
    $("spend").hidden = false;
  }

  function renderScenario(index, open = true) {
    scenario = data.scenarios[index];
    $("scenario").value = String(index);
    $("heading").textContent = scenario.heading || scenario.title;
    const mode = modeOf(scenario)?.name || "battle";
    $("challenge").textContent = [
      `${/^[aeiou]/.test(mode) ? "An" : "A"} ${mode}${level(scenario) ? ` against the game's AI on ${level(scenario)}` : ""}${scenario.heading && !scenario.title.toLowerCase().startsWith(mode.split(" ")[0]) ? `: ${scenario.title}` : ""}.`,
      scenario.challenge,
    ]
      .filter(Boolean)
      .join(" ");
    document.title = `${synthetic ? "SYNTHETIC DEMO — " : ""}${scenario.title}, WH3 Commander Bench`;
    // By commander, as the figures order them; the outcome first, so a narrow select keeps it.
    $("run-select").replaceChildren(
      ...scenario.rows
        .flatMap((row) => row.battles.map((key) => entries.get(key)))
        .map((entry) => {
          const option = el(
            "option",
            `${outcome(entry).short}, ${who(entry).name}${who(entry).short ? ` (${who(entry).short.replace(" reasoning", "")})` : ""}`,
          );
          option.value = entry.key;
          return option;
        }),
    );
    renderPlans();
    markCurrent();
    return open ? openRun(scenario.featured, false) : null;
  }

  function renderRunLine(entry) {
    const line = $("run-line"),
      row = scenario.rows.find((item) => item.battles.includes(entry.key));
    line.replaceChildren();
    if (synthetic) line.append(el("span", "SYNTHETIC DEMO", "tag synthetic"));
    const title = el("span", null, "title");
    const name = el("strong", null, "name");
    name.append(swatch(who(entry), true), who(entry).name);
    title.append(name, el("span", who(entry).detail, "detail"));
    const status = el("span", null, "result");
    status.append(el("span", outcome(entry).text));
    if (row) {
      const items = row.battles.map((key) => entries.get(key));
      const record = el(
        "span",
        items.length === 1
          ? `its only battle here${row.short ? ` with ${row.short}` : ""}`
          : `won ${items.filter(won).length} of ${items.length} here${row.short ? ` with ${row.short}` : ""}`,
        "sample",
      );
      if (row.harnesses > 1) record.title = pooledNote([row]);
      status.append(record);
    }
    line.append(title, status);
    const facts = measures(entry);
    if (entry.key === scenario.featured && scenario.featured_reason === "selected")
      facts.push("featured for its analyst notes, not as typical");
    if (facts.length) line.append(el("span", facts.join(", "), "measures"));
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
    $("watch-featured").textContent = featured
      ? `Play ${featured.feature ? "key moment" : "note 1"} (${clock(featured.time_ms)})`
      : "";
    $("watch-full").disabled = !payload?.frames?.length;
    $("download-replay").disabled = !payload;
    renderChapters();
    if (scroll) Viewer.reveal();
  }

  // Figure 2's items: one per model (its settings pooled) and per scripted rule.
  function commanders(item) {
    const out = [];
    for (const row of item.rows) {
      const same =
        row.kind === "model" && out.find((o) => o.kind === "model" && o.family === row.family);
      if (same) {
        same.rows.push(row);
        same.battles = [...same.battles, ...row.battles];
      } else out.push({ ...row, rows: [row], battles: [...row.battles] });
    }
    return out;
  }
  // The mean of several tracks ([s, x, z]), step by step in battle time; a battle that has ended
  // holds its last position. It runs as long as the median battle.
  function meanTrack(tracks) {
    const ends = tracks.map((track) => track.at(-1)[0]).sort((a, b) => a - b),
      until = ends[Math.floor((ends.length - 1) / 2)],
      out = [];
    for (let t = Math.min(...tracks.map((track) => track[0][0])); t <= until; t += 5) {
      const at = tracks.map((track) => track.findLast(([time]) => time <= t) ?? track[0]);
      out.push([t, mean(at.map((p) => p[1])), mean(at.map((p) => p[2]))]);
    }
    return out;
  }
  // Path maps earn their place only where commanders' mean positions part: some pair at least
  // 50 m apart at the median moment they share.
  const PART_M = 50;
  function pathsPart(tracked) {
    const means = tracked.map((t) => new Map(meanTrack(t).map(([s, x, z]) => [s, [x, z]])));
    return means.some((a, i) =>
      means.slice(i + 1).some((b) => {
        const gaps = [...a]
          .filter(([s]) => b.has(s))
          .map(([s, [x, z]]) => Math.hypot(x - b.get(s)[0], z - b.get(s)[1]));
        return gaps.length && median(gaps) >= PART_M;
      }),
    );
  }
  // A battle development series (report_html.development) at time s: its latest sample, held
  // after the battle ended.
  const valueAt = (dev, series, s) =>
    s >= dev.end_s ? series.at(-1) : series[Math.floor(s / dev.step_s)];
  const STEP_S = 5; // report_html.STEP_MS

  // Figure 2: one panel per model, pooling its battles here: the soldiers each side lost over
  // battle time and the orders it gave by kind, on shared axes; where their routes part, a map
  // of where its army went first. Panels are drawn at their width, two to a row when it fits.
  let plansWidth = 0;
  function renderPlans() {
    const box = $("commanders");
    box.replaceChildren();
    plansWidth = box.clientWidth;
    const items = commanders(scenario).filter((item) => item.kind === "model");
    const devs = items.flatMap((item) =>
      item.battles.map((key) => entries.get(key).battle.development).filter(Boolean),
    );
    const caption = [el("b", "Figure 2. ")];
    if (!devs.length) {
      caption.push(
        `${scenario.title}: ${items.length ? "no battle development was recorded" : "no model has played this scenario yet"}.`,
      );
      $("plans-caption").replaceChildren(...caption);
      return;
    }
    const columns = plansWidth >= 720 && items.length > 1 ? 2 : 1;
    const W = Math.max(300, Math.round((plansWidth - (columns - 1) * 40) / columns));
    const end = Math.max(...devs.map((d) => d.end_s));
    const top = nice(Math.max(1, ...devs.flatMap((d) => [...d.own, ...d.enemy])));
    const kinds = ORDERS.filter(([kind]) => devs.some((d) => d.orders[kind]?.some(Boolean)));
    const tracked = items
      .map((item) =>
        item.battles.map((key) => entries.get(key).battle.route?.track).filter((t) => t?.length),
      )
      .filter((t) => t.length);
    const frame =
      tracked.length > 1 && pathsPart(tracked) ? routeFrame(tracked.flat(), items, W) : null;
    items.forEach((item, i) =>
      box.append(commanderPanel(item, { W, end, top, kinds, frame, first: i === 0 })),
    );
    caption.push(
      `${scenario.title}: one panel per model, pooling its completed battles (scripted rules are in Figures 1 and 3). Lines: soldiers lost by its army (its colour) and by the enemy (orange; only units its army saw), thin for each battle and thick for the mean. Strips: orders the game accepted in each 5 s, darker for more, with the mean per battle.${frame ? " Maps: where its army went (the centre of its units still fighting), thick for the mean from □ to ●; ◆ enemy units where first seen." : ""} Click a panel to watch its first battle.`,
    );
    if (items.length === 1) caption.push(" Only one model has played this scenario so far.");
    $("plans-caption").replaceChildren(...caption);
    markCurrent();
  }
  // 1, 2 or 5 times a power of ten, at least `value`: the top of a shared axis.
  function nice(value) {
    const power = 10 ** Math.floor(Math.log10(value));
    return [1, 2, 5, 10].map((m) => m * power).find((v) => v >= value);
  }
  // One framing for every route map: all tracks and where the enemy was first seen.
  function routeFrame(tracks, items, w) {
    const enemies = items.flatMap((item) =>
      item.battles.flatMap((key) => (entries.get(key).battle.route?.enemy || []).map((u) => u.at)),
    );
    const points = [...tracks.flat().map(([, x, z]) => [x, z]), ...enemies];
    const xs = points.map((p) => p[0]),
      zs = points.map((p) => p[1]);
    const aspect = Math.max(
      0.36,
      Math.min(
        0.5,
        (Math.max(...zs) - Math.min(...zs) + 80) / (Math.max(...xs) - Math.min(...xs) + 80),
      ),
    );
    const h = Math.round(w * aspect);
    return { w, h, ...frameOf(points, w, h, 200, 40) };
  }
  function routeMap(item, frame) {
    const { w, h } = frame;
    const map = svg("svg", { viewBox: `0 0 ${w} ${h}`, class: "route-map", "aria-hidden": "true" });
    if (scenario.terrain)
      map.append(
        svg("path", {
          d: blockedPath(scenario.terrain, frame.x, frame.y, frame.scale),
          class: "blocked",
        }),
      );
    const tracks = item.battles
      .map((key) => entries.get(key))
      .filter((entry) => entry.battle.route?.track.length);
    if (!tracks.length) return map;
    const line = (path) =>
      path.map(([, x, z]) => `${frame.x(x).toFixed(1)},${frame.y(z).toFixed(1)}`).join(" ");
    for (const u of tracks[0].battle.route.enemy)
      map.append(
        svg("path", {
          d: `M${frame.x(u.at[0]).toFixed(1)} ${(frame.y(u.at[1]) - 3.2).toFixed(1)}l3.2 3.2-3.2 3.2-3.2-3.2z`,
          class: "foe",
        }),
      );
    for (const entry of tracks)
      map.append(svg("polyline", { points: line(entry.battle.route.track), class: "trace" }));
    const path = meanTrack(tracks.map((e) => e.battle.route.track)),
      [, sx, sz] = path[0],
      [, ex, ez] = path.at(-1);
    map.append(
      svg("polyline", { points: line(path), class: "mean", stroke: hue(item, true) }),
      svg("rect", {
        x: frame.x(sx) - 3.5,
        y: frame.y(sz) - 3.5,
        width: 7,
        height: 7,
        class: "start",
      }),
      svg("circle", {
        cx: frame.x(ex),
        cy: frame.y(ez),
        r: 3.5,
        class: "end",
        fill: hue(item, true),
      }),
    );
    return map;
  }
  function commanderPanel(item, { W, end, top, kinds, frame, first }) {
    const battles = item.battles.map((key) => entries.get(key)),
      devs = battles.map((e) => e.battle.development).filter(Boolean);
    const colour = hue(item);
    const LEFT = 76,
      RIGHT = 40,
      CHART = 132,
      ROW = 17;
    const x = (s) => LEFT + ((W - LEFT - RIGHT) * s) / Math.max(1, end);
    const y = (v) => 8 + (CHART - 16) * (1 - v / top);
    const height = CHART + kinds.length * ROW + 26;
    const chart = svg("svg", { viewBox: `0 0 ${W} ${height}`, class: "development", role: "img" });
    chart.setAttribute(
      "aria-label",
      `${item.name}: soldiers lost and orders over battle time in ${battles.length} battle${battles.length === 1 ? "" : "s"}`,
    );
    for (const v of [0, top / 2, top])
      chart.append(
        svg("line", { x1: LEFT, x2: W - RIGHT, y1: y(v), y2: y(v), class: v ? "grid" : "base" }),
        svg(
          "text",
          { x: LEFT - 8, y: y(v) + 4, class: "tick", "text-anchor": "end" },
          v.toLocaleString("en"),
        ),
      );
    chart.append(svg("text", { x: 0, y: y(top / 2) + 4, class: "tick" }, "Lost"));
    const steps = Math.ceil(end / STEP_S);
    for (const [series, stroke] of [
      ["enemy", ENEMY_INK],
      ["own", colour],
    ]) {
      for (const dev of devs)
        chart.append(
          svg("polyline", {
            points: dev[series]
              .map(
                (v, k) => `${x(Math.min(k * dev.step_s, dev.end_s)).toFixed(1)},${y(v).toFixed(1)}`,
              )
              .join(" "),
            class: "battle",
            stroke,
          }),
        );
      if (!devs.length) continue;
      const until = median(devs.map((d) => d.end_s));
      const meanLine = [];
      for (let k = 0; k <= steps && k * STEP_S <= until + STEP_S; k++) {
        const s = Math.min(k * STEP_S, until);
        meanLine.push([s, mean(devs.map((d) => valueAt(d, d[series], s)))]);
      }
      chart.append(
        svg("polyline", {
          points: meanLine.map(([s, v]) => `${x(s).toFixed(1)},${y(v).toFixed(1)}`).join(" "),
          class: "mean",
          stroke,
        }),
      );
      if (first) {
        const [s, v] = meanLine.at(-1);
        chart.append(
          svg(
            "text",
            { x: x(s) + 3, y: y(v) + (series === "own" ? 10 : -3), class: "end-label" },
            series === "own" ? "own" : "enemy",
          ),
        );
      }
    }
    // Orders by kind: a strip of 5 s cells, darker for more orders per battle.
    kinds.forEach(([kind, label], r) => {
      const top0 = CHART + r * ROW;
      chart.append(svg("text", { x: 0, y: top0 + 11, class: "tick" }, label));
      const counts = [];
      for (const dev of devs)
        (dev.orders[kind] || []).forEach((n, k) => (counts[k] = (counts[k] || 0) + n));
      const per = devs.length || 1;
      counts.forEach((n, k) => {
        if (!n) return;
        chart.append(
          svg("rect", {
            x: x(k * STEP_S),
            y: top0 + 1,
            width: Math.max(1, x(STEP_S) - x(0)),
            height: ROW - 3,
            fill: colour,
            opacity: Math.min(1, 0.18 + n / per / 2).toFixed(2),
          }),
        );
      });
      const total = counts.reduce((a, b) => a + (b || 0), 0) / per;
      chart.append(
        svg(
          "text",
          { x: W, y: top0 + 11, class: "tick count", "text-anchor": "end" },
          String(Math.round(total)),
        ),
      );
    });
    const axis = CHART + kinds.length * ROW + 4;
    const minutes = end > 900 ? 5 : end > 300 ? 2 : 1;
    for (let m = 0; m * 60 <= end; m += minutes)
      chart.append(
        svg(
          "text",
          { x: x(m * 60), y: axis + 14, class: "tick", "text-anchor": m ? "middle" : "start" },
          `${m}:00`,
        ),
      );
    // The commander's earliest battle here, in the scenario's chronological order.
    const firstBattle = scenario.battles.find((key) => item.battles.includes(key));
    const open = button("", () => openRun(firstBattle, true), "panel-open");
    open.append(chart);
    if (frame) open.append(routeMap(item, frame));
    open.setAttribute("aria-label", `Watch ${item.name}'s first battle here`);
    const card = el("figure", null, `commander ${item.kind}`);
    card.dataset.keys = item.battles.join(" ");
    const name = el("strong");
    name.append(swatch(item), item.name);
    if (pooled(item.rows)) name.append(dagger(item.rows));
    const about = el("figcaption");
    about.append(name, el("small", record({ items: battles, won: battles.filter(won).length })));
    card.append(about, open);
    return card;
  }

  // What every figure says about one commander in one scenario (completed battles only).
  function rowStats(row) {
    const items = row.battles.map((key) => entries.get(key));
    const timings = items.map((entry) => entry.battle.timing).filter(Boolean);
    // A commander battle's plans: their age is the model's latency, the executor's is not.
    const ages = timings.flatMap((t) => (t.plans.length ? t.plans : t.ages));
    const scores = items.map(scoreOf).filter((value) => value != null);
    const durations = items
      .map((entry) => entry.trial.measures?.duration_s)
      .filter((v) => v != null);
    return {
      items,
      timed: timings.length,
      won: items.filter(won).length,
      scores,
      score: scores.length ? mean(scores) : null,
      durations,
      duration: durations.length ? mean(durations) : null,
      ages,
      box: [0.1, 0.25, 0.5, 0.75, 0.9].map((q) => quantile(ages, q)),
      usd: items.every((entry) => entry.trial.llm?.usd != null)
        ? items.reduce((sum, entry) => sum + entry.trial.llm.usd, 0) / items.length
        : null,
    };
  }

  // Figure 3: per scenario, each model's score and the best scripted rule's, as bars on one
  // scale (seconds for survival) with their records, under its game mode.
  function scoreRow(cell, top) {
    const line = el("div", null, "bar-row"),
      label = el("span", null, `who ${cell.kind}`);
    label.append(swatch(cell), cell.label);
    if (cell.rows.length && pooled(cell.rows)) label.append(dagger(cell.rows, "pooled"));
    line.append(label);
    const value = cell.s?.[cell.metric];
    if (value == null) {
      line.append(
        el(
          "span",
          cell.kind === "model"
            ? cell.rows.length
              ? "not measured"
              : "no battles yet"
            : "no scripted baseline yet",
          "none",
        ),
      );
      return line;
    }
    const bar = el("span", null, "bar"),
      fill = el("i", null, "fill");
    fill.style.width = `${(100 * Math.min(value, top)) / top}%`;
    fill.style.background = cellHue(cell);
    bar.append(fill);
    line.append(bar, el("b", cellValue(cell)), el("small", record(cell.s)));
    return line;
  }
  const pick = (index) => () => {
    renderScenario(index);
    $("watch").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  };
  function renderMatrix() {
    const box = $("matrix");
    box.replaceChildren();
    const known = new Set(data.modes.map((mode) => mode.key)),
      modes = [...data.modes, { key: null, title: "Other battles" }];
    for (const mode of modes) {
      const items = data.scenarios.filter((item) =>
        mode.key === null ? !known.has(item.mode) : item.mode === mode.key,
      );
      if (!items.length) continue;
      const section = el("section", null, "mode");
      const head = el("h3");
      head.append(modeIcon(mode.key), mode.title);
      section.append(head);
      const top = topOf(items);
      const axis = el("div", null, "matrix-axis");
      axis.append(el("span"), scale(top, mode.key === "survival" ? "s survived" : ""));
      section.append(axis);
      for (const item of items) {
        // The whole row opens the scenario; its name is the button for the keyboard.
        const block = el("div", null, "scenario-row");
        block.dataset.scenario = item.id;
        block.addEventListener("click", (e) => {
          if (!e.target.closest("button, sup")) pick(data.scenarios.indexOf(item))();
        });
        const name = el("div", null, "scenario-name");
        name.append(button(item.title, pick(data.scenarios.indexOf(item)), "scenario"));
        if (item.armies?.line) name.append(el("small", item.armies.line));
        const bars = el("div", null, "bars");
        for (const cell of cells(item)) bars.append(scoreRow(cell, top));
        block.append(name, bars);
        section.append(block);
      }
      box.append(section);
    }
    // Older pilots recorded casualties only: their losses score the enemy killed.
    const killed = [...shown].filter(
      (key) => data.battles[key].progress_basis === "killed" && !won(entries.get(key)),
    );
    const caption = el("p", null, "figcap");
    caption.append(
      el("b", "Figure 3. "),
      `Each model's mean score over its completed battles in every scenario (seconds survived in endless survival) and its record, and in grey the best scripted rule's. Click a scenario to watch it above. † pools several settings or test-setup versions (hover it for which), so it is not a controlled comparison.${killed.length ? ` ${killed.length} lost battles recorded casualties only; their scores count the enemy killed, not those who fled (lower bounds).` : ""}`,
    );
    box.append(caption);
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
          caption = `${name}: spectator camera at ${clock(shot.time_ms)}, not what the model saw`;
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
      const range = span(h),
        item = el("li"),
        card = button("", () => Viewer.watch(range.from, h.end_ms ?? null, k), "chapter"),
        label = el("span", null, "label");
      label.append(el("span", String(k + 1), "number"), clock(h.time_ms));
      card.append(label, el("strong", h.title));
      card.setAttribute(
        "aria-label",
        `Analyst note ${k + 1}, ${clock(h.time_ms)}: ${h.title}. Watch it.`,
      );
      item.append(card);
      list.append(item);
    });
    markHighlights();
  }
  // The playing note's sentence, once, under the row of titles.
  function markHighlights() {
    const marked = payload?.highlights?.length ? Viewer.note : -1;
    [...$("highlights").querySelectorAll(".chapter")].forEach((card, k) =>
      card.classList.toggle("active", k === marked),
    );
    $("chapter-text").textContent = marked >= 0 ? payload.highlights[marked].text || "" : "";
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

  function renderMethod() {
    const items = [
      [
        "What a model sees",
        "Text only, at every decision: its own units, the enemy units its army can see right now, the enemy roster shown on the custom-battle screen, a coarse passability grid where the interface provides one, its last orders, notes it wrote itself and how late its previous orders landed. Models answer with orders per unit (move, attack, halt, change behaviour, use an ability; fly, build or reinforce where the battle allows), from a rules-only prompt or one with tactical tips; in the plans setup a model writes plans that scripted unit skills carry out.",
      ],
      [
        "Real time",
        "The battle runs at normal speed from start to finish and never waits for a reply; order age is measured on the battle clock, and accepted is not the same as carried out.",
      ],
      [
        "Opponent and baselines",
        "The game's own battle AI commands the enemy (difficulty in Run settings). Scripted baselines: attack nearest (walk), charge nearest (run), hold position, and per-unit skills with no model.",
      ],
      [
        "Scenarios",
        "Provisional candidates, one per intended decision problem. A different faction, map, army size or difficulty is a variant, not a new family. Each candidate needs executable alternatives and evidence that its choices matter; wins and losses alone do not establish benchmark quality. The strongest-model screen and held-out evaluation are still ahead.",
      ],
    ];
    const battles = data.omitted.battles.length,
      launches = data.omitted.setup_only.length;
    if (battles || launches)
      items.push([
        "Not shown",
        `${[
          battles &&
            `${battles} further battle${battles > 1 ? "s" : ""} (variants, pilots, incomplete attempts and diagnostic probes)`,
          launches && `${launches} launch${launches > 1 ? "es" : ""} stopped during setup`,
        ]
          .filter(Boolean)
          .join(" and ")}; the report JSON and text keep them.`,
      ]);
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
          [scenario.split, scenario.status?.replaceAll("_", " ")].filter(Boolean).join(", "),
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
            .join(", "),
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
            .join(", "),
        ],
        ["Added observation age", `${(trial.delay_ms || 0) / 1000} s`],
        ["Test-setup version", entry.battle.harness],
        ["Interface track", definition.track],
        ["Controller version", trial.card?.version || "unrecorded; see source revision"],
        ["Calibration purpose", trial.card?.disclosure?.purpose],
        ["Declared scenario knowledge", trial.card?.disclosure?.knowledge],
        ["API gateway", isModel(entry) ? definition.provider || "openai" : null],
        ["Requested model", trial.card?.model || (isModel(entry) ? definition.model : null)],
        ["Served models", trial.metrics?.actual_models?.join(", ")],
        ["Serving backends", trial.metrics?.actual_backends?.join(", ")],
        ["Backend model snapshots", trial.metrics?.backend_models?.join(", ")],
        [
          "Replies failing validation",
          trial.metrics?.reply_validation?.attempts
            ? `${trial.metrics.reply_validation.failed} of ${trial.metrics.reply_validation.attempts} (including retries; some orders may be recovered)`
            : null,
        ],
        [
          "Routing limits",
          definition.provider === "openrouter"
            ? JSON.stringify(trial.card?.routing || definition.model_routing)
            : null,
        ],
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
          omitted: data.omitted,
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
  async function setup() {
    if (synthetic) $("demo-banner").hidden = false;
    $("watch-featured").addEventListener("click", () => watchFeatured());
    $("watch-full").addEventListener("click", () => Viewer.watch(0));
    $("run-select").addEventListener("change", (e) => openRun(e.target.value, false));
    $("open-settings").addEventListener("click", openSettings);
    $("close-settings").addEventListener("click", () => $("settings-dialog").close());
    $("close-still").addEventListener("click", () => $("still-dialog").close());
    Viewer.onTime(markHighlights);
    downloads();
    renderMethod();
    if (!data.scenarios.length) {
      $("heading").textContent = "No completed battles in this report";
      for (const id of ["viewer", "results", "plans", "all"]) $(id).hidden = true;
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
      const groups = new Map();
      data.scenarios.forEach((item, index) => {
        const label = modeOf(item)?.title || "Other battles";
        if (!groups.has(label)) groups.set(label, el("optgroup"));
        groups.get(label).label = label;
        const option = el("option", item.title);
        option.value = String(index);
        groups.get(label).append(option);
      });
      $("scenario").replaceChildren(...groups.values());
      $("scenario").addEventListener("change", (e) => renderScenario(Number(e.target.value)));
      $("scenario-pick").hidden = false;
    }
    renderIndex();
    finding();
    renderHeadline();
    renderSpend();
    renderMatrix();
    await renderScenario(Math.max(0, data.scenarios.indexOf(headline)));
    renderInterface(entries.get(scenario.featured), payload);
    // Figure 2 is drawn at its width: redraw it when that changes.
    new ResizeObserver(() => {
      if (Math.abs($("commanders").clientWidth - plansWidth) > 24) renderPlans();
    }).observe($("commanders"));
    // Open on the key moment itself (the army is mid-map there) and play it once a quarter of
    // the map is in view, unless the reader prefers less motion or has already moved the replay.
    // "Play key moment" replays it with its lead-in.
    if (!featured || reduceMotion) return;
    const k = payload.highlights.indexOf(featured);
    Viewer.seek(featured.time_ms);
    const start = Viewer.time;
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        ([seen]) => {
          if (!seen.isIntersecting) return;
          observer.disconnect();
          if (Viewer.time !== start || openKey !== scenario.featured) return;
          // With Model's view on: outlines show where the model last saw each unit.
          Viewer.setLag(true);
          Viewer.watch(start, featured.end_ms ?? null, k, false);
        },
        { threshold: 0.25 },
      );
      observer.observe($("map-wrap"));
    }
  }
  setup();
})();
