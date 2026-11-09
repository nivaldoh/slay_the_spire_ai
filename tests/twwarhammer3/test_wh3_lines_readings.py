"""The two-front defence's evaluator readings (battle/lines_readings.py) on made-up records.

Reference: lines-eval.md Measurements and proposed check 2b, and the second look's B1 and A1
(runs/siege-evals-20261108/second-look.json, untracked). The trace rows have the fields play
writes ("decision": seq, time_ms, request, orders; "ack": request, ack). Offline only: these show
what the readers return on made-up records, not what a game writes.
"""

from copy import deepcopy

from test_wh3_lines import A, B, battle

from twwarhammer3.battle import lines, lines_readings, play


def trace(make, observations):
    """Trace rows and public views from a fresh policy deciding on what play.public hands it,
    every order acknowledged as applied 200 ms later."""
    policy, rows, views = make(), [], []
    for request, observation in enumerate(observations, 1):
        view = play.public(deepcopy(observation), {})
        orders = deepcopy(policy.decide(deepcopy(view)))
        ack = {"request": f"r{request}", "based_on": view["seq"],
               "applied_ms": view["time_ms"] + 200,
               "results": [{"index": index, "unit": order["unit"], "ok": True}
                           for index, order in enumerate(orders, 1)]}
        policy.acknowledge(deepcopy(ack), {})
        rows += [{"kind": "decision", "seq": view["seq"], "time_ms": view["time_ms"],
                  "request": ack["request"], "orders": orders},
                 {"kind": "ack", "request": ack["request"], "ack": ack}]
        views.append(view)
    return rows, views


def planted(request, seq, seconds, order, ok=True):
    """A decision row with one order and its ack row, applied 200 ms after its observation."""
    return [{"kind": "decision", "seq": seq, "time_ms": 1000 * seconds, "request": request,
             "orders": [order]},
            {"kind": "ack", "request": request, "ack": {
                "request": request, "based_on": seq, "applied_ms": 1000 * seconds + 200,
                "results": [{"index": 1, "unit": order["unit"], "ok": ok}]}}]


def test_branch_labels_the_side_the_reserve_or_lancers_first_go_to_after_the_cue():
    """From trace rows of each arm's own decisions on test_wh3_lines.py's made-up fights, W reads
    H, M reads L and C neither, in both cases; the cue is the second observation (3 s), from which
    the Fimir and the Horsemen are dropped so that exactly six enemies stand ahead. In case a, an
    accepted move of the Tzar Guard to L's post decided before the cue and a refused one at the
    cue change nothing; an accepted Lancer attack at the cue on an east relief unit reads L, from
    where that unit stood then, though it leaves sight after. Added to C's rows, a Tzar Guard
    attack on a town-side unit and its move behind the inner line, both west, leave neither.
    Wrong versions: a cue that needs seven enemies; an order given before the cue counted; a
    refused order counted; an attack ignored or placed where its target last stood; a town-side
    order counted by its x; H's side fixed rather than read from the declaration."""
    for scenario in (A, B):
        observations = battle(scenario)
        observations[1]["enemy"] = [unit for unit in observations[1]["enemy"]
                                    if unit["id"] not in ("e8", "e12")]
        for arm, label in ((lines.LinesWitness, "H"), (lines.LinesByMen, "L"),
                           (lines.LinesCentral, "neither")):
            rows, views = trace(arm, observations)
            got = lines_readings.branch(rows, views, scenario)
            assert (got["label"], got["trigger_ms"]) == (label, 3000), (scenario["name"], arm)
    rows, views = trace(lines.LinesWitness, battle(A))
    east = {"unit": "f5", "type": "move", "x": 225, "z": -265, "facing": None, "run": True,
            "queue": False}
    ignored = (planted("p1", 1, 1, east) + rows[:2] + planted("p2", 2, 3, east, ok=False)
               + rows[2:])
    got = lines_readings.branch(ignored, views, A)
    assert (got["label"], got["side"], got["unit"], got["applied_ms"]) == ("H", "west", "f4", 3200)
    attack = {"unit": "f6", "type": "attack", "target": "e9", "mode": "melee", "run": True,
              "queue": False}
    gone = [dict(view, enemy=[unit for unit in view["enemy"] if unit["id"] != "e9"])
            for view in views[2:]]
    got = lines_readings.branch(rows[:2] + planted("p3", 2, 3, attack) + rows[2:],
                                views[:2] + gone, A)
    assert (got["label"], got["side"], got["unit"]) == ("L", "east", "f6")
    central = trace(lines.LinesCentral, battle(A))[0]
    town = (planted("p4", 2, 3, dict(attack, unit="f5", target="e2"))
            + planted("p5", 2, 3, dict(east, x=100, z=-175)))
    assert lines_readings.branch(central[:2] + town + central[2:], views, A)["label"] == "neither"


def test_sector_routs_keep_each_unit_in_its_declared_sector_wherever_it_routs():
    """Private frames of the declared army, ids in reverse slot order: the middle regiment (slot
    10, x 130) routs at 2 s; the west end regiment (slot 8) at 3 s; the west sector's Streltsi
    (slot 9, x 60) drift to x 150 and rout at 4 s; the east sector's Streltsi (slot 11, x 200)
    drift to x 110 and rout at 6 s. Wrong versions: a unit's sector read from where it stands
    (x = 130); membership by id order; sectors one slot off; a unit outside both sectors counted
    in the one it stands in."""
    ids = {slot: f"f{13 - slot}" for slot in range(1, 13)}
    moves = {2: {9: {"x": 100}, 10: {"routing": True}}, 3: {9: {"x": 150}, 8: {"routing": True}},
             4: {9: {"routing": True}}, 5: {11: {"x": 110}}, 6: {11: {"routing": True}}}
    frames, places = [], A["deployment"]["friendly"]
    units = {slot: {"id": ids[slot], "type": p["type"], "x": p["x"], "z": p["z"], "men": 60,
                    "routing": False} for slot, p in enumerate(places, 1)}
    for second in range(1, 8):
        for slot, fields in moves.get(second, {}).items():
            units[slot].update(fields)
        frames.append({"private_record": 1, "time_ms": 1000 * second,
                       "friendly": [dict(units[slot]) for slot in sorted(units, reverse=True)],
                       "enemy": []})
    assert lines_readings.sector_routs(frames, A) == {"west": 3000, "east": 6000, "other": 2000}
    assert lines_readings.h_side(A) == "west" and lines_readings.h_side(B) == "east"
