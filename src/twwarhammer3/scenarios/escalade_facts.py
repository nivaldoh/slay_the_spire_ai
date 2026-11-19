"""What the siege attack's witness and its readings both use (ksl-emp-siege-a-v1): the fort's
front line and what counts as inside it. escalade.py and escalade_readings.py import these; the
readings never import the witness (tests/test_repo_rules.py; owner, 2026-11-15).
"""

import math

# JUDGEMENT?: Front line — Claude, 2026-11-08: the southernmost fortification centre in each 40 m
# column of x, a unit 10 m north of it inside. No battle has read the pieces; phase 3, phase 4
# and the entry-route reading rest on it, and the fort's real pieces may need another rule.
FRONT_COLUMN_M = 40
INSIDE_M = 10


def front_line(fortifications):
    """The front of the fort, west to east: the southernmost fortification centre in each
    FRONT_COLUMN_M column of x (gates, wall pieces and towers alike)."""
    columns = {}
    for piece in fortifications:
        column = math.floor(piece["x"] / FRONT_COLUMN_M)
        if column not in columns or piece["z"] < columns[column][1]:
            columns[column] = (piece["x"], piece["z"])
    return [columns[column] for column in sorted(columns)]


def inside(line, unit):
    """INSIDE_M or more north of ``line`` at the unit's x (its ends held flat beyond it)."""
    x = min(max(unit["x"], line[0][0]), line[-1][0])
    for (ax, az), (bx, bz) in zip(line, line[1:]):
        if ax <= x <= bx and bx > ax:
            return unit["z"] >= az + (bz - az) * (x - ax) / (bx - ax) + INSIDE_M
    return unit["z"] >= line[0][1] + INSIDE_M  # a single column, or x on a vertical step
