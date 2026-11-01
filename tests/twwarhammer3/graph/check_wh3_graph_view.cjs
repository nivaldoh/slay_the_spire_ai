/* Browser part of the owner-agreed graph view check. Read-only recorded battles;
   no game/API. Expected identities, times, orders and effects come from raw trace
   rows and result.json, independently of graph_view.py's data collector.

   NODE_PATH=~/.cache/wh3-playwright/node_modules node \
     tests/twwarhammer3/graph/check_wh3_graph_view.cjs OUTPUT_DIR PAGE.html EPISODE [EPISODE ...]
   Uses the existing external Playwright validation install; no project dependency.
*/
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { execFileSync } = require("node:child_process");
const { chromium } = require("playwright");
const clock = (ms) =>
  `${Math.floor(ms / 60000)}:${((Math.floor(ms / 100) / 10) % 60).toFixed(1).padStart(4, "0")}`;

async function checkLabels(page) {
  const clipped = await page.locator("#graph .node").evaluateAll((nodes) =>
    nodes.flatMap((node) => {
      const box = node.querySelector("rect").getBBox();
      return Array.from(node.querySelectorAll("text"))
        .filter((text) => {
          const b = text.getBBox();
          return b.x < box.x || b.x + b.width > box.x + box.width;
        })
        .map((text) => text.textContent);
    }),
  );
  assert.deepEqual(clipped, [], "node branch labels extend outside their boxes");
}

async function checkPartialAndTerminal(page, out) {
  // Hand-written root graph: two orders, one acknowledgement result, then closure
  // after a terminal observation. A reported success omits its witness. No gameplay result.
  const root = path.resolve(__dirname, "../../..");
  const fixture = path.resolve(out, "synthetic-partial-terminal");
  execFileSync(
    process.env.GRAPH_VIEW_PYTHON || path.join(root, ".venv/bin/python"),
    [
      "-c",
      String.raw`
import json, sys
from pathlib import Path
from twwarhammer3.battle import graph, graph_view
p=Path(sys.argv[1]); p.mkdir(parents=True, exist_ok=True)
g={"version":graph.VERSION,"entry":"move","nodes":{
 "move":{"op":"move","inputs":{"units":["u","v"],"point":{"x":20,"z":0}},
         "next":{"succeeded":"end","failed":"end","cancelled":"end"}},
 "end":{"op":"end","inputs":{},"next":{}}}}
c={"type":"graph","graph":g}; s={"battle":"synthetic","seq":1,"time_ms":1000}
o={**s,"phase":"Deployed","friendly":[
 {"id":"u","type":"foot","x":0,"z":0,"men":10,"state":[]},
 {"id":"v","type":"cavalry","x":5,"z":0,"men":10,"state":[]}],"enemy":[]}
rows=[{"kind":"observation","observation":o},
 {"kind":"team","event":"started","node":"move","node_run":1,
  "graph_sha256":graph.digest(g),"source":s,"inputs":{"units":["u","v"],"point":{"x":20,"z":0}}},
 {"kind":"decision","seq":1,"time_ms":1000,"request":"q","behavior":{
  "node":"move","graph_sha256":graph.digest(g)},"orders":[
  {"unit":"u","type":"move","x":20,"z":0},{"unit":"v","type":"move","x":20,"z":0}]},
 {"kind":"ack","request":"q","ack":{"request":"q","based_on":1,"applied_ms":1100,
  "results":[{"index":1,"unit":"u","ok":True}]}},
 {"kind":"observation","observation":{**o,"seq":2,"time_ms":1500}},
 {"kind":"team","event":"transition","node":"move","node_run":1,
  "graph_sha256":graph.digest(g),"source":{**s,"seq":2,"time_ms":1500},
  "status":"succeeded","successor":"end","outputs":{}},
 {"kind":"result","observation":{**o,"seq":3,"time_ms":2000}},
 {"kind":"team","event":"closed","node":"end","node_run":0,
  "graph_sha256":graph.digest(g),"source":{**s,"seq":2,"time_ms":1500}}]
r={"battle":"synthetic","status":"synthetic test only","card":{"source_revision":"synthetic",
 "disclosure":{"configuration":c,"configuration_sha256":graph.digest(c)}}}
(p/"result.json").write_text(json.dumps(r)); (p/"trace.jsonl").write_text("\n".join(map(json.dumps,rows))+"\n")
graph_view.write([p],p/"view.html")
`,
      fixture,
    ],
    { cwd: root, env: { ...process.env, PYTHONPATH: path.join(root, "src") } },
  );
  await page.goto(pathToFileURL(path.join(fixture, "view.html")).href);
  await page.selectOption("#filter", "all");
  const ack = await page.locator('#events option[data-line="4"]').getAttribute("value");
  await page.selectOption("#events", ack);
  assert.equal(
    await page.locator("#caption").textContent(),
    "Partial acknowledgement: 1 of 2 order results",
  );
  assert.equal(await page.locator("#state").getAttribute("data-status"), "running");
  assert(
    (await page.locator("#evidence").textContent()).includes("Missing results for order indexes 2"),
  );
  const completion = await page.locator('#events option[data-line="6"]').getAttribute("value");
  await page.selectOption("#events", completion);
  assert.equal(await page.locator("#evidence").textContent(), "No completion witness recorded.");
  const closed = await page.locator('#events option[data-line="8"]').getAttribute("value");
  await page.selectOption("#events", closed);
  assert.equal(await page.locator("#time").getAttribute("max"), "2000");
  assert((await page.locator("#event-time").textContent()).includes("Shown at 0:02.0"));
  assert(
    (await page.locator("#event-time").textContent()).includes("source observation 2 at 0:01.5"),
  );
  assert((await page.locator("#frame-time").textContent()).includes("Observation 3 at 0:02.0"));
  await checkLabels(page);
}

