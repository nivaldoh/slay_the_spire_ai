"""Digests read back what a (fake) job saved; no engine is involved."""

from test_decisions import card, combat_message, message
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


class CommandPolicy(ScriptedPolicy):
    """Plays the given commands in order and reports each choice as the model's."""

    def __init__(self, *commands):
        super().__init__()
        self.commands = list(commands)

    def choose(self, decision):
        command = self.commands.pop(0)
        return next(c for c in decision.candidates if c.command == command)

    def choice_metadata(self, decision_id):
        return {"type": "llm", "reason": "why", "notes": "plan"}


def test_run_digest_flags_recurring_mistakes_and_groups_a_fight_by_turn(
        tmp_path, harness, capsys):
    sessions, _ = harness
    reward = message(["choose", "skip", "key", "click", "wait", "state"],
                     screen_type="CARD_REWARD", choice_list=["anger"],
                     screen_state={"cards": [card("Anger", cost=0)]})
    sessions.append([MENU, NEOW, combat_message(), combat_message(), reward, reward, DEATH])
    commands = ("potion use 0 1", "end", "skip", "skip")
    play.play(tmp_path / "job", {**CONFIG, "seeds": ["SEEDA"]},
              policy_factory=lambda: CommandPolicy(*commands))
    run = tmp_path / "job/run-0000"
    # Ending a turn with 3 energy, a playable Strike and 11 unblocked damage counts twice.
    assert digest.flags(run) == [
        "Turns ended with energy and a playable card: 1 (F3); "
        "with attacks exceeding block: 1 (F3)",
        "Card rewards skipped: 2, repeatedly on F3 x2",
        "Potions used: F3 hallway Fire Potion. Held at the end: none",
        "Last end turn: F3 T2, incoming 11 against 0 block and 70 HP",
    ]
    digest.main(run)
    assert "why" not in capsys.readouterr().out
    digest.main(run, picks=True)
    assert "    CARD_REWARD: skip this card reward (why)" in capsys.readouterr().out
    digest.floor_detail(run, 3)
    assert capsys.readouterr().out.splitlines()[1:5] == [
        "T2 hp70 blk0 e3 | Jaw Worm 30 blk0 ATTACK 11",
        "    -> use potion Fire Potion -> Jaw Worm [1]  (why)",
        "    -> end turn at hp70 blk0 e3, incoming 11  (why)",
        "CARD_REWARD -> skip this card reward  (why)",
    ]
