/* Proposed offline ownership check; no game/model calls.
   NODE_PATH=~/.cache/wh3-playwright/node_modules node THIS REPORT.html OUTPUT_DIR
   Requires companion REPORT.json and raw trace paths. Reference: recorded partitions,
   owner's request for unit-to-agent indicators, and report redesign guide's stable labels. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const file = path.resolve(process.argv[2]),
    out = path.resolve(process.argv[3]);
  fs.mkdirSync(out, { recursive: true });
  const html = fs.readFileSync(file, "utf8");
  const data = JSON.parse(html.match(/<script id="report-data"[^>]*>([\s\S]*?)<\/script>/)[1]);
  const rows = JSON.parse(fs.readFileSync(file.replace(/\.html$/, ".json"), "utf8")).rows;
  const ids = { front: 1, ranged: 2, mobile: 3 };
  const names = { front: "Infantry", ranged: "Guns", mobile: "Knights" };
  const whole = {
    single: ["M", "One model"],
    tips: ["M+", "One model"],
    commander: ["C", "One model, through scripts"],
    skills: ["S", "Scripts"],
  };
  const expected = (arm, owner) =>
    whole[arm] || [
      { team: "T", gap: "R" }[arm] + ids[owner],
      `${names[owner]} ${arm === "gap" ? "rules" : "model"}`,
    ];
  const owners = {};
  for (const [name, scene] of Object.entries(data.suite.pictures)) {
    owners[name] = {};
    for (const battle of scene.battles) {
      const matches = rows.filter(
        (r) =>
          r.scenario === name && r.arm === battle.arm && path.basename(r.output) === battle.output,
      );
      assert.equal(matches.length, 1);
      const trace = fs.readFileSync(
        path.join(matches[0].output, "episode-0000", "trace.jsonl"),
        "utf8",
      );
      const event = trace
        .split("\n")
        .filter(Boolean)
        .map(JSON.parse)
        .find((e) => e.kind === "team" && e.event === "partition");
      owners[name][battle.arm] = event
        ? Object.fromEntries(
            Object.entries(event.ownership).flatMap(([member, units]) =>
              [units].flat().map((id) => [id, member]),
            ),
          )
        : {};
      assert.deepEqual(
        battle.owners,
        owners[name][battle.arm],
        "embedded ownership differs from raw partition",
      );
    }
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, offline: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const ready = () =>
    page.waitForFunction(
      () => document.getElementById("suite-page").getAttribute("aria-busy") === "false",
    );
  const seek = (t) =>
    page.locator("#suite-time").evaluate((e, t) => {
      e.value = t;
      e.dispatchEvent(new Event("input", { bubbles: true }));
    }, t);
  const noOverlap = async (locator) => {
    const boxes = await locator.evaluateAll((es) =>
      es.map((e) => {
        const b = e.getBoundingClientRect();
        return { id: e.dataset.ownerUnit, x: b.x, y: b.y, r: b.right, b: b.bottom };
      }),
    );
    for (let i = 0; i < boxes.length; i++)
      for (let j = 0; j < i; j++) {
        const a = boxes[i],
          b = boxes[j];
        assert.ok(
          a.r <= b.x || b.r <= a.x || a.b <= b.y || b.b <= a.y,
          `owner tags overlap: ${a.id}/${b.id}`,
        );
      }
  };
  const teamAndRules = async () => {
    for (const arm of await page
      .locator('.suite-pick[aria-pressed="true"]')
      .evaluateAll((es) => es.map((e) => e.parentElement.dataset.arm)))
      if (!["team", "gap"].includes(arm))
        await page.locator(`.suite-tile[data-arm="${arm}"] .suite-pick`).click();
    for (const arm of ["team", "gap"])
      if (
        (await page
          .locator(`.suite-tile[data-arm="${arm}"] .suite-pick`)
          .getAttribute("aria-pressed")) === "false"
      )
        await page.locator(`.suite-tile[data-arm="${arm}"] .suite-pick`).click();
  };
  await page.goto(pathToFileURL(file).href);
  await ready();
  await seek(6);
  assert.ok(
    await page.locator("#suite-big .suite-owner-tag").count(),
    "visible units need owner tags",
  );
  let battlesChecked = 0,
    ownerSelections = 0;
  // JUDGEMENT?: Owner display coverage — Codex, 2026-11-04: each saved method at 6 and
  // 90 seconds, all owner selectors, plus both layouts/Watch. Exhaustive times cover more;
  // these are proposed display checks, not agreed verification or a reader study.
  for (const [name, scene] of Object.entries(data.suite.pictures)) {
    await page.locator(`[data-scenario="${name}"] .suite-link`).click();
    await ready();
    await page.locator('[data-layout="separate"]').click();
    for (const battle of scene.battles) {
      const arm = battle.arm,
        pick = page.locator(`.suite-tile[data-arm="${arm}"] .suite-pick`);
      if ((await pick.getAttribute("aria-pressed")) === "false") await pick.click();
      const panel = page.locator(`.suite-panel[data-arm="${arm}"]`);
      const ownerOf = (id) => (whole[arm] ? "all" : owners[name][arm][id]);
      for (const t of [6, 90]) {
        await seek(t);
        const marks = await panel.locator("svg [data-unit]:not(polyline)").evaluateAll((es) =>
          es.map((e) => ({
            id: e.dataset.unit,
            owner: e.dataset.owner,
            title: e.querySelector("title")?.textContent,
          })),
        );
        const tags = await panel.locator(".suite-owner-tag").evaluateAll((es) =>
          es.map((e) => ({
            id: e.dataset.ownerUnit,
            owner: e.dataset.owner,
            text: e.textContent,
            font: parseFloat(e.getAttribute("font-size")) * e.getScreenCTM().a,
          })),
        );
        assert.deepEqual(
          tags.map((t) => t.id),
          marks.map((m) => m.id),
          `${name}/${arm}: every unit needs its own tag`,
        );
        await noOverlap(panel.locator(".suite-owner-tag"));
        const links = await panel.locator("[data-owner-link]").evaluateAll((es) =>
          es.map((line) => {
            const id = line.dataset.ownerLink;
            const mark = line.parentElement.querySelector(`[data-unit="${id}"]:not(polyline)`);
            let x, y;
            if (mark.tagName === "circle") {
              x = Number(mark.getAttribute("cx"));
              y = Number(mark.getAttribute("cy"));
            } else if (mark.tagName === "rect") {
              x = Number(mark.getAttribute("x")) + Number(mark.getAttribute("width")) / 2;
              y = Number(mark.getAttribute("y")) + Number(mark.getAttribute("height")) / 2;
            } else {
              [x, y] = mark
                .getAttribute("d")
                .match(/^M([\d.e+-]+) ([\d.e+-]+)/)
                .slice(1)
                .map(Number);
              y += 8.05;
            }
            return {
              id,
              x,
              y,
              x1: Number(line.getAttribute("x1")),
              y1: Number(line.getAttribute("y1")),
            };
          }),
        );
        assert.deepEqual(
          links.map((l) => l.id),
          marks.map((m) => m.id),
        );
        for (const link of links)
          assert.ok(
            Math.abs(link.x - link.x1) < 1e-6 && Math.abs(link.y - link.y1) < 1e-6,
            `wrong tag leader: ${link.id}`,
          );
        for (const [i, mark] of marks.entries()) {
          const owner = ownerOf(mark.id),
            [tag, label] = expected(arm, owner);
          assert.equal(mark.owner, owner);
          assert.equal(tags[i].owner, owner);
          assert.equal(tags[i].text, tag);
          assert.ok(mark.title.includes(`${tag}: ${label}`));
          assert.ok(Math.abs(tags[i].font - 11) < 0.1, "tag text shrank with map");
        }
      }
      const baseline = await panel
        .locator("svg [data-unit]")
        .evaluateAll((es) =>
          es.map((e) => ({ id: e.dataset.unit, opacity: Number(e.getAttribute("opacity")) })),
        );
      for (const chip of await panel.locator(".suite-owner").all()) {
        const member = await chip.getAttribute("data-owner"),
          [tag, label] = expected(arm, member);
        assert.equal(await chip.textContent(), `${tag}${label}`);
        await chip.click();
        assert.equal(await chip.getAttribute("aria-pressed"), "true");
        const focused = await panel
          .locator("svg [data-unit]")
          .evaluateAll((es) =>
            es.map((e) => ({ id: e.dataset.unit, opacity: Number(e.getAttribute("opacity")) })),
          );
        focused.forEach((m, i) =>
          assert.equal(
            m.opacity === baseline[i].opacity,
            ownerOf(m.id) === member,
            `${name}/${arm}/${m.id}: wrong highlighted owner`,
          ),
        );
        const labels = await panel
          .locator(".suite-owner-tag")
          .evaluateAll((es) => es.map((e) => e.dataset.owner));
        assert.ok(labels.every((x) => x === member));
        await chip.click();
        assert.equal(await chip.getAttribute("aria-pressed"), "false");
        ownerSelections++;
      }
      // Watch must name the same owner after switching from another method.
      await page.locator(`.suite-tile[data-arm="${arm}"] .suite-watch`).click();
      await page.waitForFunction(
        (output) => document.getElementById("suite-legend").dataset.output === output,
        battle.output,
      );
      const unit = page.locator('#map .unit[data-unit^="f"]').first();
      await unit.waitFor();
      const id = await unit.getAttribute("data-unit");
      await unit.click({ force: true });
      const [tag, label] = expected(arm, ownerOf(id));
      await page.locator(".unit-owner").waitFor();
      assert.equal(await page.locator(".unit-owner").innerText(), `Controller: ${tag} · ${label}`);
      await page.locator(".suite-close").click();
      battlesChecked++;
    }
  }
  // An overlay with identical starting positions still identifies both controllers.
  await page.locator('[data-scenario="coord-two-fronts"] .suite-link').click();
  await ready();
  await teamAndRules();
  await page.locator('[data-layout="overlay"]').click();
  await seek(6);
  const tagBox = (arm) =>
    page.locator(`#suite-big [data-arm="${arm}"] [data-owner-unit="f1"]`).boundingBox();
  const a = await tagBox("team"),
    b = await tagBox("gap");
  assert.ok(a.y + a.height <= b.y || b.y + b.height <= a.y, "coincident methods' tags overlap");
  await noOverlap(page.locator("#suite-big .suite-owner-tag"));
  await page.locator('#suite-pair .suite-owner[data-owner-arm="team"]').first().click();
  const otherTags = await page.locator('#suite-big [data-arm="gap"] .suite-owner-tag').count();
  const otherOpacity = await page
    .locator('#suite-big [data-arm="gap"] [data-unit]:not(polyline)')
    .evaluateAll((es) => es.map((e) => Number(e.getAttribute("opacity"))));
  assert.equal(otherTags, 0, "another method's owners were highlighted");
  assert.ok(
    otherOpacity.length && otherOpacity.every((n) => n <= 0.12),
    "focus leaked into another method",
  );
  const allTagged = async () =>
    assert.equal(
      await page.locator("#suite-big .suite-owner-tag").count(),
      await page.locator("#suite-big [data-unit]:not(polyline)").count(),
      "stale owner focus hid tags after changing the comparison",
    );
  await page.locator('.suite-tile[data-arm="skills"] .suite-pick').click();
  await allTagged();
  await teamAndRules();
  await page.locator('#suite-pair .suite-owner[data-owner-arm="team"]').first().click();
  await page.locator('[data-scenario="coord-pincer"] .suite-link').click();
  await ready();
  await allTagged();
  assert.equal(
    await page.locator('.suite-owner[aria-pressed="true"]').count(),
    0,
    "stale owner selection after scene change",
  );
  await teamAndRules();
  await page.locator('[data-layout="separate"]').click();
  await seek(90);
  await page.locator(".suite-stage").screenshot({ path: path.join(out, "desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".suite-stage").screenshot({ path: path.join(out, "phone.png") });
  for (const panel of await page.locator(".suite-panel").all())
    await noOverlap(panel.locator(".suite-owner-tag"));
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  const fonts = await page
    .locator("#suite-separated .suite-owner-tag")
    .evaluateAll((es) =>
      es.map((e) => parseFloat(e.getAttribute("font-size")) * e.getScreenCTM().a),
    );
  assert.ok(fonts.length && fonts.every((n) => Math.abs(n - 11) < 0.1), "phone tags are too small");
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    `PASS: ${battlesChecked} battles, ${ownerSelections} owner selections; raw partitions, tags, focus, Watch, overlap, phone/offline.`,
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
