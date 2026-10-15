/* Offline browser check of the WH3 field report: no server, network or app build.

One-time Playwright install outside the project (it is a validation tool only):
  npm install --prefix ~/.cache/wh3-playwright playwright@1.61.1
  ~/.cache/wh3-playwright/node_modules/.bin/playwright install chromium

Run from the repository root, with recorded job directories that have episode traces:
  NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
    OUTPUT_DIR runs/twwarhammer3/battle/JOB [JOB ...]

It writes OUTPUT_DIR/recorded.{html,json,txt} with `twwarhammer3 report` and the synthetic demo
OUTPUT_DIR/demo.html with make_wh3_report_demo.py, then checks both pages in headless Chromium
and leaves screenshots, downloads and a PDF in OUTPUT_DIR. Recorded checks compare the page with
the collector's JSON; the demo checks use the generator's exact invented values. */
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "../..");
const fmt = (value, digits = 1) => (value == null ? "Unavailable" : Number(value).toFixed(digits));

async function main() {
  const [output, ...jobs] = process.argv.slice(2).map((arg) => path.resolve(arg));
  assert(
    output && jobs.length,
    "Usage: node check_wh3_report_browser.cjs OUTPUT_DIR JOB [JOB ...]",
  );
  await fs.mkdir(output, { recursive: true });
  const stem = path.join(output, "recorded"),
    demo = path.join(output, "demo.html");
  const uv = (...args) => execFileSync("uv", ["run", ...args], { cwd: ROOT, stdio: "inherit" });
  uv("python", "-m", "twwarhammer3", "report", ...jobs, "--output", stem);
  uv("python", "tests/twwarhammer3/make_wh3_report_demo.py", demo);
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      offline: true,
      viewport: { width: 1440, height: 1100 },
    });
    const page = await context.newPage(),
      errors = [],
      requests = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("request", (request) => {
      if (/^https?:/.test(request.url())) requests.push(request.url());
    });
    const go = async (file) => {
      await page.goto(pathToFileURL(file).href);
      await page.waitForFunction(() => !document.getElementById("replay-content").hidden);
    };
    const text = (selector) => page.locator(selector).textContent();
    const count = (selector) => page.locator(selector).count();
    const saveDownload = async (id, name) => {
      const pending = page.waitForEvent("download");
      await page.locator(id).click();
      const download = await pending,
        target = path.join(output, name);
      await download.saveAs(target);
      assert.equal(await download.failure(), null);
      return target;
    };
    const downloaded = async (id, name) =>
      JSON.parse(await fs.readFile(await saveDownload(id, name), "utf8"));
    const noHorizontalScroll = async () =>
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));

    // Recorded evidence: the page shows the collector's values for the first comparison.
    await go(`${stem}.html`);
    const data = JSON.parse(await text("#report-data"));
    const saved = JSON.parse(await fs.readFile(`${stem}.json`, "utf8"));
    assert.deepEqual(
      data.report.groups.map((group) => group.controllers),
      saved.groups.map((group) => group.controllers),
    );
    const view = data.comparisons[0];
    const trials = view.groups.flatMap((g) => data.report.groups[g].trials);
    const rows = view.groups.flatMap((g) => data.report.groups[g].controllers);
    const plotted = trials.filter(
      (t) => t.valid && t.metrics.margin != null && t.metrics.order_age_s.mean != null,
    ).length;
    assert.equal(await count("#replay-trial option"), trials.length);
    assert.equal(await count("#replay-multiples article"), trials.length);
    assert.equal(await count("#controller-table tbody tr"), rows.length);
    const [, g, t] = data.featured[view.id].match(/^g(\d+)-t(\d+)$/);
    const featured = data.report.groups[g].trials[t];
    const replay = (await downloaded("#replay-download", "recorded-replay.json")).replay;
    const verdict = await text("#replay-verdict");
    assert.ok(verdict.includes(`${replay.summary.decisions} logged decisions`));
    assert.ok(
      verdict.includes(`median information age ${fmt(featured.metrics.order_age_s.p50)} s`),
    );
    // The replay names a controller exactly as its table row does.
    const heading = (await text("#replay-verdict h2")).split(" · ");
    assert.deepEqual(heading.slice(-2), [featured.instance, featured.episode]);
    assert.ok((await text("#controller-table")).includes(heading.slice(0, -2).join(" · ")));
    assert.match(await text("#replay-inspector"), /Decision 1/);
    assert.equal(
      await page
        .locator("#replay-inspector details")
        .filter({ hasText: "Exact recorded prompt" })
        .getAttribute("open"),
      null,
    );
    if (replay.decisions.length > 1) {
      await page.locator("#replay-map").focus();
      await page.keyboard.press("ArrowRight");
      assert.match(await text("#replay-inspector"), /Decision 2/);
      await page.keyboard.press("ArrowLeft");
      assert.match(await text("#replay-inspector"), /Decision 1/);
    }
    await page.keyboard.press("]");
    await page.locator("#replay-play").click();
    assert.equal(await text("#replay-play"), "Pause");
    await page.locator("#replay-play").click();
    if (await count("#replay-stills img")) {
      assert.ok(
        await page
          .locator("#replay-stills img")
          .evaluateAll((images) => images.every((image) => image.naturalWidth > 0)),
      );
      assert.ok(replay.stills.every((shot) => shot.policy_input === false));
      await page.locator("#replay-stills").screenshot({ path: path.join(output, "stills.png") });
    }
    for (const [index, trial] of trials.entries()) {
      await page.locator("#replay-trial").selectOption(String(index));
      await page.waitForFunction(
        (name) => document.getElementById("replay-verdict").textContent.includes(name),
        `${trial.instance} · ${trial.episode}`,
      );
    }
    assert.equal(await count(".point"), plotted);
    await page.screenshot({ path: path.join(output, "desktop.png"), fullPage: true });
    if (plotted) {
      await page.locator(".point").first().focus();
      await page.keyboard.press("Enter");
      assert.match(await text("#selection"), /order age .* s/);
    }
    await page.locator("#controller-table input").first().uncheck();
    const displayed = await downloaded("#export-data", "selected.json");
    assert.equal(
      displayed.groups.reduce((n, group) => n + group.controllers.length, 0),
      rows.length - 1,
    );
    assert.equal(displayed.all_supplied_jobs.length, data.report.jobs.length);
    await page.emulateMedia({ media: "print" });
    assert.equal(
      await page.locator('#controller-table tr[data-selected="false"]').isVisible(),
      false,
    );
    await page.pdf({
      path: path.join(output, "selected.pdf"),
      preferCSSPageSize: true,
      printBackground: true,
    });
    await page.emulateMedia({ media: "screen" });
    await page.locator("#select-all").click();
    await page.locator("#controller-table th button").nth(3).click();
    await page.locator("#axis").selectOption("cost");
    if (await count(".point")) {
      const svg = await fs.readFile(await saveDownload("#export-svg", "chart.svg"), "utf8");
      const valid = rows.reduce((n, row) => n + row.valid, 0),
        started = rows.reduce((n, row) => n + row.trials, 0);
      assert.ok(svg.includes(`${valid} valid / ${started} started`));
      const png = await fs.readFile(await saveDownload("#export-png", "chart.png"));
      assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    }
    await page.locator("#axis").selectOption("added");
    if (!trials.some((trial) => trial.delay_ms > 0)) {
      assert.match(await text("#chart"), /Not measured yet/);
      assert.equal(await page.locator("#export-svg").isDisabled(), true);
    }
    for (const [index, comparison] of data.comparisons.entries()) {
      if (comparison.groups.length) continue;
      await page.locator("#scenario").selectOption(String(index));
      assert.equal(await text("#status"), "Not measured yet");
      assert.equal(await count("#controller-table tbody tr"), 0);
      assert.ok((await text("#metadata-origin")).startsWith(comparison.metadata_origin));
    }
    for (const job of data.report.jobs.filter((job) => job.error))
      assert.ok((await text("#jobs")).includes(job.error));
    await page.locator("#scenario").selectOption("0");
    await page.waitForFunction(() => !document.getElementById("replay-content").hidden);
    await page.locator("#axis").selectOption("age");
    await page.setViewportSize({ width: 390, height: 844 });
    const mapBox = await page.locator("#replay-map").boundingBox();
    const inspectorBox = await page.locator("#replay-inspector").boundingBox();
    assert.ok(inspectorBox.y > mapBox.y + mapBox.height, "narrow replay stacks map over inspector");
    await page.screenshot({ path: path.join(output, "narrow.png"), fullPage: true });
    await noHorizontalScroll();
    await page.locator("#axis").focus();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#axis").inputValue(), "cost");

    // Synthetic demo: exact values from make_wh3_report_demo.py.
    await page.setViewportSize({ width: 1440, height: 1100 });
    await go(demo);
    assert.match(await text("#replay-availability"), /SYNTHETIC DEMO/);
    const synthetic = await downloaded("#replay-download", "synthetic-replay.json");
    assert.equal(synthetic.evidence_kind, "synthetic");
    assert.equal(synthetic.replay.evidence_kind, "synthetic");
    assert.match(await text("#replay-verdict h2"), /^Demo controller A · demo-A-launch-1/);
    assert.match(await text("#dataset-banner"), /SYNTHETIC DEMO/);
    assert.equal(await count("#controller-table tbody tr"), 9);
    assert.equal(await count("#scenario option"), 1);
    assert.match(await text("#controller-table"), /CI unavailable/);
    assert.match(await text("#trial-table"), /time_limit \(engine won\)/);
    await page.locator("#axis").selectOption("added");
    assert.equal(await count(".point"), 17);
    assert.match(await text("#chart"), /0 s.*6 s.*10 s/s);
    assert.match(await text("#tactical-table"), /demo-infantry/);
    await page.screenshot({ path: path.join(output, "demo-latency.png"), fullPage: true });
    const demoSVG = await fs.readFile(await saveDownload("#export-svg", "demo.svg"), "utf8");
    assert.match(demoSVG, /SYNTHETIC DEMO/);
    const demoJSON = await downloaded("#export-data", "demo.json");
    assert.equal(demoJSON.evidence_kind, "synthetic");
    assert.equal(demoJSON.groups.length, 3);
    for (const group of demoJSON.groups)
      for (const pair of group.paired) assert.equal(pair.a.split(" / ")[0], pair.b.split(" / ")[0]);
    for (const checkbox of await page.locator("#controller-table input").all())
      await checkbox.uncheck();
    assert.equal(await count(".point"), 0);
    assert.equal(await page.locator("#export-svg").isDisabled(), true);
    await page.setViewportSize({ width: 390, height: 844 });
    await noHorizontalScroll();

    assert.deepEqual(requests, []);
    assert.deepEqual(errors, []);
    console.log(`Offline browser checks passed; screenshots, downloads and a PDF are in ${output}`);
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
