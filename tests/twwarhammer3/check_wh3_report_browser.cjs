// TODO: was this for the benchmark report? Or is it some deprecated thing that we can remove?

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
// Figure 2's items: one per model, its commanders pooled.
const plansOf = (data, item) => {
  const items = [];
  for (const row of item.rows.filter((r) => r.kind === "model")) {
    const same = items.find((i) => i.family === row.family);
    if (same) same.battles.push(...row.battles);
    else items.push({ ...row, battles: [...row.battles] });
  }
  return items;
};
// A commander's record beside its score, as the page writes it.
const recordOf = (outcomes) =>
  outcomes.length === 1
    ? `${outcomes[0] === "won" ? "won" : outcomes[0] === "draw" ? "drew" : "lost"} its only battle`
    : `won ${outcomes.filter((o) => o === "won").length} of ${outcomes.length}`;
// The median order age of a commander's battles: per battle, its plans' ages when it has them
// (the asynchronous commander), else its batches'.
const ageOf = (data, keys) => {
  const ages = keys
    .map((key) => data.battles[key].timing)
    .filter(Boolean)
    .flatMap((t) => (t.plans.length ? t.plans : t.ages))
    .sort((a, b) => a - b);
  if (!ages.length) return null;
  const at = (ages.length - 1) / 2;
  return (
    ages[Math.floor(at)] + (ages[Math.ceil(at)] - ages[Math.floor(at)]) * (at - Math.floor(at))
  );
};

// The scenario the page opens on: Figure 1's, the largest controlled comparison, else the first.
const opening = (data) =>
  data.scenarios
    .filter((s) => s.controlled)
    .sort((a, b) => b.controlled.launches - a.controlled.launches)[0] || data.scenarios[0];

