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
  await page.waitForSelector(".suite-tile");
  await page.waitForTimeout(800);

  // Who won: one row per scenario, with the plain method names and no model id.
  const scenarios = Object.keys(report.summary.matrix);
  assert.equal(await page.locator(".suite-grid tbody tr").count(), scenarios.length);
  const grid = await page.locator(".suite-grid").innerText();
  assert.ok(!grid.includes("claude-haiku"), "the grid names methods, not the shared model");
  const wins = Object.values(report.summary.matrix).flatMap((cells) =>
    Object.values(cells)
      .flat()
      .filter((cell) => cell.outcome === "won"),
  );
  assert.equal(await page.locator(".suite-grid td.won").count(), wins.length);
  assert.ok((await page.locator(".suite-who").count()) >= 5, "each method shows who controls what");

  // Every played method gets a map on every battle: a battle without a replay fails here.
  const played = (name) =>
    Object.values(report.summary.matrix[name]).filter((cells) => cells.some((c) => c.own != null));
  const links = await page.locator(".suite-link").all();
  for (const [index, link] of links.entries()) {
    await link.click();
    await page.waitForTimeout(700);
    const name = await page
      .locator(".suite-grid tbody tr")
      .nth(index)
      .getAttribute("data-scenario");
    assert.ok((await page.locator("#suite-question").innerText()).endsWith("?"));
    assert.equal(await page.locator(".suite-tile").count(), played(name).length, name);
  }

  // Colour is the controller: each map uses as many colours as its battle's record has members.
  await links[0].click();
  await page.waitForTimeout(700);
  const picture = await page.evaluate(() => {
    const data = JSON.parse(document.getElementById("report-data").textContent),
      row = document.querySelector(".suite-grid tbody tr.current");
    return data.suite.pictures[row.dataset.scenario];
  });
  const colours = (arm) =>
    page.evaluate((key) => {
      const marks = document.querySelectorAll(`.suite-tile[data-arm="${key}"] svg g > *`);
      return new Set([...marks].map((mark) => mark.getAttribute("stroke")).filter(Boolean)).size;
    }, arm);
  for (const battle of picture.battles) {
    const members = new Set(Object.values(battle.owners)).size || 1;
    assert.equal(await colours(battle.arm), members + 1, `${battle.arm}: members and the enemy`);
  }
  const kinds = await page.evaluate(() =>
    [...document.querySelectorAll(".suite-tile svg g > *")].map((mark) => mark.tagName),
  );
  assert.ok(new Set(kinds).size >= 3, "units keep their shapes");

  // The big map overlaps two methods, solid and outlined, and any map swaps one in.
  const inPair = () => page.locator('.suite-pick[aria-pressed="true"]').count();
  assert.equal(await inPair(), 2);
  await page.locator('.suite-pick[aria-pressed="false"]').first().click();
  assert.equal(await inPair(), 2);
  const fills = await page.evaluate(() =>
    [...document.querySelectorAll("#suite-big g > circle, #suite-big g > rect")].map((mark) =>
      mark.getAttribute("fill"),
    ),
  );
  assert.ok(fills.includes("#16232b"), "the second method is outlined");
  assert.ok(
    fills.some((fill) => fill !== "#16232b"),
    "the first method is solid",
  );

  // The clock moves the armies.
  const before = await page.locator("#suite-big").innerHTML();
  await page.evaluate(() => {
    const time = document.getElementById("suite-time");
    time.value = 20;
    time.dispatchEvent(new Event("input", { bubbles: true }));
  });
  assert.notEqual(await page.locator("#suite-big").innerHTML(), before);

  // Watching a method opens its own battle, with its models named.
  assert.equal(await page.locator("#watch").isVisible(), false);
  await page.locator('.suite-tile[data-arm="team"] .suite-watch').click();
  await page.waitForTimeout(800);
  assert.ok(await page.locator("#watch").isVisible());
  const legend = await page.locator("#suite-legend").innerText();
  for (const name of ["Infantry model", "Guns model", "Knights model"])
    assert.ok(legend.includes(name));
  await page.locator(".suite-close").click();
  assert.equal(await page.locator("#watch").isVisible(), false);

  // Short by default, with the detail one click away, and nothing overflows a phone.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  assert.ok(height < 3200, `page is ${height} px tall`);
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
