// The coordination suite's page, on top of the replay viewer. Runs between replay.js and
// report.js in the one script. It reads data.suite and draws: who controls what in each method,
// who won, every method overlapped on one map and one clock, and one method's full replay.
function suitePage(data, api) {
  const $ = (id) => document.getElementById(id);
  const suite = data.suite,
    page = suite.page;
  // One colour system for the whole page: colour is the controller. Orange stays the enemy's.
  const HUES = {
    all: "#ee8fc4",
    front: "#4aa3e8",
    ranged: "#6cc04a",
    mobile: "#ae83ee",
    scripts: "#95a3ab",
  };
  const SPEED = 12; // battle seconds per second of playback
  const MARGIN_M = 40;
  const BIG_R = 7,
    SMALL_R = 19; // marker radii in map units: the small maps show at a quarter of the size
  const order = page.order.filter((arm) => suite.arms[arm]);
  const rows = data.benchmark_plans.flatMap((plan) => plan.rows);
  const keyOf = new Map(rows.map((row) => [row.output, row.battle_key]));
  const method = (arm) => page.methods[arm];
  const pictures = suite.scenarios;
  const battleOf = (name, arm) =>
    suite.pictures[name].battles.find((battle) => battle.arm === arm) || null;
  let scene = null, // the selected battle's decoded recordings, by method
    current = null,
    pair = [], // the methods on the overlap: [solid, outlined]
    time = 0,
    end = 1,
    playing = false,
    last = null,
    moved = false, // whether the reader has played or dragged the clock on this battle
    project = null;

  // The viewer and its run line name the method, not the model every method shares.
  for (const row of rows) {
    const battle = data.battles[row.battle_key];
    if (battle)
      battle.commander = {
        ...battle.commander,
        name: method(row.arm)?.name || row.arm,
        detail: method(row.arm)?.note || "",
        short: "",
      };
  }

  // Who holds a unit in one method: one colour, three colours, or grey for scripts alone.
  const memberHue = (m, member) =>
    !m.models.length ? HUES.scripts : m.models.includes("all") ? HUES.all : HUES[member];
  const memberName = (m, member) =>
    !m.models.length
      ? "Scripts"
      : m.models.includes("all")
        ? m.scripts
          ? "One model, through scripts"
          : "One model"
        : `${page.controllers[member]} ${m.rules ? "rules" : "model"}`;
  const KINDS = { front: "infantry", ranged: "guns", mobile: "knights" };
  const kindOf = (glyph) =>
    /missile|artillery/.test(glyph || "")
      ? "guns"
      : /cavalry|monster/.test(glyph || "")
        ? "knights"
        : "infantry";

  // Infantry is a circle, guns a triangle, knights a square, the enemy a diamond, on every map.
  function shape(kind, x, y, r, attrs) {
    if (kind === "guns")
      return svg("path", { d: `M${x} ${y - 1.15 * r}l${1.1 * r} ${2 * r}h${-2.2 * r}z`, ...attrs });
    if (kind === "knights")
      return svg("rect", { x: x - r, y: y - r, width: 2 * r, height: 2 * r, ...attrs });
    if (kind === "enemy")
      return svg("path", { d: `M${x} ${y - r}l${r} ${r}-${r} ${r}-${r}-${r}z`, ...attrs });
    return svg("circle", { cx: x, cy: y, r, ...attrs });
  }
  const swatch = (kind, hue, solid = true) => {
    const icon = svg("svg", { viewBox: "0 0 20 20", class: "suite-swatch" });
    icon.append(
      shape(kind, 10, 10, 7, {
        fill: solid ? hue : "none",
        stroke: hue,
        "stroke-width": solid ? 0 : 2.5,
      }),
    );
    return icon;
  };
  const tag = (kind, hue, text, solid = true) => {
    const item = el("span");
    item.append(swatch(kind, hue, solid), text);
    return item;
  };

  // Who controls what: the model or models above, the army's units below.
  function picture(arm) {
    const m = method(arm),
      W = 150,
      H = 58,
      units = { front: [18, 34, 50], ranged: [78, 94], mobile: [132] };
    const map = svg("svg", {
      viewBox: `0 0 ${W} ${H}`,
      class: "suite-who",
      role: "img",
      "aria-label": `${m.name}: ${m.note}`,
    });
    const whole = m.models.includes("all");
    const headX = (member) => (whole ? W / 2 : { front: 34, ranged: 86, mobile: 132 }[member]);
    if (m.scripts)
      map.append(
        svg("rect", { x: 10, y: 28, width: W - 20, height: 6, rx: 3, fill: HUES.scripts }),
      );
    for (const [member, xs] of Object.entries(units))
      for (const x of xs) {
        if (m.models.length && !m.scripts)
          map.append(
            svg("line", {
              x1: headX(member),
              y1: 14,
              x2: x,
              y2: 46,
              stroke: memberHue(m, member),
              "stroke-width": 1.5,
              "stroke-dasharray": m.rules ? "3 3" : null,
            }),
          );
        map.append(shape(KINDS[member], x, 49, 5, { fill: memberHue(m, member) }));
      }
    if (m.scripts && m.models.length)
      map.append(
        svg("line", { x1: W / 2, y1: 14, x2: W / 2, y2: 30, stroke: HUES.all, "stroke-width": 2 }),
      );
    for (const member of whole ? ["front"] : m.models)
      map.append(
        m.rules
          ? svg("rect", {
              x: headX(member) - 7,
              y: 3,
              width: 14,
              height: 14,
              rx: 2,
              fill: memberHue(m, member),
            })
          : svg("circle", { cx: headX(member), cy: 10, r: 8, fill: memberHue(m, member) }),
      );
    return map;
  }

  function renderGrid() {
    const table = el("table", null, "suite-grid"),
      head = el("tr"),
      body = el("tbody");
    head.append(el("th"));
    for (const arm of order) {
      const cell = el("th");
      const swatch = el("b", method(arm).name);
      cell.append(swatch, picture(arm), el("small", method(arm).note));
      head.append(cell);
    }
    const thead = el("thead");
    thead.append(head);
    for (const name of pictures) {
      const line = el("tr");
      line.dataset.scenario = name;
      const title = el("th");
      title.scope = "row";
      title.append(button(suite.pictures[name].title, () => choose(name), "suite-link"));
      line.append(title);
      for (const arm of order) {
        const battle = battleOf(name, arm),
          cell = el("td");
        if (battle) {
          const won = battle.outcome === "won";
          cell.className = won ? "won" : "lost";
          const mark = button(won ? "Won" : "Lost", () => choose(name), "suite-cell");
          mark.title = `${clock(battle.battle_s * 1000)}, broke ${Math.round(battle.taken)}% of the enemy`;
          cell.append(mark);
        } else {
          const none = el("span", "–", "suite-none");
          none.title = rows.some((row) => row.scenario === name && row.arm === arm)
            ? "Cut off before it played"
            : "Not planned";
          cell.append(none);
        }
        line.append(cell);
      }
      body.append(line);
    }
    const foot = el("tfoot"),
      wins = el("tr"),
      cost = el("tr");
    wins.append(el("th", "Won"));
    cost.append(el("th", "A battle costs"));
    for (const arm of order) {
      const row = suite.arms[arm];
      wins.append(el("td", `${row.wins} of ${row.completed}`));
      cost.append(el("td", money((row.usd || 0) + (row.authoring_usd || 0))));
    }
    foot.append(wins, cost);
    table.append(thead, body, foot);
    $("suite-grid").replaceChildren(table);
  }

  const able = (u) =>
    u.men > 0 && !(u.state || []).some((s) => s === "routing" || s === "shattered");
  const placed = (u) => Number.isFinite(u.x) && Number.isFinite(u.z);
  const frameAt = (run, t) => {
    let low = 0,
      high = run.frames.length - 1;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      if (run.frames[mid].time_ms / 1000 <= t) low = mid;
      else high = mid - 1;
    }
    return run.frames[low];
  };

  async function load(name) {
    const runs = await Promise.all(
      suite.pictures[name].battles.map(async (battle) => {
        const payload = await api.decode(keyOf.get(battle.output));
        const frames = payload.frames.filter((frame) => frame.friendly.length);
        const kinds = new Map(payload.roster.map((entry) => [entry.id, kindOf(entry.glyph)]));
        // Each unit's own path: an average over a kind would put a split army where nobody stood.
        const paths = new Map(frames[0].friendly.map((u) => [u.id, []]));
        frames.forEach((frame, index) => {
          if (index % 4) return;
          for (const u of frame.friendly)
            if (able(u) && placed(u))
              paths.get(u.id)?.push({ t: frame.time_ms / 1000, x: u.x, z: u.z });
        });
        const hue = (id) => memberHue(method(battle.arm), battle.owners[id]);
        return { battle, frames, kinds, paths, hue, terrain: payload.terrain };
      }),
    );
    return Object.fromEntries(runs.map((run) => [run.battle.arm, run]));
  }

  // One frame for every map of a battle: where units stood while still fighting, so a rout's
  // run off the map does not shrink the fight.
  function frameMaps() {
    const points = Object.values(scene).flatMap((run) =>
      run.frames
        .flatMap((frame) => [...frame.friendly, ...frame.enemy])
        .filter(able)
        .filter(placed),
    );
    const xs = points.map((u) => u.x),
      zs = points.map((u) => u.z),
      spanX = Math.max(...xs) - Math.min(...xs) + 2 * MARGIN_M,
      spanZ = Math.max(...zs) - Math.min(...zs) + 2 * MARGIN_M,
      W = 1000,
      H = Math.min(480, Math.max(380, (W * spanZ) / spanX));
    const scale = Math.min(W / spanX, H / spanZ),
      midX = (Math.min(...xs) + Math.max(...xs)) / 2,
      midZ = (Math.min(...zs) + Math.max(...zs)) / 2;
    project = { W, H, x: (x) => W / 2 + (x - midX) * scale, y: (z) => H / 2 - (z - midZ) * scale };
    project.scale = scale;
    project.blocked = (Object.values(scene).find((run) => run.terrain) || {}).terrain;
  }

  function sheet(map) {
    map.setAttribute("viewBox", `0 0 ${project.W} ${project.H}`);
    map.replaceChildren();
    if (project.blocked)
      map.append(
        svg("path", {
          d: blockedPath(project.blocked, project.x, project.y, project.scale),
          class: "suite-blocked",
        }),
      );
    const layer = svg("g");
    map.append(layer);
    return layer;
  }

  function drawArmy(layer, run, r, solid) {
    const frame = frameAt(run, Math.min(time, run.battle.battle_s));
    for (const u of frame.enemy.filter((item) => placed(item) && item.men > 0))
      layer.append(
        shape("enemy", project.x(u.x), project.y(u.z), 0.8 * r, {
          fill: solid ? TEAM.enemy : "none",
          stroke: TEAM.enemy,
          "stroke-width": solid ? 0 : r / 4,
          opacity: able(u) ? 0.85 : 0.2,
        }),
      );
    for (const u of frame.friendly.filter((item) => placed(item) && item.men > 0))
      layer.append(
        shape(run.kinds.get(u.id), project.x(u.x), project.y(u.z), r, {
          fill: solid ? run.hue(u.id) : "#16232b",
          stroke: run.hue(u.id),
          "stroke-width": r / 3.5,
          opacity: able(u) ? 1 : 0.25,
        }),
      );
  }

  function drawPaths(layer, run, solid) {
    for (const [id, path] of run.paths) {
      const seen = path.filter((p) => p.t <= time);
      if (seen.length > 1)
        layer.append(
          svg("polyline", {
            points: seen
              .map((p) => `${project.x(p.x).toFixed(1)},${project.y(p.z).toFixed(1)}`)
              .join(" "),
            fill: "none",
            stroke: run.hue(id),
            "stroke-width": 1.6,
            "stroke-dasharray": solid ? null : "6 5",
            opacity: 0.6,
          }),
        );
    }
  }

  function draw() {
    for (const tile of document.querySelectorAll(".suite-tile")) {
      const run = scene[tile.dataset.arm],
        frame = frameAt(run, Math.min(time, run.battle.battle_s));
      const left = frame.friendly.filter(able).reduce((sum, u) => sum + u.men, 0),
        all = frame.friendly.reduce((sum, u) => sum + (u.men0 || 0), 0);
      const over = time >= run.battle.battle_s;
      tile.querySelector(".suite-bar i").style.width = `${all ? (100 * left) / all : 0}%`;
      tile.querySelector("em").textContent = over
        ? `${run.battle.outcome === "won" ? "Won" : "Lost"} ${clock(run.battle.battle_s * 1000)}`
        : "";
      tile.classList.toggle("won", over && run.battle.outcome === "won");
      const layer = tile.layer;
      layer.replaceChildren();
      drawArmy(layer, run, SMALL_R, true);
    }
    const big = $("suite-big").layer;
    big.replaceChildren();
    for (const [index, arm] of [...pair].reverse().entries()) {
      const solid = index === pair.length - 1;
      drawPaths(big, scene[arm], solid);
      drawArmy(big, scene[arm], BIG_R, solid);
    }
    $("suite-clock").textContent = clock(time * 1000);
    $("suite-time").value = time;
  }

  function tick(now) {
    if (!playing) return;
    if (last != null) time = Math.min(end, time + ((now - last) / 1000) * SPEED);
    last = now;
    draw();
    if (time >= end) return setPlaying(false);
    requestAnimationFrame(tick);
  }

  function setPlaying(on) {
    playing = on;
    last = null;
    $("suite-play").textContent = on ? "Pause" : "Play";
    if (on) {
      if (time >= end || !moved) time = 0;
      moved = true;
      requestAnimationFrame(tick);
    }
  }

  function showPair() {
    const box = $("suite-pair");
    box.replaceChildren();
    const [solid, outlined] = pair;
    box.append(tag("front", "#dfe7ea", method(solid).name));
    if (outlined) box.append(tag("front", "#dfe7ea", method(outlined).name, false));
    box.append(el("small", "on one map. Click the maps above to change which two."));
    for (const tile of document.querySelectorAll(".suite-tile"))
      tile
        .querySelector(".suite-pick")
        .setAttribute("aria-pressed", String(pair.includes(tile.dataset.arm)));
  }

  function togglePair(arm) {
    if (pair.includes(arm)) {
      if (pair.length > 1) pair = pair.filter((item) => item !== arm);
    } else pair = [...pair, arm].slice(-2);
    showPair();
    draw();
  }

  function renderTiles() {
    const box = $("suite-tiles");
    box.replaceChildren();
    for (const arm of order) {
      if (!scene[arm]) continue;
      const tile = el("div", null, "suite-tile");
      tile.dataset.arm = arm;
      const pick = el("button", null, "suite-pick");
      pick.type = "button";
      const map = svg("svg", { class: "suite-small", role: "img" });
      map.setAttribute("aria-label", `${method(arm).name}, at the same moment of battle`);
      tile.layer = sheet(map);
      const bar = el("span", null, "suite-bar");
      bar.append(el("i"));
      pick.append(el("b", method(arm).name), el("em"), bar, map);
      pick.addEventListener("click", () => togglePair(arm));
      tile.append(
        pick,
        button("Watch", () => watch(arm), "suite-watch"),
      );
      box.append(tile);
    }
  }

  // One method's own replay, with its units coloured by the model that controlled them.
  function watch(arm) {
    const battle = scene[arm].battle,
      m = method(arm);
    setPlaying(false);
    document.body.classList.add("suite-watching");
    Viewer.setUnitHue((id) => memberHue(m, battle.owners[id]));
    const legend = $("suite-legend");
    legend.hidden = false;
    legend.replaceChildren(el("b", m.name));
    for (const member of m.models.includes("all") || !m.models.length ? ["front"] : m.models)
      legend.append(
        tag(
          m.models.includes("all") || !m.models.length ? "front" : KINDS[member],
          memberHue(m, member),
          memberName(m, member),
        ),
      );
    legend.append(button("Close", closeWatch, "suite-close"));
    return api.open(keyOf.get(battle.output), false).then(() => legend.scrollIntoView());
  }
  function closeWatch() {
    document.body.classList.remove("suite-watching");
    $("suite-legend").hidden = true;
  }

  async function choose(name) {
    setPlaying(false);
    closeWatch();
    current = name;
    const item = suite.pictures[name];
    for (const line of document.querySelectorAll(".suite-grid tbody tr"))
      line.classList.toggle("current", line.dataset.scenario === name);
    $("suite-question").textContent = item.question;
    $("suite-why").textContent = item.why;
    $("suite-seen").textContent = page.current ? item.seen : "";
    const plan = $("suite-plan");
    plan.replaceChildren(el("b", "The plan (no method sees it):"));
    for (const part of item.plan) {
      const entry = el("span");
      for (const who of part.who) entry.append(swatch(KINDS[who], HUES[who]));
      entry.append(`${part.who.map((who) => page.controllers[who]).join(", ")}: ${part.job}`);
      plan.append(entry);
    }
    scene = await load(name);
    if (current !== name) return;
    const lengths = Object.values(scene).map((run) => run.battle.battle_s);
    end = Math.max(...lengths);
    // Open where the battles have already diverged: the moment the first one ended.
    time = Math.min(...lengths);
    moved = false;
    $("suite-time").max = end;
    // Start on the two most different results; any two can be picked.
    const ranked = Object.values(scene).sort((a, b) => b.battle.taken - a.battle.taken);
    pair = [ranked[0], ranked.at(-1)]
      .map((run) => run.battle.arm)
      .filter((arm, index, all) => all.indexOf(arm) === index);
    frameMaps();
    renderTiles();
    const big = $("suite-big");
    big.layer = sheet(big);
    showPair();
    draw();
  }

  function start() {
    document.body.classList.add("is-suite");
    $("page-title").textContent = page.title;
    $("page-dek").textContent = page.dek;
    $("suite-page").hidden = false;
    $("suite-more").hidden = false;
    $("suite-more-body").append($("benchmark-results"));
    const readings = page.readings;
    page.current = readings && readings.plans.join() === page.plans.join();
    if (page.current)
      $("suite-reading").replaceChildren(...readings.lines.map((line) => el("p", line)));
    renderGrid();
    $("suite-key").append(
      tag("front", HUES.all, "One model, whole army"),
      tag("front", HUES.front, "Infantry model or rules"),
      tag("guns", HUES.ranged, "Guns model or rules"),
      tag("knights", HUES.mobile, "Knights model or rules"),
      tag("front", HUES.scripts, "Scripts"),
      tag("enemy", TEAM.enemy, "Enemy"),
      "Bar: men still fighting",
    );
    $("suite-play").addEventListener("click", () => setPlaying(!playing));
    $("suite-time").addEventListener("input", (event) => {
      setPlaying(false);
      moved = true;
      time = Number(event.target.value);
      draw();
    });
    document.title = `${page.title} WH3 coordination suite`;
    return choose(pictures[0]);
  }

  return { start };
}
