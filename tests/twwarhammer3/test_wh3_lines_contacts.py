"""Draft Alesia contact readings on synthetic private records, never a live-game check.

Reference: lines-eval.md Measurements (two of four living units, first melee positions),
its declared G/H/L slots, and capture.copy_private_record's boolean melee field.
"""

from copy import deepcopy

import pytest

from twwarhammer3.battle import lines_readings, setup
from twwarhammer3.protocol import ProtocolError


@pytest.fixture(params=("ksl-nor-lines-a-v1", "ksl-nor-lines-b-v1"))
def declaration(request):
    return setup.scenarios()[request.param]


def identity(slot):
    return f"e{13 - slot}"


def initial(declaration):
    reading = {side: [dict(point, id=identity(slot) if side == "enemy" else f"f{slot}")
                      for slot, point in enumerate(points, 1)]
               for side, points in declaration["deployment"].items()}
    for rows in reading.values():
        rows.reverse()
    return {"battle": "battle-one", "setup": {"deployment_reading": reading}}


def frame(declaration, time_ms, melee=(), dead=(), points=None):
    # Every current position has left its start. Binding from the replay instead of the
    # supplied private setup, current x, list order or sorted ids gives different groups.
    rows = []
    for slot, point in enumerate(declaration["deployment"]["enemy"], 1):
        x, z = (points or {}).get(slot, (point["x"] + 500, point["z"] + 500))
        rows.append({"id": identity(slot), "type": point["type"], "x": x, "z": z,
                     "men": 0 if slot in dead else 60, "melee": slot in melee})
    return {"private_record": 1, "battle": "battle-one", "time_ms": time_ms,
            "friendly": [], "enemy": list(reversed(rows))}


def test_contacts_need_simultaneous_living_members_and_keep_first_points(declaration):
    first = initial(declaration)
    frames = [frame(declaration, 0, (1, 5, 12), (5,), {1: (77, -160)}),
              frame(declaration, 1000, (2, 5, 6), (5,)),
              frame(declaration, 2000, (1, 2, 5, 6), (5,)),
              frame(declaration, 3000, (6, 7), (5,)),
              frame(declaration, 4000, (11, 12), (5,)),
              frame(declaration, 5000, (1, 2, 6, 7, 11, 12), (5,), {1: (999, 999)})]
    untouched = deepcopy((frames, first, declaration))
    got = lines_readings.contacts(frames, declaration, first)
    assert got["contact_ms"] == {"G": 2000, "H": 3000, "L": 4000}
    assert got["contact_spread_ms"] == 2000
    assert got["groups"] == {"G": ["e12", "e11", "e10", "e9"],
                             "H": ["e8", "e7", "e6", "e5"],
                             "L": ["e4", "e3", "e2", "e1"]}
    assert got["first_melee"][identity(1)] == {"time_ms": 0, "x": 77, "z": -160}
    assert got["first_melee"][identity(2)]["time_ms"] == 1000
    assert got["first_melee"][identity(5)] is None  # dead melee flag never counts
    assert got["first_melee"][identity(12)]["time_ms"] == 0  # lone Horsemen is not L contact
    assert (frames, first, declaration) == untouched
    got["first_melee"][identity(1)]["x"] = -999
    assert (frames, first, declaration) == untouched


def test_no_contact_and_partial_group_contact_remain_unknown(declaration):
    first = initial(declaration)
    got = lines_readings.contacts([], declaration, first)
    assert got["contact_ms"] == {"G": None, "H": None, "L": None}
    assert got["contact_spread_ms"] is None
    assert len(got["first_melee"]) == 12 and set(got["first_melee"].values()) == {None}
    got = lines_readings.contacts([frame(declaration, 0, (1, 2)),
                                  frame(declaration, 1000, (1, 2))], declaration, first)
    assert got["contact_ms"] == {"G": 0, "H": None, "L": None}
    assert got["contact_spread_ms"] is None


