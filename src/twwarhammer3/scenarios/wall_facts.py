"""What the walled siege defence's witness and its readings both use (cth-emp-siege-a-v1): the
reserve's type keys and the public wall line with its distance and inside tests. wall_defence.py
and wall_readings.py import these; the readings never import the witness
(tests/test_repo_rules.py; owner, 2026-11-15).
"""

import math

LORD = "wh3_main_cth_cha_lord_magistrate_0"
JADE = "wh3_main_cth_inf_jade_warriors_0"
RESERVE = (LORD, JADE)

# The wall line and what counts as inside it. The values rest on JUDGEMENT
# src/twwarhammer3/scenarios/wall_defence.py Wall witness thresholds.
WALL_ENDS = ((-384, -81), (384, -81))  # the line's ends, at the side walls' z
WALL_POINTS = ("c6", "c5", "c2", "c4", "c3")  # in x order, west to east
INSIDE_M = 10  # an enemy this far or more north of the wall line is inside


def _segment_distance(x, z, a, b):
    (ax, az), (bx, bz) = a, b
    dx, dz = bx - ax, bz - az
    share = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(x - ax - share * dx, z - az - share * dz)


def wall_line(points):
    """The public wall line, west to east: WALL_ENDS around WALL_POINTS ({id: {"x", "z"}})."""
    return [WALL_ENDS[0], *((points[name]["x"], points[name]["z"]) for name in WALL_POINTS),
            WALL_ENDS[1]]


def wall_distance(line, unit):
    """Metres from ``unit`` to the nearest point of ``line``."""
    return min(_segment_distance(unit["x"], unit["z"], a, b) for a, b in zip(line, line[1:]))


def inside(line, unit):
    """INSIDE_M or more north of ``line`` at the unit's x (its ends held flat beyond it)."""
    x = min(max(unit["x"], line[0][0]), line[-1][0])
    for (ax, az), (bx, bz) in zip(line, line[1:]):
        if ax <= x <= bx:
            return unit["z"] >= az + (bz - az) * (x - ax) / (bx - ax) + INSIDE_M
    return False
