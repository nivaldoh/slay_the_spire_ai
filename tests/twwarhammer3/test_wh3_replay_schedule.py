"""The fixed-schedule foil on a battle recorded through the play loop; no live game.

The recording and the replay both run through play.play_episode with FakeMailbox, so the
schedule is read from the trace format play writes. The replay launch numbers both armies'
units differently from the recording, as a fresh launch may.
"""

import json
from functools import partial

import pytest
from wh3_fixtures import CONFIG, FakeMailbox

from twwarhammer3.battle import play
from twwarhammer3.battle.replay_schedule import ReplaySchedule, build, carried_out, digest
from twwarhammer3.protocol import HIDDEN_KEYS, PolicyFailure, refused, validate_orders

SWORDS, KNIGHTS = "wh_main_emp_inf_swordsmen", "wh_main_emp_cav_empire_knights"
BOYZ, ARRERS = "wh_main_grn_inf_orc_boyz", "wh_main_grn_inf_orc_arrer_boyz"
SCENARIO = {"name": "siege-a", "map": "siege map", "battle_type": "siege",
            "player": {"units": [SWORDS, SWORDS, KNIGHTS]},
            "enemy": {"units": [BOYZ, BOYZ, ARRERS]}}
START_MS = 5200


def unit(identity, kind, x, z):
    return {"id": identity, "type": kind, "class": "infantry", "x": x, "z": z, "men": 90,
            "men0": 90, "hp": 1.0, "state": []}


def mover(time_ms, start, end):
    """A unit walking from ``start`` at START_MS to ``end`` at 20200 ms, then standing."""
    share = min(max((time_ms - START_MS) / 15000, 0), 1)
    return tuple(a + (b - a) * share for a, b in zip(start, end))


def recorded_armies(time_ms):
    # e2 walks from beside e1 to the west: its first and last positions pick different Boyz.
    # f1 walks to beside f2's start: pairing from a later position would give it this f2.
    return ([unit("f1", SWORDS, *mover(time_ms, (0, -100), (60, -60))),
             unit("f2", SWORDS, 40, -100), unit("f3", KNIGHTS, 100, -120)],
            [unit("e1", BOYZ, 70, 110), unit("e2", BOYZ, *mover(time_ms, (60, 100), (10, 60))),
             unit("e3", ARRERS, 120, 140)])


def relaunched_armies(time_ms):
    """The same battle in a launch that numbered both armies in another order."""
    return ([unit("f1", KNIGHTS, 100, -120), unit("f2", SWORDS, 40, -100),
             unit("f3", SWORDS, 0, -100)],
            [unit("e1", BOYZ, *mover(time_ms, (62, 100), (12, 58))), unit("e2", ARRERS, 120, 140),
             unit("e3", BOYZ, 70, 110)])


def frame(seq, time_ms, armies, result=None):
    friendly, enemy = armies
    return {"schema": 1, "job": "job", "battle": "b1", "seq": seq, "phase": "Deployed",
            "time_ms": time_ms, "speed": 1, "awaiting_orders": False, "remaining_ms": 900000,
            "armies": {"player": {"faction": "emp"}, "enemy": {"faction": "grn"}},
            "friendly": friendly, "enemy": enemy,
            "enemy_roster": [{"id": row["id"], "type": row["type"]} for row in enemy],
            "mode": {"type": "siege", "role": "defender"}, "orders": None, "result": result,
            "ack": True, "final": {"friendly": {}, "enemy": {}} if result else None}


def frames(armies, step_ms, end_ms=40000):
    times = range(START_MS, end_ms, step_ms)
    rows = [{**frame(0, 0, armies(0)), "phase": "Deployment"}]
    rows += [frame(seq, time_ms, armies(time_ms)) for seq, time_ms in enumerate(times, 1)]
    return rows + [frame(len(rows), end_ms, armies(end_ms), result="won")]


def move(identity, x, z):
    return {"unit": identity, "type": "move", "x": x, "z": z, "run": True}


def attack(identity, target):
    return {"unit": identity, "type": "attack", "target": target, "run": True}


class Witness:
    """The recorded winner: each batch of PLAN at the first decision at or after its time."""

    PLAN = ((START_MS, [move("f1", 60, -60), move("f3", 150, 0)]),
            (20000, [attack("f1", "e2"), attack("f3", "e3")]),
            (30000, [move("f2", 40, 0), move("f3", 999, 999)]),
            (35000, [attack("f1", "e1")]))

    def __init__(self):
        self.left = list(self.PLAN)

    def decide(self, observation):
        orders = []
        while self.left and self.left[0][0] <= observation["time_ms"]:
            orders += self.left.pop(0)[1]
        return orders

    def acknowledge(self, ack, latency):
        pass

    def metadata(self):
        return {"type": "witness"}


