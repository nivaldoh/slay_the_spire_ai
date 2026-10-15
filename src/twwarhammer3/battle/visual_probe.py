"""Owner-requested, scripted visual-report acceptance probes. Never calibration.

Run each case into a new directory; play still requires committed sources and owns
one game at unpaused 1x. The imagery case sends one in-game Lua probe through menu.json,
not desktop input, and records unsupported APIs as failures. Camera projection and
capture cost are questions for the resulting evidence, not assumptions in the report.
"""

import argparse
import json
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gameai.provenance import write_json
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.engine.runtime import BRIDGE_DIR

# API references (Creative Assembly scripting documentation mirror):
# https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_camera.html
# https://chadvandy.github.io/tw_modding_resources/WH3/battle/common.html
LUA = r'''
local output = {kind = "imagery_probe", policy_input = false,
    projection = "unverified",
    visibility = "not audited; may show information hidden from controller"}
local cam = bm:camera()
local prefix = "C:/wh3-agent/bridge/visual-probe-"
local function xyz(v) return {v:get_x(), v:get_y(), v:get_z()} end
output.before = {position = xyz(cam:position()), target = xyz(cam:target())}
local function attempt(name, fn)
    local start = os.clock()
    local ok, result = pcall(fn)
    output[name] = {ok = ok, result = tostring(result), cpu_ms = (os.clock() - start) * 1000}
end
attempt("screenshots_path", function() return common.get_appdata_screenshots_path() end)
local target = cam:target()
local x, z = target:get_x(), target:get_z()
local height = bm.battle:get_terrain_height(x, z)
output.requested = {position = {x, height + 500, z - 0.1}, target = {x, height, z}, fov = 45}
attempt("camera", function()
    cam:move_to(v(x, height + 500, z - 0.1), v(x, height, z), 0, true, 45)
end)
local unit = bm:get_player_army():units():item(1)
output.names = {}
for _, expression in ipairs({"UnitRecordContext.Name", "UnitRecordContext.OnscreenName",
    "UnitRecordContext.LocalisedName", "UnitDetailsContext.Name"}) do
    local ok, value = pcall(common.get_context_value, "CcoBattleUnit",
        tostring(unit:unique_ui_id()), expression)
    output.names[expression] = {ok = ok, value = tostring(value)}
end
bm:callback(function()
    output.time_ms = bm.battle:time_elapsed_ms()
    output.after = {position = xyz(cam:position()), target = xyz(cam:target())}
    attempt("screenshot", function() common.take_screenshot(prefix .. "opening.tga") end)
    output.after_capture_ms = bm.battle:time_elapsed_ms()
    local file = io.open(prefix .. "metadata.json", "w")
    if file then file:write(twwarhammer3_json.encode(output)); file:close() end
end, 500, "wh3_visual_probe")
return "scheduled imagery probe; battle remains unpaused at 1x"
'''


def command(output: Path, case: str) -> list[str]:
    args = [sys.executable, "-m", "twwarhammer3", "play", "--policy", "rush_nearest",
            "--scenario", "kho5-dwf5" if case == "imagery" else "brt-cavalry-emp-assault",
            "--episodes", "1", "--output", str(output),
            "--episode-timeout", "90" if case == "imagery" else "1320",
            "--run-timeout", "1200" if case == "imagery" else "2800"]
    if case != "off":
        args.append("--record-replay")
    else:
        args.append("--no-record-replay")
    return args


def run(output: Path, case: str) -> int:
    if output.exists():
        raise ValueError("probe output must be a new directory")
    sent = False
    samples, previous_seq = [], None
    started = time.monotonic()
    # A native screenshot can block a frame; this probe measures that possibility.
    # The eventual capture path must be chosen from evidence before it is enabled.
    prefix = f"visual-probe-{secrets.token_hex(6)}-"
    process = subprocess.Popen(command(output, case))
    mailbox = Mailbox(BRIDGE_DIR, job=output.name)
    try:
        while process.poll() is None:
            if case == "imagery":
                observation = mailbox.read_observation()
                if observation and observation.get("seq") != previous_seq:
                    previous_seq = observation.get("seq")
                    samples.append({"wall_s": time.monotonic() - started,
                                    "time_ms": observation.get("time_ms"), "seq": previous_seq})
                if observation and observation.get("phase") == "Deployed" and not sent:
                    mailbox.write_menu([{"lua": LUA.replace("visual-probe-", prefix)}])
                    sent = True
            time.sleep(.2)
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    evidence = {"case": case, "returncode": process.returncode, "imagery_sent": sent,
                "calibration": False, "speed": 1, "pause": False}
    if output.exists():
        if case == "imagery":
            (output / "visual-probe-observations.jsonl").write_text(
                "".join(json.dumps(sample) + "\n" for sample in samples))
            for suffix in ("opening.tga", "metadata.json"):
                source = BRIDGE_DIR / (prefix + suffix)
                if source.exists():
                    shutil.copyfile(source, output / ("visual-probe-" + suffix))
            image = output / "visual-probe-opening.tga"
            evidence["screenshot_bytes"] = image.stat().st_size if image.exists() else None
            if image.exists():
                try:
                    from PIL import Image

                    with Image.open(image) as picture:
                        evidence["screenshot_size"] = list(picture.size)
                except (ImportError, OSError) as exc:
                    evidence["image_error"] = str(exc)
        write_json(output / "visual-probe.json", evidence)
    return process.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=("off", "on", "imagery"), required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.case))


if __name__ == "__main__":
    main()