def test_first_melee_records_continue_after_every_group_contacted(declaration):
    frames = [frame(declaration, 1000, (1, 2, 5, 6, 9, 10)),
              frame(declaration, 2000, (3, 7, 11),
                    points={3: (23, -150), 7: (22, -305), 11: (230, -315)})]
    got = lines_readings.contacts(frames, declaration, initial(declaration))
    assert got["contact_ms"] == {"G": 1000, "H": 1000, "L": 1000}
    assert got["contact_spread_ms"] == 0
    assert got["first_melee"][identity(3)] == {"time_ms": 2000, "x": 23, "z": -150}
    assert got["first_melee"][identity(7)] == {"time_ms": 2000, "x": 22, "z": -305}
    assert got["first_melee"][identity(11)] == {"time_ms": 2000, "x": 230, "z": -315}
    assert got["first_melee"][identity(4)] is None


def test_contact_spread_preserves_a_late_group(declaration):
    frames = [frame(declaration, 1000, (5, 6, 9, 10)),
              frame(declaration, 201000, (1, 2))]
    got = lines_readings.contacts(frames, declaration, initial(declaration))
    assert got["contact_ms"] == {"G": 201000, "H": 1000, "L": 1000}
    assert got["contact_spread_ms"] == 200000


def test_missing_melee_coordinates_stay_unknown(declaration):
    sample = frame(declaration, 1000, (1, 2))
    unit = next(row for row in sample["enemy"] if row["id"] == identity(1))
    del unit["x"]
    del unit["z"]
    got = lines_readings.contacts([sample], declaration, initial(declaration))
    assert got["first_melee"][identity(1)] == {"time_ms": 1000, "x": None, "z": None}


@pytest.mark.parametrize("problem", ("unit", "melee", "men", "duplicate", "public", "battle",
                                   "setup", "version", "version_bool", "unreadable", "initial_ids",
                                   "initial_battle", "other_case"))
def test_incomplete_or_foreign_contact_evidence_is_refused(declaration, problem):
    first, sample = initial(declaration), frame(declaration, 1000, (1, 2))
    frames = [sample]
    if problem == "unit":
        sample["enemy"].pop()
    elif problem in ("melee", "men"):
        del sample["enemy"][0][problem]
    elif problem == "duplicate":
        sample["enemy"].append(deepcopy(sample["enemy"][0]))
    elif problem == "public":
        del sample["private_record"]
        for row in sample["enemy"]:
            row["state"] = ["melee"] if row.pop("melee") else []
    elif problem == "battle":
        sample["battle"] = "another-battle"
    elif problem == "version":
        sample["private_record"] = 2
    elif problem == "version_bool":
        sample["private_record"] = True  # session opt-in is not the recorder's numeric format
    elif problem == "unreadable":
        sample["enemy"][0]["melee"] = "false"
    elif problem == "initial_ids":
        rows = first["setup"]["deployment_reading"]["enemy"]
        rows[0]["id"] = rows[1]["id"]
        frames = []
    elif problem == "initial_battle":
        del first["battle"]
        frames = []
    elif problem == "other_case":
        name = "ksl-nor-lines-b-v1" if declaration["name"] == "ksl-nor-lines-a-v1" \
            else "ksl-nor-lines-a-v1"
        first = initial(setup.scenarios()[name])
    else:
        del first["setup"]
    with pytest.raises(ProtocolError):
        lines_readings.contacts(frames, declaration, first)


def test_heavy_side_refuses_a_group_split_between_the_two_sectors(declaration):
    # Existing h_side contract: H occupies one side in the declaration. Removing its refusal
    # would silently choose one of two sides, independent of the new contact reader.
    changed = deepcopy(declaration)
    point = changed["deployment"]["enemy"][4]
    point["x"] = 260 - point["x"]
    with pytest.raises(ValueError, match="H on one side"):
        lines_readings.h_side(changed)