class RockMailbox(FakeMailbox):
    """The engine refuses a move to (999, 999) as unreachable, as a move into rock is."""

    def wait_observation(self, *, battle, after_seq, timeout):
        orders = self.pending[1] if self.pending else []
        item = super().wait_observation(battle=battle, after_seq=after_seq, timeout=timeout)
        for result in (item.get("orders") or {}).get("results", []):
            if orders[result["index"] - 1].get("x") == 999:
                result.update(ok=False, error="unreachable")
        return item


def record(tmp_path, cell=None, end_ms=40000):
    """The witness's won episode, played at ``cell`` (play's delay_ms and interval_ms)."""
    config = {**CONFIG, "interval_ms": 0, **(cell or {}), "policy": "witness",
              "scenario": SCENARIO["name"]}
    job = tmp_path / "witness-job"
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "config": config, "scenario": SCENARIO, "source_revision": "r1"}))
    result = play.play_episode(job / "episode-0000", config, Witness,
                               RockMailbox(frames(recorded_armies, 1000, end_ms)), not_battle=None)
    assert result["status"] == "won"
    return job / "episode-0000"


def applied(episode):
    """When the engine applied each batch with orders, from a trace's acknowledgements."""
    rows = [json.loads(line) for line in (episode / "trace.jsonl").open()]
    return [row["ack"]["applied_ms"] for row in rows
            if row["kind"] == "ack" and row["ack"]["results"]]


@pytest.mark.parametrize("step_ms", (300, 1100))
def test_a_relaunch_gets_the_wins_accepted_orders_at_their_battle_times_on_its_own_units(
        tmp_path, step_ms):
    schedule = build(record(tmp_path))
    replay = frames(relaunched_armies, step_ms)
    mailbox = FakeMailbox(replay)
    result = play.play_episode(tmp_path / "replay", {**CONFIG, "interval_ms": 0,
                                                     "policy": "replay_schedule"},
                               partial(ReplaySchedule, schedule, scenario=SCENARIO), mailbox,
                               not_battle=None)
    times = {row["seq"]: row["time_ms"] for row in replay}
    sent = [(times[seq], orders) for _, seq, orders in mailbox.requests if orders]

    def first_at(ms):  # the first decision at or after the engine applied the recorded batch
        return min(time_ms for time_ms in times.values() if time_ms >= ms)

    # Recorded f1, f2, f3 start where f3, f2, f1 start here. The Boyz e2 attacked was last seen
    # at (10, 60), where this launch's e1 walks to. The Boyz e1 stands at (70, 110), as e3 does
    # here, and by 35 s this launch's e1, a Boyz too, is nearer the attacker (f3 here). The
    # Arrer Boyz are e2 here. The move into rock was refused in the win, so it is not replayed.
    assert sent == [(first_at(5700), [move("f3", 60, -60), move("f1", 150, 0)]),
                    (first_at(20700), [attack("f3", "e1"), attack("f1", "e2")]),
                    (first_at(30700), [move("f2", 40, 0)]),
                    (first_at(35700), [attack("f3", "e3")])]
    assert result["status"] == "won" and result["invalid"] == 0
    rows = [json.loads(line) for line in (tmp_path / "replay/trace.jsonl").open()]
    summary = [{key: value for key, value in row.items() if key != "elapsed"}
               for row in rows if row.get("event") == "replay_schedule"]
    assert summary == [{"kind": "team", "event": "replay_schedule", "due": 6, "unanswered": 0,
                        "sent": 6, "accepted": 6, "unmatched": 0, "bind_max_m": 0.0,
                        "carried_out": True}]


def test_under_added_age_the_foil_applies_each_batch_that_age_after_the_witness_did(tmp_path):
    cell = {"delay_ms": 5000, "interval_ms": 5000}  # the set's shared model-like cell
    episode = record(tmp_path, cell, end_ms=60000)
    schedule, witness = build(episode), applied(episode)
    assert witness == [10700, 28700, 40700]  # the batches of 30 s and 35 s went together
    assert [batch["time_ms"] for batch in schedule["batches"]] == witness
    assert (schedule["source"]["delay_ms"], schedule["source"]["interval_ms"]) == (5000, 5000)
    play.play_episode(tmp_path / "replay", {**CONFIG, **cell, "policy": "replay_schedule"},
                      partial(ReplaySchedule, schedule, scenario=SCENARIO),
                      FakeMailbox(frames(relaunched_armies, 1000, 60000)), not_battle=None)
    # The foil decides on 5 s old observations 5 s after each acknowledgement, so its bases fall
    # at 5.2, 11.2, 17.2 ... s. Its first basis at or after each witness time is 0.5 s later, and
    # the engine applies that batch 5.5 s after it: 5 s of age and the fake 0.5 s to apply.
    assert applied(tmp_path / "replay") == [time_ms + 6000 for time_ms in witness]


