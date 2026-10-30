"""The offline peer comparison (battle/peers.py) on synthetic observations that each client's
worker sends through the real coordinator over loopback (engine/link.py), so the evidence
files have the coordinator's own layout. Positions and identities are made up; nothing here
says how real peers' observations line up."""

import math

import pytest

from twwarhammer3.battle.peers import compare
from twwarhammer3.engine.link import Coordinator, WorkerLink, token_sha256

HALBERDIERS, HANDGUNNERS = "wh_main_emp_inf_halberdiers", "wh_main_emp_inf_handgunners"


def attempt(tmp_path, sent: dict) -> dict:
    """The summary of an attempt whose clients' workers sent these observation lists."""
    manifest = {"match": "m1", "attempt": "a1", "expected": {},
                "clients": {client: {"token_sha256": token_sha256(f"token-{client}")}
                            for client in sent}}
    with Coordinator(manifest, tmp_path / "a1", clock=lambda: 0.0) as coordinator:
        for client, observations in sent.items():
            if observations is None:
                continue  # this client's worker never connected
            link = WorkerLink(coordinator.url, f"token-{client}", match="m1", attempt="a1",
                              client=client, manifest={}, stop=lambda: None, clock=lambda: 0.0)
            link.hello()
            for data in observations:
                link.event("observation", data)
            link.beat()
    return compare(tmp_path / "a1")


def unit(alliance, army, index, x, z, type=HALBERDIERS, ui_id=None):
    return {"ui_id": ui_id or f"{alliance}{army}{index}", "type": type, "alliance": alliance,
            "army": army, "index": index, "owner": "own", "x": x, "z": z}


def army(shift=0.0):
    """Two same-type units in army 1 of alliance 1, a different unit beside them, an enemy and
    a reinforcement army's unit; each at its own position."""
    return [unit(1, 1, 1, 100.25 + shift, -40.5), unit(1, 1, 2, 130.75 + shift, -40.5),
            unit(1, 1, 3, 115.0 + shift, -60.125, HANDGUNNERS),
            unit(2, 1, 1, 100.0 - shift, 240.0), unit(2, "r1", 1, -300.0, 300.0 + shift)]


def observation(battle, seq, time_ms, units):
    native = {"mode": "observe", "is_multiplayer": True, "is_spectator": False,
              "local_alliance": 1, "local_army": 1, "army_unique_id": 7, "units": units}
    return {"schema": 1, "job": "mp", "battle": battle, "seq": seq, "phase": "Deployed",
            "time_ms": time_ms, "native": native}


def run(client, times, change=None):
    """A client's observations at these times, the army advancing 2 m a sample; ``change``
    maps a time to its units in place of the default."""
    return [observation(f"battle-{client}", seq, time_ms,
                        (change or {}).get(time_ms, army(2.0 * seq)))
            for seq, time_ms in enumerate(times, 1)]


def counts(pair, *fields):
    return {field: pair[field] for field in fields}


def test_identical_peers_are_exact_at_every_common_time_for_every_pair(tmp_path):
    times = [5200, 6200, 7200]
    summary = attempt(tmp_path, {client: run(client, times) for client in "ABC"})
    assert [pair["clients"] for pair in summary["pairs"]] == [["A", "B"], ["A", "C"], ["B", "C"]]
    for pair in summary["pairs"]:
        assert counts(pair, "common_times", "compared_times", "units_compared", "exact",
                      "position_differences", "type_mismatches", "ui_id_mismatches") == {
            "common_times": 3, "compared_times": 3, "units_compared": 15, "exact": 15,
            "position_differences": 0, "type_mismatches": 0, "ui_id_mismatches": 0}
        assert pair["differences"] == [] and pair["first_difference_ms"] is None
        assert pair["max_dx"] is None and pair["max_dz"] is None
        assert all(not times for times in pair["only"].values())
        assert all(not units for units in pair["missing"].values())
    assert summary["clients"]["B"] == {"battle": "battle-B", "observations": 3,
                                       "repeated_times": 0, "without_native": 0,
                                       "native_errors": 0, "failed_rows": 0}


