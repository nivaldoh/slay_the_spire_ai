"""Record an owner-played attempt at a scenario, separate from automatic play/scoring.

Support timing by default; ``--scenario`` names another. The existing
single-player-compatible observer borrows controllers only for authored
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
from twwarhammer3.battle.capture import copy_private_record, copy_recording
from twwarhammer3.battle.play import SOURCES, battle_session, engine_ending, start_frontend
from twwarhammer3.battle.reserve import check as check_reserve
from twwarhammer3.battle.reserve import materialize
from twwarhammer3.battle.setup import (
    check_battle,
    check_job,
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

# The mod runs neither under the observer session: setup_reserve asserts no multiplayer mode for
# reserve versions 1-2 and load() goes inactive on custom. A session without them would record a
# different battle. A waves reserve (version 3) runs there, and the first observation checks it.
# JUDGEMENT: Observer holds waves — Claude, 2026-11-08 (siege defence design, recorder support):
# the observer session now keeps a waves scenario's held enemy groups under script control. Refusing
# waves leaves this battle no owner demonstration; deciding check 10 (human win) rests on it.
OBSERVER_REFUSES = ("reserve", "custom")


def refused(scenario):
    """The fields of ``scenario`` the observer session cannot run."""
    return [key for key in OBSERVER_REFUSES if scenario.get(key)
            and not (key == "reserve" and scenario[key].get("kind") == "waves")]


def windows_name(path):
    if windows.NATIVE:
        return str(path.resolve())
    return subprocess.check_output(["wslpath", "-w", str(path.resolve())], text=True).strip()


def settings(scenario):
    # observe is supported in single-player; it takes no lasting friendly controllers,
    # drops battle orders, leaves speed alone, and disables checkpoint injection/UI actions.
    # A waves scenario's held enemy groups are the one lasting enemy control it keeps.
    waves = (scenario.get("reserve") or {}).get("kind") == "waves"
    return {"enabled": True, "menu": True, "autostart": False, "multiplayer": "observe",
            "observe_ms": 1000, "tick_ms": 250, "record_replay": True, "stills": False,
            **battle_session(scenario), **({"reserve": materialize(scenario)} if waves else {})}


def record(output, ffmpeg, timeout, name=None):
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    name = name or SCENARIO
    scenario = scenarios()[name]
    for key in refused(scenario):
        raise ValueError(f"{name} cannot be recorded: the mod refuses {key} under the observer"
                         " session, and a session without it is a different battle")
    check_job(scenario, output.name)
    # JUDGEMENT?: Recorder needs expect — Claude, 2026-11-05: no `expect` means a refusal here.
    # Skipping its checks, as play does, would keep videos of a setup nothing read back;
    # which owner demonstrations can exist rests on this.
    if not scenario.get("expect"):
        raise ValueError(f"{name} cannot be recorded: it declares no expect, so its setup cannot"
                         " be checked")
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
    observation = latest = None
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
                            latest = observation
                            if "setup_checks" not in manifest:
                                manifest["initial_observation"] = observation
                                write_json(output / "initial-observation.json", observation)
                                manifest["setup_checks"] = check_battle(scenario, observation)
                                if scenario.get("reserve"):
                                    # A hold the mod skipped or bound wrongly ends the attempt.
                                    manifest["reserve"] = check_reserve(scenario, observation)
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
        if "reserve" in manifest and latest is not None:
            # Releases come after the first observation's check: the last observation's evidence
            # is checked too, and a refusal is kept beside the attempt, which it does not end.
            try:
                manifest["reserve_final"] = check_reserve(scenario, latest)
            except ProtocolError as exc:
                manifest["reserve_final"] = {"error": str(exc)}
        if activated:
            manifest["recording"] = copy_recording(BRIDGE_DIR, output, job=output.name,
                                                   battle=manifest.get("battle"))
            if scenario.get("private_record"):
                manifest["private_record"] = copy_private_record(
                    BRIDGE_DIR, output, job=output.name, battle=manifest.get("battle"))
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
    run.add_argument("--scenario", help=f"scenario to record (default {SCENARIO})")
    run.add_argument("--ffmpeg", required=True, help="Windows FFmpeg executable with gfxcapture")
    run.add_argument("--timeout", required=True, type=float, help="Windows watchdog seconds")
    label = commands.add_parser("label-pauses")
    label.add_argument("directory", type=Path)
    label.add_argument("labels", type=Path)
    args = parser.parse_args()
    if args.command == "label-pauses":
        label_pauses(args.directory, args.labels)
        return 0
    result = record(args.output.resolve(), args.ffmpeg, args.timeout, args.scenario)
    return 0 if result["status"] == "engine_ended" else 1


if __name__ == "__main__":
    raise SystemExit(main())
