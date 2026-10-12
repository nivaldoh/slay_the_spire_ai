"""Digests read back what a (fake) job saved; no engine is involved."""

from test_decisions import combat_message
from test_play import CONFIG, DEATH, MENU, NEOW, ScriptedPolicy, harness

from spire.fullrun import digest, play

__all__ = ["harness"]


def test_job_table_reports_each_seed_and_the_last_fight(tmp_path, harness, capsys):
    sessions, _ = harness
    elite = combat_message()
    elite["game_state"]["room_type"] = "MonsterRoomElite"
    sessions += [[MENU, NEOW, elite, DEATH], [MENU, NEOW, combat_message(), DEATH]]
    play.play(tmp_path / "job", CONFIG, policy_factory=ScriptedPolicy)
    table = digest.job_table(tmp_path / "job").splitlines()
    assert table[0] == "job: source test, completed"
    assert table[3].startswith("| SEEDA | lost | ")
    assert digest.last_fight(tmp_path / "job/run-0000").endswith("(elite)")
    # The fixture's Louse is already dead; only enemies still standing are named.
    assert digest.last_fight(tmp_path / "job/run-0001") == "Jaw Worm"
    digest.main(tmp_path / "job/run-0000")
    assert "Final notes" in capsys.readouterr().out
