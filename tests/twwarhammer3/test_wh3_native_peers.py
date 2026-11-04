"""Completed-tick comparison on captures the real probe agent writes.

Reference: the plan's stage 2 rules (every scheduled sample required, missing evidence is
inconclusive, conflicting records fail, no tolerance) and its fault table: missing tick or
participant, conflicting record, changed raw value, duplicate submission. Fixtures come from
multiplayer_probe.js itself. Field comparability between real clients stays uncalibrated.
"""

import json
import sys

import pytest
from test_wh3_multiplayer_probe import agent_check

from twwarhammer3.__main__ import main
from twwarhammer3.battle.peers import compare_captures, load_capture, submission_problems

GENERATE = r'''
load(`
const env = ptr(0x6000000), session = ptr(0x6100000), checks = ptr(0x6200000);
const entry = ptr(0x6300000), world = ptr(0x6600000), table = ptr(0x6700000);
const alliance = ptr(0x6800000), armies = ptr(0x6900000), army = ptr(0x6a00000);
const units = ptr(0x6b00000), unit = ptr(0x6c00000), body = ptr(0x6d00000);
const alliance2 = ptr(0x7500000), armies2 = ptr(0x7600000), army2 = ptr(0x7700000);
const army3 = ptr(0x7800000), units2 = ptr(0x7900000), unit2 = ptr(0x7a00000);
const unit3 = ptr(0x7b00000), unit4 = ptr(0x7c00000);
const entity = ptr(0x6e00000), id = ptr(0x6f00000), model = ptr(0x7200000);
const state = ptr(0x7300000), script = ptr(0x7400000);
pointers.set(session.value, VTABLE.session);
pointers.set(session.add(0x20).value, env.value);
pointers.set(env.add(ENV.checksums).value, checks.value);
pointers.set(checks.add(0x48).value, entry.value);
pointers.set(env.add(ENV.worker_job).value, 0);
pointers.set(env.add(ENV.setup).value, world.value);
pointers.set(env.add(ENV.provider).value, 0x7000000);
// The walk Lua's alliances, armies and units getters make (0x2ec53d0, 0x2dd8f28, 0x2ed0708).
pointers.set(env.add(0x440).value, model.value);
pointers.set(model.add(0x150).value, state.value);
pointers.set(state.add(0x138).value, table.value);
words.set(state.add(0x134).value, 2);
words.set(state.add(0x28).value, 7);
words.set(world.add(0xc8).value, 5);
pointers.set(table.value, alliance.value);
pointers.set(table.add(8).value, alliance2.value);
words.set(alliance2.add(0x34).value, 2);
pointers.set(alliance2.add(0x38).value, armies2.value);
pointers.set(armies2.value, army2.value);
pointers.set(armies2.add(8).value, army3.value);
words.set(army2.add(0x164).value, 2);
pointers.set(army2.add(0x168).value, units2.value);
pointers.set(units2.value, unit2.value);
pointers.set(units2.add(8).value, unit3.value);
words.set(army3.add(0x164).value, 1);
pointers.set(army3.add(0x168).value, units2.add(16).value);
pointers.set(units2.add(16).value, unit4.value);
for (const [other, id] of [[unit2, 78], [unit3, 79], [unit4, 80]]) {
    for (const [offset, value] of [[0x3ea0, id], [0xa4, 1], [0x80, 2], [0x88, 3],
                                   [0x3d90, 4], [0x3b70, 1]])
        words.set(other.add(offset).value, value);
    pointers.set(other.add(0x32f8).value, 0);   // a unit with no body keeps only its first fields
}
words.set(alliance.add(0x34).value, 1);
pointers.set(alliance.add(0x38).value, armies.value);
pointers.set(armies.value, army.value);
words.set(army.add(0x164).value, 1);
pointers.set(army.add(0x168).value, units.value);
pointers.set(units.value, unit.value);
for (const [offset, value] of [[0x3ea0, 77], [0xa4, 60], [0x80, 1000], [0x88, 900],
                               [0x3d90, 12], [0x3b70, 2]])
    words.set(unit.add(offset).value, value);
pointers.set(unit.add(0x32f8).value, body.value);
pointers.set(body.add(0xc90).value, entity.value);
pointers.set(body.add(0xc28).value, 0);
words.set(body.add(0xb70).value, 0xfff00123);
for (const [offset, value] of [[0x88, 0x41200000], [0x8c, 0x42000000], [0x90, 0x43000000]])
    words.set(entity.add(offset).value, value);
words.set(id.value, 0xabc);
// Offsets from the getters 0x2ec9be0 and 0x2f2e86c: decided +0x5d0, zero-based winner +0x5cc.
pointers.set(0x448f208, script.value);
pointers.set(script.add(0x468).value, env.value);
words.set(script.add(0x5d0).value, 0);
words.set(script.add(0x5cc).value, 0xffffffff);
function call(name, argument, result) {
    const callbacks = hooks.get(Number(BUILD[name][0])), invocation = {};
    if (callbacks.onEnter) callbacks.onEnter.call(invocation, [argument]);
    if (callbacks.onLeave) callbacks.onLeave.call(invocation, result);
}
call('env_ctor', env, ptr(0));
call('session_ctor', session, ptr(0));
const out = ptr(0x7100000);
words.set(out.value, 1);
for (let t = 1; t <= 24; t++) {
    words.set(env.add(ENV.tick).value, t);
    words.set(entry.add(0x18).value, t);
    words.set(entry.add(0x14).value, 1000 + t);
    if (t === 23) {
        words.set(script.add(0x5d0).value, 1);
        words.set(script.add(0x5cc).value, 1);
    }
    if (t === 13 || t === 1 || t === 11) {
        words.set(ptr(0x7000000).add(0x5008).value, 8);
        hooks.get(Number(BUILD.command_packet[0])).onEnter.call(
            {}, [ptr(1), ptr(0x7000008), id, ptr(1)]);
    }
    call('post_tick', env, ptr(0));
    call('session_step', session, out);
}
`);
fs.writeFileSync(process.argv[4], messages.map(JSON.stringify).join('\n') + '\n');
'''


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    path = tmp_path_factory.mktemp("capture") / "agent.jsonl"
    agent_check(GENERATE.replace("process.argv[4]", json.dumps(str(path))))
    return [json.loads(line) for line in path.read_text().splitlines()]


