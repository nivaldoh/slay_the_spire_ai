/* Offline browser check of the WH3 report: no server, network or app build.

One-time Playwright install outside the project (it is a validation tool only):
  npm install --prefix ~/.cache/wh3-playwright playwright@1.61.1
  ~/.cache/wh3-playwright/node_modules/.bin/playwright install chromium

Run from the repository root, with recorded job directories that have episode traces:
  NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
    OUTPUT_DIR runs/twwarhammer3/battle/JOB [JOB ...]

It writes OUTPUT_DIR/recorded.{html,json,txt} with `twwarhammer3 report`, and the synthetic demo
OUTPUT_DIR/demo.html and the invented two-model launches OUTPUT_DIR/pair.html with
make_wh3_report_demo.py, then checks the pages in headless Chromium from file:// URLs and leaves
screenshots and downloads in OUTPUT_DIR. Recorded checks compare the page with the collector's
JSON; the demo and pair checks use the generator's invented values. */
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "../..");
const clock = (ms) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
// The run line's outcome: always the engine's result, with the battle clock duration. A battle
// that reached the scenario's timer ended there, whatever older jobs recorded as `ended_by`.
// Figure 2's items: one per model (its commanders pooled) and per scripted rule, without the
// commanders that never give orders or recorded no army track.
const plansOf = (data, item) => {
  const items = [];
  for (const row of item.rows) {
    const same =
      row.kind === "model" && items.find((i) => i.kind === "model" && i.family === row.family);
    if (same) same.battles.push(...row.battles);
    else items.push({ ...row, battles: [...row.battles] });
  }
  const silent = (keys) => {
    const timings = keys.map((key) => data.battles[key].timing).filter(Boolean);
    return timings.length && !timings.some((t) => t.plans.length || t.ages.length);
  };
  return items.filter(
    (i) => !silent(i.battles) && i.battles.some((key) => data.battles[key].route?.track.length),
  );
};

const outcome = (trial, group) => {
  if (!trial.valid) return "Did not finish";
  const word = { won: "Won", lost: "Lost", draw: "Draw" }[trial.engine_outcome];
  const ms = trial.battle_ms ?? trial.battle_s * 1000,
    duration = clock(ms),
    limit = group?.definition?.scenario?.expect?.time_limit_s;
  if (trial.ended_by === "time_limit" || (limit && ms >= limit * 1000))
    return `${word} at the time limit (${duration})`;
  return `${word} ${trial.engine_outcome === "draw" ? "after" : "in"} ${duration}`;
};

