// Runs after replay.js in the same script and uses its helpers (el, svg, clock, Viewer, ...).
(() => {
  const $ = (id) => document.getElementById(id);
  const data = JSON.parse($("report-data").textContent);
  const report = data.report;
  const synthetic = data.evidence_kind === "synthetic";
  const NOTICE =
    "SYNTHETIC DEMO: invented values that exercise the report; not benchmark evidence.";
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
  const on = (entry, year = true) => {
    const day = date(entry.battle.date, year);
    return day ? `, ${day}` : "";
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
        text: "Did not finish",
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
  // A battle's score: 100 for a win, else the share of the enemy army broken at the end. A
  // battle that did not finish, or recorded no enemy measure, has none.
  const scoreOf = (entry) =>
    !entry.trial.valid
      ? null
      : (
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
  // A scenario's game mode, as data.modes names it ("land battle").
  const modeOf = (item) => data.modes.find((mode) => mode.key === item.mode);
  function context(entry) {
    return { kind: who(entry).kind, rule: who(entry).detail, synthetic };
  }
  function scenarioEntries(item = scenario) {
    return item.battles.map((key) => entries.get(key));
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
    if (score != null) out.push(`score ${points(score)}${basis ? ` (${basis})` : ""}`);
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
    const held = m.objective_time?.points || [];
    if (held.length)
      out.push(
        `objectives held ${held.map((p) => (p.share == null ? "not recorded" : percent(p.share))).join(", ")} of the time observed`,
      );
    const r = m.resources || {};
    if (r.status === "available") {
      if (r.tickets)
        out.push(
          `tickets: own ${r.tickets.us ?? "?"}, enemy ${r.tickets.enemy ?? "?"}${r.tickets_goal ? `; goal ${r.tickets_goal}` : ""}`,
        );
      if (r.supplies_left != null) out.push(`${r.supplies_left} supplies left`);
      if (r.build) out.push(`${r.build} built`);
      if (r.reinforce) out.push(`${r.reinforce} reinforcements bought`);
    }
    // A battle that did not finish keeps its last observation, labelled so.
    if (out.length && m.basis === "last_observation") out[0] = `at failure: ${out[0]}`;
    return out;
  }
  function markCurrent() {
    for (const node of document.querySelectorAll("[data-keys]"))
      node.setAttribute("aria-current", String(node.dataset.keys.split(" ").includes(openKey)));
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
    const days =
      from === to
        ? from
        : from.split(" ").slice(1).join(" ") === to.split(" ").slice(1).join(" ")
          ? `${from.split(" ")[0]}–${to}`
          : `${from} – ${to}`;
    $("facts").textContent =
      `WH3 Commander Bench, early results${days ? ` from ${days}` : ""}: ${all.length} battles in ${data.scenarios.length} scenarios, ${models.join(" and ") || "no models"}${scripted.size ? ` against ${scripted.size} scripted baselines` : ""}.`;
  }

  // The score scale, 0 to 100, shared by every score bar.
  function scale() {
    const node = el("div", null, "scale");
    for (const value of [0, 50, 100]) {
      const tick = el("span", String(value));
      tick.style.left = `${value}%`;
      node.append(tick);
    }
    return node;
  }
  // A commander's score: the bar reaches its mean, the line spans its worst to its best battle.
  function scoreBar(s) {
    const node = el("div", null, "score");
    if (s.score == null) {
      node.append(el("span", "no finished battle", "none"));
      return node;
    }
    const bar = el("span", null, "bar"),
      fill = el("i", null, "fill");
    fill.style.width = `${s.score}%`;
    bar.append(fill);
    if (s.scores.length > 1) {
      const range = el("i", null, "range"),
        low = Math.min(...s.scores);
      range.style.left = `${low}%`;
      range.style.width = `${Math.max(...s.scores) - low}%`;
      bar.append(range);
    }
    node.append(el("b", points(s.score)), bar);
    return node;
  }
  function whoCell(row, short = false) {
    const cell = el("div", null, "who-cell");
    cell.append(el("strong", row.name));
    if (short ? row.short : row.detail) cell.append(el("small", short ? row.short : row.detail));
    if (row.harnesses > 1) {
      const mark = el("sup", "†", "versions");
      mark.title = `Battles from ${row.harnesses} harness versions (controller, interface or game code). Run settings names each battle's; the report JSON keeps per-version groups.`;
      cell.firstChild.append(mark);
    }
    return cell;
  }
  const won_of = (s) => `${s.won} of ${s.valid.length}`;
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
    const table = $("headline-table");
    table.replaceChildren();
    const head = el("div", null, "board-head");
    const axis = el("div", null, "score");
    axis.append(el("span", "Score"), scale());
    head.append(el("span"), axis, el("span", "Won"), el("span", "Order age"), el("span", "Cost"));
    table.append(head);
    for (const s of all) {
      const line = el("div", null, `board-row ${s.row.kind}`);
      line.append(
        whoCell(s.row, true),
        scoreBar(s),
        el("span", won_of(s)),
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
      `, a ${modeOf(item)?.name || "battle"}: ${item.controlled.launches} game launches, each commander ${item.controlled.once ? "once " : ""}per launch with the same harness${level(item) ? `, against the game's AI on ${level(item)}` : ""}${item.split === "development" ? "; prompts were tuned on this scenario" : ""}. Figure 3 pools all ${item.battles.length} of its battles.`,
    );
    $("headline-foot").replaceChildren(
      ...[
        item.footnote && `* ${item.footnote}`,
        "Score: 100 for success; otherwise the percentage of enemy strength broken in land battles, ticket goal reached in conquest/domination, objective ownership time in sieges/settlements, or batteries in the extraction zone. Survival shows duration instead of an enemy-denominator score. Bars are means and lines span the observed range; scores from different objectives are not interchangeable.",
        "Order age: how old the battle state behind a reply's orders was when the game accepted them (median). Cost: API cost per battle.",
      ]
        .filter(Boolean)
        .map((text) => el("span", text)),
    );
    $("finding").replaceChildren(...finding(item, all));
    $("headline").hidden = false;
  }
  // The headline in two sentences, from the same numbers as Figure 1.
  function finding(item, all) {
    const models = all.filter((s) => s.row.kind === "model" && s.score != null),
      scripts = all.filter((s) => s.row.kind === "scripted" && s.score != null);
    if (!models.length) return [];
    const spread = (values) =>
      Math.min(...values) === Math.max(...values)
        ? seconds(values[0])
        : `${Math.min(...values).toFixed(1)}–${seconds(Math.max(...values))}`;
    const aged = models.filter((s) => s.ages.length),
      best = Math.max(...scripts.map((s) => s.score));
    return [
      `In ${item.title}${level(item) ? `, against the game's AI on ${level(item)}` : ""}, `,
      ...models.flatMap((s, i) => [
        i ? " and " : "",
        el("span", s.row.name, "nowrap"),
        `${i ? "" : " scores"} ${points(s.score)}`,
      ]),
      ` out of 100${scripts.length ? `; the best scripted rule, ${points(best)}` : ""}. `,
      ...(aged.length
        ? [
            "The models' orders act on views of the battle ",
            el("strong", `${spread(aged.map((s) => s.box[2]))} old`, "nowrap"),
            ...(scripts.some((s) => s.ages.length)
              ? [
                  "; the rules' on ",
                  el(
                    "span",
                    `${spread(scripts.filter((s) => s.ages.length).map((s) => s.box[2]))}.`,
                    "nowrap",
                  ),
                ]
              : ["."]),
          ]
        : []),
    ];
  }

  function renderScenario(index, open = true) {
    scenario = data.scenarios[index];
    $("scenario").value = String(index);
    $("question").textContent = scenario.question || scenario.title;
    const mode = modeOf(scenario)?.name || "battle";
    $("challenge").textContent = [
      `${/^[aeiou]/.test(mode) ? "An" : "A"} ${mode}${level(scenario) ? ` against the game's AI on ${level(scenario)}` : ""}${scenario.question && !scenario.title.toLowerCase().startsWith(mode.split(" ")[0]) ? `: ${scenario.title}` : ""}.`,
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
    $("matrix")
      .querySelector(`tr[data-scenario="${scenario.id}"]`)
      ?.closest("details")
      ?.setAttribute("open", "");
    return open ? openRun(scenario.featured, false) : null;
  }

  function renderRunLine(entry) {
    const line = $("run-line"),
      row = scenario.rows.find((item) => item.battles.includes(entry.key));
    line.replaceChildren();
    if (synthetic) line.append(el("span", "SYNTHETIC DEMO", "tag synthetic"));
    const title = el("span", null, "title");
    title.append(el("strong", who(entry).name, "name"), el("span", who(entry).detail, "detail"));
    const result = outcome(entry),
      status = el("span", null, "result");
    status.append(el("span", result.text, result.tone));
    if (row) {
      const items = row.battles.map((key) => entries.get(key)),
        valid = items.filter((e) => e.trial.valid),
        failed = items.length - valid.length;
      const record = el(
        "span",
        items.length === 1
          ? `its only battle here${row.short ? ` with ${row.short}` : ""}`
          : `won ${valid.filter(won).length} of ${valid.length} here${row.short ? ` with ${row.short}` : ""}${failed ? ` (+${failed} did not finish)` : ""}`,
        "sample",
      );
      if (row.harnesses > 1) record.title = "Battles from more than one harness version";
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
    $("watch-featured").textContent = featured?.feature ? "▶ Key maneuver" : "▶ Analyst note 1";
    $("watch-full").disabled = !payload?.frames?.length;
    $("download-replay").disabled = !payload;
    renderChapters();
    if (scroll) Viewer.reveal();
  }

  // Figure 2: one map per model (its settings pooled) and per scripted rule: every battle's
  // army track thin, their mean position thick. Commanders that give no orders are left out.
  function renderPlans() {
    const box = $("routes");
    box.replaceChildren();
    const items = [];
    for (const row of scenario.rows) {
      const same =
        row.kind === "model" &&
        items.find((item) => item.kind === "model" && item.family === row.family);
      if (same) {
        same.rows.push(row);
        same.battles = [...same.battles, ...row.battles];
      } else items.push({ ...row, rows: [row], battles: [...row.battles] });
    }
    const silent = items.filter((item) => {
      const s = rowStats(item);
      return s.timed && !s.ages.length;
    });
    const shown = items.filter(
      (item) =>
        !silent.includes(item) &&
        item.battles.some((key) => entries.get(key).battle.route?.track.length),
    );
    const caption = [
      el("b", "Figure 2. "),
      `${scenario.title}: where each commander's army went (the centre of its units still fighting), in every battle as a thin line, brighter for wins, and as the mean position over time, thick from □ to ●. ◆ enemy units where first seen in its first battle. Click a map to watch its first finished battle.`,
    ];
    if (shown.some((item) => item.rows.length > 1 || item.harnesses > 1))
      caption.push(" † pools several settings or harness versions.");
    if (silent.length)
      caption.push(
        ` Left out: ${silent.map((item) => item.name).join(", ")}, which never ${silent.length > 1 ? "give" : "gives"} orders.`,
      );
    const untracked = items.filter((item) => !silent.includes(item) && !shown.includes(item));
    if (untracked.length)
      caption.push(` No positions recorded: ${untracked.map((item) => item.name).join(", ")}.`);
    if (shown.length === 1) caption.push(" Only one commander has played this scenario so far.");
    $("plans-caption").replaceChildren(...caption);
    if (!shown.length) {
      box.append(el("p", "No army positions were recorded in this scenario.", "caption"));
      return;
    }
    // One framing for every map: all tracks and where the enemy was first seen.
    const tracked = shown.flatMap((item) =>
      item.battles.map((key) => entries.get(key)).filter((e) => e.battle.route?.track.length),
    );
    const extent = tracked.flatMap((entry) => [
      ...entry.battle.route.track.map(([, x, z]) => [x, z]),
      ...entry.battle.route.enemy.map((u) => u.at),
    ]);
    const xs = extent.map((p) => p[0]),
      zs = extent.map((p) => p[1]);
    let [x0, z0, x1, z1] = [Math.min(...xs), Math.min(...zs), Math.max(...xs), Math.max(...zs)];
    const margin = Math.max(40, 0.08 * Math.max(x1 - x0, z1 - z0));
    [x0, z0, x1, z1] = [x0 - margin, z0 - margin, x1 + margin, z1 + margin];
    const aspect = Math.max(0.6, Math.min(1.2, (z1 - z0) / (x1 - x0)));
    const w = 240,
      h = Math.round(w * aspect),
      scale = Math.min(w / (x1 - x0), h / (z1 - z0));
    const px = (x) => w / 2 + (x - (x0 + x1) / 2) * scale,
      py = (z) => h / 2 - (z - (z0 + z1) / 2) * scale;
    const line = (path) =>
      path.map(([x, z]) => `${px(x).toFixed(1)},${py(z).toFixed(1)}`).join(" ");
    const ground = scenario.terrain ? blockedPath(scenario.terrain, px, py, scale) : "";
    for (const item of shown) {
      const battles = item.battles.map((key) => entries.get(key)),
        tracks = battles.filter((e) => e.battle.route?.track.length),
        s = rowStats(item);
      const map = svg("svg", { viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" });
      if (ground) map.append(svg("path", { d: ground, class: "blocked" }));
      for (const u of tracks[0].battle.route.enemy)
        map.append(
          svg("path", {
            d: `M${px(u.at[0])} ${py(u.at[1]) - 3.4}l3.4 3.4-3.4 3.4-3.4-3.4z`,
            class: "foe",
          }),
        );
      for (const entry of tracks)
        map.append(
          svg("polyline", {
            points: line(entry.battle.route.track.map(([, x, z]) => [x, z])),
            class: `trace ${won(entry) ? "won" : ""}`,
          }),
        );
      const path = meanTrack(tracks.map((e) => e.battle.route.track)),
        [sx, sz] = path[0],
        [ex, ez] = path.at(-1);
      map.append(
        svg("polyline", { points: line(path), class: "mean" }),
        svg("rect", { x: px(sx) - 3.5, y: py(sz) - 3.5, width: 7, height: 7, class: "start" }),
        svg("circle", { cx: px(ex), cy: py(ez), r: 3.5, class: "end" }),
      );
      // The earliest finished battle, in the scenario's chronological order.
      const ordered = [...battles].sort(
          (a, b) => scenario.battles.indexOf(a.key) - scenario.battles.indexOf(b.key),
        ),
        first = ordered.find((e) => e.trial.valid) || ordered[0];
      const card = el("figure", null, `plan ${item.kind}`),
        open = button("", () => openRun(first.key, true), "plan-map");
      open.append(map);
      open.setAttribute("aria-label", `Watch ${item.name}'s first finished battle here`);
      card.dataset.keys = item.battles.join(" ");
      const name = el("strong", item.name);
      if (item.rows.length > 1 || item.harnesses > 1) {
        const mark = el("sup", "†", "versions");
        mark.title = item.rows.map((row) => `${row.detail}: ${row.battles.length}`).join("\n");
        name.append(mark);
      }
      const failed = battles.length - s.valid.length;
      const about = el("figcaption");
      about.append(
        name,
        el(
          "small",
          `${battles.length} battle${battles.length === 1 ? "" : "s"}: ${s.won} won${failed ? `, ${failed} did not finish` : ""}`,
        ),
      );
      card.append(open, about);
      box.append(card);
    }
    markCurrent();
  }
  // The mean of several tracks, step by step in battle time; a battle that has ended holds its
  // last position. It runs as long as the median battle.
  function meanTrack(tracks) {
    const ends = tracks.map((track) => track.at(-1)[0]).sort((a, b) => a - b),
      until = ends[Math.floor((ends.length - 1) / 2)],
      out = [];
    for (let t = Math.min(...tracks.map((track) => track[0][0])); t <= until; t += 5) {
      const at = tracks.map((track) => track.findLast(([time]) => time <= t) ?? track[0]);
      out.push([mean(at.map((p) => p[1])), mean(at.map((p) => p[2]))]);
    }
    return out;
  }

  // What every figure says about one commander in one scenario.
  function rowStats(row) {
    const items = row.battles.map((key) => entries.get(key));
    const timings = items.map((entry) => entry.battle.timing).filter(Boolean);
    const valid = items.filter((entry) => entry.trial.valid);
    const plans = timings.flatMap((t) => t.plans);
    // A commander's model plans: their age is the model's latency, the executor's is not.
    const ages = plans.length ? plans : timings.flatMap((t) => t.ages);
    const scores = valid.map(scoreOf).filter((value) => value != null);
    return {
      items,
      valid,
      timed: timings.length,
      won: valid.filter(won).length,
      scores,
      score: scores.length ? mean(scores) : null,
      ages,
      executor: plans.length ? median(timings.flatMap((t) => t.ages)) : null,
      box: [0.1, 0.25, 0.5, 0.75, 0.9].map((q) => quantile(ages, q)),
      usd: items.every((entry) => entry.trial.llm?.usd != null)
        ? items.reduce((sum, entry) => sum + entry.trial.llm.usd, 0) / items.length
        : null,
    };
  }

  // Figure 3: each model's score in every scenario, and the best scripted rule's.
  function families() {
    const all = [...shown].map((key) => entries.get(key));
    const names = [...new Set(all.filter(isModel).map((entry) => who(entry).family))].sort();
    if (all.some((entry) => who(entry).kind === "scripted")) names.push("Scripted");
    return names;
  }
  function scoreCell(item, family) {
    const cell = el("div", null, "cell"),
      rows = item.rows.filter((row) => row.family === family);
    if (!rows.length) {
      cell.append(el("span", family === "Scripted" ? "no baseline yet" : "–", "none"));
      return cell;
    }
    // A model pools its commanders here; the scripted column shows its best rule.
    const stats = rows.map((row) => ({ row, ...rowStats(row) }));
    const pooled = rowStats({ battles: rows.flatMap((row) => row.battles) }),
      best = stats.filter((s) => s.score != null).sort((a, b) => b.score - a.score)[0],
      shown = family === "Scripted" ? best : pooled;
    if (shown?.score == null) {
      cell.append(el("span", pooled.valid.length ? "not measured" : "did not finish", "none"));
      return cell;
    }
    cell.style.setProperty("--score", shown.score / 100);
    cell.append(el("b", points(shown.score)));
    cell.append(
      el("small", family === "Scripted" ? best.row.name : `${shown.scores.length} finished`),
    );
    if (family === "Scripted" && best.row.harnesses > 1) {
      const mark = el("sup", "†", "pooled");
      mark.title = `${best.row.name}: battles from ${best.row.harnesses} harness versions`;
      cell.firstChild.append(mark);
    }
    if (family !== "Scripted" && (rows.length > 1 || rows.some((row) => row.harnesses > 1))) {
      const mark = el("sup", "†", "pooled");
      mark.title = stats
        .map(
          (s) =>
            `${s.row.name}, ${s.row.detail}: ${s.score == null ? "no score" : points(s.score)}${s.row.harnesses > 1 ? ` (${s.row.harnesses} harness versions)` : ""}`,
        )
        .join("\n");
      cell.firstChild.append(mark);
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
    const known = new Set(data.modes.map((mode) => mode.key)),
      modes = data.scenarios.some((item) => !known.has(item.mode))
        ? [...data.modes, { key: null, title: "Other battles" }]
        : data.modes;
    for (const mode of modes) {
      const items = data.scenarios.filter((item) =>
        mode.key === null ? !known.has(item.mode) : item.mode === mode.key,
      );
      const fold = el("details"),
        head = el("summary");
      head.append(
        el("span", mode.title),
        el("small", `${items.length} scenario${items.length === 1 ? "" : "s"}`),
      );
      fold.append(head);
      fold.open = items.includes(headline || data.scenarios[0]);
      if (!items.length) {
        fold.append(el("p", "No battles of this type yet.", "placeholder"));
        box.append(fold);
        continue;
      }
      // Fixed column widths, so each model's column lines up across the modes.
      const table = el("table"),
        row = el("tr"),
        columns = el("colgroup");
      columns.append(el("col"), ...all.map(() => el("col")));
      columns.firstChild.style.width = "40%";
      for (const label of [
        "Scenario",
        ...all.map((f) => (f === "Scripted" ? "Best scripted rule" : f)),
      ]) {
        const th = el("th", label);
        th.scope = "col";
        row.append(th);
      }
      const thead = el("thead"),
        body = el("tbody");
      thead.append(row);
      for (const item of items) {
        const tr = el("tr"),
          name = el("td");
        tr.dataset.scenario = item.id;
        name.append(button(item.title, pick(data.scenarios.indexOf(item)), "scenario"));
        const sides = [item.armies?.friendly, item.armies?.enemy].filter(Boolean).join(" against ");
        if (sides) name.append(el("small", sides));
        tr.append(name);
        for (const family of all) {
          const td = el("td");
          td.dataset.label = family === "Scripted" ? "Best scripted rule" : family;
          td.append(scoreCell(item, family));
          tr.append(td);
        }
        body.append(tr);
      }
      table.append(columns, thead, body);
      fold.append(table);
      box.append(fold);
    }
    // Older pilots recorded casualties only: their losses score the enemy killed.
    const killed = [...shown].filter(
      (key) => data.battles[key].progress_basis === "killed" && !won(entries.get(key)),
    );
    const caption = el("p", null, "figcap");
    caption.append(
      el("b", "Figure 3. "),
      `Each model's mean score over its finished battles in every scenario, darker for higher, beside the best scripted rule's; one section per game mode. Click a scenario to watch it above. † pools settings or harness versions: not a controlled comparison.${killed.length ? ` ${killed.length} lost pilot battles recorded casualties only; their scores count the enemy killed, not those who fled (lower bounds).` : ""}`,
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
      label.append(
        el("span", String(k + 1), "number"),
        `${clock(h.time_ms)} ${KINDS[h.kind] || "Moment"}`,
      );
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
        "Text only, at every decision: its own units, the enemy units its army can see right now, the enemy roster shown on the custom-battle screen, a coarse passability grid where the interface provides one, its last orders, notes it wrote itself and how late its previous orders landed. Prompted models answer with orders per unit (move, attack, halt, change behaviour, use an ability; fly, build or reinforce where the battle allows), with tactical advice in the prompt (“tactics” in the battle menu) or without it; the plan harness (“plans”) answers instead with plans that scripted unit skills carry out.",
      ],
      [
        "Real time",
        "The battle runs at normal speed from start to finish and never waits for a reply; order age is measured on the battle clock, and accepted is not the same as carried out. Deferred self-comparisons will vary army workload, neutral prompt length, useful history, factual representation or added observation age separately. More units also change combat and action volume; they do not isolate context length.",
      ],
      [
        "Opponent and baselines",
        "The game's own battle AI commands the enemy (difficulty in Run settings). Scripted baselines: attack nearest (walk), charge nearest (run), hold position, and per-unit skills with no model.",
      ],
      [
        "Scenario coverage",
        `${new Set(data.scenarios.filter((s) => s.core_candidate && s.family).map((s) => s.family)).size} candidate decision families have evidence. Map, faction, difficulty and size variants do not count as new families; historical pilots remain inspectable. Each new family needs a distinct hard choice and at least two credible plays.`,
      ],
      ["Status", status()],
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
        ["Failure", trial.error],
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
    renderFacts();
    renderMethod();
    if (!data.scenarios.length) {
      $("question").textContent = "No recorded battles in this report";
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
    renderHeadline();
    renderMatrix();
    await renderScenario(Math.max(0, data.scenarios.indexOf(headline)));
    renderInterface(entries.get(scenario.featured), payload);
    // Open on the key maneuver itself (the army is mid-map there) and play it once a quarter of
    // the map is in view, unless the reader prefers less motion or has already moved the replay.
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