def write(path, rows, stopped=True):
    tail = [{"event": "capture_stopped", "ready": True, "failed": False}] if stopped else []
    path.write_text("\n".join(json.dumps(row) for row in [*rows, *tail]) + "\n")
    return path


def pair(tmp_path, rows, change=None, **options):
    second = json.loads(json.dumps(rows))
    if change:
        second = change(second) or second
    return compare_captures({"A": load_capture(write(tmp_path / "a", rows)),
                             "B": load_capture(write(tmp_path / "b", second))}, **options)


def test_the_agent_writes_every_tick_scheduled_witnesses_and_the_ones_around_a_command(rows):
    ticks = [r["tick"] for r in rows if r["event"] == "completed_tick"]
    assert ticks == list(range(1, 25))
    assert all(r["phase"] == 5 and r["sim_phase"] == 7
               for r in rows if r["event"] == "completed_tick")
    witnesses = [(r["tick"], r["reason"]) for r in rows if r["event"] == "witness"]
    # A packet before tick 1 has no earlier state and says so; one right after a sent tick
    # needs no second "before" row.
    assert witnesses == [(1, "after_command"), (10, "schedule"), (11, "after_command"),
                         (12, "before_command"), (13, "after_command"), (20, "schedule")]
    availability = [r["before_available"] for r in rows if r["event"] == "witness"
                    and r["reason"] == "after_command"]
    assert availability == [False, True, True]
    units = next(r for r in rows if r["event"] == "witness" and r["tick"] == 10)["units"]
    # alliance, army and index stay apart: each element is its own unit at each level.
    assert [(row[:3], row[3]) for row in units] == [
        ([0, 0, 0], 77), ([1, 0, 0], 78), ([1, 0, 1], 79), ([1, 1, 0], 80)]
    assert len(units[1]) == 9, "no body, no position fields"
    unit = units[0]
    # alliance, army, index, id, men, hp words, ammo, morale, kind, raw x y z, low 16 of bearing
    assert unit == [0, 0, 0, 77, 60, 1000, 900, 12, 2, 0, 0x41200000, 0x42000000, 0x43000000,
                    0x123]


def test_the_agent_records_the_decided_winner_once_from_the_tick_it_appears(rows):
    decided = [r for r in rows if r["event"] == "battle_decided"]
    assert [(r["tick"], r["winner"]) for r in decided] == [(23, 1)]


def test_differing_winners_conflict_and_a_one_sided_ending_is_inconclusive(tmp_path, rows):
    def other(second):
        next(r for r in second if r["event"] == "battle_decided")["winner"] = 0
    assert pair(tmp_path, rows, other)["verdict"] == "conflict"

    def none(second):
        return [r for r in second if r["event"] != "battle_decided"]
    assert pair(tmp_path, rows, none)["verdict"] == "inconclusive"


def test_identical_captures_agree_and_cover_every_tick(tmp_path, rows):
    summary = pair(tmp_path, rows)
    assert summary["verdict"] == "agreed"
    assert summary["ticks_compared"] == 24
    assert summary["witness_ticks_compared"] == 2
    assert summary["units_compared"] == 8
    assert not summary["phase_differences"]
    assert summary["interval"] == [1, 24]