async function main() {
  const [outputArg, ...args] = process.argv.slice(2);
  const output = outputArg && path.resolve(outputArg);
  const reuse = args[0] === "--report" ? path.resolve(args[1]) : null;
  const jobs = reuse ? [] : args.map((arg) => path.resolve(arg));
  assert(
    output && (jobs.length || reuse),
    "Usage: node check_wh3_report_browser.cjs OUTPUT_DIR JOB [JOB ...] | OUTPUT_DIR --report STEM",
  );
  await fs.mkdir(output, { recursive: true });
  const stem = reuse || path.join(output, "recorded"),
    demo = path.join(output, "demo.html"),
    pair = path.join(output, "pair.html");
  const uv = (...args) => execFileSync("uv", ["run", ...args], { cwd: ROOT, stdio: "inherit" });
  if (!reuse) uv("python", "-m", "twwarhammer3", "report", ...jobs, "--output", stem);
  uv("python", "tests/twwarhammer3/make_wh3_report_demo.py", demo, pair);
  const browser = await chromium.launch({ headless: true });
  try {
    // Reduced motion: the page then does not play the key maneuver on load.
    const context = await browser.newContext({
      offline: true,
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
    });
    const page = await context.newPage(),
      errors = [],
      requests = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("request", (request) => {
      if (!/^(file|data|blob):/.test(request.url())) requests.push(request.url());
    });
    const go = async (file) => {
      await page.goto(pathToFileURL(file).href);
      await page.waitForSelector("#map-layer .unit");
    };
    const text = (selector) => page.locator(selector).innerText();
    const count = (selector) => page.locator(selector).count();
    const seek = (ms) => page.evaluate((t) => Viewer.seek(t), ms);
    const scrub = (ms) =>
      page.locator("#scrubber").evaluate((node, s) => {
        node.value = s;
        node.dispatchEvent(new Event("input"));
      }, ms / 1000);
    const dimmed = () => count('#map-layer .unit[opacity="0.25"]');
    const saveDownload = async (id, name) => {
      const pending = page.waitForEvent("download");
      await page.locator(id).click();
      const download = await pending,
        target = path.join(output, name);
      await download.saveAs(target);
      assert.equal(await download.failure(), null);
      return { target, suggested: download.suggestedFilename() };
    };
    const downloaded = async (id, name) => {
      const { target, suggested } = await saveDownload(id, name);
      return { value: JSON.parse(await fs.readFile(target, "utf8")), suggested };
    };
    const noHorizontalScroll = async () =>
      assert.ok(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        "no horizontal page scroll",
      );

    // Recorded evidence: the header, run line and replay of the featured run.
    await go(`${stem}.html`);
    const data = JSON.parse(await page.locator("#report-data").textContent());
    const saved = JSON.parse(await fs.readFile(`${stem}.json`, "utf8"));
    assert.deepEqual(
      data.report.groups.map((group) => group.controllers),
      saved.groups.map((group) => group.controllers),
    );
    const scenario = data.scenarios[0];
    assert.equal(await text("#question"), scenario.question || scenario.title);
    const [, g, t] = scenario.featured.match(/^g(\d+)-t(\d+)$/);
    const featured = saved.groups[g].trials[t];
    const runLine = await text("#run-line"),
      featuredOutcome = outcome(featured, saved.groups[g]);
    assert.ok(runLine.includes(featuredOutcome), `run line shows ${featuredOutcome}`);
    assert.ok(runLine.includes(data.battles[scenario.featured].commander.name));
    // A curated pick states the commander's record and that it is not a typical result.
    if (scenario.featured_reason === "selected")
      assert.match(
        runLine,
        /won \d+ of \d+ here[\s\S]*featured for its analyst notes, not as typical/,
      );
    // A battle's score: 100 for a win, else the share of the enemy army broken, in percent.
    const scoreOf = (key) => {
      const [, gi, ti] = key.match(/^g(\d+)-t(\d+)$/),
        trial = saved.groups[gi].trials[ti],
        progress = data.battles[key].progress;
      if (!trial.valid) return null;
      if (trial.engine_outcome === "won") return 100;
      return progress == null ? null : 100 * progress;
    };
    // As printed: never rounded up to a win's 100.
    const meanScore = (keys) => {
      const scores = keys.map(scoreOf).filter((v) => v != null);
      if (!scores.length) return null;
      const value = scores.reduce((a, b) => a + b, 0) / scores.length;
      return value >= 100 ? 100 : Math.min(99, Math.round(value));
    };
    // Figure 1: the controlled comparison, one score per commander.
    const headline = data.scenarios.find((item) => item.controlled);
    if (headline) {
      assert.match(await text("#headline"), /Figure 1\./);
      const subset = new Set(headline.controlled.battles);
      const rows = headline.rows
        .map((row) => row.battles.filter((key) => subset.has(key)))
        .filter((keys) => keys.length);
      assert.equal(await count("#headline .board-row"), rows.length);
      const shown = await page.locator("#headline .board-row .score b").allInnerTexts();
      assert.deepEqual(
        shown.map(Number),
        rows.map((keys) => meanScore(keys)).filter((v) => v != null),
      );
      assert.match(await text("#finding"), /scores \d+/);
    }
    await page.screenshot({ path: path.join(output, "desktop.png") });

    const { value: replayFile } = await downloaded("#download-replay", "recorded-replay.json");
    const replay = replayFile.replay;
    assert.ok(!("measures" in replayFile.trial), "evaluation stays outside public replay exports");
    assert.ok(replay.frames.every((frame) => !("evaluation" in frame) && !("final" in frame)));
    assert.ok(replay.frames.length && replay.decisions.length);
    assert.ok(replay.stills?.every((shot) => shot.policy_input === false) ?? true);
    const applied = replay.decisions.filter((d) => d.applied_ms != null);
    const first = applied[0],
      second = applied[1];
    const panelHeading = () => text("#moment .decision-head h3");
    assert.match(await panelHeading(), new RegExp(`at ${clock(first.applied_ms)}`));

    // The moment panel: the model's explanation, its orders and what followed (folded), without
    // JSON.
    const panel = await text("#moment");
    if (first.reason) assert.ok(panel.includes(first.reason), "the stated reason is quoted");
    assert.equal(await count("#moment .orders li"), first.summary.length);
    assert.equal(
      await count("#moment .facts li"),
      first.next.length + (first.next_truncated ? 1 : 0),
    );
    const facts = await page.locator("#moment .facts").textContent();
    for (const fact of first.next) assert.ok(facts.includes(fact.text));
    assert.doesNotMatch(panel, /[{[]\s*"|"\w+"\s*:/, "no JSON in the default panel");
    assert.equal(await count("#moment details[open]"), 0);
    assert.match(panel, /\d+\.\d s old when the game accepted these orders/);
    assert.match(await text("#method"), /accepted is not the same as carried out/);

    // Keyboard: ←/→ step through decisions, [ ] through events, Space plays and pauses.
    await page.locator("#map").focus();
    await page.keyboard.press("ArrowRight");
    assert.match(await panelHeading(), new RegExp(`at ${clock(second.applied_ms)}`));
    assert.ok((await text("#clock")).startsWith(clock(second.applied_ms)));
    await page.keyboard.press("ArrowLeft");
    assert.match(await panelHeading(), new RegExp(`at ${clock(first.applied_ms)}`));
    const [one, two] = replay.events.filter((e) => e.time_ms > first.applied_ms + 1);
    if (two && two.time_ms > one.time_ms + 1) {
      await page.keyboard.press("]");
      assert.equal(await page.evaluate(() => Viewer.time), one.time_ms);
      await page.keyboard.press("]");
      assert.equal(await page.evaluate(() => Viewer.time), two.time_ms);
      await page.keyboard.press("[");
      assert.equal(await page.evaluate(() => Viewer.time), one.time_ms);
    }
    await page.keyboard.press(" ");
    assert.match(await text("#play"), /Pause/);
    await page.keyboard.press(" ");
    assert.match(await text("#play"), /Play/);

    // Never a reply before it was applied: just before each application the panel waits.
    for (const d of applied.slice(1, 40)) {
      const requested = d.decision_time_ms ?? d.time_ms;
      if (d.applied_ms - requested < 200) continue;
      await seek(d.applied_ms - 1);
      const before = await text("#moment");
      const waiting = `Waiting \\d+\\.\\d s for the (model|controller)'s next reply`;
      assert.match(before, new RegExp(waiting));
      const heading = await panelHeading();
      const previous = applied[applied.indexOf(d) - 1];
      if (clock(previous.applied_ms) !== clock(d.applied_ms))
        assert.doesNotMatch(heading, new RegExp(`at ${clock(d.applied_ms)}$`));
      await seek(d.applied_ms);
      assert.match(await panelHeading(), new RegExp(`at ${clock(d.applied_ms)}`));
    }
    const withOrders = applied.find(
      (d) => d.steps.length && d.basis_frame != null && d.after_frame != null,
    );
    await seek(withOrders.applied_ms);
    await page.locator("#moment button.inspect").click();
    assert.match(await text("#moment .pinned-line"), /Pinned: decision issued at/);
    assert.match(await text("#map-caption"), /The reply applied at/);
    assert.match(await text("#moment"), /While the reply was being generated/);
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "inspect.png") });
    await page.locator("#moment .pinned-line button").click();
    assert.equal(await count("#moment .pinned-line"), 0);

    // Selecting a unit shows its role, from a roster chip (the roster folds) and from the map.
    const archer = replay.roster.find((u) => u.glyph === "missile_cavalry") || replay.roster[0];
    await page.locator(".armies > summary").click();
    await page.locator(`#roster button[aria-label^="${archer.display},"]`).click();
    assert.ok((await text("#moment .unit-card")).includes(archer.role));
    assert.ok((await text("#map-selection")).includes(archer.display));
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "unit.png") });
    await page.locator("#moment .unit-card button").click();
    const lord = replay.roster[0];
    // Dispatched on the marker: another unit's marker may lie on top of it at this moment.
    await page.locator(`#map-layer [data-unit="${lord.id}"]`).first().dispatchEvent("click");
    assert.ok((await text("#moment .unit-card")).includes(lord.role));
    await page.locator("#moment .unit-card button").click();

    // Unselected units' recent routes start at the unit, through the waypoints still ahead.
    const mover = applied.find((d) =>
      d.steps.some((step) => step.kind === "move" && step.status !== "rejected"),
    );
    const moving = mover && replay.frames.find((f) => f.time_ms > mover.applied_ms);
    assert.ok(moving, "a recorded battle with an accepted move has a frame after it");
    await seek(moving.time_ms);
    const faint = await page.evaluate(() => {
      const at = new Set(
        [...document.querySelectorAll("#map-layer .unit")].map((node) =>
          node
            .getAttribute("transform")
            .match(/translate\(([^)]+)\)/)[1]
            .replace(" ", ","),
        ),
      );
      const starts = [
        ...document.querySelectorAll('#map-layer > g[opacity="0.3"] > polyline[stroke="#56b4e9"]'),
      ].map((line) => line.getAttribute("points").split(" ")[0]);
      return { drawn: starts.length, loose: starts.filter((p) => !at.has(p)) };
    });
    assert.ok(faint.drawn > 0, "faint routes are drawn for moving units");
    assert.deepEqual(faint.loose, [], "every faint route starts at a unit");

    // Watch the featured maneuver plays from the highlight's lead-in.
    if (replay.highlights?.length) {
      const highlight = replay.highlights.find((h) => h.feature) || replay.highlights[0];
      await page.locator("#watch-featured").click();
      assert.match(await text("#play"), /Pause/);
      await page.waitForTimeout(500);
      const at = await page.evaluate(() => Viewer.time);
      assert.ok(at >= highlight.time_ms - highlight.lead_in_s * 1000);
      await page.locator("#play").click();
      // The watched note dims the other units only until the time is moved by hand.
      if (highlight.units?.length) assert.ok((await dimmed()) > 0, "the watched note's emphasis");
      await scrub(await page.evaluate(() => Viewer.time));
      assert.equal(await dimmed(), 0, "scrubbing ends the watched note's emphasis");
      // Overlapping note windows mark one card, the one the map caption names.
      for (const h of replay.highlights) {
        await seek(h.time_ms);
        const marked = await page
          .locator("#highlights .chapter")
          .evaluateAll((cards) => cards.findIndex((card) => card.classList.contains("active")));
        assert.equal(await count("#highlights .chapter.active"), 1);
        assert.match(await text("#map-caption"), new RegExp(`^Note ${marked + 1}: `));
      }
      assert.equal(await count("#highlights .chapter"), replay.highlights.length);
    }
    // The model's view: outlines of the observation behind the model's current work.
    await seek(second.applied_ms + 500);
    await page.locator("#lag-toggle").click();
    assert.equal(await page.locator("#lag-toggle").getAttribute("aria-pressed"), "true");
    assert.match(await text("#map-lag"), /Outlines: where units stood \d+\.\d s ago/);
    assert.ok((await count("#map-lag-layer .unit")) > 0, "the model's view draws outlines");
    await page.locator("#lag-toggle").click();
    assert.equal(await count("#map-lag-layer .unit"), 0);
    assert.ok(await page.locator("#map-lag").isHidden());
    // Only embedded stills appear; failed or throttled captures never do.
    const embedded = (replay.stills || []).filter(
      (shot) => shot.image && shot.status === "embedded",
    );
    assert.equal(await count("#stills img"), embedded.length);
    const page_text = await page.locator("body").innerText();
    assert.doesNotMatch(page_text, /capture_failed|throttled|Capture missing|Not measured yet/i);
    if (embedded.length) assert.match(await text("#stills-block"), /not what the model saw/);

    // Figure 2: one map per model and per scripted rule; a map opens its first battle, and
    // every battle opens from the battle select.
    const trialOf = (key) => {
      const [, gi, ti] = key.match(/^g(\d+)-t(\d+)$/);
      return saved.groups[gi].trials[ti];
    };
    const outcomeOf = (key) => outcome(trialOf(key), saved.groups[key.match(/^g(\d+)/)[1]]);
    const plans = plansOf(data, scenario);
    assert.equal(await count("#routes .plan"), plans.length);
    for (const [index, item] of plans.entries()) {
      const plan = page.locator("#routes .plan").nth(index);
      assert.equal(
        (await plan.locator("figcaption strong").innerText()).replace("†", ""),
        item.name,
      );
      const finished = item.battles.map(trialOf).filter((trial) => trial.valid);
      const wins = finished.filter((trial) => trial.engine_outcome === "won");
      assert.match(
        await plan.locator("figcaption small").innerText(),
        new RegExp(`^${finished.length} battles?, ${wins.length} won`),
      );
      await plan.locator(".plan-map").click();
      await page.waitForFunction(
        (k) => document.getElementById("run-select").value === k,
        item.battles[0],
      );
    }
    for (const key of scenario.battles) {
      await page.selectOption("#run-select", key);
      await page.waitForSelector("#map-layer .unit");
      assert.ok((await text("#run-line")).includes(outcomeOf(key)), `${key} opens its run`);
    }
    await page.locator("#plans").scrollIntoViewIfNeeded();
    await page.locator("#plans").screenshot({ path: path.join(output, "compare.png") });
    assert.equal(await count("#matrix tr[data-scenario]"), data.scenarios.length);
    // Figure 3: one section per game mode in the game's order, the empty ones as placeholders;
    // the first scenario's mode is open.
    const sections = await page.locator("#matrix > details > summary span").allInnerTexts();
    assert.deepEqual(
      sections.slice(0, data.modes.length),
      data.modes.map((mode) => mode.title),
    );
    const empty = data.modes.filter((mode) => !data.scenarios.some((s) => s.mode === mode.key));
    assert.equal(await count("#matrix .placeholder"), empty.length);
    // Every model score in Figure 3 is its battles' mean as printed: a loss never reads 100.
    for (const item of data.scenarios) {
      const row = page.locator(`#matrix tr[data-scenario="${item.id}"]`);
      const cells = await row
        .locator("td")
        .evaluateAll((tds) =>
          tds.map((td) => td.querySelector(".cell b")?.firstChild?.textContent),
        );
      const heads = await row.evaluate((tr) =>
        [...tr.closest("table").querySelectorAll("thead th")].map((th) => th.textContent),
      );
      heads.forEach((family, i) => {
        if (!i || family === "Best scripted rule") return;
        const expected = meanScore(
          item.rows.filter((r) => r.family === family).flatMap((r) => r.battles),
        );
        if (expected != null) assert.equal(Number(cells[i]), expected, `${item.title}: ${family}`);
      });
    }
    assert.equal(
      await page.locator("#matrix > details[open] > summary span").first().innerText(),
      data.modes.find((mode) => mode.key === scenario.mode).title,
    );
    // Unrun or setup-only scenarios never become a scenario or run option.
    assert.equal(await page.locator("#run-select option").count(), scenario.battles.length);
    const setupOnly =
      data.setup_only.length + data.scenarios.reduce((n, s) => n + s.setup_only_jobs.length, 0);
    if (setupOnly) assert.match(await text("#method"), /stopped during setup/);
    for (const item of data.setup_only)
      assert.ok(!data.scenarios.some((entry) => entry.name === item.scenario));

    // Run settings and downloads.
    await page.locator("#open-settings").click();
    assert.match(await text("#settings-body"), /Source revision/);
    const open = await page.locator("#run-select").inputValue();
    assert.ok((await text("#settings-body")).includes(data.battles[open].harness));
    await page.screenshot({ path: path.join(output, "settings.png") });
    await page.locator("#close-settings").click();
    const { value: reportFile } = await downloaded("#download-report", "recorded-report.json");
    assert.equal(reportFile.report.groups.length, data.report.groups.length);
    assert.equal(reportFile.scenarios.length, data.scenarios.length);

    // Phone width: the map is on the first screen and nothing scrolls sideways.
    await page.setViewportSize({ width: 390, height: 844 });
    await go(`${stem}.html`);
    await noHorizontalScroll();
    const map = await page.locator("#map").boundingBox();
    assert.ok(map.y < 844, "the map starts on the first phone screen");
    await page.screenshot({ path: path.join(output, "phone.png"), fullPage: true });

    // The copied HTML is self-contained; every scenario has its own measures and replay.
    const copied = path.join(output, "copied-benchmark.html");
    await fs.copyFile(`${stem}.html`, copied);
    await page.setViewportSize({ width: 1440, height: 900 });
    await go(copied);
    await page.locator("#all").scrollIntoViewIfNeeded();
    await page.locator("#all").screenshot({ path: path.join(output, "suite.png") });
    for (const [index, item] of data.scenarios.entries()) {
      const link = page.locator(`#matrix tr[data-scenario="${item.id}"] .scenario`);
      await link.evaluate((node) => (node.closest("details").open = true)); // pilots fold
      await link.click();
      await page.waitForFunction(
        (key) => document.getElementById("run-select").value === key,
        item.featured,
      );
      if (data.scenarios.length > 1)
        assert.equal(await page.locator("#scenario").inputValue(), String(index));
      assert.ok((await text("#run-line")).includes(outcomeOf(item.featured)));
      assert.equal(await count("#routes .plan"), plansOf(data, item).length);
      if (data.replays[item.featured]) {
        await page.waitForFunction(() => !document.getElementById("download-replay").disabled);
        await page.waitForSelector("#map-layer .unit");
      }
      await page.locator("#open-settings").click();
      assert.match(await text("#settings-body"), /Evaluator version/);
      await page.locator("#close-settings").click();
      // A battle with whole-unit counts or objective time shows them in its run card.
      for (const key of item.battles) {
        const { units, objective_time } = trialOf(key).measures;
        const both = units.friendly && units.enemy;
        if (!both && !objective_time.points.length) continue;
        await page.selectOption("#run-select", key);
        await page.waitForFunction((k) => document.getElementById("run-select").value === k, key);
        const card = await text("#run-line");
        if (both)
          assert.ok(
            card.includes(
              `units still fighting: own ${units.friendly.active} of ${units.friendly.registered}`,
            ),
          );
        if (objective_time.points.length) assert.match(card, /objectives held/);
      }
    }
    // The results and the matrix remain usable on a phone.
    await page.setViewportSize({ width: 390, height: 844 });
    await noHorizontalScroll();
    await page.locator("#results").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "progress-phone.png") });
    await page.locator("#all").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "suite-phone.png") });

    // Two models of llm_rules paired in each launch: every row names the model and effort its
    // runs played with, a run whose controller failed to build (pair-c, --effort high) takes
    // them from its policy name, and the suffixed run finds its base policy's prompt.
    await page.setViewportSize({ width: 1440, height: 900 });
    await go(pair);
    const pairData = JSON.parse(await page.locator("#report-data").textContent());
    const sol = (effort) => ["gpt-6-sol", `${effort} reasoning, no tactical advice`],
      luna = ["gpt-6-luna", "medium reasoning, no tactical advice"];
    assert.deepEqual(
      pairData.scenarios[0].rows.map((row) => [row.name, row.detail]),
      [luna, sol("high"), sol("low")],
    );
    // Figure 2 pools a model's settings into one map, marked †.
    assert.equal(await count("#routes .plan"), 2);
    assert.match(await page.locator("#routes .plan").nth(1).innerText(), /gpt-6-sol†/);
    assert.match(await text("#routes"), /1 did not finish/);
    const lunaKey = `g0-t${pairData.report.groups[0].trials.findIndex((t) => t.policy.includes("@"))}`;
    await page.selectOption("#run-select", lunaKey);
    await page.waitForSelector("#map-layer .unit");
    await page.locator("#open-settings").click();
    const settings = await text("#settings-body");
    assert.ok(settings.includes(`${luna.join(", ")}, policy llm_rules@gpt-6-luna/medium`));
    assert.match(settings, /Prompt the model received \(no tactical advice\)/);
    await page.locator("#close-settings").click();

    // Synthetic demo: SYNTHETIC DEMO in the page, the viewer and every download.
    await go(demo);
    assert.match(await page.title(), /SYNTHETIC DEMO/);
    assert.match(await text("#demo-banner"), /SYNTHETIC DEMO/);
    assert.match(await text("#run-line"), /SYNTHETIC DEMO/);
    assert.match(await text("#map-synthetic"), /SYNTHETIC DEMO/);
    const demoReplay = await downloaded("#download-replay", "synthetic-replay.json");
    assert.match(demoReplay.suggested, /SYNTHETIC-DEMO/);
    assert.match(demoReplay.value.notice, /SYNTHETIC DEMO/);
    assert.equal(demoReplay.value.replay.evidence_kind, "synthetic");
    const demoReport = await downloaded("#download-report", "synthetic-report.json");
    assert.match(demoReport.suggested, /SYNTHETIC-DEMO/);
    assert.match(demoReport.value.notice, /SYNTHETIC DEMO/);
    assert.equal(demoReport.value.evidence_kind, "synthetic");
    // A batch validation refused reads as refused, never as keeping current orders.
    const refused = demoReplay.value.replay.decisions.find((d) => d.invalid);
    await seek(refused.applied_ms);
    const refusedPanel = await text("#moment");
    assert.match(refusedPanel, /refused by validation/);
    assert.doesNotMatch(refusedPanel, /Keeping current orders/);
    const demoData = JSON.parse(await page.locator("#report-data").textContent());
    assert.equal(await count("#routes .plan"), plansOf(demoData, demoData.scenarios[0]).length);
    const options = await page.locator("#run-select option").allInnerTexts();
    assert.ok(options.some((option) => /time limit/.test(option)));
    const failed = await page
      .locator("#run-select option", { hasText: "Did not finish" })
      .first()
      .getAttribute("value");
    assert.match(await text("#method"), /stopped during setup/);
    assert.match(await text("#run-line"), /objectives held 60% of the time observed/);
    assert.match(await text("#run-line"), /500 supplies left/);
    // A battle that did not finish names its failure in Run settings, not in the page.
    await page.selectOption("#run-select", failed);
    assert.match(await text("#run-line"), /Did not finish/);
    await page.locator("#open-settings").click();
    assert.match(await text("#settings-body"), /Synthetic policy failure/);
    await page.locator("#close-settings").click();
    await page.selectOption(
      "#run-select",
      await page.locator("#run-select option").first().getAttribute("value"),
    );
    // The demo tag sits clear of the scale bar and north arrow.
    const tag = await page.locator("#map-synthetic").boundingBox(),
      furniture = await page.locator("#map-furniture").boundingBox();
    assert.ok(tag.y + tag.height <= furniture.y, "the demo tag covers no map furniture");
    await page.screenshot({ path: path.join(output, "demo.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await noHorizontalScroll();

    assert.deepEqual(requests, []);
    assert.deepEqual(errors, []);
    console.log(`Offline browser checks passed; screenshots and downloads are in ${output}`);
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