def test_a_centimetre_or_one_ulp_off_is_a_difference_reported_raw_with_its_first_time_and_max(
        tmp_path):
    near, far = army(2.0 * 2), army(2.0 * 3)
    near[1]["x"] += 0.01
    near[2]["z"] = math.nextafter(near[2]["z"], math.inf)  # any tolerance would hide it
    far[3]["x"] += 1.5
    far[3]["z"] -= 2.5
    summary = attempt(tmp_path, {"A": run("A", [1000, 2000, 3000]),
                                 "B": run("B", [1000, 2000, 3000], {2000: near, 3000: far})})
    pair = summary["pairs"][0]
    dx = near[1]["x"] - army(2.0 * 2)[1]["x"]
    dz = near[2]["z"] - army(2.0 * 2)[2]["z"]
    assert dx != 0 and dz != 0
    assert pair["differences"] == [
        {"time_ms": 2000, "unit": [1, 1, 2], "dx": dx, "dz": 0.0},
        {"time_ms": 2000, "unit": [1, 1, 3], "dx": 0.0, "dz": dz},
        {"time_ms": 3000, "unit": [2, 1, 1], "dx": 1.5, "dz": -2.5}]
    assert counts(pair, "units_compared", "exact", "position_differences") == {
        "units_compared": 15, "exact": 12, "position_differences": 3}
    assert pair["first_difference_ms"] == 2000
    assert pair["max_dx"] == {"value": 1.5, "time_ms": 3000, "unit": [2, 1, 1]}
    assert pair["max_dz"] == {"value": 2.5, "time_ms": 3000, "unit": [2, 1, 1]}


def test_a_time_only_one_client_has_is_unavailable_and_never_matched_to_the_nearest(tmp_path):
    summary = attempt(tmp_path, {"A": run("A", [1000, 2000, 3000]),
                                 "B": run("B", [1000, 2100, 3000])})
    pair = summary["pairs"][0]
    assert pair["only"] == {"A": [2000], "B": [2100]}
    assert counts(pair, "common_times", "compared_times", "units_compared", "exact") == {
        "common_times": 2, "compared_times": 2, "units_compared": 10, "exact": 10}


def test_a_differing_ui_id_or_type_is_reported_and_neither_joins_units(tmp_path):
    renamed = army(2.0)
    renamed[0]["ui_id"], renamed[3]["type"] = "9999", HANDGUNNERS
    summary = attempt(tmp_path, {"A": run("A", [1000]), "B": run("B", [1000], {1000: renamed})})
    pair = summary["pairs"][0]
    assert pair["differences"] == [
        {"time_ms": 1000, "unit": [1, 1, 1], "dx": 0.0, "dz": 0.0, "ui_id": ["111", "9999"]},
        {"time_ms": 1000, "unit": [2, 1, 1], "dx": 0.0, "dz": 0.0,
         "type": [HALBERDIERS, HANDGUNNERS]}]
    assert counts(pair, "units_compared", "exact", "position_differences", "type_mismatches",
                  "ui_id_mismatches") == {"units_compared": 5, "exact": 3,
                                          "position_differences": 0, "type_mismatches": 1,
                                          "ui_id_mismatches": 1}
    assert pair["missing"] == {"A": [], "B": []} and pair["first_difference_ms"] == 1000


def test_two_same_type_units_in_one_army_are_joined_by_index_not_type(tmp_path):
    swapped = army(2.0)
    swapped[0], swapped[1] = swapped[1], swapped[0]  # listed in the other order
    summary = attempt(tmp_path, {"A": run("A", [1000]), "B": run("B", [1000], {1000: swapped})})
    pair = summary["pairs"][0]
    assert counts(pair, "units_compared", "exact") == {"units_compared": 5, "exact": 5}
    assert pair["differences"] == []


def test_a_unit_on_one_side_only_is_missing_there(tmp_path):
    fewer = army(2.0)
    del fewer[4]
    extra = army(2.0 * 2) + [unit(2, 1, 2, 120.0, 240.0)]
    summary = attempt(tmp_path, {"A": run("A", [1000, 2000], {2000: extra}),
                                 "B": run("B", [1000, 2000], {1000: fewer})})
    pair = summary["pairs"][0]
    assert pair["missing"] == {"A": [], "B": [{"time_ms": 1000, "unit": [2, "r1", 1]},
                                              {"time_ms": 2000, "unit": [2, 1, 2]}]}
    assert counts(pair, "units_compared", "exact") == {"units_compared": 9, "exact": 9}


