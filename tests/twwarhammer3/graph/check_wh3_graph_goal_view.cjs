/* Offline browser regression for model hints. Explicit synthetic source rows;
   no game/API and no completion or strength claim.
   NODE_PATH=~/.cache/wh3-playwright/node_modules node THIS_FILE OUTPUT_DIR
*/
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { execFileSync } = require("node:child_process");
const { chromium } = require("playwright");

async function main() {
  const out = path.resolve(process.argv[2]);
  await fs.mkdir(out, { recursive: true });
  const root = path.resolve(__dirname, "../../..");
  execFileSync(
    process.env.GRAPH_VIEW_PYTHON || path.join(root, ".venv/bin/python"),
    [
      "-c",
      String.raw`
import sys
from pathlib import Path
from twwarhammer3.battle import graph_view
sys.path.insert(0, "tests/twwarhammer3/graph")
from test_wh3_graph_goal_view import recording, write
out = Path(sys.argv[1])
for used in (True, False):
    episode, result, rows = recording(out / str(used))
    if not used:
        rows[-1]["record"]["outputs"]["target"] = "near"
        rows[-1]["record"]["selection"]["used"] = False
        write(episode, result, rows)
    graph_view.write([episode], episode / "view.html")
`,
      out,
    ],
    { cwd: root, env: { ...process.env, PYTHONPATH: path.join(root, "src") } },
  );
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  await context.setOffline(true);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("request", (r) => assert(!/^https?:/.test(r.url()), "network request"));
  try {
    for (const used of [true, false]) {
      const directory = path.join(out, used ? "True" : "False");
      const rows = (await fs.readFile(path.join(directory, "trace.jsonl"), "utf8"))
        .trim()
        .split("\n")
        .map(JSON.parse);
      const adopted = rows[4].record;
      const transition = rows[6].record;
      await page.goto(pathToFileURL(path.join(directory, "view.html")).href);
      await page.selectOption("#filter", "all");
      const event = await page.locator('#events option[data-line="7"]').getAttribute("value");
      await page.selectOption("#events", event);
      const shown = JSON.parse(await page.locator("#record").textContent());
      assert.equal(shown.outputs.target, transition.outputs.target);
      assert.deepEqual(shown.selection.preference.source, adopted.source);
      assert.equal(shown.selection.used, used);
      const evidence = await page.locator("#evidence").textContent();
      assert(evidence.includes(`Model preference ${adopted.target}`));
      assert(evidence.includes("Goal 1, observation 1 at 0:01.0, trace row 5"));
      assert(
        evidence.includes(
          used ? "used within this node's eligible targets" : "graph fallback used",
        ),
      );
      assert(
        (await page.locator("#event-time").textContent()).includes(
          "source observation 2 at 0:01.1",
        ),
      );
      await page.screenshot({ path: path.join(directory, "browser.png"), fullPage: true });
    }
    assert.deepEqual(errors, []);
    await fs.writeFile(
      path.join(out, "result.json"),
      JSON.stringify({ passed: 2, errors }, null, 2),
    );
    process.stdout.write("2 synthetic goal-view browser cases passed\n");
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  process.stderr.write(`${e.stack}\n`);
  process.exitCode = 1;
});
