/* Optional offline browser check. Requires Playwright in NODE_PATH; no app build. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

async function main() {
  const [recorded, demo, output, modelReport, cameraReport] =
    process.argv.slice(2);
  assert(
    recorded && demo && output,
    "Usage: node check_wh3_report_browser.cjs RECORDED.html DEMO.html OUTPUT_DIR [MODEL.html] [CAMERA.html]",
  );
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      offline: true,
      viewport: { width: 1440, height: 1100 },
    });
    const page = await context.newPage(),
      errors = [],
      requests = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("request", (request) => {
      if (/^https?:/.test(request.url())) requests.push(request.url());
    });
    const go = async (file) =>
      page.goto(pathToFileURL(path.resolve(file)).href);
    const saveDownload = async (id, name) => {
      const pending = page.waitForEvent("download");
      await page.locator(id).click();
      const download = await pending,
        target = path.join(output, name);
      await download.saveAs(target);
      assert.equal(await download.failure(), null);
      return target;
    };
    await go(recorded);
    await page.waitForFunction(
      () => !document.getElementById("replay-content").hidden,
    );
    assert.match(
      await page.locator("#replay-verdict").textContent(),
      /gpt-6-sol.*96 logged decisions/s,
    );
    assert.equal(await page.locator("#replay-trial option").count(), 3);
    assert.equal(await page.locator("#replay-multiples article").count(), 3);
    assert.match(
      await page.locator("#replay-inspector").textContent(),
      /Decision 1/,
    );
    assert.equal(
      await page
        .locator("#replay-inspector details")
        .filter({ hasText: "Exact recorded prompt" })
        .getAttribute("open"),
      null,
    );
    await page.locator("#replay-map").focus();
    await page.keyboard.press("ArrowRight");
    assert.match(
      await page.locator("#replay-inspector").textContent(),
      /Decision 2/,
    );
    await page.keyboard.press("ArrowLeft");
    assert.match(
      await page.locator("#replay-inspector").textContent(),
      /Decision 1/,
    );
    await page.keyboard.press("]");
    assert.notEqual(await page.locator("#replay-time").inputValue(), "5.3");
    await page.locator("#replay-play").click();
    assert.equal(await page.locator("#replay-play").textContent(), "Pause");
    await page.locator("#replay-play").click();
    const replayExport = JSON.parse(
      await fs.readFile(
        await saveDownload("#replay-download", "recorded-replay.json"),
        "utf8",
      ),
    );
    assert.equal(replayExport.replay.summary.decisions, 96);
    assert.equal(replayExport.replay.summary.acknowledged_orders, 436);
    assert.equal(replayExport.replay.summary.unacknowledged_orders, 5);
    assert.equal(replayExport.replay.summary.rejections, 29);
    assert.equal(replayExport.evidence_kind, "recorded");
    await page.locator("#replay-trial").selectOption("0");
    await page.waitForFunction(() =>
      document
        .getElementById("replay-verdict")
        .textContent.includes("attack_nearest"),
    );
    assert.match(await page.locator("#replay-verdict").textContent(), /lost/);
    await page.locator("#replay-trial").selectOption("2");
    assert.equal(
      await page.locator("#status").textContent(),
      "Development pilot: one independent launch",
    );
    assert.equal(await page.locator("#controller-table tbody tr").count(), 3);
    assert.equal(await page.locator(".point").count(), 3);
    assert.match(
      await page.locator("#controller-table").textContent(),
      /\$0\.79336/,
    );
    const saved = JSON.parse(
      await fs.readFile(recorded.replace(/\.html$/, ".json"), "utf8"),
    );
    const embedded = JSON.parse(
      await page.locator("#report-data").textContent(),
    );
    assert.deepEqual(
      embedded.report.groups.map((group) => group.controllers),
      saved.groups.map((group) => group.controllers),
    );
    await page.screenshot({
      path: path.join(output, "desktop.png"),
      fullPage: true,
    });
    const point = page.locator(".point").first();
    await point.focus();
    await page.keyboard.press("Enter");
    assert.match(
      await page.locator("#selection").textContent(),
      /order age .* s/,
    );
    await page.locator("#controller-table input").first().uncheck();
    assert.equal(await page.locator(".point").count(), 2);
    const displayed = JSON.parse(
      await fs.readFile(
        await saveDownload("#export-data", "selected.json"),
        "utf8",
      ),
    );
    assert.equal(displayed.groups[0].controllers.length, 2);
    assert.equal(displayed.groups[0].trials.length, 2);
    assert.equal(displayed.all_supplied_jobs.length, 2);
    await page.emulateMedia({ media: "print" });
    assert.equal(
      await page
        .locator('#controller-table tr[data-selected="false"]')
        .isVisible(),
      false,
    );
    await page.pdf({
      path: path.join(output, "selected.pdf"),
      preferCSSPageSize: true,
      printBackground: true,
    });
    await page.emulateMedia({ media: "screen" });
    await page.locator("#select-all").click();
    await page.locator("#controller-table th button").nth(3).click();
    assert.match(
      await page.locator("#controller-table tbody tr").first().textContent(),
      /Walk-nearest/,
    );
    await page.locator("#axis").selectOption("cost");
    assert.equal(await page.locator(".point").count(), 3);
    const svg = await fs.readFile(
      await saveDownload("#export-svg", "chart.svg"),
      "utf8",
    );
    assert.match(svg, /one independent launch/);
    assert.match(svg, /6763d0e/);
    assert.match(svg, /3 valid \/ 3 started/);
    const png = await fs.readFile(
      await saveDownload("#export-png", "chart.png"),
    );
    assert.deepEqual(
      [...png.subarray(0, 8)],
      [137, 80, 78, 71, 13, 10, 26, 10],
    );
    await page.locator("#axis").selectOption("added");
    assert.match(
      await page.locator("#chart").textContent(),
      /Not measured yet/,
    );
    assert.equal(await page.locator("#export-svg").isDisabled(), true);
    await page.locator("#scenario").selectOption("1");
    assert.equal(
      await page.locator("#status").textContent(),
      "Not measured yet",
    );
    assert.equal(await page.locator("#controller-table tbody tr").count(), 0);
    assert.match(
      await page.locator("#jobs").textContent(),
      /KeyboardInterrupt/,
    );
    assert.match(await page.locator("#jobs").textContent(), /0 \/ 0/);
    await page.locator("#scenario").selectOption("2");
    assert.match(
      await page.locator("#metadata-origin").textContent(),
      /Current catalogue/,
    );
    await page.locator("#scenario").selectOption("0");
    await page.locator("#axis").selectOption("age");
    await page.setViewportSize({ width: 390, height: 844 });
    const mapBox = await page.locator("#replay-map").boundingBox();
    const inspectorBox = await page.locator("#replay-inspector").boundingBox();
    assert.ok(
      inspectorBox.y > mapBox.y + mapBox.height,
      "narrow replay stacks map over inspector",
    );
    await page.screenshot({
      path: path.join(output, "narrow.png"),
      fullPage: true,
    });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await page.locator("#axis").focus();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#axis").inputValue(), "cost");
    await go(demo);
    await page.waitForFunction(
      () => !document.getElementById("replay-content").hidden,
    );
    assert.match(
      await page.locator("#replay-availability").textContent(),
      /SYNTHETIC DEMO/,
    );
    const syntheticReplay = JSON.parse(
      await fs.readFile(
        await saveDownload("#replay-download", "synthetic-replay.json"),
        "utf8",
      ),
    );
    assert.equal(syntheticReplay.evidence_kind, "synthetic");
    assert.equal(syntheticReplay.replay.evidence_kind, "synthetic");
    await page.setViewportSize({ width: 1440, height: 1100 });
    assert.match(
      await page.locator("#dataset-banner").textContent(),
      /SYNTHETIC DEMO/,
    );
    assert.equal(await page.locator("#controller-table tbody tr").count(), 9);
    assert.equal(await page.locator("#scenario option").count(), 1);
    assert.match(
      await page.locator("#controller-table").textContent(),
      /CI unavailable/,
    );
    assert.match(
      await page.locator("#trial-table").textContent(),
      /time_limit \(engine won\)/,
    );
    await page.locator("#axis").selectOption("added");
    assert.equal(await page.locator(".point").count(), 17);
    assert.match(await page.locator("#chart").textContent(), /0 s.*6 s.*10 s/s);
    assert.match(
      await page.locator("#tactical-table").textContent(),
      /demo-infantry/,
    );
    await page.screenshot({
      path: path.join(output, "demo-latency.png"),
      fullPage: true,
    });
    const demoSVG = await fs.readFile(
      await saveDownload("#export-svg", "demo.svg"),
      "utf8",
    );
    assert.match(demoSVG, /SYNTHETIC DEMO/);
    const demoJSON = JSON.parse(
      await fs.readFile(
        await saveDownload("#export-data", "demo.json"),
        "utf8",
      ),
    );
    assert.equal(demoJSON.evidence_kind, "synthetic");
    assert.equal(demoJSON.groups.length, 3);
    for (const group of demoJSON.groups)
      for (const pair of group.paired) {
        assert.equal(pair.a.split(" / ")[0], pair.b.split(" / ")[0]);
      }
    for (const checkbox of await page.locator("#controller-table input").all())
      await checkbox.uncheck();
    assert.equal(await page.locator(".point").count(), 0);
    assert.equal(await page.locator("#export-svg").isDisabled(), true);
    if (modelReport) {
      await go(modelReport);
      await page.waitForFunction(
        () => document.querySelectorAll("#replay-stills img").length > 0,
      );
      const model = JSON.parse(
        await fs.readFile(
          await saveDownload("#replay-download", "model-replay.json"),
          "utf8",
        ),
      ).replay;
      assert.equal(model.recorder_version, 1);
      assert.ok(model.frames.length > model.decisions.length);
      assert.ok(
        model.roster.some((unit) => unit.name_source === "unit_names.json"),
      );
      assert.ok(model.stills.some((shot) => shot.image));
      assert.ok(model.stills.every((shot) => shot.policy_input === false));
      assert.ok(
        await page
          .locator("#replay-stills img")
          .evaluateAll((images) =>
            images.every((image) => image.naturalWidth > 0),
          ),
      );
      await page.locator("#replay-stills").screenshot({
        path: path.join(output, "model-stills.png"),
      });
      await page.locator("#replay-section").screenshot({
        path: path.join(output, "model-replay.png"),
      });
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
      );
      await page.screenshot({
        path: path.join(output, "model-narrow.png"),
        fullPage: true,
      });
    }
    if (cameraReport) {
      await page.setViewportSize({ width: 1440, height: 1100 });
      await go(cameraReport);
      await page.waitForFunction(
        () => document.querySelectorAll("#replay-stills img").length >= 2,
      );
      assert.match(
        await page.locator("#replay-verdict").textContent(),
        /truncated/,
      );
      assert.match(
        await page.locator("#replay-stills").textContent(),
        /Capture deferred to maintain 30 s spacing/,
      );
      assert.ok(
        await page
          .locator("#replay-stills img")
          .evaluateAll((images) =>
            images.every((image) => image.naturalWidth > 0),
          ),
      );
      await page.locator("#replay-stills").screenshot({
        path: path.join(output, "close-camera.png"),
      });
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
      );
    }
    assert.deepEqual(requests, []);
    assert.deepEqual(errors, []);
    console.log(
      "Offline browser checks passed: values, selection, sorting, keyboard, narrow layout, SVG/PNG/JSON, print, placeholders, synthetic latency and evidence separation.",
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
