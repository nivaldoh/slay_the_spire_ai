"""Three helpers on public unit records that witnesses and readings both use: the units still in
the fight, a direction and a centre. They were in calibration.py until 2026-11-15. A readings
module may import this module and never a witness module (tests/test_repo_rules.py). OUT comes
from skills.py, so a reading that uses ``_active`` still loads that controller file and llm.py.
"""

import math

from twwarhammer3.battle.skills import OUT


def _active(units) -> list[dict]:
    return [unit for unit in units if unit.get("men") and unit.get("x") is not None
            and unit.get("z") is not None and not OUT.intersection(unit.get("state", []))]


def _direction(origin: dict, target: dict) -> tuple[float, float]:
    dx, dz = target["x"] - origin["x"], target["z"] - origin["z"]
    length = math.hypot(dx, dz)
    return (dx / length, dz / length) if length else (0, 1)


def _centre(units: list[dict]) -> dict:
    return {axis: sum(unit[axis] for unit in units) / len(units) for axis in ("x", "z")}
