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

  // Colour is the controller: every unit on every map, against this file's own table of colours
  // and the battle's partition record, so a swapped colour fails as well as a missing one.
  const HUES = {
    all: "#ee8fc4",
    front: "#4aa3e8",
    ranged: "#6cc04a",
    mobile: "#ae83ee",
    scripts: "#95a3ab",
  };
  const SHAPES = { front: "circle", ranged: "path", mobile: "rect" };
  const MODELS = { team: true, gap: true };
  const SINGLE = { single: "all", tips: "all", commander: "all", skills: "scripts" };
  const pictures = await page.evaluate(
    () => JSON.parse(document.getElementById("report-data").textContent).suite.pictures,
  );
  for (const [index, link] of links.entries()) {
    await link.click();
    await page.waitForTimeout(700);
    const name = await page
      .locator(".suite-grid tbody tr")
      .nth(index)
      .getAttribute("data-scenario");
    for (const battle of pictures[name].battles) {
      const marks = await page.evaluate(
        (arm) =>
          [...document.querySelectorAll(`.suite-tile[data-arm="${arm}"] [data-unit]`)].map(
            (mark) => [mark.dataset.unit, mark.getAttribute("stroke"), mark.tagName],
          ),
        battle.arm,
      );
      assert.ok(marks.length, `${name} ${battle.arm} drew no units`);
      for (const [unit, hue, tag] of marks) {
        const member = MODELS[battle.arm] ? battle.owners[unit] : SINGLE[battle.arm];
        assert.equal(hue, HUES[member], `${name} ${battle.arm} ${unit} ${member}`);
        if (MODELS[battle.arm]) assert.equal(tag, SHAPES[member], `${name} ${unit} shape`);
      }
    }
  }
  await links[0].click();
  await page.waitForTimeout(700);

  // A finished battle shows its end state: a lost army has no one left fighting at the clock's end.
  const finish = await page.locator("#suite-time").getAttribute("max");
  await page.evaluate((value) => {
    const time = document.getElementById("suite-time");
    time.value = value;
    time.dispatchEvent(new Event("input", { bubbles: true }));
  }, finish);
  const tiles = await page.evaluate(() =>
    [...document.querySelectorAll(".suite-tile")].map(
      (tile) => tile.querySelector("em").textContent,
    ),
  );
  assert.ok(
    tiles.every((text) => /^(Won|Lost) /.test(text)),
    `tiles at the end: ${tiles}`,
  );

  // A second click during a slow load keeps the second battle's maps.
  await links[1].click();
  await links[2].click();
  await page.waitForTimeout(1200);
  const heading = await page.locator("#suite-question").innerText();
  const third =
    pictures[await page.locator(".suite-grid tbody tr").nth(2).getAttribute("data-scenario")];
  assert.equal(heading, third.question);
  assert.equal(await page.locator(".suite-tile").count(), third.battles.length);
  await links[0].click();
  await page.waitForTimeout(700);

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

  // A table's Watch shows its replay too, in that battle's own colours and names.
  await page.locator("#suite-more > summary").click();
  await page.locator("#benchmark-results button", { hasText: "Watch" }).first().click();
  await page.waitForTimeout(800);
  assert.ok(await page.locator("#watch").isVisible(), "the table's Watch shows the replay");
  const shown = await page.locator("#run-line .name").innerText();
  assert.ok((await page.locator("#suite-legend").innerText()).startsWith(shown), "legend matches");
  await page.locator("#suite-more > summary").click();
  await page.locator(".suite-close").click();

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
