/* Check a scripted screen inside the combined model/benchmark report.
   Usage: NODE_PATH=~/.cache/wh3-playwright/node_modules node
   tests/twwarhammer3/check_wh3_scripted_screen_browser.cjs HTML JOBS_JSON OUTPUT_DIR
   JOBS_JSON is the frozen list: one launch per distinct condition, including losing controls.
   Compare displayed rows and outcomes with that list and original engine endings.
   Browser mechanics follow check_wh3_report_browser.cjs. No game or API calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const [html, jobsFile, output] = process.argv.slice(2);
  assert(html && jobsFile && output, "HTML JOBS_JSON OUTPUT_DIR");
  const jobs = JSON.parse(await fs.readFile(jobsFile, "utf8")).map((job) => path.resolve(job));
  const conditions = new Set(jobs.map((job) => path.basename(job)));
  assert.equal(conditions.size, jobs.length);
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce", offline: true,
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.waitForSelector("#matrix .scenario-row");
    const data = await page.locator("#report-data").evaluate((node) => JSON.parse(node.textContent));
    assert(data.scenarios.some((item) => item.rows.some((row) => row.kind === "model")));
    const trials = new Map(data.report.groups.flatMap((group, g) =>
      group.trials.map((trial, t) => [`g${g}-t${t}`, trial])));
    const visited = new Set();
    for (const job of jobs) {
      const keys = data.scenarios.flatMap((item) => item.battles).filter((key) =>
        path.basename(trials.get(key).instance) === path.basename(job));
      assert.equal(keys.length, 1, `${job}: one displayed screen condition`);
      const key = keys[0], item = data.scenarios.find((scenario) => scenario.battles.includes(key));
      assert(item.rows.every((row) => row.kind === "scripted"));
      const owners = item.rows.filter((row) => row.battles.includes(key));
      assert.equal(owners.length, 1, `${job}: exactly one controller row`);
      assert.equal(owners[0].battles.filter((battle) =>
        conditions.has(path.basename(trials.get(battle).instance))).length, 1,
        `${job}: distinct frozen conditions must not merge into one controller row`);
      assert.equal(owners[0].name, data.battles[key].commander.name);
      assert(data.replays[key], `${job}: embedded replay`);
      const block = page.locator(`#matrix .scenario-row[data-scenario="${item.id}"]`);
      assert.equal(await block.locator(".bar-row").count(), item.rows.length,
        `${item.name}: every scripted controller keeps its own visible row`);
      const text = await block.innerText();
      for (const row of item.rows) assert(text.includes(row.name), row.name);
      await block.locator("button.scenario").click();
      await page.locator("#run-select").selectOption(key);
      await page.waitForFunction((selected) => document.querySelector("#run-select").value === selected
        && !document.querySelector("#download-replay").disabled, key);
      const raw = JSON.parse(await fs.readFile(path.join(job, trials.get(key).episode, "result.json")));
      assert.equal(raw.ended_by, "engine_result");
      assert.equal(raw.status, raw.engine_ending.result);
      assert.match(await page.locator("#run-line").innerText(),
        new RegExp({ won: "Won", lost: "Lost", draw: "Draw" }[raw.engine_ending.result]));
      assert(await page.locator("#map-layer .unit").count() > 0);
      if (!visited.size) {
        await page.locator("#viewer").scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(output, "desktop-replay.png") });
        await block.scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(output, "desktop-rows.png") });
      }
      visited.add(key);
    }
    assert.equal(visited.size, jobs.length);
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(output, "phone.png") });
    assert.deepEqual(errors, []);
    console.log(`${visited.size} frozen scripted conditions retained beside model scenarios; all rows, engine outcomes, replays and phone layout passed.`);
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
