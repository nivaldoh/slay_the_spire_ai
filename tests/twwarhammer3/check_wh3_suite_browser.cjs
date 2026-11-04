/* Offline check of the coordination suite page. No game or API calls.
   Run: NODE_PATH=~/.cache/wh3-playwright/node_modules node
   tests/twwarhammer3/check_wh3_suite_browser.cjs runs/twwarhammer3/reports/suite.html
   Expected values come from the report's own JSON beside the page, so this checks that the page
   shows them and stays short, not that they are right; suite.py's tests and a recount do that. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const file = path.resolve(process.argv[2]);
  const report = JSON.parse(fs.readFileSync(file.replace(/\.html$/, ".json")));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  await page.goto(pathToFileURL(file).href);
  await page.waitForSelector(".suite-row");
  await page.waitForTimeout(800);

  // Who won: one row per scenario, with the plain method names and no model id.
  const scenarios = Object.keys(report.summary.matrix);
  assert.equal(await page.locator(".suite-grid tbody tr").count(), scenarios.length);
  const grid = await page.locator(".suite-grid").innerText();
  assert.ok(!grid.includes("claude-haiku"), "the grid names methods, not the shared model");
  const wins = Object.values(report.summary.matrix).flatMap((cells) =>
    Object.values(cells).flat().filter((cell) => cell.outcome === "won"),
  );
  assert.equal(await page.locator(".suite-grid td.won").count(), wins.length);

  // The selected battle: its question, every group with a job, one timeline per played method.
  for (const link of await page.locator(".suite-link").all()) {
    await link.click();
    await page.waitForTimeout(200);
    assert.ok((await page.locator("#suite-question").innerText()).endsWith("?"));
    assert.ok((await page.locator(".suite-jobs li").count()) >= 2);
    assert.ok((await page.locator(".suite-seen").innerText()).length > 20);
    assert.ok((await page.locator(".suite-row").count()) >= 2);
    assert.ok(await page.locator(".suite-map text").count());
    for (const answer of await page.locator(".suite-row-name em").allInnerTexts())
      assert.ok(answer.length > 5);
  }

  // A timeline row opens that method's battle; the map outlines its groups.
  const row = page.locator(".suite-row").first();
  const method = await row.locator("b").innerText();
  await row.click();
  await page.waitForTimeout(800);
  assert.equal(await page.locator("#run-line .name").innerText(), method);
  assert.ok(await page.locator("#map-layer .suite-group-tag").count());
  await page.evaluate(() => {
    const scrubber = document.getElementById("scrubber");
    scrubber.value = 30;
    scrubber.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.waitForTimeout(300);
  assert.ok(await page.locator(".suite-row.current .suite-playhead").isVisible());

  // Short by default: the detail is one click away, and nothing overflows a phone.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  assert.ok(height < 3400, `page is ${height} px tall`);
  assert.equal(await page.locator("#benchmark-results").isVisible(), false);
  await page.locator("#suite-more > summary").click();
  assert.ok(await page.locator("#benchmark-results").isVisible());
  await page.locator("#suite-more > summary").click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  const wide = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  assert.ok(wide <= 1, `${wide} px of sideways scroll at phone width`);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log("suite page: all checks passed");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