def test_a_second_battle_id_in_one_clients_events_is_refused(tmp_path):
    restarted = run("A", [1000, 2000])
    restarted[1]["battle"] = "battle-A2"
    with pytest.raises(ValueError, match=r"client A's events hold more than one battle id "
                                         r"\(battle-A, battle-A2\)"):
        attempt(tmp_path, {"A": restarted, "B": run("B", [1000, 2000])})


def test_a_time_with_two_different_observations_of_one_client_is_repeated_not_compared(
        tmp_path):
    # As the Lua's finish() does: the terminal observation at the regular one's battle time.
    sent_a = run("A", [1000, 2000, 3000])
    sent_a.append({**observation("battle-A", 4, 3000, army(2.0 * 3)),
                   "phase": "VictoryCountdown"})
    summary = attempt(tmp_path, {"A": sent_a, "B": run("B", [1000, 2000, 3000])})
    assert counts(summary["clients"]["A"], "observations", "repeated_times") == {
        "observations": 4, "repeated_times": 1}
    pair = summary["pairs"][0]
    assert pair["repeated"] == {"A": [3000], "B": []}
    assert pair["only"] == {"A": [], "B": []}
    assert counts(pair, "common_times", "compared_times", "units_compared", "exact") == {
        "common_times": 3, "compared_times": 2, "units_compared": 10, "exact": 10}
    resent = run("A", [1000])
    summary = attempt(tmp_path / "again", {"A": resent * 2, "B": run("B", [1000])})
    assert counts(summary["clients"]["A"], "observations", "repeated_times") == {
        "observations": 1, "repeated_times": 0}
    assert summary["pairs"][0]["exact"] == 5


def test_missing_native_failed_reads_and_an_absent_client_are_counted(tmp_path):
    loading = {"schema": 1, "job": "mp", "battle": "battle-A", "seq": 0, "phase": "Loading",
               "time_ms": 0, "friendly": [], "enemy_roster": [], "enemy": []}
    failed = army(2.0 * 2)
    failed[1] = {"alliance": 1, "army": 1, "index": 2, "error": "unique_ui_id: no unit"}
    sent_a = run("A", [1000, 2000, 3000], {2000: failed})
    sent_a[2]["native"]["errors"] = ["units: alliances failed"]
    sent_a[2]["native"]["units"] = []
    sent_b = [observation("battle-B", 0, 0, army()), *run("B", [1000, 2000, 3000])]
    summary = attempt(tmp_path, {"A": [loading, *sent_a], "B": sent_b, "C": None})
    assert summary["clients"]["A"] == {"battle": "battle-A", "observations": 4,
                                       "repeated_times": 0, "without_native": 1,
                                       "native_errors": 1, "failed_rows": 1}
    assert summary["clients"]["C"]["observations"] == 0
    pair = summary["pairs"][0]
    assert counts(pair, "common_times", "compared_times", "units_compared", "exact") == {
        "common_times": 4, "compared_times": 3, "units_compared": 9, "exact": 9}
    assert pair["failed_rows"] == {"A": 1, "B": 0}
    assert pair["missing"]["B"] == [] and len(pair["missing"]["A"]) == 5  # all of 3000's
    assert summary["pairs"][1]["only"] == {"A": [0, 1000, 2000, 3000], "C": []}


def test_a_failed_reinforcement_row_without_alliance_is_not_also_missing(tmp_path):
    # The Lua reads a reinforcement unit's alliance inside the guarded call, so its error row
    # can lack one; "r1" names the reinforcement army across alliances.
    failed = army(2.0)
    failed[1] = {"alliance": 1, "army": 1, "index": 2, "error": "position: no unit"}
    failed[4] = {"army": "r1", "index": 1, "error": "is_valid_target: no unit"}
    extra = army(2.0) + [unit(2, 1, 2, 120.0, 240.0)]  # army 1 index 2, but of alliance 2
    summary = attempt(tmp_path, {"A": run("A", [1000], {1000: failed}),
                                 "B": run("B", [1000], {1000: extra})})
    pair = summary["pairs"][0]
    assert pair["failed_rows"] == {"A": 2, "B": 0}
    assert pair["missing"] == {"A": [{"time_ms": 1000, "unit": [2, 1, 2]}], "B": []}
    assert counts(pair, "units_compared", "exact") == {"units_compared": 3, "exact": 3}