// The run line's outcome: always the engine's result, with the battle clock duration. A battle
// that reached the scenario's timer ended there, whatever older jobs recorded as `ended_by`.
const outcome = (trial, group) => {
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
    // At 1440 × 900 the map's top is on the first screen.
    const mapTop = (await page.locator("#map").boundingBox()).y;
    if (mapTop >= 900) await page.screenshot({ path: path.join(output, "opening-failure.png") });
    assert.ok(mapTop < 900, `the map starts on screen (top: ${mapTop}px)`);
    assert.deepEqual(
      data.report.groups.map((group) => group.controllers),
      saved.groups.map((group) => group.controllers),
    );
    const scenario = opening(data);
    const trialOf = (key) => {
      const [, gi, ti] = key.match(/^g(\d+)-t(\d+)$/);
      return saved.groups[gi].trials[ti];
    };
    assert.equal(await text("#heading"), scenario.heading || scenario.title);
    // The masthead's index: one map per scenario, the opening one marked; the finding speaks
    // for the benchmark as a whole.
    if (data.scenarios.length > 1) {
      assert.equal(await count("#index .index-item"), data.scenarios.length);
      // Each map draws its army where it began.
      for (const item of data.scenarios)
        assert.equal(
          await count(`#index .index-item[data-scenario="${item.id}"] svg circle`),
          item.start?.friendly.length ?? 0,
        );
      assert.equal(
        await page.locator('#index .index-item[aria-current="true"]').getAttribute("data-scenario"),
        scenario.id,
      );
      assert.deepEqual(
        await page.locator("#index .index-name").allInnerTexts(),
        data.scenarios.map((s) => s.short),
      );
      // Under each map, a bar per model and one for the best rule.
      const models = new Set(
        data.scenarios.flatMap((s) =>
          s.rows.filter((r) => r.kind === "model").map((r) => r.family),
        ),
      ).size;
      const rules = data.scenarios.some((s) => s.rows.some((r) => r.kind === "scripted"));
      assert.equal(
        await count("#index .index-item:first-child .index-bars i"),
        models + (rules ? 1 : 0),
      );
    }
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
    // The page shows only completed battles of its scenarios; the JSON keeps every one.
    const pageKeys = data.scenarios.flatMap((s) => s.battles);
    assert.ok(
      pageKeys.every((key) => trialOf(key).valid),
      "only completed battles on the page",
    );
    assert.equal(
      pageKeys.length + data.omitted.battles.length,
      saved.groups.reduce((n, group) => n + group.trials.length, 0),
    );
    if (data.scenarios.some((s) => s.core_candidate))
      assert.ok(
        data.scenarios.every((s) => s.core_candidate),
        "only core scenarios",
      );
    assert.ok(Object.keys(data.replays).every((key) => pageKeys.includes(key)));
    // A battle's score: 100 for a win, else the share of the enemy army broken, in percent.
    const scoreOf = (key) => {
      const [, gi, ti] = key.match(/^g(\d+)-t(\d+)$/),
        trial = saved.groups[gi].trials[ti],
        progress = data.battles[key].progress;
      const custom = data.battles[key].objective_outcome;
      if (custom != null ? custom === "success" : trial.engine_outcome === "won") return 100;
      return progress == null ? null : Math.min(99.99, 100 * progress);
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
      // Each row's record and median order age; a commander battle's plan ages stand for that
      // battle only (a regression: they once hid every other battle's ages).
      const cells = await page
        .locator("#headline .board-row")
        .evaluateAll((lines) =>
          lines.map((line) => [...line.children].slice(2, 4).map((cell) => cell.textContent)),
        );
      rows.forEach((keys, i) => {
        assert.equal(
          cells[i][0],
          recordOf(keys.map((key) => trialOf(key).engine_outcome)),
          `Figure 1 record, row ${i}`,
        );
        const age = ageOf(data, keys);
        if (age != null)
          assert.equal(cells[i][1], `${age.toFixed(1)} s`, `Figure 1 order age, row ${i}`);
      });
      assert.match(await text("#finding"), /or more battles per model under one test setup/);
    }
    assert.match(await text("#finding"), /Early results .*: \d+ battles in/);
    // Cumulative API spend per model, every attempt included.
    const spend = {};
    for (const group of saved.groups)
      for (const [t, trial] of group.trials.entries()) {
        const key = `g${saved.groups.indexOf(group)}-t${t}`;
        if (data.battles[key].commander.kind === "model" && trial.llm?.usd != null)
          spend[data.battles[key].commander.family] =
            (spend[data.battles[key].commander.family] || 0) + trial.llm.usd;
      }
    for (const [family, usd] of Object.entries(spend))
      assert.ok((await text("#spend")).includes(`${family} $${usd.toFixed(2)}`), `spend ${family}`);
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
    const facts = first.next.length
      ? await page.locator("#moment .facts").textContent()
      : "";
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

    // Selecting a unit shows its role, from a roster chip (the two armies are open) and from the
    // map; a selected unit is named on the map even when it is crowded.
    const archer = replay.roster.find((u) => u.glyph === "missile_cavalry") || replay.roster[0];
    assert.equal(await page.locator(".armies").getAttribute("open"), "");
    await page.locator(`#roster button[aria-label^="${archer.display},"]`).click();
    assert.ok((await text("#moment .unit-card")).includes(archer.role));
    assert.ok((await text("#map-selection")).includes(archer.display));
    assert.ok(
      (await page.locator("#map-layer").textContent()).includes(archer.short),
      "the selected unit's label",
    );
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "unit.png") });
    await page.locator("#moment .unit-card button").click();
    const lord = replay.roster[0];
    // Dispatched on the marker: another unit's marker may lie on top of it at this moment.
    await page.locator(`#map-layer [data-unit="${lord.id}"]`).first().dispatchEvent("click");
    assert.ok((await text("#moment .unit-card")).includes(lord.role));
    await page.locator("#moment .unit-card button").click();

    // JUDGEMENT?: Route example — Codex, 2026-10-31: use the existing demo for this check.
    // Recorded coverage would need a pending waypoint; only command display is checked.

    // Rests on JUDGEMENT? src/twwarhammer3/battle/report_assets/replay.js Recent routes.
    // Rests on JUDGEMENT? src/twwarhammer3/battle/report_assets/replay.js Waypoint cutoff.
    async function checkPendingRoutes(replay) {
      const applied = replay.decisions.filter((d) => d.applied_ms != null);
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
    }

    // An accepted ability order rings its unit on the map for a few seconds; its line in the
    // moment panel carries the same mark.
    const cast = applied.find((d) =>
      d.steps.some((s) => s.kind === "ability" && s.status !== "rejected" && s.unit !== "army"),
    );
    if (cast) {
      await seek(cast.applied_ms + 500);
      assert.ok((await count("#map-layer .ability-ring")) > 0, "ability ring");
      assert.ok((await count("#moment .orders li.ability")) > 0, "ability mark in the panel");
      await seek(cast.applied_ms + 6000);
      const later = applied.some(
        (d) =>
          d.applied_ms > cast.applied_ms &&
          d.applied_ms <= cast.applied_ms + 6000 &&
          d.steps.some((s) => s.kind === "ability"),
      );
      if (!later) assert.equal(await count("#map-layer .ability-ring"), 0, "the ring fades out");
    }

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

    // Figure 2: one panel per model and per scripted rule; a panel opens its first battle, and
    // every battle opens from the battle select.
    const outcomeOf = (key) => outcome(trialOf(key), saved.groups[key.match(/^g(\d+)/)[1]]);
    const plans = plansOf(data, scenario);
    assert.equal(await count("#commanders .commander"), plans.length);
    for (const [index, item] of plans.entries()) {
      const plan = page.locator("#commanders .commander").nth(index);
      assert.equal(
        (await plan.locator("figcaption strong").innerText()).replace("†", ""),
        item.name,
      );
      assert.equal(
        await plan.locator("figcaption small").innerText(),
        recordOf(item.battles.map((key) => trialOf(key).engine_outcome)),
      );
      // Its battle development: soldiers lost and orders by kind, on shared axes.
      if (item.battles.some((key) => data.battles[key].development))
        assert.equal(await plan.locator("svg.development").count(), 1);
      // A panel opens the commander's earliest battle here.
      const first = scenario.battles.find((key) => item.battles.includes(key));
      await plan.locator(".panel-open").click();
      await page.waitForFunction((k) => document.getElementById("run-select").value === k, first);
    }
    for (const key of scenario.battles) {
      await page.selectOption("#run-select", key);
      await page.waitForSelector("#map-layer .unit");
      assert.ok((await text("#run-line")).includes(outcomeOf(key)), `${key} opens its run`);
    }
    await page.locator("#plans").scrollIntoViewIfNeeded();
    await page.locator("#plans").screenshot({ path: path.join(output, "compare.png") });
    assert.equal(await count("#matrix .scenario-row"), data.scenarios.length);
    // Figure 3: one section per game mode with scenarios on the page, in page order.
    const sections = await page.locator("#matrix .mode h3").allInnerTexts();
    assert.deepEqual(
      sections,
      data.modes
        .filter((mode) => data.scenarios.some((s) => s.mode === mode.key))
        .map((m) => m.title),
    );
    // Every model's bar in Figure 3 is its battles' mean as printed: a loss never reads 100.
    const families = [
      ...new Set(
        data.scenarios.flatMap((s) =>
          s.rows.filter((r) => r.kind === "model").map((r) => r.family),
        ),
      ),
    ].sort();
    for (const item of data.scenarios) {
      const values = await page
        .locator(`#matrix .scenario-row[data-scenario="${item.id}"] .bar-row`)
        .evaluateAll((rows) => rows.map((row) => row.querySelector("b")?.textContent ?? null));
      families.forEach((family, i) => {
        const keys = item.rows.filter((r) => r.family === family).flatMap((r) => r.battles);
        if (item.mode === "survival") {
          const seconds = keys
            .map(trialOf)
            .map((t) => t.measures?.duration_s)
            .filter((v) => v != null);
          if (seconds.length)
            assert.equal(
              values[i],
              `${Math.round(seconds.reduce((a, b) => a + b, 0) / seconds.length)} s`,
              `${item.title}: ${family}; values ${JSON.stringify(values)}; errors ${errors}`,
            );
          return;
        }
        const expected = meanScore(keys);
        assert.equal(
          values[i] == null ? null : Number(values[i]),
          expected,
          `${item.title}: ${family}`,
        );
      });
    }
    // Only completed battles become run options; the rest are counted in the method.
    assert.equal(await page.locator("#run-select option").count(), scenario.battles.length);
    if (data.omitted.setup_only.length) assert.match(await text("#method"), /stopped during setup/);
    if (data.omitted.battles.length)
      assert.match(
        await text("#method"),
        new RegExp(`${data.omitted.battles.length} further battle`),
      );

    // Run settings and downloads.
    await page.locator("#open-settings").click();
    assert.match(await text("#settings-body"), /Source revision/);
    const open = await page.locator("#run-select").inputValue();
    assert.ok((await text("#settings-body")).includes(data.battles[open].harness));
    await page.screenshot({ path: path.join(output, "settings.png") });
    await page.locator("#close-settings").click();
    const routed = data.report.groups
      .flatMap((group, g) => group.trials.map((trial, t) => ({ key: `g${g}-t${t}`, trial })))
      .find(({ key, trial }) => data.battles[key] && trial.metrics?.backend_models?.length);
    if (routed) {
      const routedScenario = data.scenarios.find((item) => item.battles.includes(routed.key));
      if (data.scenarios.length > 1)
        await page.locator(`#index .index-item[data-scenario="${routedScenario.id}"]`).click();
      await page.selectOption("#run-select", routed.key);
      await page.locator("#open-settings").click();
      const settings = await text("#settings-body"),
        validation = routed.trial.metrics.reply_validation;
      for (const snapshot of routed.trial.metrics.backend_models)
        assert.ok(settings.includes(snapshot), "Run settings identifies the served snapshot");
      assert.ok(settings.includes(`${validation.failed} of ${validation.attempts}`));
      await page.screenshot({ path: path.join(output, "router-settings.png") });
      await page.locator("#close-settings").click();
    }
    const { value: reportFile } = await downloaded("#download-report", "recorded-report.json");
    assert.equal(reportFile.report.groups.length, data.report.groups.length);
    assert.equal(reportFile.scenarios.length, data.scenarios.length);

    // Phone width: every scenario of the index on screen, the map soon after, nothing sideways.
    await page.setViewportSize({ width: 390, height: 844 });
    await go(`${stem}.html`);
    await noHorizontalScroll();
    for (const box of await page
      .locator("#index .index-item")
      .evaluateAll((items) => items.map((item) => item.getBoundingClientRect().right)))
      assert.ok(box <= 390, "the index wraps on a phone");
    const map = await page.locator("#map").boundingBox();
    assert.ok(map.y < 2 * 844, "the map starts within two phone screens");
    await page.screenshot({ path: path.join(output, "phone.png"), fullPage: true });

    // The copied HTML is self-contained; every scenario has its own measures and replay.
    const copied = path.join(output, "copied-benchmark.html");
    await fs.copyFile(`${stem}.html`, copied);
    await page.setViewportSize({ width: 1440, height: 900 });
    await go(copied);
    await page.locator("#all").scrollIntoViewIfNeeded();
    await page.locator("#all").screenshot({ path: path.join(output, "suite.png") });
    const navigation = data.scenarios.length > 1 ? "#index" : "#matrix";
    await page.locator(navigation).screenshot({ path: path.join(output, "index.png") });
    for (const [index, item] of data.scenarios.entries()) {
      // Scenarios open from the index (and from Figure 3's names, below).
      const link =
        data.scenarios.length > 1
          ? page.locator(`#index .index-item[data-scenario="${item.id}"]`)
          : page.locator(`#matrix .scenario-row[data-scenario="${item.id}"] .scenario`);
      await link.click();
      await page.waitForFunction(
        (key) => document.getElementById("run-select").value === key,
        item.featured,
      );
      if (data.scenarios.length > 1) {
        assert.equal(await page.locator("#scenario").inputValue(), String(index));
        assert.equal(await link.getAttribute("aria-current"), "true");
      }
      assert.ok((await text("#run-line")).includes(outcomeOf(item.featured)));
      assert.equal(await count("#commanders .commander"), plansOf(data, item).length);
      if (data.replays[item.featured]) {
        await page.waitForFunction(() => !document.getElementById("download-replay").disabled);
        await page.waitForSelector("#map-layer .unit");
      }
      if (item.mode === "siege_defence") {
        await page.locator("#viewer").screenshot({ path: path.join(output, "siege.png") });
        await page.locator("#plans").screenshot({ path: path.join(output, "plans-siege.png") });
      }
      if (item.battles.some((key) => trialOf(key).measures?.custom_objective)) {
        assert.match(await text("#run-line"), /evacuation/);
        assert.match(await page.locator("#map-layer").textContent(), /Extraction/);
        await page.locator("#watch").screenshot({ path: path.join(output, "evacuation.png") });
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
    const sol = (effort) => ["gpt-6-sol", `${effort} reasoning, rules-only prompt`],
      luna = ["gpt-6-luna", "medium reasoning, rules-only prompt"];
    assert.deepEqual(
      pairData.scenarios[0].rows.map((row) => [row.name, row.detail]),
      [luna, sol("high"), sol("low")],
    );
    // Figure 2 pools a model's settings into one panel, marked †; the battle whose controller
    // failed to build is not on the page.
    assert.equal(await count("#commanders .commander"), 2);
    assert.match(await page.locator("#commanders .commander").nth(1).innerText(), /gpt-6-sol†/);
    assert.equal(pairData.omitted.battles.length, 1);
    const lunaKey = `g0-t${pairData.report.groups[0].trials.findIndex((t) => t.policy.includes("@"))}`;
    await page.selectOption("#run-select", lunaKey);
    await page.waitForSelector("#map-layer .unit");
    await page.locator("#open-settings").click();
    const settings = await text("#settings-body");
    assert.ok(settings.includes(`${luna.join(", ")}, policy llm_rules@gpt-6-luna/medium`));
    assert.match(settings, /Prompt the model received \(rules-only prompt\)/);
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
    await checkPendingRoutes(demoReplay.value.replay);
    await seek(0);
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
    assert.equal(
      await count("#commanders .commander"),
      plansOf(demoData, opening(demoData)).length,
    );
    const options = await page.locator("#run-select option").allInnerTexts();
    assert.ok(options.some((option) => /time limit/.test(option)));
    // The battle that did not finish stays in the data, off the page.
    assert.ok(!options.some((option) => /Did not finish/.test(option)));
    assert.match(await text("#method"), /stopped during setup/);
    assert.match(await text("#method"), /1 further battle/);
    assert.match(await text("#run-line"), /objectives held 60% of the time observed/);
    assert.match(await text("#run-line"), /500 supplies left/);
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
