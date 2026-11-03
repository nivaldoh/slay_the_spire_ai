/* Offline check of the existing visual report with mirror plans. Expected conditions are
   recomputed from raw first-ending unit reads under benchmark-initial.md, not legacy bars.
   Run: NODE_PATH=~/.cache/wh3-playwright/node_modules node
   tests/twwarhammer3/check_wh3_benchmark_report_browser.cjs STEM OUTPUT_DIR [EMPTY_STEM] [UNPLANNED_STEM]
   Browser mechanics follow check_wh3_report_browser.cjs; plan joins follow SWE-bench's
   swebench/harness/reporting.py (docs/references.md). No game or API calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

const read = async (p) => JSON.parse(await fs.readFile(p, "utf8"));
function condition(result) {
  const units = result.benchmark?.units;
  if (!units || units.length !== 5 || !result.setup_checks) return null;
  let total = 0;
  for (const id of Object.keys(result.start.friendly)) {
    const u = units.find((item) => item.id === id);
    if (
      !u ||
      u.error ||
      !Number.isFinite(u.hp) ||
      !Number.isFinite(u.men) ||
      ["wavering", "routing", "shattered", "departed"].some((key) => typeof u[key] !== "boolean")
    )
      return null;
    const factor =
      u.men === 0 || u.departed || u.shattered ? 0 : u.routing ? 0.5 : u.wavering ? 0.8 : 1;
    total += u.hp * factor;
  }
  return (100 * total) / 5;
}

async function main() {
  const [stemArg, outputArg, emptyArg, unplannedArg] = process.argv.slice(2);
  assert(stemArg && outputArg, "STEM OUTPUT_DIR [EMPTY_STEM]");
  const stem = path.resolve(stemArg),
    output = path.resolve(outputArg);
  await fs.mkdir(output, { recursive: true });
  const saved = await read(`${stem}.json`);
  const expected = saved.benchmark_plans.flatMap((p) => p.rows);
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      offline: true,
      reducedMotion: "reduce",
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage(),
      errors = [],
      network = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      if (!/^(file|data|blob):/.test(r.url())) network.push(r.url());
    });
    await page.goto(pathToFileURL(`${stem}.html`).href);
    await page.waitForFunction(() => !document.querySelector("#benchmark-results").hidden);
    const data = await page.locator("#report-data").evaluate((e) => JSON.parse(e.textContent));
    assert.equal(await page.locator(".benchmark-table tbody tr").count(), expected.length);
    const scoreInputs = [];
    for (let i = 0; i < expected.length; i++) {
      const row = expected[i],
        node = page.locator(".benchmark-table tbody tr").nth(i);
      if (!row.outcome) {
        assert.match(await node.locator(".benchmark-outcome").innerText(), /No engine outcome/);
        continue;
      }
      const raw = await read(path.join(row.output, "episode-0000/result.json"));
      const measured = condition(raw);
      assert.equal(raw.engine_ending?.result || raw.status, row.outcome);
      assert.equal(
        await node.locator(".benchmark-outcome").innerText(),
        { won: "Won", lost: "Lost", draw: "Draw" }[row.outcome],
      );
      assert.equal(
        await node.locator(".benchmark-condition b").innerText(),
        measured == null ? "unavailable" : measured.toFixed(2),
      );
      const key = data.benchmark_plans.flatMap((p) => p.rows)[i].battle_key;
      await node.locator(".benchmark-watch").click();
      await page.waitForFunction(
        (key) =>
          document.querySelector("#run-select").value === key &&
          !document.querySelector("#download-replay").disabled,
        key,
      );
      assert.match(
        await page.locator("#run-line").innerText(),
        new RegExp(`condition ${measured.toFixed(2)} / 100`),
      );
      assert((await page.locator("#map-layer .unit").count()) >= 5);
      const before = await page.locator("#scrubber").inputValue();
      await page.locator("#next-decision").click();
      assert(Number(await page.locator("#scrubber").inputValue()) > Number(before));
      scoreInputs.push({
        job: path.basename(row.output),
        outcome: row.outcome,
        condition: measured,
      });
    }
    assert.equal(await page.locator("#headline").isHidden(), true);
    assert.doesNotMatch(await page.locator("#run-line").innerText(), /score \d/);
    await page.locator("#benchmark-results").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "desktop-scores.png") });
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "desktop-replay.png") });
    const downloadReady = page.waitForEvent("download");
    await page.locator("#download-report").click();
    const download = await downloadReady;
    await download.saveAs(path.join(output, "downloaded-report.json"));
    const downloaded = await read(path.join(output, "downloaded-report.json"));
    assert.equal(downloaded.report.benchmark_plans.flatMap((p) => p.rows).length, expected.length);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator("#benchmark-results").scrollIntoViewIfNeeded();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const scoreBox = await page.locator(".benchmark-condition").first().boundingBox();
    assert(
      scoreBox.x >= 0 && scoreBox.x + scoreBox.width <= 390,
      "phone scores fit beside their engine outcome without horizontal scrolling",
    );
    await page.screenshot({ path: path.join(output, "phone-scores.png") });
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "phone-replay.png") });
    // A copied standalone file must retain scores and the replay without its evidence tree.
    const copied = path.join(output, "copied-report.html");
    await fs.copyFile(`${stem}.html`, copied);
    await page.goto(pathToFileURL(copied).href);
    await page.waitForFunction(() => !document.querySelector("#download-replay").disabled);
    assert.equal(await page.locator(".benchmark-table tbody tr").count(), expected.length);
    if (emptyArg) {
      await page.goto(pathToFileURL(`${path.resolve(emptyArg)}.html`).href);
      await page.waitForFunction(() => !document.querySelector("#benchmark-results").hidden);
      assert(await page.locator("#viewer").isHidden());
      assert((await page.locator(".benchmark-table tbody tr").count()) > 0);
      assert.equal(await page.locator(".benchmark-watch").count(), 0);
      assert((await page.locator("#benchmark-attempts").innerText()).includes("never started"));
    }
    if (unplannedArg) {
      await page.goto(pathToFileURL(`${path.resolve(unplannedArg)}.html`).href);
      await page.waitForFunction(() => !document.querySelector("#benchmark-results").hidden);
      const text = await page.locator("#benchmark-attempts").innerText();
      assert.match(text, /Error count unavailable/);
      assert.doesNotMatch(text, /0 recorded error events/);
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    await fs.writeFile(
      path.join(output, "checked-raw-scores.json"),
      JSON.stringify(scoreInputs, null, 2),
    );
    console.log(
      `${scoreInputs.length} raw scores/outcomes and replay links passed; desktop, phone, offline copy, download${emptyArg ? ", never-started plan" : ""}; no browser errors or network.`,
    );
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