def test_a_schedule_is_refused_under_another_scenario_declaration_or_from_a_battle_not_won(
        tmp_path):
    episode = record(tmp_path)
    schedule = build(episode)
    ReplaySchedule(schedule, scenario=json.loads(json.dumps(SCENARIO)))  # the same declaration
    other = {**SCENARIO, "enemy": {"units": [BOYZ, BOYZ, BOYZ]}}
    with pytest.raises(ValueError, match="another scenario"):
        ReplaySchedule(schedule, scenario=other)
    result = json.loads((episode / "result.json").read_text())
    (episode / "result.json").write_text(json.dumps({**result, "status": "lost"}))
    with pytest.raises(ValueError, match="won battle"):
        build(episode)


def schedule_of(*batches):
    """A schedule by hand: (time_ms, orders) batches for the recorded armies at START_MS."""
    friendly, _ = recorded_armies(START_MS)
    return {"version": 1, "scenario_sha256": digest(SCENARIO), "source": {},
            "start": {row["id"]: {key: row[key] for key in ("type", "x", "z")} for row in friendly},
            "batches": [{"time_ms": time_ms, "request": f"r{index}", "orders": entries}
                        for index, (time_ms, entries) in enumerate(batches, 1)]}


def view(time_ms, armies=recorded_armies):
    observation = frame(1, time_ms, armies(time_ms))
    return {key: value for key, value in observation.items() if key not in HIDDEN_KEYS}


def test_due_batches_join_one_decision_unless_they_order_a_unit_twice():
    policy = ReplaySchedule(schedule_of(
        (5700, [{"order": move("f1", 0, 0)}]), (6000, [{"order": move("f2", 40, 0)}]),
        (6300, [{"order": move("f1", 0, 50)}]), (6400, [{"order": move("f3", 150, 0)}])),
        scenario=SCENARIO)
    late = view(6500)  # a slow first decision: all four batches are due
    first = policy.decide(late)
    validate_orders(first, late)
    assert first == [move("f1", 0, 0), move("f2", 40, 0)]
    # f1's second move waits a decision, and so does the batch after it, keeping their order.
    assert policy.decide(view(6800)) == [move("f1", 0, 50), move("f3", 150, 0)]
    assert policy.decide(view(7100)) == []


def test_an_order_without_a_matching_target_or_unit_is_dropped_and_counts_against():
    target = {"type": ARRERS, "x": 120, "z": 140}
    policy = ReplaySchedule(schedule_of(
        (5700, [{"order": attack("f1", "e3"), "target": target}, {"order": move("f2", 40, 0)},
                {"order": move("f4", 0, 0)}])), scenario=SCENARIO)
    assert policy.decide(view(START_MS)) == []  # own units are paired here, before f4 arrives
    friendly, enemy = recorded_armies(6000)
    later = frame(2, 6000, (friendly + [unit("f4", KNIGHTS, 0, -300)],
                            [row for row in enemy if row["type"] != ARRERS]))
    # The attack is not redirected to the Boyz in sight; this launch's f4, a reinforcement, is
    # not the recorded one.
    assert policy.decide(later) == [move("f2", 40, 0)]
    policy.acknowledge({"results": [{"index": 1, "unit": "f2", "ok": True}]}, {})
    policy.close()
    assert policy.drain_events() == [{"event": "replay_schedule", "due": 3, "unanswered": 0,
                                      "sent": 1, "accepted": 1, "unmatched": 2,
                                      "bind_max_m": 0.0, "carried_out": False}]


def test_carried_out_counts_accepted_orders_against_those_due_when_the_battle_ended():
    assert carried_out(9, 10) and not carried_out(8, 10)
    assert not carried_out(0, 0)  # a foil that never gave its play did not carry it out
    batches = [(5700 + 1000 * index, [{"order": move("f1", 0, index)}]) for index in range(25)]
    policy = ReplaySchedule(schedule_of(*batches), scenario=SCENARIO)
    assert policy.decide(view(START_MS)) == []  # own units are paired at their starts
    for time_ms in range(6000, 26000, 1000):  # 20 decisions, one batch due at each
        orders = policy.decide(view(time_ms))
        assert len(orders) == 1
        if time_ms == 9000:  # play voided the batch: the engine never saw it
            policy.acknowledge(refused(orders, "illegal"), {})
        else:  # the engine answers, and at 12 s it refuses the order
            policy.acknowledge({"results": [{"index": 1, "unit": "f1", "ok": time_ms != 12000}]},
                               {})
    # The battle ends before the engine answers the 21st decision, as play then calls only close.
    assert len(policy.decide(view(26000))) == 1
    policy.close()
    # Of the 20 due orders that play or the engine answered, the engine accepted 18: 90%.
    assert policy.drain_events() == [{"event": "replay_schedule", "due": 21, "unanswered": 1,
                                      "sent": 19, "accepted": 18, "unmatched": 0,
                                      "bind_max_m": 0.0, "carried_out": True}]


