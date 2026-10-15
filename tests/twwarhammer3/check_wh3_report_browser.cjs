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
// The run line's outcome: always the engine's result, with the battle clock duration.
const outcome = (trial) => {
  if (!trial.valid) return `Did not finish${trial.error ? `: ${trial.error}` : ""}`;
  const word = { won: "Won", lost: "Lost", draw: "Draw" }[trial.engine_outcome];
  const duration = clock(trial.battle_ms ?? trial.battle_s * 1000);
  if (trial.ended_by === "time_limit") return `${word} at the time limit (${duration})`;
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
    const context = await browser.newContext({
      offline: true,
      viewport: { width: 1440, height: 900 },
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
    const row = saved.groups[g].controllers.find((item) => item.controller === featured.controller);
    const runLine = await text("#run-line");
    assert.ok(runLine.includes(outcome(featured)), `run line shows ${outcome(featured)}`);
    if (row.valid === 1) assert.match(runLine, /Single recorded battle/);
    if (scenario.featured_reason === "selected") assert.match(runLine, /Selected example/i);
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

    // The moment panel: the model's explanation, its orders and what followed, without JSON.
    const panel = await text("#moment");
    if (first.reason) assert.ok(panel.includes(first.reason), "the stated reason is quoted");
    assert.equal(await count("#moment .orders li"), first.summary.length);
    assert.equal(
      await count("#moment .facts li"),
      first.next.length + (first.next_truncated ? 1 : 0),
    );
    for (const fact of first.next) assert.ok(panel.includes(fact.text));
    assert.doesNotMatch(panel, /[{[]\s*"|"\w+"\s*:/, "no JSON in the default panel");
    assert.equal(await count("#moment details[open]"), 0);
    assert.match(panel, /These orders used a view of the battlefield from \d+\.\d s earlier/);
    assert.match(panel, /not that it was carried out/);

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
      const waiting = `Waiting for the (model|controller)'s next reply \\(requested at ${clock(requested)}\\)`;
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
    assert.match(await text("#map-caption"), /Inspecting the reply applied at/);
    assert.match(await text("#moment"), /While the response was being generated/);
    await page.locator("#viewer").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "inspect.png") });
    await page.locator("#moment .pinned-line button").click();
    assert.equal(await count("#moment .pinned-line"), 0);

    // Selecting a unit shows its role, from a roster chip and from the map.
    const archer = replay.roster.find((u) => u.glyph === "missile_cavalry") || replay.roster[0];
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

    // Unselected units' recent routes start at the unit, toward its engine destination.
    const moving = replay.frames.find(
      (f) => f.time_ms > first.applied_ms && f.friendly.some((u) => u.dest),
    );
    if (moving) {
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
          ...document.querySelectorAll(
            '#map-layer > g[opacity="0.3"] > polyline[stroke="#56b4e9"]',
          ),
        ].map((line) => line.getAttribute("points").split(" ")[0]);
        return { drawn: starts.length, loose: starts.filter((p) => !at.has(p)) };
      });
      assert.ok(faint.drawn > 0, "faint routes are drawn for moving units");
      assert.deepEqual(faint.loose, [], "every faint route starts at a unit");
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
          .locator("#highlights .highlight")
          .evaluateAll((cards) => cards.findIndex((card) => card.classList.contains("active")));
        assert.equal(await count("#highlights .highlight.active"), 1);
        assert.match(await text("#map-caption"), new RegExp(`^Analyst note ${marked + 1} `));
      }
      assert.equal(await count("#highlights .highlight"), replay.highlights.length);
      assert.match(await text("#highlights"), /analyst note/i);
    }
    // Only embedded stills appear; failed or throttled captures never do.
    const embedded = (replay.stills || []).filter(
      (shot) => shot.image && shot.status === "embedded",
    );
    assert.equal(await count("#stills img"), embedded.length);
    const page_text = await page.locator("body").innerText();
    assert.doesNotMatch(page_text, /capture_failed|throttled|Capture missing|Not measured yet/i);
    if (embedded.length) assert.match(await text("#stills"), /not what the model saw/);

    // Compare: one row per controller with the collector's battles won and order delay.
    const views = scenario.comparisons.map((index) => data.comparisons[index]);
    const summaries = views.flatMap((view) =>
      view.groups.flatMap((group) =>
        saved.groups[group].controllers.map((summary) => ({ group, summary })),
      ),
    );
    assert.equal(await count("#run-sets tbody tr"), summaries.length);
    for (const { group, summary } of summaries) {
      const tr = page.locator(
        `#run-sets tr[data-group="${group}"][data-controller="${summary.controller}"]`,
      );
      const cells = await tr.locator("td").allInnerTexts();
      const won = (summary.outcomes.won || 0) + (summary.time_limit_engine_outcomes?.won || 0);
      assert.ok(
        cells[1].startsWith(`${won} of ${summary.valid}`),
        `${summary.controller} battles won`,
      );
      const delay = summary.order_age_median_s;
      assert.equal(cells[2], delay == null ? "not recorded" : `${delay.toFixed(1)} s`);
    }
    // Every replay button opens its run in the viewer.
    const keys = await page
      .locator("#run-sets .replays button")
      .evaluateAll((nodes) => nodes.map((node) => node.dataset.key));
    assert.ok(keys.length);
    for (const key of keys) {
      const [, gi, ti] = key.match(/^g(\d+)-t(\d+)$/);
      const trial = saved.groups[gi].trials[ti];
      await page.locator(`#run-sets .replays button[data-key="${key}"]`).click();
      await page.waitForFunction(
        (k) =>
          document
            .querySelector(`.replays button[data-key="${k}"]`)
            .getAttribute("aria-current") === "true",
        key,
      );
      await page.waitForSelector("#map-layer .unit");
      assert.ok((await text("#run-line")).includes(outcome(trial)), `${key} opens its run`);
      assert.equal(await page.locator("#run-select").inputValue(), key);
    }
    await page.locator("#compare").scrollIntoViewIfNeeded();
    await page.locator("#compare").screenshot({ path: path.join(output, "compare.png") });
    // Unrun or setup-only scenarios never become a scenario or run option.
    const options = await page.locator("#run-select option").count();
    assert.equal(
      options,
      views.reduce(
        (n, view) => n + view.groups.reduce((m, gi) => m + saved.groups[gi].trials.length, 0),
        0,
      ),
    );
    if (data.setup_only.length) assert.match(await text("#setup-only"), /stopped during setup/);
    for (const item of data.setup_only)
      assert.ok(!data.scenarios.some((entry) => entry.name === item.scenario));

    // Run settings and downloads.
    await page.locator("#open-settings").click();
    assert.match(await text("#settings-body"), /Source revision/);
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
    await page.locator("#suite > summary").click();
    assert.equal(await count("#suite-table tbody tr"), data.scenarios.length);
    assert.match(await text("#suite"), /Whole units/);
    await page.screenshot({ path: path.join(output, "suite.png") });
    for (const [index, item] of data.scenarios.entries()) {
      if (data.scenarios.length > 1) await page.selectOption("#scenario", String(index));
      await page.waitForFunction(
        (key) => document.getElementById("run-select").value === key,
        item.featured,
      );
      const [, gi, ti] = item.featured.match(/^g(\d+)-t(\d+)$/);
      const trial = saved.groups[gi].trials[ti];
      assert.equal(await count("#progress-runs tbody tr"), item.overview.started);
      assert.ok((await text("#common-measures")).includes(outcome(trial)));
      const progressRow = page
        .locator(`#progress-runs button[data-key="${item.featured}"]`)
        .locator("xpath=ancestor::tr");
      for (const side of ["friendly", "enemy"]) {
        const counts = trial.measures.soldiers[side];
        assert.ok(
          (await progressRow.innerText()).includes(
            `${counts.remaining ?? "unavailable"} / ${counts.registered ?? "unavailable"}`,
          ),
        );
      }
      const objective = trial.measures.objective_time;
      if (objective.status === "available") {
        assert.equal(
          await count("#common-measures .objective-results tbody tr"),
          objective.points.length,
        );
        for (const point of objective.points) {
          assert.ok((await text("#common-measures")).includes(`${point.id} · ${point.key}`));
        }
      } else assert.match(await text("#common-measures"), /not applicable|unavailable/);
      if (data.replays[item.featured]) {
        await page.waitForFunction(() => !document.getElementById("download-replay").disabled);
        await page.waitForSelector("#map-layer .unit");
      }
      await page.locator("#open-settings").click();
      assert.match(await text("#settings-body"), /Evaluator version/);
      await page.locator("#close-settings").click();
    }
    // Expanded overview and progress tables remain usable on a phone.
    await page.setViewportSize({ width: 390, height: 844 });
    await noHorizontalScroll();
    await page.locator("#suite").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "suite-phone.png") });
    await page.locator("#compare").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "progress-phone.png") });

    // Two models of llm_rules paired in each launch: every row names the model and effort its
    // runs played with, a run whose controller failed to build (pair-c, --effort high) takes
    // them from its policy name, and the suffixed run finds its base policy's prompt.
    await page.setViewportSize({ width: 1440, height: 900 });
    await go(pair);
    const pairData = JSON.parse(await page.locator("#report-data").textContent());
    const sol = (effort) => `gpt-6-sol · ${effort} reasoning · rules-only prompt`,
      luna = "gpt-6-luna · medium reasoning · rules-only prompt";
    assert.deepEqual(await page.locator("#run-sets td.name").allInnerTexts(), [
      luna,
      luna,
      sol("high"),
      sol("low"),
    ]);
    const lunaRow = (g) =>
      page.locator(`#run-sets tr[data-group="${g}"][data-controller^="llm_rules@"] td`);
    assert.equal(await lunaRow(1).first().innerText(), luna);
    assert.match(await lunaRow(1).nth(1).innerText(), /failed: controller construction/);
    const lunaKey = `g0-t${pairData.report.groups[0].trials.findIndex((t) => t.policy.includes("@"))}`;
    await page.locator(`#run-sets .replays button[data-key="${lunaKey}"]`).click();
    await page.waitForSelector("#map-layer .unit");
    await page.locator("#open-settings").click();
    const settings = await text("#settings-body");
    assert.ok(settings.includes(`${luna} · policy llm_rules@gpt-6-luna/medium`));
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
    assert.equal(await count("#run-sets tbody tr"), 9);
    assert.match(await text("#run-sets"), /1 at the time limit/);
    assert.match(await text("#run-sets"), /failed: Synthetic policy failure/);
    assert.match(await text("#setup-only"), /stopped during setup/);
    assert.match(await text("#progress-runs"), /2 alive, 1 destroyed, 1 active \/ 3 registered/);
    assert.match(await text("#common-measures"), /c1 · demo_gate/);
    assert.match(await text("#common-measures"), /60.0%/);
    // A key event's watch (no analyst notes) dims nothing.
    if (await count("#highlights .highlight .watch")) {
      await page.locator("#highlights .highlight .watch").first().click();
      await page.waitForTimeout(300);
      assert.equal(await dimmed(), 0, "a key event's watch dims no unit");
      await page.locator("#play").click();
    }
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
