"""Presentation image conversion, after gameplay. Pillow is an optional report extra."""

import base64
import io
import json
import re
import shutil
import time
from pathlib import Path

from gameai.provenance import write_json

MAX_STILL_BYTES = 256 * 1024


def imagery_settings(config: dict) -> dict:
    return {"version": 1, "enabled": bool(config.get("stills")), "policy_input": False,
            "max_stills": 4, "projection": "unregistered_grid_and_stills"}


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
            pending = any(shot.get("status") == "pending" for shot in record.get("stills", []))
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(.05)
        write_json(episode / "imagery.json", record)
        write_json(episode / "unit_names.json", record.get("names", {}))
        shots = []
        for entry in record.get("stills", []):
            shot = {**entry, "policy_input": False}
            if shot.get("status") == "pending":
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
