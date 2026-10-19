import json

from twwarhammer3.battle.cards import CARDS, cycles, outcome, verdict


def _frame(second, melee):
    return {"time_ms": second * 1000,
            "friendly": [{"id": "f1", "state": ["melee"] if melee else ["moving"]}]}


def test_a_cycle_needs_an_applied_pull_out_during_melee_and_a_new_charge(tmp_path):
    # Engagements 10-15 s, 31-35 s (1 s flicker at 33 s merges) and 51-53 s.
    melee = set(range(10, 16)) | {31, 32, 34, 35} | set(range(51, 54))
    frames = [_frame(second, second in melee) for second in range(60)]
    (tmp_path / "replay.jsonl").write_text("".join(json.dumps(f) + "\n" for f in frames))
    records = [
        {"kind": "decision", "request": "r1", "orders": [{"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r1",
         "ack": {"applied_ms": 13000, "results": [{"index": 1, "ok": True}]}},
        # An attack on another unit inside the second engagement is not a pull-out, nor is
        # a refused move, nor a move in the last engagement (no charge follows it).
        {"kind": "decision", "request": "r2", "orders": [{"unit": "f1", "type": "attack"},
                                                         {"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r2", "ack": {"applied_ms": 32000, "results": [
            {"index": 1, "ok": True}, {"index": 2, "ok": False}]}},
        {"kind": "decision", "request": "r3", "orders": [{"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r3",
         "ack": {"applied_ms": 52000, "results": [{"index": 1, "ok": True}]}},
    ]
    (tmp_path / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    assert cycles(tmp_path) == 1


def test_controller_failures_forfeit_while_game_failures_and_operator_stops_are_rerun():
    assert outcome({"status": "won", "ended_by": "engine_result"}) == "won"
    assert outcome({"status": "won", "ended_by": "time_limit"}) == "lost"
    for status, error in [("policy_failure", "No valid reply after declared retries"),
                          ("policy_failure", "decide: KeyError: 'terrain'"),
                          ("truncated", "no observation after seq 8573")]:
        assert outcome({"status": status, "battle": "b", "error": error}) == "forfeit"
    for episode in [{"status": "policy_failure", "battle": "b",
                     "error": "decide: APIError: HTTP 402: credits"},
                    {"status": "policy_failure", "error": "controller construction: no key"},
                    {"status": "budget_exhausted", "battle": "b"},
                    {"status": "infrastructure_failure", "battle": "b"},
                    {"status": "interrupted", "battle": "b"}]:
        assert outcome(episode) == "excluded"


def test_one_foil_win_fails_the_card_whatever_the_witness_did():
    card = CARDS["chariot"]

    def rows(result, count):
        return [{"outcome": result, "cycles": 3, "setup": "s", "source": "x"}] * count
    cells = {(foil, 0, 0): rows("lost", 10) for foil in card["foils"]}
    cells.update({key: rows("won", 5) for key in card["witnesses"]})
    assert verdict(card, cells)[-1] == "Verdict: admitted"
    cells[("rush_nearest", 0, 0)] = rows("lost", 9) + rows("won", 1)
    assert "rush_nearest won 1 of 10" in verdict(card, cells)[-1]
    # A foil's forfeit is no launch.
    cells[("rush_nearest", 0, 0)] = rows("lost", 9) + rows("forfeit", 1)
    assert "rush_nearest has 9 of 10 launches" in verdict(card, cells)[-1]
