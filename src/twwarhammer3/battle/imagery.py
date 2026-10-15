"""Presentation image conversion, after gameplay. Pillow is an optional report extra."""

import base64
import io
import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from gameai.provenance import write_json
from gameai.windows import WINDOWS_PYTHON, windows_path

MAX_STILL_BYTES = 256 * 1024


def imagery_settings(config: dict) -> dict:
    return {"version": 3, "enabled": bool(config.get("stills")), "policy_input": False,
            "backend": "passive_windows_pillow",
            "max_stills": 4, "projection": "unregistered_grid_and_stills"}


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
                if observation.get("job") != self.job or not re.fullmatch(r"[\w.-]+", battle):
                    continue
                record = json.loads((self.bridge / f"imagery-{battle}.json").read_text())
                if record.get("job") != self.job or record.get("battle") != battle:
                    continue
                for shot in record.get("stills", []):
                    trigger = shot.get("trigger")
                    if trigger not in {"opening", "approach", "incoming_fire",
                                       "first_contact", "first_rout", "ending"}:
                        continue
                    key = (battle, trigger)
                    if key in seen or shot.get("status") != "capture_ready":
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
                    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                        captured = {"status": "capture_failed", "error": str(exc)}
                    write_json(self.bridge / f"capture-{battle}-{trigger}.json",
                               {**captured, "job": self.job, "battle": battle, "trigger": trigger})
            except (OSError, ValueError):
                # The Lua writer removes then renames; retry incomplete mailbox reads.
                continue


def copy_presentation(bridge: Path, episode: Path, *, job: str, battle: str | None) -> dict:
    """Copy this battle's presentation sidecar after its order loop has ended."""
    if not battle or not re.fullmatch(r"[\w.-]+", battle, flags=re.ASCII):
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


def webp(path: Path, *, max_size: tuple[int, int] = (1600, 1000)) -> dict:
    from PIL import Image

    with Image.open(path) as source:
        original_size = source.size
        image = source.convert("RGB")
        image.thumbnail(max_size)
        while True:
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=78, method=6)
            if buffer.tell() <= MAX_STILL_BYTES:
                break
            image.thumbnail((max(1, image.width * 4 // 5), max(1, image.height * 4 // 5)))
    return {"image": "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "original_size": list(original_size), "size": list(image.size),
            "bytes": len(buffer.getvalue())}


def stills(episode: Path, entries: list[dict], *, embed: bool) -> list[dict]:
    """Retain failed captures and metadata, even when only featured images are embedded."""
    output = []
    for entry in entries:
        item = {**entry, "policy_input": False}
        filename = entry.get("file")
        if filename and embed:
            # Capture manifests name local files, never arbitrary report-host paths.
            if Path(filename).name != filename:
                item.update(status="error", error="Invalid still filename")
            else:
                try:
                    item.update(webp(episode / filename), status="embedded")
                except (OSError, ValueError, ImportError) as exc:
                    item.update(status="error", error=f"{type(exc).__name__}: cannot convert "
                                f"{filename}; Pillow is available in the report extra")
        elif filename:
            item["status"] = "metadata_only_nonfeatured_trial"
        output.append(item)
    return output
