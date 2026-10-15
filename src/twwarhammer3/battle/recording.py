"""Copy optional presentation evidence after an episode; never on the order path."""

import json
import re
import shutil
from pathlib import Path

RECORDER_VERSION = 1


def recording_settings(config: dict) -> dict:
    return {
        "version": RECORDER_VERSION,
        "enabled": bool(config.get("record_replay")),
        "interval_ms": 1000,
        "cost_validation": "pending_live_probe",
    }


def copy_recording(bridge: Path, episode: Path, *, job: str, battle: str | None) -> dict:
    if not battle or not re.fullmatch(r"[\w.-]+", battle, flags=re.ASCII):
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
        return {
            "status": "copied",
            "file": "replay.jsonl",
            "version": header.get("recorder"),
            "bytes": (episode / "replay.jsonl").stat().st_size,
        }
    except (OSError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
