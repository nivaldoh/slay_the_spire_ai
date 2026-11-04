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

  const setClock = (value) =>
    page.evaluate((target) => {
      const time = document.getElementById("suite-time");
      time.value = target === "end" ? time.max : target;
      time.dispatchEvent(new Event("input", { bubbles: true }));
    }, value);
  const pictures = await page.evaluate(
    () => JSON.parse(document.getElementById("report-data").textContent).suite.pictures,
  );
  const clockText = (seconds) =>
    `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
  const ending = (battle) =>
    `${battle.outcome === "won" ? "Won" : "Lost"} ${clockText(battle.battle_s)}`;

  // Regression, first because it needs an undecoded battle: click one, then the battle already
  // loaded. The slow load finishes last and must not replace the second battle's data.
  const rows = page.locator(".suite-grid tbody tr");
  const nameOf = (index) => rows.nth(index).getAttribute("data-scenario");
  const lastBattles = pictures[await nameOf(0)].battles;
  await page.evaluate(() => {
    const buttons = document.querySelectorAll(".suite-link");
    buttons[1].click(); // both in one task: a browser click would wait out the first load
    buttons[0].click();
  });
  await page.waitForTimeout(1500);
  await setClock("end");
  assert.equal(
    await page.locator(`.suite-tile[data-arm="${lastBattles[0].arm}"] em`).innerText(),
    ending(lastBattles[0]),
    "a slow load replaced the second battle's data",
  );

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

  // Colour is the controller: each unit and path on the small maps and the big map, against this
  // file's own table and the battle's partition record, so a swapped colour fails.
  const HUES = {
    all: "#ee8fc4",
    front: "#4aa3e8",
    ranged: "#6cc04a",
    mobile: "#ae83ee",
    scripts: "#95a3ab",
  };
  const SHAPES = { circle: "front", path: "ranged", rect: "mobile" };
  const SINGLE = { single: "all", tips: "all", commander: "all", skills: "scripts" };
  const memberOf = (battle, unit) => SINGLE[battle.arm] || battle.owners[unit];
  const drawn = (selector) =>
    page.evaluate(
      (query) =>
        [...document.querySelectorAll(query)].map((mark) => ({
          unit: mark.dataset.unit,
          hue: mark.getAttribute("stroke"),
          tag: mark.tagName,
          opacity: mark.getAttribute("opacity"),
        })),
      selector,
    );
  for (const [index, link] of links.entries()) {
    await link.click();
    await page.waitForTimeout(700);
    const name = await nameOf(index);
    const pair = await page.evaluate(() =>
      [...document.querySelectorAll("#suite-big g[data-arm]")].map((item) => item.dataset.arm),
    );
    assert.equal(pair.length, Math.min(2, pictures[name].battles.length), `${name} pair`);
    for (const battle of pictures[name].battles) {
      const marks = await drawn(`.suite-tile[data-arm="${battle.arm}"] [data-unit]`);
      assert.ok(marks.length, `${name} ${battle.arm} drew no units`);
      const big = pair.includes(battle.arm)
        ? await drawn(`#suite-big g[data-arm="${battle.arm}"] [data-unit]`)
        : [];
      for (const mark of [...marks, ...big]) {
        const member = memberOf(battle, mark.unit);
        assert.equal(mark.hue, HUES[member], `${name} ${battle.arm} ${mark.unit} ${member}`);
      }
      // Team and rules members are unit classes, so each mark's shape must match its member.
      if (!SINGLE[battle.arm])
        for (const mark of marks)
          assert.equal(SHAPES[mark.tag], memberOf(battle, mark.unit), `${name} ${mark.unit} shape`);
    }

    // At the clock's end: each tile's result, an empty bar on a loss, a fuller one on a win, and
    // the big map's labels name how their battles ended.
    await setClock("end");
    for (const battle of pictures[name].battles) {
      const tile = page.locator(`.suite-tile[data-arm="${battle.arm}"]`);
      assert.equal(await tile.locator("em").innerText(), ending(battle), `${name} ${battle.arm}`);
      const width = parseFloat(
        await tile.locator(".suite-bar i").evaluate((bar) => bar.style.width),
      );
      if (battle.outcome === "won") assert.ok(width > 0, `${name} ${battle.arm} won with no army`);
      else {
        assert.equal(width, 0, `${name} ${battle.arm} lost with ${width}% still fighting`);
        const standing = await drawn(`.suite-tile[data-arm="${battle.arm}"] [data-unit]`);
        assert.ok(
          standing.every((mark) => mark.opacity !== "1"),
          `${name} ${battle.arm} still drawn`,
        );
      }
    }
    for (const arm of pair) {
      const battle = pictures[name].battles.find((item) => item.arm === arm);
      assert.equal(
        await page.locator(`#suite-pair [data-arm="${arm}"] em`).innerText(),
        ending(battle),
      );
    }
  }
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
  await setClock(20);
  assert.notEqual(await page.locator("#suite-big").innerHTML(), before);

  // Each opened replay names its battle and models, and colours its own units by its own record,
  // whichever way it was opened: a colour left over from the last replay fails.
  const replayColours = async () => {
    const legend = page.locator("#suite-legend");
    const output = await legend.getAttribute("data-output");
    const battle = Object.values(pictures)
      .flatMap((item) => item.battles.map((entry) => ({ ...entry, title: item.title })))
      .find((entry) => entry.output === output);
    assert.ok((await legend.innerText()).startsWith(battle.title), `${output} names no battle`);
    const units = await page.evaluate(() =>
      [...document.querySelectorAll('#map-layer .unit[data-unit^="f"]')].map((unit) => ({
        unit: unit.dataset.unit,
        hue: [...unit.children]
          .map((part) => part.getAttribute("stroke"))
          .find((value) => value && value !== "#fff"),
      })),
    );
    assert.ok(units.length, `${output} drew no units`);
    for (const { unit, hue } of units)
      assert.equal(hue, HUES[memberOf(battle, unit)], `${output} ${unit}`);
    return battle;
  };
  assert.equal(await page.locator("#watch").isVisible(), false);
  await page.locator('.suite-tile[data-arm="team"] .suite-watch').click();
  await page.waitForTimeout(800);
  assert.ok(await page.locator("#watch").isVisible());
  await replayColours();
  const legend = await page.locator("#suite-legend").innerText();
  for (const name of ["Infantry model", "Guns model", "Knights model"])
    assert.ok(legend.includes(name));
  await page.locator(".suite-close").click();
  assert.equal(await page.locator("#watch").isVisible(), false);

  // The tables' Watch buttons show the replay too, with its key on screen.
  await page.locator("#suite-more > summary").click();
  const seen = new Set();
  const watches = page.locator("#benchmark-results button", { hasText: "Watch" });
  for (let index = 0; index < 5; index++) {
    await watches.nth(index).click();
    await page.waitForTimeout(800);
    assert.ok(await page.locator("#watch").isVisible(), "a table's Watch shows the replay");
    seen.add((await replayColours()).arm);
    await page.evaluate(() => document.querySelector("#suite-more").scrollIntoView());
  }
  assert.ok(seen.size > 1, "the replay check covered more than one method");
  await watches.first().click();
  await page.waitForTimeout(800);
  const top = await page
    .locator("#suite-legend")
    .evaluate((item) => item.getBoundingClientRect().top);
  assert.ok(top >= 0, "the replay's key is on screen");
  await page.locator(".suite-close").click();
  await page.locator("#suite-more > summary").click();

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
