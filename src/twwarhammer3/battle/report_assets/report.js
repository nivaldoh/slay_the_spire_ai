// Runs after replay.js in the same script and uses its shared helpers (el, svg, fmt, ...).
(() => {
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const report = data.report;
  const $ = (id) => document.getElementById(id);
  const percent = (value) => (value == null ? "Unavailable" : `${fmt(value * 100, 1)}%`);
  const money = (value) => (value == null ? "Unavailable" : `$${fmt(value, 5)}`);
  const code = (prefix, index) => `${prefix}${String(index + 1).padStart(2, "0")}`;
  const distinct = (values) => [...new Set(values)];
  const synthetic = data.evidence_kind === "synthetic";
  const palette = ["#325e4f", "#3c5f81", "#8e493c", "#795b89", "#876824", "#336c70"];
  let view,
    rows = [],
    selected = new Set(),
    sort = { key: "label", direction: 1 };
  let chartSVG = null;

  function table(headers, contents) {
    const node = el("table"),
      head = el("thead"),
      tr = el("tr"),
      body = el("tbody");
    for (const name of headers) {
      const th = el("th", name);
      th.scope = "col";
      tr.append(th);
    }
    head.append(tr);
    for (const cells of contents) {
      const row = el("tr");
      for (const cell of cells) {
        const td = el("td");
        if (cell instanceof Node) td.append(cell);
        else td.textContent = cell ?? "Unavailable";
        row.append(td);
      }
      body.append(row);
    }
    node.append(head, body);
    return node;
  }
  function empty(target, text, note) {
    const node = el("p", text, "empty");
    if (note) node.append(el("small", note));
    target.replaceChildren(node);
  }
  function groups() {
    return view.groups.map((index) => report.groups[index]);
  }
  function allTrials() {
    return groups().flatMap((group) => group.trials);
  }
  function currentRows() {
    return rows.filter((row) => selected.has(row.id));
  }
  function currentTrials() {
    return currentRows().flatMap((row) => row.items.map((trial) => ({ trial, row })));
  }
  function status() {
    if (synthetic) return "SYNTHETIC DEMO · invented values · not benchmark evidence";
    const scenario = view.definition.scenario || {};
    if (!allTrials().length) return "Not measured yet";
    if (scenario.split === "held_out")
      return `Held-out evaluation · ${scenario.status === "admitted" ? "admitted scenario" : "admission not established"}`;
    if (scenario.status === "admitted") return "Admitted scenario";
    const n = distinct(allTrials().map((trial) => trial.instance)).length;
    return `Development pilot: ${n === 1 ? "one independent launch" : `${n} independent launches`}`;
  }
  function identity(group, summary) {
    const items = group.trials.filter((trial) => trial.controller === summary.controller);
    const first = items[0] || {},
      card = first.card || {};
    const modelPolicy = data.model_policies.includes(first.policy);
    const model = card.model || (modelPolicy ? group.definition.model : null);
    const effort = card.effort || (modelPolicy ? group.definition.effort : null);
    const aliases = { attack_nearest: "Walk-nearest", rush_nearest: "Run-nearest" };
    const policy = first.policy || summary.controller;
    let label = model
      ? `${model} · ${effort || "effort unrecorded"} · ${policy}`
      : `${aliases[policy] || policy}${card.kind === "scripted" || policy in aliases ? " · scripted" : ""}`;
    if (card.kind === "external")
      label += ` · ${(card.source_sha256 || "source unknown").slice(0, 12)}`;
    return { label, items, delay: first.delay_ms, card };
  }
  function loadView(index) {
    view = data.comparisons[index];
    rows = view.groups
      .flatMap((groupIndex) => {
        const group = report.groups[groupIndex];
        return group.controllers.map((summary, index) => ({
          ...summary,
          ...identity(group, summary),
          id: `g${groupIndex}-r${index}`,
          groupIndex,
          evidence: code("E", groupIndex),
        }));
      })
      .sort(
        (a, b) => a.label.localeCompare(b.label) || a.delay - b.delay || a.id.localeCompare(b.id),
      );
    rows.forEach((row, index) => {
      row.symbol = index;
      row.code = code("C", index);
    });
    selected = new Set(rows.map((row) => row.id));
    sort = { key: "label", direction: 1 };
    renderBrief();
    renderControllers();
    renderSelection();
    renderJobs();
    // The replay names each trial's controller exactly as its table row does.
    const names = {};
    for (const row of rows)
      for (const trial of row.items)
        names[`g${row.groupIndex}-t${report.groups[row.groupIndex].trials.indexOf(trial)}`] =
          row.label;
    window.wh3Replay.load(data, view, status(), names);
  }
  function renderBrief() {
    const definition = view.definition,
      scenario = definition.scenario || {},
      expect = scenario.expect || {};
    $("status").textContent = status();
    $("brief-heading").textContent = scenario.family || scenario.name || "Unlabelled scenario";
    $("scenario-name").textContent = scenario.name || "Scenario identifier unavailable";
    $("brief-text").textContent =
      scenario.brief || "No tactical brief was recorded for this scenario.";
    $("metadata-origin").textContent =
      `${synthetic ? "Synthetic fixture" : view.metadata_origin}. ${allTrials().length ? "Scenario admission is not inferred from wins." : "No started trials in the supplied evidence. This is not a gameplay loss."}`;
    const role =
      scenario.attacker === "player"
        ? "Attacker"
        : scenario.attacker === "enemy"
          ? "Defender"
          : expect.player_defends == null
            ? "Unrecorded"
            : expect.player_defends
              ? "Defender"
              : "Attacker";
    const settings = [
      ["Player role", role],
      [
        "Battle timer",
        expect.time_limit_s == null
          ? "Unrecorded"
          : `${expect.time_limit_s / 60} min · ${expect.time_limit_s} s`,
      ],
      [
        "AI difficulty",
        (expect.difficulty || "Unrecorded").replace(/^ai_level_/, "").replaceAll("_", " "),
      ],
      ["AI stat modifier", expect.ai_stats_modifier ?? "Unrecorded"],
      [
        "Forces · player / enemy",
        `${scenario.player?.units?.length ?? "?"} / ${scenario.enemy?.units?.length ?? "?"} units`,
      ],
      [
        "Split / admission",
        `${scenario.split || "Unrecorded"} / ${scenario.status || "Unrecorded"}`,
      ],
    ];
    $("settings").replaceChildren(
      ...settings.map(([name, value]) => {
        const node = el("div");
        node.append(el("dt", name), el("dd", value));
        return node;
      }),
    );
    $("forces").replaceChildren();
    for (const side of ["player", "enemy"]) {
      const force = scenario[side] || {},
        ul = el("ul");
      $("forces").append(el("p", `${side}: ${force.faction || "faction unrecorded"}`, "mono"));
      const units = (force.units || []).map((unit, index) => force.mounts?.[String(index)] || unit);
      for (const unit of distinct(units))
        ul.append(el("li", `${units.filter((value) => value === unit).length} × ${unit}`));
      $("forces").append(ul);
    }
    $("scenario-detail").textContent = json(scenario);
    $("comparison-settings").textContent =
      `Source ${definition.source || "unrecorded"} · Build ${definition.game?.steam_build_id || "unrecorded"} · ${definition.track || "interface unrecorded"} · Observation ${definition.observe_ms ?? "?"} ms / tick ${definition.tick_ms ?? "?"} ms / pacing ${definition.interval_ms ?? "?"} ms`;
    $("limitations").textContent = report.limitations || "";
  }
  const columns = [
    ["label", "Controller / added age"],
    ["outcomes", "W / L / D / T"],
    ["win_rate", "Non-timer win rate · 95% CI"],
    ["margin", "Active margin"],
    ["instances", "Independent launches"],
    ["valid", "Valid / started"],
    ["cost", "USD / attempted trial"],
    ["failures", "Failures"],
  ];
  function sortValue(row, key) {
    if (key === "cost") return meanCost(row);
    if (key === "margin") return row.means.margin;
    if (key === "failures") return row.trials - row.valid;
    if (key === "outcomes") return row.outcomes.won || 0;
    return row[key];
  }
  function renderControllers() {
    if (!rows.length) {
      empty(
        $("controller-table"),
        "Not measured yet",
        "No controller trial records in this comparison.",
      );
      return;
    }
    const node = el("table"),
      head = el("thead"),
      heading = el("tr"),
      body = el("tbody");
    for (const [key, title] of columns) {
      const th = el("th"),
        button = el(
          "button",
          title + (sort.key === key ? (sort.direction === 1 ? " ↑" : " ↓") : ""),
        );
      th.scope = "col";
      th.setAttribute(
        "aria-sort",
        sort.key === key ? (sort.direction === 1 ? "ascending" : "descending") : "none",
      );
      button.addEventListener("click", () => {
        sort = { key, direction: sort.key === key ? -sort.direction : 1 };
        renderControllers();
      });
      th.append(button);
      heading.append(th);
    }
    const sorted = [...rows].sort((a, b) => {
      const x = sortValue(a, sort.key),
        y = sortValue(b, sort.key);
      if (x == null || y == null)
        return x == null ? (y == null ? a.id.localeCompare(b.id) : 1) : -1;
      return (
        (typeof x === "string" ? x.localeCompare(y) : x - y) * sort.direction ||
        a.label.localeCompare(b.label) ||
        a.id.localeCompare(b.id)
      );
    });
    for (const row of sorted) {
      const tr = el("tr"),
        td = el("td", undefined, "identity"),
        label = el("label"),
        checkbox = el("input");
      checkbox.type = "checkbox";
      checkbox.checked = selected.has(row.id);
      tr.dataset.selected = String(checkbox.checked);
      checkbox.setAttribute(
        "aria-label",
        `${row.label}, +${(row.delay || 0) / 1000}s, ${row.evidence}`,
      );
      checkbox.addEventListener("change", () => {
        tr.dataset.selected = String(checkbox.checked);
        if (checkbox.checked) selected.add(row.id);
        else selected.delete(row.id);
        renderSelection();
      });
      label.append(checkbox, el("span", row.label));
      td.append(
        label,
        el("small", `${row.code} / ${row.evidence} / +${(row.delay || 0) / 1000}s added age`),
      );
      tr.append(td);
      const interval = row.win_ci95
        ? `[${percent(row.win_ci95[0])}, ${percent(row.win_ci95[1])}]`
        : "CI unavailable";
      const values = [
        ["won", "lost", "draw", "time_limit"].map((key) => row.outcomes[key] || 0).join(" / "),
        `${percent(row.win_rate)} · ${interval}`,
        fmt(row.means.margin, 3),
        row.instances,
        `${row.valid} / ${row.trials}`,
        money(meanCost(row)),
        row.trials - row.valid,
      ];
      for (const value of values) tr.append(el("td", String(value), "number"));
      body.append(tr);
    }
    head.append(heading);
    node.append(head, body);
    $("controller-table").replaceChildren(node);
  }
  function trialText(trial, row) {
    const metrics = trial.metrics;
    return `${row.label} · ${row.evidence} · ${trial.instance}/${trial.episode} · ${trial.outcome}${trial.outcome === "time_limit" ? ` (engine ${trial.engine_outcome})` : ""} · margin ${metrics.margin ?? "unavailable"} · order age ${metrics.order_age_s?.mean ?? "unavailable"} s · snapshot age at decision ${metrics.snapshot_age_at_decision_s?.mean ?? "unavailable"} s · requested added age ${(trial.delay_ms || 0) / 1000} s · inference USD ${trialCost(trial) ?? "unavailable"}`;
  }
  function meanCost(row) {
    // The collector's recorded USD sum is retained in JSON. An incomplete cost
    // record is not evidence of free inference, so withhold its displayed mean.
    return row.trials && row.items.every((trial) => trialCost(trial) != null)
      ? row.usd / row.trials
      : null;
  }
  function chooseTrial(trial, row) {
    $("selection").textContent = trialText(trial, row);
  }
  function renderTrials() {
    const trials = currentTrials();
    if (!trials.length) {
      empty($("trial-table"), rows.length ? "No controllers selected" : "Not measured yet");
      empty($("tactical-table"), "No selected trial values");
      return;
    }
    $("trial-table").replaceChildren(
      table(
        [
          "Trial · select for exact values",
          "Controller / group",
          "Outcome",
          "Margin",
          "Order age (s)",
          "Snapshot age at decision (s)",
          "Added age (s)",
          "Inference USD",
        ],
        trials.map(({ trial, row }) => {
          const button = el("button", `${trial.instance}/${trial.episode}`, "trial-pick");
          button.addEventListener("click", () => chooseTrial(trial, row));
          return [
            button,
            `${row.label} / ${row.evidence}`,
            `${trial.outcome}${trial.outcome === "time_limit" ? ` (engine ${trial.engine_outcome})` : ""}`,
            fmt(trial.metrics.margin, 3),
            fmt(trial.metrics.order_age_s?.mean, 3),
            fmt(trial.metrics.snapshot_age_at_decision_s?.mean, 3),
            (trial.delay_ms || 0) / 1000,
            money(trialCost(trial)),
          ];
        }),
      ),
    );
    const tactical = trials.filter(
      ({ trial }) => trial.protected_left != null || trial.objectives != null,
    );
    if (!tactical.length) {
      empty($("tactical-table"), "No tactical metrics recorded for these trials");
      return;
    }
    $("tactical-table").replaceChildren(
      table(
        [
          "Trial / controller",
          "Protected units · active share",
          "Victory-point control share",
          "Key-point control share",
          "Control-share method",
          "Supplies left",
          "Reinforcement purchases by type",
        ],
        tactical.map(({ trial, row }) => [
          `${trial.instance}/${trial.episode} · ${row.code}`,
          percent(trial.protected_left),
          percent(trial.objectives?.victory_held),
          percent(trial.objectives?.key_held),
          trial.objectives
            ? trial.objectives.method || "legacy observation samples"
            : "Unavailable",
          trial.objectives?.supplies_left ?? "Unavailable",
          trial.objectives?.reinforcements_by_type == null
            ? "Unavailable"
            : json(trial.objectives.reinforcements_by_type),
        ]),
      ),
    );
  }
  function renderEvidence() {
    const active = currentRows(),
      trials = currentTrials(),
      pairs = [];
    for (const index of view.groups) {
      const labels = active.filter((row) => row.groupIndex === index).map((row) => row.controller);
      for (const pair of report.groups[index].paired)
        if (labels.includes(pair.a) && labels.includes(pair.b)) {
          pairs.push({ evidence_group: code("E", index), ...pair });
        }
    }
    $("pairs").replaceChildren();
    if (!pairs.length) empty($("pairs"), "No paired comparisons for the selection");
    for (const pair of pairs) {
      const item = el("details"),
        ci = pair.ci95 ? pair.ci95.map((value) => fmt(value, 3)).join(", ") : "unavailable";
      item.append(
        el(
          "summary",
          `${pair.evidence_group} · ${pair.a} − ${pair.b} · ${pair.n} paired launches · mean ${fmt(pair.mean, 3)} · 95% CI ${ci}`,
        ),
        el("pre", json(pair)),
      );
      $("pairs").append(item);
    }
    const failed = trials.filter(({ trial }) => !trial.valid).length;
    const unchecked = trials.filter(({ trial }) => !trial.setup_checked).length;
    const flagged = trials.filter(({ trial }) => trial.start_flagged).length;
    const rejections = trials.reduce(
      (sum, { trial }) =>
        sum + Object.values(trial.metrics.rejections || {}).reduce((a, b) => a + b, 0),
      0,
    );
    $("failure-summary").textContent =
      `Selected trials: ${failed} failures / incomplete results · ${unchecked} unchecked setups · ${flagged} flagged starts · ${rejections} order rejections. Job interruptions, including those with zero started battles, are listed below.`;
    $("failures").replaceChildren(
      el(
        "pre",
        json(
          trials.map(({ trial, row }) => ({
            controller: row.label,
            evidence_group: row.evidence,
            instance: trial.instance,
            episode: trial.episode,
            outcome: trial.outcome,
            engine_outcome: trial.engine_outcome,
            error: trial.error,
            setup_checked: trial.setup_checked,
            start_flagged: trial.start_flagged,
            start_comparison: trial.start_comparison,
            rejections: trial.metrics.rejections,
          })),
        ),
      ),
    );
    $("provenance").textContent = json({
      metadata_origin: view.metadata_origin,
      evidence_kind: data.evidence_kind,
      comparison: view.definition,
      evidence_groups: view.groups.map((index) => ({
        id: code("E", index),
        definition: report.groups[index].definition,
      })),
      controllers: active.map((row) => ({
        label: row.label,
        evidence_group: row.evidence,
        card: row.card,
      })),
      jobs: view.jobs.map((index) => report.jobs[index]),
    });
  }
  function renderJobs() {
    const trials = report.groups.flatMap((group) => group.trials);
    $("jobs").replaceChildren(
      table(
        [
          "Job identifier",
          "Recorded status",
          "Valid / started",
          "Wall seconds",
          "Error",
          "Setup checks",
        ],
        (report.jobs || []).map((job) => {
          const items = trials.filter((trial) => trial.instance === job.instance);
          return [
            job.instance,
            job.recorded_status || "Unrecorded",
            `${items.filter((trial) => trial.valid).length} / ${items.length}`,
            fmt(job.wall_seconds, 2),
            job.error || "None recorded",
            job.setup_checks ? json(job.setup_checks) : "Unavailable",
          ];
        }),
      ),
    );
  }
  function wrapSVG(target, value, x, y, maxChars = 110, size = 12, color = "#60665d") {
    // Wrap exported labels too: no dependence on CSS or browser-only foreignObject.
    const lines = String(value).match(
      new RegExp(`.{1,${maxChars}}(?:\\s|$)|.{1,${maxChars}}`, "g"),
    ) || [""];
    lines.forEach((line, index) =>
      target.append(
        svg("text", { x, y: y + index * 17, fill: color, "font-size": size }, line.trim()),
      ),
    );
    return y + lines.length * 17;
  }
  function marker(symbol, x, y, color) {
    const attrs = { fill: color, stroke: "#fbf9f2", "stroke-width": 2 };
    switch (symbol % 4) {
      case 0:
        return svg("circle", { ...attrs, cx: x, cy: y, r: 7 });
      case 1:
        return svg("rect", { ...attrs, x: x - 7, y: y - 7, width: 14, height: 14 });
      case 2:
        return svg("path", {
          ...attrs,
          d: `M${x},${y - 9}L${x + 9},${y}L${x},${y + 9}L${x - 9},${y}Z`,
        });
      default:
        return svg("path", {
          ...attrs,
          d: `M${x},${y - 9}L${x + 9},${y + 7}L${x - 9},${y + 7}Z`,
        });
    }
  }
  function renderChart() {
    chartSVG = null;
    const axis = $("axis").value,
      trials = currentTrials(),
      selectedRows = currentRows();
    const hasAdded = trials.some(({ trial }) => trial.delay_ms > 0);
    const axisTitle =
      axis === "cost"
        ? "Inference cost per attempted trial (USD)"
        : axis === "added"
          ? "Requested added snapshot age (seconds)"
          : "Mean measured information age at order issuance (seconds)";
    $("chart-note").textContent =
      axis === "added"
        ? "Controlled added-age conditions. Exact measured ages appear in the trial table and point selection. Horizontal offsets separate overlapping points; no unmeasured condition is interpolated."
        : "One point per valid trial with both metrics recorded. Shapes and controller codes identify evidence rows. Select a point with a click, Enter or Space; the trial table provides the same values.";
    const points = trials.filter(
      ({ trial }) =>
        trial.valid &&
        trial.metrics.margin != null &&
        (axis === "cost"
          ? trialCost(trial) != null
          : axis === "added" || trial.metrics.order_age_s?.mean != null),
    );
    if (!points.length || (axis === "added" && !hasAdded)) {
      empty(
        $("chart"),
        axis === "added"
          ? "Not measured yet"
          : rows.length
            ? "No plottable trials selected"
            : "Not measured yet",
        axis === "added"
          ? "The 0 / 6 / 10-second experiment has no added-age results in this selection."
          : "Missing metrics are not plotted as zero.",
      );
      $("export-svg").disabled = true;
      $("export-png").disabled = true;
      return;
    }
    const chart = svg("svg", {
      xmlns: "http://www.w3.org/2000/svg",
      role: "img",
      "aria-label": `${axisTitle} versus active-strength margin`,
      "font-family": "system-ui, sans-serif",
    });
    chart.append(svg("title", {}, `${status()} — ${axisTitle} versus active-strength margin`));
    chart.append(
      svg(
        "desc",
        {},
        "Individual trial points. Exact values are also available in the trial table.",
      ),
    );
    const background = svg("rect", { width: 1040, height: "100%", fill: "#fbf9f2" });
    chart.append(background);
    let top = wrapSVG(
      chart,
      `WH3 FIELD REPORT · ${view.definition.scenario?.name || "Unlabelled scenario"}`,
      30,
      30,
      105,
      15,
      "#252d29",
    );
    top = wrapSVG(chart, status(), 30, top + 6, 120, 12, "#876824");
    top = wrapSVG(
      chart,
      `${selectedRows.reduce((n, row) => n + row.valid, 0)} valid / ${trials.length} started · ${distinct(trials.map(({ trial }) => trial.instance)).length} launches with selected trials · ${points.length} plotted / ${trials.length - points.length} excluded (invalid or missing metrics)`,
      30,
      top + 6,
    );
    const y0 = top + 22,
      plotH = 285,
      x0 = 90,
      plotW = 870;
    const conditions = distinct([
      0,
      6,
      10,
      ...trials.map(({ trial }) => (trial.delay_ms || 0) / 1000),
    ]).sort((a, b) => a - b);
    const xValue = ({ trial }) =>
      axis === "cost"
        ? trialCost(trial)
        : axis === "added"
          ? (trial.delay_ms || 0) / 1000
          : trial.metrics.order_age_s.mean;
    const maxX = Math.max(...points.map(xValue), 0.01) * 1.1;
    const px = (point, index) =>
      axis === "added"
        ? x0 +
          ((conditions.indexOf(xValue(point)) + 0.5) / conditions.length) * plotW +
          ((index % 7) - 3) * 5
        : x0 + (xValue(point) / maxX) * plotW;
    const py = (margin) => y0 + ((1 - margin) / 2) * plotH;
    chart.append(
      svg(
        "text",
        { x: x0, y: y0 - 10, fill: "#60665d", "font-size": 11 },
        "ACTIVE-STRENGTH MARGIN",
      ),
    );
    for (const value of [-1, -0.5, 0, 0.5, 1]) {
      const y = py(value);
      chart.append(
        svg("line", {
          x1: x0,
          x2: x0 + plotW,
          y1: y,
          y2: y,
          stroke: value === 0 ? "#9b9e90" : "#dddace",
          "stroke-dasharray": value === 0 ? "4 4" : "none",
        }),
        svg(
          "text",
          { x: x0 - 12, y: y + 4, "text-anchor": "end", fill: "#60665d", "font-size": 12 },
          value.toFixed(1),
        ),
      );
    }
    const ticks =
      axis === "added" ? conditions : Array.from({ length: 6 }, (_, i) => (maxX * i) / 5);
    ticks.forEach((value, index) => {
      const x =
        axis === "added"
          ? x0 + ((index + 0.5) / conditions.length) * plotW
          : x0 + (value / maxX) * plotW;
      chart.append(
        svg(
          "text",
          { x, y: y0 + plotH + 24, "text-anchor": "middle", "font-size": 12, fill: "#60665d" },
          axis === "added"
            ? `${value} s${points.some((point) => xValue(point) === value) ? "" : " · not measured"}`
            : fmt(value, axis === "cost" ? 3 : 1),
        ),
      );
    });
    chart.append(
      svg(
        "text",
        {
          x: x0 + plotW / 2,
          y: y0 + plotH + 52,
          "text-anchor": "middle",
          "font-size": 12,
          fill: "#252d29",
        },
        axisTitle,
      ),
    );
    points.forEach((point, index) => {
      const { trial, row } = point,
        x = px(point, index),
        y = py(trial.metrics.margin),
        color = palette[row.symbol % palette.length];
      const dot = marker(row.symbol, x, y, color);
      dot.setAttribute("tabindex", "0");
      dot.setAttribute("role", "button");
      dot.setAttribute("class", "point");
      dot.setAttribute("aria-label", trialText(trial, row));
      dot.append(svg("title", {}, trialText(trial, row)));
      dot.addEventListener("click", () => chooseTrial(trial, row));
      dot.addEventListener("keydown", (event) => {
        if (["Enter", " "].includes(event.key)) {
          event.preventDefault();
          chooseTrial(trial, row);
        }
      });
      chart.append(dot);
      if (points.length <= 12)
        chart.append(svg("text", { x: x + 11, y: y - 10, fill: color, "font-size": 11 }, row.code));
    });
    let bottom = y0 + plotH + 83;
    for (const row of selectedRows) {
      chart.append(marker(row.symbol, 37, bottom - 4, palette[row.symbol % palette.length]));
      bottom = wrapSVG(
        chart,
        `${row.code} · ${row.label} · ${row.evidence} · +${(row.delay || 0) / 1000}s · ${row.valid}/${row.trials} valid/started · ${row.instances} launches`,
        55,
        bottom,
        120,
        11,
      );
      bottom += 7;
    }
    const def = view.definition,
      expect = def.scenario?.expect || {};
    bottom = wrapSVG(
      chart,
      `Source ${def.source || "unrecorded"} · build ${def.game?.steam_build_id || "unrecorded"} · ${def.track || "interface unrecorded"}`,
      30,
      bottom + 8,
      130,
      10,
    );
    bottom = wrapSVG(
      chart,
      `Observe/tick/pacing: ${def.observe_ms ?? "?"}/${def.tick_ms ?? "?"}/${def.interval_ms ?? "?"} ms · AI ${expect.difficulty || "?"} ×${expect.ai_stats_modifier || "?"} · timer ${expect.time_limit_s ?? "?"} s · split ${def.scenario?.split || "?"}`,
      30,
      bottom + 3,
      130,
      10,
    );
    bottom = wrapSVG(
      chart,
      "Descriptive trial points, not a causal estimate. Rematches are correlated; evidence groups are not pooled. Missing values are excluded.",
      30,
      bottom + 3,
      130,
      10,
    );
    chart.setAttribute("viewBox", `0 0 1040 ${bottom + 20}`);
    chart.setAttribute("width", "1040");
    chart.setAttribute("height", String(bottom + 20));
    chartSVG = chart;
    $("chart").replaceChildren(chart);
    $("export-svg").disabled = false;
    $("export-png").disabled = false;
  }
  function renderSelection() {
    $("selection").textContent = "Select a trial point or a row below for exact values.";
    renderTrials();
    renderChart();
    renderEvidence();
  }
  function exportFile(blob, extension) {
    download(
      blob,
      `wh3-${synthetic ? "synthetic-demo-" : ""}${view.id}-${$("axis").value}.${extension}`,
    );
    $("export-status").textContent = `${extension.toUpperCase()} download ready.`;
  }
  function svgBlob() {
    return new Blob([new XMLSerializer().serializeToString(chartSVG)], {
      type: "image/svg+xml;charset=utf-8",
    });
  }
  $("export-svg").addEventListener("click", () => {
    if (chartSVG) exportFile(svgBlob(), "svg");
  });
  $("export-png").addEventListener("click", async () => {
    if (!chartSVG) return;
    const url = URL.createObjectURL(svgBlob());
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      const canvas = el("canvas");
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) exportFile(blob, "png");
        else $("export-status").textContent = "PNG export failed; SVG remains available.";
      }, "image/png");
    } catch {
      $("export-status").textContent = "PNG export failed; SVG remains available.";
    } finally {
      URL.revokeObjectURL(url);
    }
  });
  $("export-data").addEventListener("click", () => {
    const active = currentRows();
    const output = {
      schema: 1,
      evidence_kind: data.evidence_kind,
      status: status(),
      metadata_origin: view.metadata_origin,
      chart_view: $("axis").value,
      comparison: view.definition,
      limitations: report.limitations,
      groups: view.groups
        .map((index) => {
          const group = report.groups[index],
            labels = active.filter((row) => row.groupIndex === index).map((row) => row.controller);
          return {
            ...group,
            controllers: group.controllers.filter((row) => labels.includes(row.controller)),
            trials: group.trials.filter((trial) => labels.includes(trial.controller)),
            paired: group.paired.filter(
              (pair) => labels.includes(pair.a) && labels.includes(pair.b),
            ),
          };
        })
        .filter((group) => group.controllers.length),
      comparison_jobs: view.jobs.map((index) => report.jobs[index]),
      all_supplied_jobs: report.jobs,
      all_supplied_jobs_throughput: report.throughput,
    };
    exportFile(new Blob([json(output)], { type: "application/json" }), "json");
  });
  let closedForPrint = [];
  window.addEventListener("beforeprint", () => {
    closedForPrint = [$("trial-details"), $("tactical-details")].filter((node) => !node.open);
    closedForPrint.forEach((node) => {
      node.open = true;
    });
  });
  window.addEventListener("afterprint", () => {
    closedForPrint.forEach((node) => {
      node.open = false;
    });
    closedForPrint = [];
  });
  $("print").addEventListener("click", () => window.print());
  $("axis").addEventListener("change", renderChart);
  $("scenario").addEventListener("change", (event) => loadView(Number(event.target.value)));
  $("select-all").addEventListener("click", () => {
    selected = new Set(rows.map((row) => row.id));
    renderControllers();
    renderSelection();
  });
  const banner = $("dataset-banner");
  banner.textContent = synthetic
    ? "SYNTHETIC DEMO — All values are invented to demonstrate the report. These are not recorded game results."
    : "RECORDED EVIDENCE · Read status and sample size before comparing controllers. No composite score or overall ranking.";
  if (synthetic) {
    banner.classList.add("demo");
    document.title = "SYNTHETIC DEMO — WH3 Benchmark Field Report";
  }
  const throughput = report.throughput || {},
    interrupted = (report.jobs || []).filter((job) => job.recorded_status === "interrupted").length;
  const totals = [
    ["Scope", "All supplied jobs"],
    [
      "Valid / started battles",
      `${throughput.valid_trials ?? "?"} / ${throughput.started_trials ?? "?"}`,
    ],
    ["Launched jobs / interruptions", `${report.jobs?.length ?? 0} / ${interrupted}`],
    ["Job wall time · includes setup", `${fmt(throughput.job_wall_s, 2)} s`],
    ["Valid battles / wall hour", fmt(throughput.valid_trials_per_wall_hour, 2)],
  ];
  $("totals").append(
    ...totals.map(([label, value]) => {
      const node = el("div", undefined, "total-label");
      node.append(el("strong", value), el("span", label));
      return node;
    }),
  );
  data.comparisons.forEach((comparison, index) => {
    const d = comparison.definition,
      s = d.scenario || {};
    const option = el(
      "option",
      `${s.name || "Unlabelled"} · AI ×${s.expect?.ai_stats_modifier || "?"} · ${d.source ? `source ${String(d.source).slice(0, 7)}` : "catalogue"}${comparison.groups.length ? "" : " · Not measured yet"}`,
    );
    option.value = String(index);
    $("scenario").append(option);
  });
  if (data.comparisons.length) loadView(0);
  else {
    $("status").textContent = "Not measured yet";
    for (const id of ["scenario", "axis", "select-all", "export-data", "export-svg", "export-png"])
      $(id).disabled = true;
  }
})();
