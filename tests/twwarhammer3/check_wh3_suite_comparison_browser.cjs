/* Proposed offline check: separate recordings on a shared clock (redesign guide §4).
   Usage: NODE_PATH=~/.cache/wh3-playwright/node_modules node THIS REPORT.html OUTPUT_DIR
   Needs REPORT.json beside the HTML and its raw evidence directories.
   Checks source frames against their raw trace/recorder lines, then checks the rendered
   identities/positions/times. No coordination score, game or API calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { gunzipSync } = require("node:zlib");
const { chromium } = require("playwright");

(async () => {
  const file = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3]);
  fs.mkdirSync(out, { recursive: true });
  const html = fs.readFileSync(file, "utf8");
  const data = JSON.parse(html.match(/<script id="report-data"[^>]*>([\s\S]*?)<\/script>/)[1]);
  const rows = data.benchmark_plans.flatMap((p) => p.rows);
  const fullRows = JSON.parse(fs.readFileSync(file.replace(/\.html$/, ".json"), "utf8")).rows;
  const runs = {};
  for (const row of rows) {
    if (!data.replays[row.battle_key]) continue;
    const replay = JSON.parse(gunzipSync(Buffer.from(data.replays[row.battle_key], "base64")));
    const frames = replay.frames.filter((f) => f.friendly.length);
    const files = {};
    const matches = fullRows.filter(
      (r) =>
        path.basename(r.output) === path.basename(row.output) &&
        r.arm === row.arm &&
        r.scenario === row.scenario,
    );
    assert.equal(matches.length, 1, "raw evidence path must be unambiguous in the report JSON");
    const raw = (source) => {
      files[source.file] ||= fs
        .readFileSync(path.join(matches[0].output, "episode-0000", source.file), "utf8")
        .trim()
        .split("\n")
        .map(JSON.parse);
      const r = files[source.file][source.line - 1];
      return r.observation || r;
    };
    // Evidence source is independent of the browser's selection function. No later frame may
    // be shown early; equal-time observations retain the recorded payload's ordering.
    for (const f of frames) {
      const source = raw(f.source);
      assert.equal(f.time_ms, source.time_ms);
      for (const side of ["friendly", "enemy"]) {
        assert.deepEqual(
          f[side].map((u) => u.id),
          source[side].map((u) => u.id),
        );
        f[side].forEach((u, i) => {
          assert.ok(Math.abs(u.x - source[side][i].x) <= 0.051);
          assert.ok(Math.abs(u.z - source[side][i].z) <= 0.051);
        });
      }
    }
    runs[row.battle_key] = { row, frames };
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, offline: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(pathToFileURL(file).href);
  await page.waitForSelector(".suite-tile");
  const setTime = (seconds) =>
    page.locator("#suite-time").evaluate((e, t) => {
      e.value = t;
      e.dispatchEvent(new Event("input", { bubbles: true }));
    }, seconds);
  const clock = (ms) => {
    const deciseconds = Math.floor(ms / 100),
      seconds = Math.floor(deciseconds / 10);
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}.${deciseconds % 10}`;
  };
  const latest = (frames, t) => frames.filter((f) => f.time_ms <= t * 1000).at(-1);

  // Regression first: the old viewer displays future first samples at 0:00.
  await setTime(0);
  const firstScenario = data.suite.scenarios[0];
  for (const battle of data.suite.pictures[firstScenario].battles) {
    const row = rows.find((r) => r.output === battle.output),
      run = runs[row.battle_key];
    if (run.frames[0].time_ms <= 0) continue;
    assert.equal(
      await page.locator(`.suite-tile[data-arm="${battle.arm}"] svg [data-unit]`).count(),
      0,
      `${battle.arm}: positions drawn before recording began`,
    );
    assert.equal(
      await page.locator(`.suite-tile[data-arm="${battle.arm}"] .suite-bar`).isVisible(),
      false,
    );
  }
  let checkedPanels = 0;
  for (const name of data.suite.scenarios) {
    await page.locator(`[data-scenario="${name}"] .suite-link`).click();
    await page.waitForFunction(
      () => document.getElementById("suite-page").getAttribute("aria-busy") === "false",
    );
    await page.locator('[data-layout="separate"]').click();
    assert.equal(await page.locator("#suite-big").isVisible(), false);
    const battles = data.suite.pictures[name].battles;
    const keys = Object.fromEntries(
      battles.map((b) => [b.arm, rows.find((r) => r.output === b.output).battle_key]),
    );
    const scene = Object.values(keys).map((key) => runs[key]);
    const points = scene
      .flatMap((r) => r.frames.flatMap((f) => [...f.friendly, ...f.enemy]))
      .filter(
        (u) => u.men > 0 && !(u.state || []).some((s) => ["routing", "shattered"].includes(s)),
      )
      .filter((u) => Number.isFinite(u.x) && Number.isFinite(u.z));
    const xs = points.map((u) => u.x),
      zs = points.map((u) => u.z);
    const minX = Math.min(...xs),
      maxX = Math.max(...xs),
      minZ = Math.min(...zs),
      maxZ = Math.max(...zs),
      spanX = maxX - minX + 80,
      spanZ = maxZ - minZ + 80;
    const width = 1000,
      height = Math.min(480, Math.max(380, (width * spanZ) / spanX));
    const scale = Math.min(width / spanX, height / spanZ);
    const X = (x) => width / 2 + (x - (minX + maxX) / 2) * scale;
    const Y = (z) => height / 2 - (z - (minZ + maxZ) / 2) * scale;
    // JUDGEMENT?: Comparison check coverage — Codex, 2026-11-04: sample boundaries and
    // 90 s for each scene's initial pair. All frames/pairs would cover more; these are
    // proposed display checks, not agreed verification.
    const times = [
      0,
      ...scene.flatMap((r) => [
        Math.floor(r.frames[0].time_ms / 1000),
        Math.ceil(r.frames[0].time_ms / 1000),
        Math.ceil(r.frames.at(-1).time_ms / 1000),
      ]),
      Math.min(90, ...scene.map((r) => Math.floor(r.frames.at(-1).time_ms / 1000))),
    ];
    for (const t of new Set(times)) {
      await setTime(t);
      for (const panel of await page.locator(".suite-panel").all()) {
        const arm = await panel.getAttribute("data-arm"),
          frames = runs[keys[arm]].frames;
        const expected = latest(frames, t);
        const sample = await panel.locator(".suite-sample").innerText();
        assert.equal(
          sample,
          !expected
            ? `Recording starts ${clock(frames[0].time_ms)}`
            : `${t * 1000 > frames.at(-1).time_ms ? "Holding final sample" : "Recorded"} ${clock(expected.time_ms)}`,
        );
        const marks = await panel
          .locator("svg g > [data-unit]:not(polyline), svg [data-enemy]")
          .evaluateAll((els) =>
            els.map((e) => ({
              id: e.dataset.unit || e.dataset.enemy,
              side: e.dataset.enemy ? "enemy" : "friendly",
              shape: e.tagName,
              x: e.getAttribute("cx") || e.getAttribute("x"),
              y: e.getAttribute("cy") || e.getAttribute("y"),
              d: e.getAttribute("d"),
              transform: (() => {
                const m = e.ownerSVGElement.getScreenCTM().inverse().multiply(e.getScreenCTM());
                return [m.a, m.b, m.c, m.d, m.e, m.f];
              })(),
            })),
          );
        const expectedUnits = expected
          ? ["enemy", "friendly"].flatMap((side) =>
              expected[side]
                .filter((u) => Number.isFinite(u.x) && Number.isFinite(u.z) && u.men > 0)
                .map((u) => ({ ...u, side })),
            )
          : [];
        assert.deepEqual(
          marks.map((m) => [m.side, m.id]),
          expectedUnits.map((u) => [u.side, u.id]),
          `${name}/${arm} at ${t}`,
        );
        marks.forEach((m, i) => {
          const u = expectedUnits[i];
          let x, y;
          if (m.shape === "circle") {
            x = Number(m.x);
            y = Number(m.y);
          } else if (m.shape === "rect") {
            x = Number(m.x) + 7;
            y = Number(m.y) + 7;
          } else {
            [x, y] = m.d
              .match(/^M([\d.e+-]+) ([\d.e+-]+)/)
              .slice(1)
              .map(Number);
            y += m.side === "enemy" ? 5.6 : 8.05;
          }
          const [a, b, c, d, e, f] = m.transform;
          assert.ok(
            Math.abs(a * x + c * y + e - X(u.x)) < 1e-6,
            `${name}/${arm}/${u.id} x at ${t}`,
          );
          assert.ok(
            Math.abs(b * x + d * y + f - Y(u.z)) < 1e-6,
            `${name}/${arm}/${u.id} z at ${t}`,
          );
        });
        const paths = await panel
          .locator("polyline[data-unit]")
          .evaluateAll((els) =>
            els.map((e) => ({ id: e.dataset.unit, points: e.getAttribute("points").split(" ") })),
          );
        if (t >= 60) assert.ok(paths.length > 0, `${name}/${arm}: missing recorded paths`);
        for (const line of paths) {
          const recorded = frames
            .filter((f) => f.time_ms <= t * 1000)
            .flatMap((f) => f.friendly.filter((u) => u.id === line.id))
            .filter(
              (u) =>
                u.men > 0 && !(u.state || []).some((s) => ["routing", "shattered"].includes(s)),
            )
            .map((u) => `${X(u.x).toFixed(1)},${Y(u.z).toFixed(1)}`);
          let cursor = 0;
          for (const point of line.points) {
            const found = recorded.indexOf(point, cursor);
            assert.ok(
              found >= 0,
              `${name}/${arm}/${line.id}: path point ${point} absent/out of order at ${t}`,
            );
            cursor = found + 1;
          }
        }
        checkedPanels++;
      }
    }
    const boxes = await page
      .locator(".suite-panel svg")
      .evaluateAll((els) => els.map((e) => e.getAttribute("viewBox")));
    assert.equal(new Set(boxes).size, 1, "comparison scales differ");
    const screenScales = await page.locator(".suite-panel svg").evaluateAll((els) =>
      els.map((e) => {
        const m = e.getScreenCTM();
        return [Math.hypot(m.a, m.b), Math.hypot(m.c, m.d)];
      }),
    );
    for (const scale of screenScales)
      scale.forEach((value, i) =>
        assert.ok(Math.abs(value - screenScales[0][i]) < 1e-6, "displayed map scales differ"),
      );
    await page.locator('[data-layout="overlay"]').click();
    assert.equal(await page.locator("#suite-big").isVisible(), true);
    assert.equal(await page.locator("#suite-separated").isVisible(), false);
  }
  // Pick a different pair while split, then keep that pair when switching back.
  const multi = data.suite.scenarios.find((name) => data.suite.pictures[name].battles.length > 2);
  assert.ok(multi, "pair-change check needs at least three recorded methods");
  await page.locator(`[data-scenario="${multi}"] .suite-link`).click();
  await page.waitForFunction(
    () => document.getElementById("suite-page").getAttribute("aria-busy") === "false",
  );
  await page.locator('[data-layout="separate"]').click();
  const panelArms = () =>
    page.locator(".suite-panel").evaluateAll((els) => els.map((e) => e.dataset.arm));
  const original = await panelArms();
  const other = page.locator('.suite-pick[aria-pressed="false"]').first();
  await other.click();
  const pair = await panelArms();
  assert.notDeepEqual(pair, original, "pair selection must actually change");
  const selected = await page
    .locator('.suite-pick[aria-pressed="true"]')
    .evaluateAll((els) => els.map((e) => e.parentElement.dataset.arm));
  assert.deepEqual([...pair].sort(), [...selected].sort());
  await page.locator('[data-layout="overlay"]').click();
  const overlay = await page
    .locator(".suite-pair [data-arm]")
    .evaluateAll((els) => els.map((e) => e.dataset.arm));
  assert.deepEqual(overlay, pair);
  await page.locator('[data-layout="separate"]').click();
  assert.deepEqual(await panelArms(), pair);
  assert.match(await page.locator("#suite-plan").innerText(), /possible tactic.*designer/i);
  await page.screenshot({ path: path.join(out, "desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const boxes = await page
    .locator(".suite-panel")
    .evaluateAll((els) =>
      els.map((e) => ({ x: e.getBoundingClientRect().x, y: e.getBoundingClientRect().y })),
    );
  if (boxes.length === 2) {
    assert.equal(boxes[0].x, boxes[1].x);
    assert.ok(boxes[1].y > boxes[0].y);
  }
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(out, "phone.png"), fullPage: true });
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    `PASS: ${checkedPanels} panel/time checks against cited raw records; separate enemies, shared scale, coverage, mode/pair changes, desktop/phone, offline.`,
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