def test_a_changed_checksum_conflicts(tmp_path, rows):
    def change(second):
        next(r for r in second if r["event"] == "completed_tick" and r["tick"] == 7)["checksum"] = 1
    summary = pair(tmp_path, rows, change)
    assert summary["verdict"] == "conflict"
    assert [c["tick"] for c in summary["checksum_conflicts"]] == [7]


def test_a_changed_raw_value_conflicts_even_with_equal_checksums(tmp_path, rows):
    def change(second):
        next(r for r in second if r["event"] == "witness" and r["tick"] == 20)["units"][0][10] += 1
    summary = pair(tmp_path, rows, change)
    assert summary["verdict"] == "conflict"
    assert summary["unit_conflicts"][0]["tick"] == 20
    assert not summary["checksum_conflicts"]


def test_a_missing_unit_conflicts(tmp_path, rows):
    def change(second):
        next(r for r in second if r["event"] == "witness" and r["tick"] == 10)["units"] = []
    assert pair(tmp_path, rows, change)["verdict"] == "conflict"


def test_a_gap_inside_the_interval_is_inconclusive_never_agreed(tmp_path, rows):
    def tick(second):
        return [r for r in second if not (r["event"] == "completed_tick" and r["tick"] == 9)]

    def witness(second):
        return [r for r in second if not (r["event"] == "witness" and r["tick"] == 20)]
    gap = pair(tmp_path, rows, tick)
    assert gap["verdict"] == "inconclusive" and gap["missing_ticks"]["B"] == [9]
    gone = pair(tmp_path, rows, witness)
    assert gone["verdict"] == "inconclusive" and gone["missing_witness"]["B"] == [20]


def test_a_stalled_or_late_peer_is_never_agreed_by_default(tmp_path, rows):
    def stall(second):
        return [r for r in second if r.get("tick", 0) <= 15]

    def late(second):
        return [r for r in second if r.get("tick", 99) > 10]
    stalled = pair(tmp_path, rows, stall)
    assert stalled["verdict"] == "inconclusive" and stalled["clients"]["B"]["last_tick"] == 15
    assert stalled["missing_ticks"]["B"] == list(range(16, 25))
    assert pair(tmp_path, rows, stall, start=1)["verdict"] == "inconclusive"
    assert pair(tmp_path, rows, late)["verdict"] == "inconclusive"
    narrowed = pair(tmp_path, rows, stall, start=1, end=15)
    assert narrowed["verdict"] == "agreed", "only when the interval is declared"


def test_no_raw_evidence_compared_is_inconclusive_not_agreed(tmp_path, rows):
    no_schedule = pair(tmp_path, rows, start=11, end=19)
    assert no_schedule["ticks_compared"] == 9 and no_schedule["witness_ticks_compared"] == 0
    assert no_schedule["verdict"] == "inconclusive"

    def empty(both):
        for row in both:
            if row["event"] == "witness":
                row["units"] = []
    unitless = json.loads(json.dumps(rows))
    empty(unitless)
    summary = pair(tmp_path, unitless, empty)
    assert summary["witness_ticks_compared"] == 2 and summary["units_compared"] == 0
    assert summary["verdict"] == "inconclusive"


def test_a_simulated_phase_difference_is_inconclusive_until_calibrated(tmp_path, rows):
    def other(second):
        row = next(r for r in second if r["event"] == "completed_tick" and r["tick"] == 3)
        row["sim_phase"] = 6
    summary = pair(tmp_path, rows, other)
    assert summary["verdict"] == "inconclusive" and summary["phase_differences"][0]["tick"] == 3

    def client_copy(second):
        next(r for r in second if r["event"] == "completed_tick")["phase"] = 9
    assert pair(tmp_path, rows, client_copy)["verdict"] == "agreed", "the UI copy is not compared"

    def repeat(second):
        return [*second, dict(next(r for r in second if r["event"] == "completed_tick"),
                              sim_phase=6)]
    summary = pair(tmp_path, rows, repeat)
    assert summary["own_conflicts"]["B"] == [{"tick": 1, "kind": "phase"}]
    assert summary["verdict"] == "conflict"


def test_a_missing_participant_or_failed_capture_is_inconclusive(tmp_path, rows):
    empty = compare_captures({"A": load_capture(write(tmp_path / "a", rows)),
                              "B": load_capture(write(tmp_path / "b", []))})
    assert empty["verdict"] == "inconclusive"
    unclean = compare_captures({"A": load_capture(write(tmp_path / "a", rows)),
                                "B": load_capture(write(tmp_path / "b", rows, stopped=False))})
    assert unclean["verdict"] == "inconclusive"
    failed = pair(tmp_path, rows, lambda s: s + [{"event": "probe_error", "message": "x"}])
    assert failed["verdict"] == "inconclusive"


