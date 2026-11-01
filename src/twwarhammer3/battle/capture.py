"""Optional presentation evidence captured beside a battle: replay frames and game stills.

Never on the order path: stills are taken by a thread independent of the policy loop, and
both copies run after an episode's order loop has ended. Nothing here is policy input.
"""

import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from gameai.provenance import write_json
from gameai.windows import WINDOWS_PYTHON, windows_path

RECORDER_VERSION = 1
# Battle ids and still triggers become bridge file names.
NAME = re.compile(r"[\w.-]+", re.ASCII)


# JUDGEMENT?: Recorder in scored battles — assistant, 2026-10-15 (flagged by Claude, 2026-10-28):
# the 1 Hz recorder is on by default on one scripted off/on pair, which integration.md says does
# not establish an exact overhead; every manifest copies the label. Off is the alternative.
def recording_settings(config: dict) -> dict:
    return {"version": RECORDER_VERSION, "enabled": bool(config.get("record_replay")),
            "interval_ms": 1000, "cost_validation": "scripted_off_on_20261015"}


def imagery_settings(config: dict) -> dict:
    return {"version": 3, "enabled": bool(config.get("stills")), "policy_input": False,
            "backend": "passive_windows_pillow",
            "max_stills": 4, "projection": "unregistered_grid_and_stills"}


def copy_recording(bridge: Path, episode: Path, *, job: str, battle: str | None) -> dict:
    if not battle or not NAME.fullmatch(battle):
        return {"status": "missing_battle_id"}
    source = bridge / f"replay-{battle}.jsonl"
    if not source.exists():
        return {"status": "missing", "file": source.name}
    try:
        # Keep a byte-for-byte copy, including a partial final line on interruption.
        # A battle-specific name prevents a rematch from overwriting these bytes.
        with source.open("rb") as handle:
            header = json.loads(handle.readline())
        if header.get("job") != job or header.get("battle") != battle:
            return {"status": "identity_mismatch", "file": source.name}
        shutil.copyfile(source, episode / "replay.jsonl")
        return {"status": "copied", "file": "replay.jsonl", "version": header.get("recorder"),
                "bytes": (episode / "replay.jsonl").stat().st_size}
    except (OSError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}


class PassiveCapture:
    """Handle presentation requests in a thread independent of the policy/order loop."""

    def __init__(self, bridge: Path, *, job: str, pid: int, enabled: bool):
        self.bridge, self.job, self.pid, self.enabled = bridge, job, pid, enabled
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def __enter__(self):
        if self.enabled:
            self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        if self.enabled:
            self.thread.join(timeout=7)

    def run(self):
        seen = set()
        while not self.stop.wait(.1):
            try:
                observation = json.loads((self.bridge / "observation.json").read_text())
                battle = observation.get("battle", "")
                if observation.get("job") != self.job or not NAME.fullmatch(battle):
                    continue
                record = json.loads((self.bridge / f"imagery-{battle}.json").read_text())
                if record.get("job") != self.job or record.get("battle") != battle:
                    continue
                for shot in record.get("stills", []):
                    trigger = shot.get("trigger") or ""
                    key = (battle, trigger)
                    if (not NAME.fullmatch(trigger) or key in seen
                            or shot.get("status") != "capture_ready"):
                        continue
                    seen.add(key)
                    output = self.bridge / f"still-{battle}-{trigger}.png"
                    try:
                        process = subprocess.run([
                            str(WINDOWS_PYTHON),
                            windows_path(self.bridge.parent / "windows_capture.py"),
                            str(self.pid), windows_path(output),
                            windows_path(self.bridge / "observation.json"), self.job, battle,
                        ], capture_output=True, text=True, timeout=6)
                        captured = json.loads(process.stdout)
                        if not isinstance(captured, dict):
                            captured = {"status": "capture_failed",
                                        "error": "Capture output must be a JSON object"}
                    except Exception as exc:
                        captured = {"status": "capture_failed",
                                    "error": f"{type(exc).__name__}: {exc}"}
                    write_json(self.bridge / f"capture-{battle}-{trigger}.json",
                               {**captured, "job": self.job, "battle": battle, "trigger": trigger})
            except (OSError, ValueError):
                # The Lua writer removes then renames; retry incomplete mailbox reads.
                continue


def copy_presentation(bridge: Path, episode: Path, *, job: str, battle: str | None) -> dict:
    """Copy this battle's presentation sidecar after its order loop has ended."""
    if not battle or not NAME.fullmatch(battle):
        return {"status": "missing_battle_id"}
    path = bridge / f"imagery-{battle}.json"
    try:
        # Only after the episode: allow the terminal camera callback to finish.
        # This never waits between a policy decision and its order submission.
        deadline = time.monotonic() + 2
        while True:
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.05)
                continue
            if record.get("job") != job or record.get("battle") != battle:
                return {"status": "identity_mismatch"}
            pending = False
            for shot in record.get("stills", []):
                if shot.get("status") == "capture_ready":
                    captured_path = bridge / f"capture-{battle}-{shot['trigger']}.json"
                    if captured_path.exists():
                        captured = json.loads(captured_path.read_text())
                        if captured.get("job") == job and captured.get("battle") == battle:
                            shot.update(captured)
                pending = pending or shot.get("status") in {"pending", "capture_ready"}
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(.05)
        write_json(episode / "imagery.json", record)
        write_json(episode / "unit_names.json", record.get("names", {}))
        shots = []
        for entry in record.get("stills", []):
            shot = {**entry, "policy_input": False}
            if shot.get("status") in {"pending", "capture_ready"}:
                shot.update(status="capture_failed", error="Capture callback did not finish")
            filename = shot.get("file")
            if filename:
                # The one check of still names: the report later reads them from the episode.
                if Path(filename).name != filename or not filename.startswith(f"still-{battle}-"):
                    shot.update(status="capture_failed", error="Invalid capture filename")
                    shot.pop("file", None)
                else:
                    try:
                        shutil.copyfile(bridge / filename, episode / filename)
                        shot["bytes"] = (episode / filename).stat().st_size
                    except OSError as exc:
                        shot.update(status="capture_failed", error=str(exc))
                        shot.pop("file", None)
            shots.append(shot)
        write_json(episode / "stills.json", shots)
        return {"status": "copied", "stills": len(shots), "names": len(record.get("names", {}))}
    except (OSError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
