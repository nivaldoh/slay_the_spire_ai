"""The suite page's script (suite.js), run by Node on a small embedded payload with a minimal
stand-in for the browser's DOM: battles of every suite arm get a tile, a name and owner tags, and
a scenario with no finished battle neither crashes the page nor opens. The real page, its styles
and the replay viewer are not exercised (check_wh3_suite_browser.cjs drives a browser)."""
import json
import shutil
import subprocess

from twwarhammer3.battle import report_html, suite

NOTES = json.loads(report_html.NOTES_PATH.read_text())
SPLIT = {"team", "gap"}  # the arms that record a partition (suite.owners)
RUN = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const [replayPath, suitePath, payloadPath] = process.argv.slice(2);
const { data, replays } = JSON.parse(fs.readFileSync(payloadPath, "utf8"));

// Just the DOM the suite page touches: elements, text, classes, attributes and simple selectors
// (tag, .class and [attribute], joined by descendant spaces).
class Text {
  constructor(text) {
    this.textContent = String(text);
    this.parentNode = null;
  }
}
class Element {
  constructor(tag) {
    Object.assign(this, { tagName: tag.toUpperCase(), childNodes: [], parentNode: null });
    Object.assign(this, { attributes: {}, dataset: {}, listeners: {}, className: "" });
    this.style = { setProperty() {} };
  }
  get children() {
    return this.childNodes.filter((node) => node instanceof Element);
  }
  get classList() {
    const names = () => this.className.split(/\s+/).filter(Boolean);
    return {
      add: (name) => (this.className = [...names(), name].join(" ")),
      remove: (name) => (this.className = names().filter((n) => n !== name).join(" ")),
      toggle: (name, on = !names().includes(name)) => {
        this.className = [...names().filter((n) => n !== name), ...(on ? [name] : [])].join(" ");
        return on;
      },
      contains: (name) => names().includes(name),
    };
  }
  append(...items) {
    for (const item of items) {
      const node = item instanceof Element || item instanceof Text ? item : new Text(item);
      const old = node.parentNode?.childNodes;
      if (old) old.splice(old.indexOf(node), 1);
      node.parentNode = this;
      this.childNodes.push(node);
    }
  }
  replaceChildren(...items) {
    this.childNodes = [];
    this.append(...items);
  }
  get textContent() {
    return this.childNodes.map((node) => node.textContent).join("");
  }
  set textContent(value) {
    this.replaceChildren(String(value));
  }
  setAttribute(key, value) {
    this.attributes[key] = String(value);
  }
  getAttribute(key) {
    return this.attributes[key] ?? null;
  }
  toggleAttribute(key, on = !(key in this.attributes)) {
    if (on) this.attributes[key] = "";
    else delete this.attributes[key];
    return on;
  }
  addEventListener(type, action) {
    (this.listeners[type] ||= []).push(action);
  }
  fire(type) {
    for (const action of this.listeners[type] || []) action({ target: this });
  }
  get ownerSVGElement() {
    let node = this.parentNode;
    while (node && node.tagName !== "SVG") node = node.parentNode;
    return node;
  }
  getBoundingClientRect() {
    return { width: 0 }; // no layout: owner tags are not placed
  }
  scrollIntoView() {}
  matches(simple) {
    const classes = (this.className || this.attributes.class || "").split(/\s+/);
    return [...simple.matchAll(/([.[]?)([\w-]+)\]?/g)].every(([, kind, name]) => {
      if (kind === ".") return classes.includes(name);
      if (kind !== "[") return this.tagName === name.toUpperCase();
      const key = name.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase()); // data-a-b: aB
      return name in this.attributes || (name.startsWith("data-") && key in this.dataset);
    });
  }
  querySelectorAll(selector) {
    const parts = selector.trim().split(/\s+/),
      found = [];
    const chain = (node) => {
      let index = parts.length - 2;
      for (let up = node.parentNode; index >= 0 && up; up = up.parentNode)
        if (up.matches(parts[index])) index--;
      return index < 0;
    };
    const walk = (node) => {
      for (const child of node.children) {
        if (child.matches(parts.at(-1)) && chain(child)) found.push(child);
        walk(child);
      }
    };
    walk(this);
    return found;
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

const root = new Element("html"),
  body = new Element("body");
root.append(body);
const document = {
  body,
  title: "",
  createElement: (tag) => new Element(tag),
  createElementNS: (_, tag) => new Element(tag),
  createTextNode: (text) => new Text(text),
  getElementById: (id) => root.querySelectorAll("*").find((node) => node.id === id) || null,
  querySelectorAll: (selector) => root.querySelectorAll(selector),
};
const tags = { "suite-big": "svg", "suite-time": "input", "suite-play": "button" };
for (const id of ["page-title", "page-dek", "suite-page", "suite-grid", "suite-reading",
  "suite-question", "suite-why", "suite-seen", "suite-plan", "suite-tiles", "suite-layout",
  "suite-pair", "suite-big", "suite-separated", "suite-play", "suite-clock", "suite-time",
  "suite-key", "suite-legend", "suite-more", "suite-more-body", "benchmark-results", "watch"]) {
  const node = new Element(tags[id] || "div");
  node.id = node.className = id; // report.html gives the suite's boxes their id as a class
  body.append(node);
}
for (const layout of ["overlay", "separate"]) {
  const node = new Element("button");
  node.dataset.layout = layout;
  document.getElementById("suite-layout").append(node);
}
Object.assign(globalThis, {
  document,
  window: globalThis,
  addEventListener() {},
  requestAnimationFrame: () => 0,
  Viewer: { setUnitHue() {} },
});

// The page's own helpers (el, svg, button, clock, money, TEAM, ...): replay.js before its viewer.
const replay = fs.readFileSync(replayPath, "utf8"),
  cut = replay.indexOf("const Viewer = (() => {");
if (cut < 0) throw new Error("replay.js: viewer marker not found");
vm.runInThisContext(`${replay.slice(0, cut)}\n${fs.readFileSync(suitePath, "utf8")}
globalThis.suitePage = suitePage;`);

const api = { decode: async (key) => replays[key] ?? null };
api.open = async (key) => api.paint(key);
const $ = (id) => document.getElementById(id);
const errors = [];
const attempt = async (action) => {
  try {
    await action();
  } catch (error) {
    errors.push(String(error));
  }
};
const legends = {};
(async () => {
  await attempt(() => suitePage(data, api).start());
  // What opening a battle from the attempts table does first, then moving the shared clock.
  for (const key of Object.keys(replays))
    await attempt(() => {
      api.paint(key);
      legends[key] = $("suite-legend").textContent;
    });
  $("suite-time").value = "3";
  await attempt(() => $("suite-time").fire("input"));
  const texts = (selector, from = document) =>
    from.querySelectorAll(selector).map((node) => node.textContent);
  const everything = (node) =>
    [node.textContent, ...Object.values(node.attributes), ...node.children.map(everything)]
      .join(" ");
  console.log(JSON.stringify({
    errors,
    busy: $("suite-page").getAttribute("aria-busy"),
    columns: texts(".suite-grid thead b"),
    rows: document.querySelectorAll(".suite-grid tbody tr").map((row) => ({
      scenario: row.dataset.scenario,
      current: row.classList.contains("current"),
      link: Boolean(row.querySelector(".suite-link")),
      cells: texts("td", row),
    })),
    question: $("suite-question").textContent,
    tiles: document.querySelectorAll(".suite-tile").map((tile) => tile.dataset.arm),
    tilesText: $("suite-tiles").textContent,
    pair: document.querySelectorAll(".suite-pair [data-arm]").map((item) => item.dataset.arm),
    owners: texts(".suite-owner b"),
    overlap: $("suite-big").querySelectorAll("[data-unit]").length,
    legends,
    page: everything(body),
  }));
})();
"""


def page(scenarios):
    """A suite payload: {scenario: [(arm, taken)]}, one short recording per battle."""
    rows, pictures, replays, arms = [], {}, {}, {}
    for name, battles in scenarios.items():
        picture = pictures[name] = {"title": name.title(), "question": f"{name}?", "why": "w",
                                    "seen": "s", "plan": [], "battles": []}
        for arm, taken in battles:
            output, end = f"{name}--{arm}", 100 + taken
            rows.append({"output": output, "battle_key": output, "scenario": name, "arm": arm})
            picture["battles"].append({
                "output": output, "arm": arm, "outcome": "lost", "battle_s": end, "taken": taken,
                "owners": {"u1": "front", "u2": "ranged"} if arm in SPLIT else {}})
            replays[output] = {"terrain": None, "roster": [
                {"id": "u1", "glyph": "infantry"}, {"id": "u2", "glyph": "missile_infantry"}],
                "frames": [{"time_ms": t * 1000, "enemy": [{"id": "e1", "x": 0, "z": 300 - t,
                                                             "men": 90}],
                            "friendly": [{"id": unit, "x": x + t, "z": 0, "men": 100, "men0": 120}
                                         for unit, x in (("u1", -50), ("u2", 50))]}
                           for t in (0, 30, end)]}
            arms.setdefault(arm, {"completed": 0, "wins": 0, "usd": 0, "authoring_usd": 0})
            arms[arm]["completed"] += 1
    data = {"battles": {}, "benchmark_plans": [{"rows": rows}],
            "suite": {"page": {**NOTES["suite"], "plans": ["test"]}, "arms": arms,
                      "scenarios": list(scenarios), "pictures": pictures}}
    return data, replays


def run(tmp_path, scenarios):
    node = shutil.which("node")
    assert node is not None, "Node.js is required to run the suite page's JavaScript"
    data, replays = page(scenarios)
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"data": data, "replays": replays}))
    result = subprocess.run([node, "-", str(report_html.ASSETS / "replay.js"),
                             str(report_html.ASSETS / "suite.js"), str(payload)],
                            input=RUN, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_every_suite_arm_has_a_page_method_and_scripted_arms_keep_their_replays():
    methods = NOTES["suite"]["methods"]
    assert set(methods) == set(suite.ARMS)
    # A diagnostic battle gets no replay on the page (report_html.display_data); the arms that
    # call no model are scripted comparisons, so the suite page can draw them.
    for arm, args in suite.ARMS.items():
        if "--provider" not in args:
            policy = args[args.index("--policy") + 1]
            assert report_html.commander({"policy": policy}, {})["kind"] == "scripted", arm


def test_battles_of_every_suite_arm_get_a_tile_a_name_and_owner_tags(tmp_path):
    # Distinct enemy shares: the overlap opens on the extremes, here rush and concentrate.
    taken = {arm: 50 + index for index, arm in enumerate(suite.ARMS)}
    taken.update(rush=5, concentrate=95)
    state = run(tmp_path, {"coord-two-fronts": list(taken.items())})
    methods = NOTES["suite"]["methods"]
    assert state["errors"] == [] and state["busy"] == "false"
    assert state["tiles"] == NOTES["suite"]["order"]
    assert state["columns"] == [methods[arm]["name"] for arm in NOTES["suite"]["order"]]
    assert sorted(state["pair"]) == ["concentrate", "rush"] and state["overlap"] > 0
    assert state["owners"] and "undefined" not in "".join(state["owners"])
    for arm in suite.ARMS:
        assert state["legends"][f"coord-two-fronts--{arm}"].startswith(
            f"Coord-Two-Fronts: {methods[arm]['name']}")
    assert "undefined" not in state["page"]


def test_a_scenario_with_no_finished_battle_does_not_open_and_says_so(tmp_path):
    state = run(tmp_path, {"coord-rear-raid": [], "coord-relief": [("single", 40), ("team", 10)]})
    assert state["errors"] == [] and state["busy"] == "false"
    empty, played = state["rows"]
    assert not empty["link"] and set(empty["cells"]) == {"–"} and not empty["current"]
    assert played["link"] and played["current"] and state["question"] == "coord-relief?"
    assert state["tiles"] == ["single", "team"]
    # Before any battle has finished, the page opens on the first scenario and says so.
    state = run(tmp_path, {"coord-rear-raid": [], "coord-relief": []})
    assert state["errors"] == [] and state["busy"] == "false"
    assert state["question"] == "coord-rear-raid?" and state["tiles"] == []
    assert "No battle has finished" in state["tilesText"] and state["overlap"] == 0


def run_payload(tmp_path, data, replays):
    """run() for a payload edited after page()."""
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"data": data, "replays": replays}))
    result = subprocess.run([shutil.which("node"), "-", str(report_html.ASSETS / "replay.js"),
                             str(report_html.ASSETS / "suite.js"), str(payload)],
                            input=RUN, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_a_scenario_without_page_notes_gets_a_row_that_opens(tmp_path):
    """Owner, 2026-11-13: "A row for every scenario (Recommended)". suite.scenario_pictures
    gives such a scenario its name, no question and no plan; the page must open it."""
    data, replays = page({"coord-siege": [("single", 40)]})
    data["suite"]["pictures"]["coord-siege"].update(title="coord-siege", question=None,
                                                    why=None, seen=None, plan=[])
    state = run_payload(tmp_path, data, replays)
    assert state["errors"] == [] and state["busy"] == "false"
    assert [row["scenario"] for row in state["rows"]] == ["coord-siege"]
    assert state["rows"][0]["link"] and state["rows"][0]["current"]
    assert state["question"] == "This scenario has no page notes."
    assert "designer" not in state["page"] and "undefined" not in state["page"]


def test_a_repeated_pair_shows_its_first_battle_in_the_tiles_and_the_overlap(tmp_path):
    """Owner, 2026-11-13: "First battle everywhere (Recommended)". Wrong version: the grid shows
    the first battle and the tiles and overlap the last, here single's repeat at 95%."""
    data, replays = page({"coord-relief": [("single", 40), ("team", 10), ("rush", 50)]})
    first = data["suite"]["pictures"]["coord-relief"]["battles"][0]
    repeat = {**first, "output": "coord-relief--single-2", "taken": 95, "outcome": "won"}
    data["suite"]["pictures"]["coord-relief"]["battles"].append(repeat)
    data["benchmark_plans"][0]["rows"].append({"output": repeat["output"], "arm": "single",
                                               "battle_key": repeat["output"],
                                               "scenario": "coord-relief"})
    replays[repeat["output"]] = replays[first["output"]]
    state = run_payload(tmp_path, data, replays)
    assert state["errors"] == [] and state["busy"] == "false"
    assert "Lost" in state["rows"][0]["cells"] and "Won" not in state["rows"][0]["cells"]
    assert sorted(state["pair"]) == ["rush", "team"] and sorted(state["tiles"]) == [
        "rush", "single", "team"]