def test_a_client_repeating_a_tick_with_another_value_conflicts(tmp_path, rows):
    def repeat(second):
        row = dict(next(r for r in second if r["event"] == "completed_tick"), checksum=5)
        return second + [row]
    summary = pair(tmp_path, rows, repeat)
    assert summary["verdict"] == "conflict"
    assert summary["own_conflicts"]["B"] == [{"tick": 1, "kind": "checksum"}]


def test_submission_counts_catch_a_duplicate_packet(tmp_path, rows):
    capture = load_capture(write(tmp_path / "a", rows))
    assert submission_problems(capture, {0xabc: 3}) == []
    duplicate = next(r for r in rows if r["event"] == "command_packet")
    twice = load_capture(write(tmp_path / "b", [*rows, duplicate]))
    assert submission_problems(twice, {0xabc: 3}) == [
        {"id": 0xabc, "expected": 3, "observed": 4}]


def test_submission_counts_catch_a_missing_packet_and_ignore_commands_nobody_named(tmp_path, rows):
    capture = load_capture(write(tmp_path / "a", rows))
    assert submission_problems(capture, {0xabc: 4}) == [
        {"id": 0xabc, "expected": 4, "observed": 3}]
    # The engine sends its own commands at battle start, so an unnamed id is no problem.
    assert submission_problems(capture, {}) == []
    assert submission_problems(capture, {1: 1}) == [{"id": 1, "expected": 1, "observed": 0}]


def test_a_duplicate_packet_fails_the_comparison_even_with_identical_positions(tmp_path, rows):
    duplicate = next(r for r in rows if r["event"] == "command_packet")
    summary = compare_captures(
        {"A": load_capture(write(tmp_path / "a", rows)),
         "B": load_capture(write(tmp_path / "b", [*rows, duplicate]))},
        expected_packets={"A": {0xabc: 3}, "B": {0xabc: 3}})
    assert summary["verdict"] == "conflict"
    assert summary["submission_problems"] == {
        "A": [], "B": [{"id": 0xabc, "expected": 3, "observed": 4}]}


def test_two_battles_in_one_capture_need_a_named_generation(tmp_path, rows):
    second = [dict(row, generation=row["generation"] + 1) for row in rows if "generation" in row]
    path = write(tmp_path / "a", [*rows, *second])
    with pytest.raises(ValueError, match="generation"):
        load_capture(path)
    second_only = load_capture(path, generation=2)
    assert second_only["generation"] == 2 and sorted(second_only["ticks"]) == list(range(1, 25))
    # The first battle's rows must not mix in: rewrite one, it stays out of the second.
    changed = [dict(r, checksum=7) if r["event"] == "completed_tick" else r for r in rows]
    mixed = load_capture(write(tmp_path / "b", [*changed, *second]), generation=2)
    assert mixed["conflicts"] == [] and mixed["ticks"] == second_only["ticks"]


def test_a_torn_last_line_is_an_unclean_stop_and_a_torn_earlier_line_refuses(tmp_path, rows):
    path = write(tmp_path / "a", rows, stopped=False)
    path.write_text(path.read_text() + '{"event": "compl')
    assert load_capture(path)["stopped"] is False
    path.write_text('{"event"\n' + path.read_text())
    with pytest.raises(ValueError, match="line 1"):
        load_capture(path)


def test_one_capture_is_not_a_comparison():
    with pytest.raises(ValueError, match="two clients"):
        compare_captures({"A": {}})


def test_the_command_line_takes_native_captures_or_an_attempt_not_both(
        tmp_path, rows, capsys, monkeypatch):
    a, b = write(tmp_path / "a", rows), write(tmp_path / "b", rows)

    def run(*arguments):
        monkeypatch.setattr(sys, "argv", ["wh3", "compare-peers", *arguments])
        return main()

    assert run("--native", f"A={a}", f"B={b}", "--end", "20") == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["verdict"] == "agreed" and summary["interval"] == [1, 20]
    assert run("--native", f"A={a}", f"B={b}", "--packets", f"B={0xabc}:9") == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "conflict"
    # Each client names its own battle: generations count per client since attach.
    second = [dict(r, generation=2) for r in rows if "generation" in r]
    both = write(tmp_path / "c", [dict(r, checksum=7) if r["event"] == "completed_tick" else r
                                  for r in rows if "generation" in r] + second)
    assert run("--native", f"A={a}#1", f"B={both}#2") == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "agreed"
    with pytest.raises(SystemExit):
        run()
    with pytest.raises(SystemExit):
        run(str(tmp_path), "--native", f"A={a}", f"B={b}")
