// The coordination suite's page, on top of the replay viewer. Runs between replay.js and
// report.js in the one script. It reads data.suite and draws: who won, the selected battle's
// coordination problem, what each method's groups did and when, and the replay.
function suitePage(data, api) {
  const $ = (id) => document.getElementById(id);
  const suite = data.suite,
    page = suite.page;
  // Hues for one army's groups. Orange stays the enemy's; blue, green and violet are told apart
  // by people with the common colour-vision differences, and names always sit beside them.
  const GROUP_HUES = ["#3a8fd9", "#1f9e74", "#9a68d6"];
  const order = page.order.filter((arm) => suite.arms[arm]);
  const rows = data.benchmark_plans.flatMap((plan) => plan.rows);
  const keyOf = new Map(rows.map((row) => [row.output, row.battle_key]));
  const nameOf = (arm) => page.methods[arm]?.[0] || arm;
  let picture = null,
    picked = null;

  // The viewer and its run line name the method, not the model every method shares.
  for (const row of rows) {
    const battle = data.battles[row.battle_key];
    if (battle)
      battle.commander = {
        ...battle.commander,
        name: nameOf(row.arm),
        detail: page.methods[row.arm]?.[1] || "",
        short: "",
      };
  }

  const pictures = Object.keys(suite.pictures).sort(
    (a, b) => suite.scenarios.indexOf(a) - suite.scenarios.indexOf(b),
  );
  const hueOf = (name) =>
    GROUP_HUES[picture.groups.findIndex((group) => group.name === name)] || GROUP_HUES[0];
  const battleOf = (name, arm) =>
    suite.pictures[name].battles.find((battle) => battle.arm === arm) || null;
  const planned = (name, arm) =>
    rows.some((row) => row.scenario === name && row.arm === arm);
  const lostText = (battle) => `Lost, broke ${Math.round(battle.taken)}% of enemy`;

  function renderGrid() {
    const table = el("table", null, "suite-grid"),
      head = el("tr"),
      body = el("tbody");
    head.append(el("th", "Battle"));
    for (const arm of order) {
      const cell = el("th");
      cell.append(el("b", nameOf(arm)), el("small", page.methods[arm][1]));
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
          cell.append(
            button(
              won ? `Won in ${clock(battle.battle_s * 1000)}` : lostText(battle),
              () => choose(name, arm, true),
              "suite-cell",
            ),
          );
        } else {
          const none = el("span", "\u2013", "suite-none");
          none.title = planned(name, arm) ? "Planned, cut off before it played" : "Not planned";
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
    cost.append(el("th", "Cost a battle"));
    for (const arm of order) {
      const row = suite.arms[arm];
      wins.append(el("td", `${row.wins} of ${row.completed}`));
      cost.append(el("td", money((row.usd || 0) + (row.authoring_usd || 0))));
    }
    foot.append(wins, cost);
    table.append(thead, body, foot);
    $("suite-grid").replaceChildren(table);
  }

  // The battle at its start: every group named, with the links it depends on.
  function diagram() {
    const W = 560,
      H = 330,
      margin = 58,
      units = [...picture.start.friendly, ...picture.start.enemy];
    const xs = units.map((u) => u.x),
      zs = units.map((u) => u.z);
    const midX = (Math.min(...xs) + Math.max(...xs)) / 2,
      midZ = (Math.min(...zs) + Math.max(...zs)) / 2;
    const scale = Math.min(
      (W - 2 * margin) / Math.max(120, Math.max(...xs) - Math.min(...xs)),
      (H - 2 * margin) / Math.max(120, Math.max(...zs) - Math.min(...zs)),
    );
    const X = (x) => W / 2 + (x - midX) * scale,
      Y = (z) => H / 2 - (z - midZ) * scale;
    const map = svg("svg", {
      viewBox: `0 0 ${W} ${H}`,
      class: "suite-map",
      role: "img",
      "aria-label": `${picture.title} at the start: ${picture.why}`,
    });
    const centre = (side, name) => {
      const own = picture.start[side].filter((u) => u.group === name);
      return {
        x: own.reduce((sum, u) => sum + X(u.x), 0) / own.length,
        y: own.reduce((sum, u) => sum + Y(u.z), 0) / own.length,
        own,
      };
    };
    for (const [from, to] of picture.links) {
      const a = centre("friendly", from),
        b = centre("friendly", to);
      map.append(
        svg("line", {
          x1: a.x,
          y1: a.y,
          x2: b.x,
          y2: b.y,
          class: "suite-link-line",
          stroke: hueOf(from),
        }),
      );
    }
    for (const group of picture.enemy) {
      const { x, y, own } = centre("enemy", group.name);
      for (const u of own)
        map.append(
          svg("path", {
            d: `M${X(u.x)} ${Y(u.z) - 6}l6 6-6 6-6-6z`,
            fill: TEAM.enemy,
          }),
        );
      const low = Math.max(...own.map((u) => Y(u.z)));
      map.append(svg("text", { x, y: low + 26, class: "suite-enemy-tag" }, group.name));
    }
    const seats = picture.groups.map((group) => centre("friendly", group.name));
    picture.groups.forEach((group, index) => {
      const { x, y, own } = seats[index],
        hue = hueOf(group.name);
      map.append(outline(own.map((u) => ({ x: X(u.x), y: Y(u.z) })), hue, 26));
      for (const u of own)
        map.append(svg("circle", { cx: X(u.x), cy: Y(u.z), r: 5.5, fill: hue }));
      // Above the group, or beside it when another group stands too close for that.
      const crowded = seats.some(
        (seat, other) => other !== index && Math.hypot(seat.x - x, seat.y - y) < 130,
      );
      const left = index % 2 === 1,
        edge = own.map((u) => X(u.x));
      const tag = crowded
        ? {
            x: left ? Math.min(...edge) - 20 : Math.max(...edge) + 20,
            y: y + 4,
            "text-anchor": left ? "end" : "start",
          }
        : { x, y: Math.min(...own.map((u) => Y(u.z))) - 18 };
      map.append(svg("text", { ...tag, class: "suite-group-tag", fill: hue }, group.name));
    });
    return map;
  }

  function jobs() {
    const list = el("ul", null, "suite-jobs");
    for (const group of picture.groups) {
      const item = el("li");
      const name = el("b", group.name);
      name.style.color = hueOf(group.name);
      item.append(name, el("span", group.job));
      list.append(item);
    }
    return list;
  }

  const percent = (s, end) => `${Math.min(100, (100 * s) / end).toFixed(2)}%`;

  function timeline() {
    const played = order.filter((arm) => battleOf(picture.name, arm));
    const end = Math.max(...played.map((arm) => battleOf(picture.name, arm).battle_s));
    const box = el("div", null, "suite-lanes");
    const axis = el("div", null, "suite-axis");
    const step = end > 480 ? 180 : 60;
    for (let s = step; s < end; s += step) {
      const tick = el("span", clock(s * 1000));
      tick.style.left = percent(s, end);
      axis.append(tick);
    }
    box.append(el("h3", "What happened"));
    if (page.current && picture.seen) box.append(el("p", picture.seen, "suite-seen"));
    const key = el("p", null, "suite-key");
    for (const group of picture.groups) {
      const mark = el("span", group.name, "suite-swatch");
      mark.style.setProperty("--hue", hueOf(group.name));
      key.append(mark);
    }
    key.append(
      el(
        "span",
        "Thick bar: in melee. Thin line: not in melee, including shooting. Nothing: all routed or dead, for now. Click a method to watch its battle below; the black tick is the replay's position.",
      ),
    );
    box.append(key);
    for (const arm of order) {
      const battle = battleOf(picture.name, arm);
      if (!battle) continue;
      const row = el("button", null, "suite-row");
      row.type = "button";
      row.dataset.arm = arm;
      row.addEventListener("click", () => pick(arm, true));
      const label = el("span", null, "suite-row-name");
      label.append(
        el("b", nameOf(arm)),
        el(
          "small",
          battle.outcome === "won" ? `Won in ${clock(battle.battle_s * 1000)}` : lostText(battle),
        ),
        el("em", battle.answer),
      );
      const bars = el("span", null, "suite-bars");
      for (const group of picture.groups) {
        const lane = el("span", null, "suite-lane");
        lane.style.setProperty("--hue", hueOf(group.name));
        for (const [from, to, state] of battle.lanes[group.name] || []) {
          const part = el("i", null, state === "fight" ? "fight" : "ready");
          part.style.left = percent(from, end);
          part.style.width = percent(Math.max(to - from, 1), end);
          lane.append(part);
        }
        bars.append(lane);
      }
      const edge = el("span", null, battle.outcome === "won" ? "suite-end won" : "suite-end");
      edge.style.left = percent(battle.battle_s, end);
      const head = el("span", null, "suite-playhead");
      head.hidden = true;
      bars.append(edge, head);
      row.append(label, bars);
      box.append(row);
    }
    const ruler = el("div", null, "suite-ruler");
    ruler.append(el("span"), axis);
    box.append(ruler);
    return box;
  }

  // The convex hull of map points (Andrew's monotone chain), for a group's outline.
  function hull(points) {
    const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
    if (sorted.length < 3) return sorted;
    const turn = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
    const half = (list) => {
      const chain = [];
      for (const p of list) {
        while (chain.length > 1 && turn(chain.at(-2), chain.at(-1), p) <= 0) chain.pop();
        chain.push(p);
      }
      chain.pop();
      return chain;
    };
    return [...half(sorted), ...half([...sorted].reverse())];
  }

  // A soft shape around a group's points, hugging them so one straggler stretches the shape,
  // not the whole map.
  function outline(points, hue, width) {
    const edge = hull(points);
    if (edge.length < 2)
      return svg("circle", {
        cx: edge[0].x,
        cy: edge[0].y,
        r: width / 2,
        fill: hue,
        "fill-opacity": 0.16,
      });
    return svg("path", {
      d: `M${edge.map((p) => `${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join("L")}Z`,
      fill: hue,
      "fill-opacity": 0.16,
      stroke: hue,
      "stroke-opacity": 0.16,
      "stroke-width": width,
      "stroke-linejoin": "round",
    });
  }

  // On the replay, only the shapes and names: the links belong to the start map.
  function overlay(layer, frame, proj) {
    if (!picture || !picked) return;
    const battle = battleOf(picture.name, picked);
    if (!battle) return;
    const seats = new Map();
    for (const group of picture.groups) {
      const units = frame.friendly.filter(
        (u) =>
          battle.groups[u.id] === group.name &&
          Number.isFinite(u.x) &&
          u.men > 0 &&
          !(u.state || []).some((state) => state === "routing" || state === "shattered"),
      );
      if (!units.length) continue;
      const points = units.map((u) => ({ x: proj.x(u.x), y: proj.y(u.z) }));
      seats.set(group.name, {
        points,
        x: points.reduce((sum, p) => sum + p.x, 0) / points.length,
        y: points.reduce((sum, p) => sum + p.y, 0) / points.length,
        top: Math.min(...points.map((p) => p.y)),
      });
    }
    for (const [name, seat] of seats) layer.append(outline(seat.points, hueOf(name), 46 * proj.k));
    return () => {
      for (const [name, seat] of seats)
        layer.append(
          svg(
            "text",
            {
              x: seat.x,
              y: seat.top - 25 * proj.k - 12,
              class: "suite-group-tag",
              fill: hueOf(name),
            },
            name,
          ),
        );
    };
  }

  function pick(arm, scroll) {
    picked = arm;
    for (const row of document.querySelectorAll(".suite-row"))
      row.classList.toggle("current", row.dataset.arm === arm);
    for (const cell of document.querySelectorAll(".suite-playhead"))
      cell.hidden = cell.closest(".suite-row").dataset.arm !== arm;
    const battle = battleOf(picture.name, arm);
    return api.open(keyOf.get(battle.output), scroll);
  }

  function choose(name, arm = null, scroll = false) {
    picture = { name, ...suite.pictures[name], terrain: api.terrainOf(keyOf.get(suite.pictures[name].battles[0].output)) };
    for (const line of document.querySelectorAll(".suite-grid tbody tr"))
      line.classList.toggle("current", line.dataset.scenario === name);
    $("suite-title").textContent = picture.title;
    $("suite-question").textContent = picture.question;
    $("suite-why").textContent = picture.why;
    $("suite-link-note").textContent = picture.link ? `Dashed line: ${picture.link}.` : "";
    $("suite-map").replaceChildren(diagram());
    $("suite-jobs").replaceChildren(jobs());
    $("suite-timeline").replaceChildren(timeline());
    return pick(arm || order.find((item) => battleOf(name, item)), scroll);
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
    if (page.current) {
      const list = el("ul", null, "suite-readings");
      for (const line of readings.lines) list.append(el("li", line));
      $("suite-reading").replaceChildren(list);
      $("suite-reading").append(
        el(
          "p",
          "Broke means the share of the enemy dead or routed at the end. A battle ends when one army has gone; none reached the timer. A dash means not played: Three models and Model over scripts were cut off on Rear raid, the battle nobody has won, and Scripts only was never planned for two. One battle per pair, and difficulty was tuned the same night on these methods' earlier battles, so these are leads and rank nothing.",
          "suite-caveat",
        ),
        el(
          "p",
          "Groups on the maps are parts of the army, not players. One model commands them all; three models split by unit type, so a group can answer to more than one model.",
          "suite-caveat",
        ),
      );
    }
    renderGrid();
    Viewer.setOverlay(overlay);
    Viewer.onTime((time) => {
      if (!picked) return;
      const battle = battleOf(picture.name, picked),
        end = Math.max(
          ...order
            .map((arm) => battleOf(picture.name, arm))
            .filter(Boolean)
            .map((item) => item.battle_s),
        );
      const head = document.querySelector(".suite-row.current .suite-playhead");
      if (head && battle) head.style.left = percent(time / 1000, end);
    });
    document.title = `${page.title} WH3 coordination suite`;
    return choose(pictures[0]);
  }

  return { start };
}
