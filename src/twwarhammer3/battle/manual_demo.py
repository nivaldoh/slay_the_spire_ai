"""Record an owner-played support timing attempt, separate from automatic play/scoring.

The existing single-player-compatible observer borrows controllers only for authored
setup and releases them. The owner starts deployment and may pause; this driver never
sends battle orders or speed changes. Video and Windows samples retain pause/stall
ambiguity for independent labels. No result here establishes automatic-interface feasibility.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

from gameai import windows
from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from twwarhammer3.battle.capture import copy_recording
from twwarhammer3.battle.play import SOURCES, engine_ending, start_frontend
from twwarhammer3.battle.setup import (
    check_battle,
    check_menu,
    expected_mode,
    scenario_steps,
    scenarios,
    validate_declaration,
)
from twwarhammer3.battle.support_timing import SCENARIO
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.engine.runtime import BRIDGE_DIR, OwnedGame, RuntimeLock, prepare_runtime
from twwarhammer3.protocol import ProtocolError


def windows_name(path):
    if windows.NATIVE:
        return str(path.resolve())
    return subprocess.check_output(["wslpath", "-w", str(path.resolve())], text=True).strip()


def settings(scenario):
    # observe is supported in single-player; it takes no lasting friendly controllers,
    # drops battle orders, leaves speed alone, and disables checkpoint injection/UI actions.
    return {"enabled": True, "menu": True, "autostart": False, "multiplayer": "observe",
            "observe_ms": 1000, "tick_ms": 250, "record_replay": True, "stills": False,
            "benchmark": "behaviour-defaults", "deployment": scenario["deployment"]}


def record(output, ffmpeg, timeout):
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    scenario = scenarios()[SCENARIO]
    config = {"attach": False, "skip_menu": False, "episode_timeout": 1320, "start_timeout": 900,
              "run_timeout": timeout, "episodes": 1}
    validate_declaration(scenario, config)
    revision = committed_revision("recording a manual demonstration", SOURCES)
    environment = collect_diagnostics()
    steps = scenario_steps(scenario, build_id=environment.get("game", {}).get("steam_build_id"))
    output.mkdir(parents=True)
    manifest = {"kind": "manual_demonstration", "scenario": scenario, "source_revision": revision,
                "source_files": source_fingerprints(SOURCES), "environment": environment,
                "session": settings(scenario), "status": "starting", "pause_intervals": None,
                "pause_status": "unknown; label the video, never infer pause from a stalled clock",
                "automatic_interface_feasibility": "unverified"}
    write_json(output / "manifest.json", manifest)
    capture = None
    observation = None
    activated = False
    try:
        with RuntimeLock():
            manifest["deployment"] = prepare_runtime()
            mailbox = Mailbox(BRIDGE_DIR, job=output.name)
            mailbox.reset()
            activated = True
            with (mailbox.owned_session(settings(scenario)),
                  OwnedGame(output / "game.log", timeout=timeout) as game):
                manifest["game"] = game.info
                script = Path(__file__).resolve().parents[1] / "engine/manual_capture.py"
                command = [str(windows.WINDOWS_PYTHON), windows_name(script),
                           "--bridge", windows.windows_path(BRIDGE_DIR),
                           "--output", windows_name(output),
                           "--ffmpeg", ffmpeg, "--pid", str(game.info["pid"]),
                           "--job", output.name, "--timeout", str(timeout)]
                with (output / "capture-process.log").open("x") as log:
                    capture = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        ready_deadline = time.monotonic() + 60
                        while not (output / "capture-ready.json").exists():
                            if capture.poll() is not None or time.monotonic() > ready_deadline:
                                raise RuntimeError("video did not become ready; "
                                                   "see capture-process.log")
                            time.sleep(.2)
                        start_frontend(mailbox, config, output, steps)
                        manifest["menu_checks"] = check_menu(scenario, output)
                        write_json(output / "manifest.json", manifest)
                        print("Recording. Owner: start battle, wait for setup readback, then play.",
                              flush=True)
                        last = None
                        while capture.poll() is None:
                            observation = mailbox.read_observation()
                            if (not observation
                                    or (observation["battle"], observation["seq"]) == last):
                                time.sleep(.2)
                                continue
                            last = (observation["battle"], observation["seq"])
                            write_json(output / "last-observation.json", observation)
                            if observation["battle"] != manifest.setdefault(
                                    "battle", observation["battle"]):
                                raise ProtocolError("manual attempt restarted; retain evidence")
                            if observation.get("result") in ("won", "lost", "draw"):
                                manifest["engine_ending"] = engine_ending(observation)
                                write_json(output / "ending.json", observation)
                            if not observation.get("friendly"):
                                continue
                            if "setup_checks" not in manifest:
                                manifest["initial_observation"] = observation
                                write_json(output / "initial-observation.json", observation)
                                manifest["setup_checks"] = check_battle(scenario, observation)
                                for key, value in expected_mode(scenario).items():
                                    if observation.get("mode", {}).get(key) != value:
                                        raise ProtocolError(f"manual setup: wrong {key}")
                                if observation.get("speed") != 1:
                                    raise ProtocolError("manual setup must start at 1x")
                                manifest["status"] = "recording"
                                write_json(output / "manifest.json", manifest)
                                print("Setup readback passed. Owner may play and pause.",
                                      flush=True)
                            if observation.get("speed") not in (0, 1):
                                raise ProtocolError("manual play requires 1x or an owner pause")
                            if source_fingerprints(SOURCES) != manifest["source_files"]:
                                raise RuntimeError("source changed during manual attempt")
                            if observation.get("result") in ("won", "lost", "draw"):
                                manifest["status"] = "engine_ended"
                                # Give the independent Windows reader time to retain the ending.
                                time.sleep(.5)
                                break
                        else:
                            raise RuntimeError("capture stopped before an engine ending")
                    finally:
                        (output / "stop-capture").touch()
                        try:
                            capture.wait(timeout=20)
                        except subprocess.TimeoutExpired:
                            capture.kill()
                            capture.wait()
                            manifest["capture_error"] = "recorder required termination"
                if (output / "capture-result.json").exists():
                    manifest["capture"] = json.loads((output / "capture-result.json").read_text())
                    if manifest["capture"].get("status") != "stopped":
                        manifest["status"] = "capture_failure"
                else:
                    manifest["status"] = "capture_failure"
    except BaseException as exc:
        manifest.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failure",
                        error=str(exc))
        raise
    finally:
        # Preserve evidence even when setup, capture or the owner aborts the attempt.
        if activated:
            manifest["recording"] = copy_recording(BRIDGE_DIR, output, job=output.name,
                                                   battle=manifest.get("battle"))
            for name in ("menu.log", "mod.log"):
                source = BRIDGE_DIR / name
                if source.exists():
                    (output / name).write_bytes(source.read_bytes())
        write_json(output / "manifest.json", manifest)
    return manifest


def label_pauses(directory, labels_path):
    """Attach independent video labels without rewriting the original attempt."""
    labels = json.loads(labels_path.read_text())
    if (not labels.get("reviewer") or labels.get("complete") is not True
            or labels.get("video_sha256") != sha256(directory / "video.mkv")):
        raise ValueError("pause labels need reviewer, complete=true and matching video_sha256")
    progress = (directory / "video-progress.txt").read_text().splitlines()
    times = [int(line.split("=", 1)[1]) / 1e6 for line in progress
             if line.startswith("out_time_us=")]
    if not times or max(times) <= 0:
        raise ValueError("video duration unavailable")
    previous = 0
    for interval in labels["intervals"]:
        start, end = interval["start_s"], interval["end_s"]
        if not (0 <= previous <= start < end <= max(times)) or not interval.get("evidence"):
            raise ValueError("invalid/overlapping pause interval or missing video evidence")
        previous = end
    with (directory / "pause-labels.json").open("x") as file:
        json.dump({**labels, "source_sha256": sha256(labels_path),
                   "basis": "independent video PTS labels; no automatic pause inference"},
                  file, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("record")
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--ffmpeg", required=True, help="Windows FFmpeg executable with gfxcapture")
    run.add_argument("--timeout", required=True, type=float, help="Windows watchdog seconds")
    label = commands.add_parser("label-pauses")
    label.add_argument("directory", type=Path)
    label.add_argument("labels", type=Path)
    args = parser.parse_args()
    if args.command == "label-pauses":
        label_pauses(args.directory, args.labels)
        return 0
    result = record(args.output.resolve(), args.ffmpeg, args.timeout)
    return 0 if result["status"] == "engine_ended" else 1


if __name__ == "__main__":
    raise SystemExit(main())