def test_the_own_army_must_match_the_recorded_one_by_type():
    policy = ReplaySchedule(schedule_of((5700, [{"order": move("f1", 0, 0)}])), scenario=SCENARIO)
    friendly, enemy = recorded_armies(START_MS)
    friendly.append(unit("f4", SWORDS, 80, -100))  # one more than recorded; pairing would work
    with pytest.raises(PolicyFailure, match="differ") as failure:
        policy.decide(frame(1, START_MS, (friendly, enemy)))
    assert failure.value.__cause__ is not None  # ends the episode; not a forfeit that waits


class Public(dict):
    """An observation that fails the test when a hidden key is read."""

    def __getitem__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in HIDDEN_KEYS, key
        return super().get(key, default)


def test_it_reads_no_hidden_key():
    entries = [{"order": attack("f1", "e2"), "target": {"type": BOYZ, "x": 10, "z": 60}}]
    friendly, enemy = recorded_armies(6000)
    hidden = Public(view(6000), evaluation={"enemy": {"men": 1}}, final={"result": "won"},
                    native={"id": 1}, setup={"deployment_reading": {"friendly": friendly,
                                                                    "enemy": enemy}})
    policy = ReplaySchedule(schedule_of((5700, entries)), scenario=SCENARIO)
    assert policy.decide(hidden) == [attack("f1", "e2")]


def rewrite(episode, change):
    """Apply ``change`` to every row of a recorded episode's trace."""
    path = episode / "trace.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(change(row)) + "\n" for row in rows))


@pytest.mark.parametrize("which", [slice(None), slice(1, None)], ids=["all", "all-but-first"])
def test_a_trace_whose_acknowledgements_number_no_order_is_refused(tmp_path, which):
    """Older traces' acknowledgements carry no order index. Wrong versions (2026-11-13 refusal
    sweep and review): without the refusal the first accepted order fails as a KeyError, and a
    refusal only when no result is numbered lets a partly numbered acknowledgement through."""
    episode = record(tmp_path)

    def unnumbered(row):
        for item in (row.get("ack") or {}).get("results", [])[which]:
            item.pop("index", None)
        return row

    rewrite(episode, unnumbered)
    with pytest.raises(ValueError, match="acknowledgements without order indices"):
        build(episode)


def test_a_trace_with_no_own_unit_in_any_observation_is_refused(tmp_path):
    """Wrong version (2026-11-13 refusal sweep): without the refusal the schedule is written
    with no starting places, so a replay could pair no unit."""
    episode = record(tmp_path)

    def unarmed(row):
        if row["kind"] == "observation":
            row["observation"]["friendly"] = []
        return row

    rewrite(episode, unarmed)
    with pytest.raises(ValueError, match="no observation with own units"):
        build(episode)


@pytest.mark.parametrize("key", ["type", "x", "z"])
def test_an_own_unit_without_type_or_place_at_the_first_view_ends_the_replay(key):
    """Wrong version (2026-11-13 refusal sweep): without the refusal an untyped unit reads as a
    different roster and an unplaced one is paired silently, at an infinite distance."""
    policy = ReplaySchedule(schedule_of((5700, [{"order": move("f1", 0, 0)}])), scenario=SCENARIO)
    friendly, enemy = recorded_armies(START_MS)
    friendly[0][key] = None
    with pytest.raises(PolicyFailure, match="typed and placed") as failure:
        policy.decide(frame(1, START_MS, (friendly, enemy)))
    assert failure.value.__cause__ is not None  # ends the episode, as a roster mismatch does


@pytest.mark.parametrize("version", [2, None])
def test_a_schedule_of_another_or_no_version_is_refused(version):
    """Wrong versions (2026-11-13 refusal sweep and review): without the refusal a version 2
    schedule is replayed as if it were version 1, and an unversioned one if the check defaults
    a missing version to 1."""
    schedule = schedule_of((5700, [{"order": move("f1", 0, 0)}]))
    if version is None:
        del schedule["version"]
    else:
        schedule["version"] = version
    with pytest.raises(ValueError, match=f"replay schedule version {version!r}, not 1"):
        ReplaySchedule(schedule, scenario=SCENARIO)