async function main() {
  const [out, html, ...episodes] = process.argv.slice(2);
  assert(out && html && episodes.length, "OUTPUT_DIR PAGE.html EPISODE [EPISODE ...]");
  await fs.mkdir(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  await context.setOffline(true);
  const page = await context.newPage(),
    errors = [],
    checks = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("request", (request) =>
    assert(!/^https?:/.test(request.url()), "viewer requested a network resource"),
  );
  try {
    await page.goto(pathToFileURL(path.resolve(html)).href);
    assert.equal(await page.locator("#episode option").count(), episodes.length);
    for (const [index, episode] of episodes.entries()) {
      const rows = (await fs.readFile(path.join(episode, "trace.jsonl"), "utf8"))
        .trim()
        .split("\n")
        .map(JSON.parse);
      const result = JSON.parse(await fs.readFile(path.join(episode, "result.json"), "utf8"));
      const config = result.card.disclosure.configuration;
      await page.selectOption("#episode", String(index));
      assert((await page.locator("#outcome").textContent()).includes(result.engine_ending.result));
      assert(
        (await page.locator("#outcome").textContent()).includes(
          clock(result.engine_ending.battle_ms),
        ),
      );
      for (const [member, value] of Object.entries(config.members)) {
        if (value.controller.type !== "graph") continue;
        const spec = value.controller.graph;
        await page.selectOption("#member", member);
        await page.selectOption("#filter", "all");
        assert.equal(
          await page.locator("#graph [data-node]").count(),
          Object.keys(spec.nodes).length,
        );
        await checkLabels(page);
        const orderIndex = rows.findIndex(
          (r) => r.kind === "decision" && r.behavior?.member === member && r.orders?.length,
        );
        assert(orderIndex >= 0, `no recorded order for ${member}`);
        const order = rows[orderIndex],
          node = order.behavior.node;
        async function selectRow(row) {
          const option = page.locator(`#events option[data-line="${row + 1}"]`);
          assert.equal(await option.count(), 1, `trace row ${row + 1} not mapped exactly once`);
          await page.selectOption("#events", await option.getAttribute("value"));
        }
        await selectRow(orderIndex);
        assert.equal(await page.locator("#state").getAttribute("data-status"), "running");
        assert.equal(await page.locator("#state").getAttribute("data-node"), node);
        const evidence = await page.locator("#evidence").textContent();
        for (const o of order.orders)
          assert(evidence.includes(o.unit) && evidence.includes(o.type));
        const timing = await page.locator("#event-time").textContent();
        assert(timing.includes(`observation ${order.behavior.source_seq}`));
        assert(timing.includes(clock(order.behavior.source_ms)));
        const ackIndex = rows.findIndex((r) => r.kind === "ack" && r.request === order.request);
        assert(ackIndex > orderIndex);
        await selectRow(ackIndex);
        assert.equal(await page.locator("#caption").textContent(), "Order accepted by engine");
        assert.equal(
          await page.locator("#state").getAttribute("data-status"),
          "running",
          "ack completed the graph",
        );
        assert.equal(await page.locator("#state").getAttribute("data-node"), node);
        const doneIndex = rows.findIndex(
          (r, i) =>
            i > ackIndex &&
            r.kind === "team" &&
            r.member === member &&
            r.event === "member_event" &&
            r.record.event === "transition" &&
            r.record.node === node &&
            r.record.status === "succeeded",
        );
        assert(doneIndex > ackIndex, `no completed ${node} for ${member}`);
        const completed = rows[doneIndex].record;
        await selectRow(doneIndex);
        assert.equal(await page.locator("#state").getAttribute("data-status"), "ready");
        assert.equal(await page.locator("#state").getAttribute("data-node"), completed.successor);
        assert.equal(spec.nodes[node].next.succeeded, completed.successor);
        assert.equal(await page.locator("#evidence").textContent(), completed.witness);
        assert(
          (await page.locator("#caption").textContent()).includes("graph reported completion"),
        );
        const prior = rows
          .slice(0, doneIndex + 1)
          .filter((r) => r.kind === "observation")
          .at(-1).observation;
        assert(
          (await page.locator("#frame-time").textContent()).includes(`Observation ${prior.seq} `),
        );
        const expected = [...prior.friendly, ...prior.enemy].filter(
          (u) => Number.isFinite(u.x) && Number.isFinite(u.z),
        );
        const drawn = await page.locator("#map [data-unit]").evaluateAll((nodes) =>
          nodes.map((el) => ({
            id: el.dataset.unit,
            x: Number(el.dataset.x),
            z: Number(el.dataset.z),
            position: el
              .getAttribute("transform")
              .match(/[-\d.]+/g)
              .map(Number),
          })),
        );
        assert.deepEqual(drawn.map((u) => u.id).sort(), expected.map((u) => u.id).sort());
        let scale;
        for (const u of drawn) {
          const raw = expected.find((p) => p.id === u.id);
          assert.equal(u.x, raw.x);
          assert.equal(u.z, raw.z);
          const base = drawn[0];
          for (const [world, screen, sign] of [
            ["x", 0, 1],
            ["z", 1, -1],
          ]) {
            const delta = u[world] - base[world];
            if (Math.abs(delta) < 1e-6) continue;
            const ratio = (sign * (u.position[screen] - base.position[screen])) / delta;
            assert(ratio > 0, "map reversed an axis");
            scale ??= ratio;
            assert(Math.abs(ratio - scale) < 1e-6, "map distances use different scales");
          }
        }
        assert(
          await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
          "horizontal overflow",
        );
        await page.screenshot({ path: path.join(out, `${index}-${member}.png`), fullPage: true });
        checks.push({
          episode,
          member,
          order_line: orderIndex + 1,
          ack_line: ackIndex + 1,
          witness_line: doneIndex + 1,
          source_seq: completed.source.seq,
          frame_seq: prior.seq,
        });
        // Exercise seek/event navigation and playback through the actual controls.
        await page.locator("#previous").click();
        await page.locator("#next").click();
        await page.locator("#time").evaluate((el) => {
          el.value = el.min;
          el.dispatchEvent(new Event("input"));
        });
        await page.locator("#play").click();
        await page.waitForTimeout(150);
        await page.locator("#play").click();
        assert(
          Number(await page.locator("#time").inputValue()) >
            Number(await page.locator("#time").getAttribute("min")),
        );
      }
    }
    await checkPartialAndTerminal(page, out);
    assert.deepEqual(errors, []);
    await fs.writeFile(
      path.join(out, "checks.json"),
      JSON.stringify(
        {
          passed: true,
          checks,
          synthetic_checks: ["partial ack", "terminal observation", "missing witness"],
        },
        null,
        2,
      ),
    );
    process.stdout.write(
      `${checks.length} recorded member checks and 3 synthetic regressions passed; no browser errors or network requests.\n`,
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  process.stderr.write(`${error.stack}\n`);
  process.exitCode = 1;
});
