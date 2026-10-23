"""Small game messages and a policy shared by full-run tests."""

from spire_messages import message

MENU = {"ready_for_command": True, "in_game": False, "available_commands": ["start", "state"],
        "game_state": {}}
NEOW = message(["choose", "key", "click", "wait", "state"], screen_type="EVENT",
               choice_list=["talk"], screen_state={"options": [{"text": "[Talk]"}]})
DEATH = message(["proceed"], screen_type="GAME_OVER", screen_name="DEATH", current_hp=0,
                screen_state={"victory": False, "score": 42})

CONFIG = {"seeds": ["SEEDA", "SEEDB"], "max_actions": 50, "run_timeout": 100,
          "bridge_timeout": 30}


class ScriptedPolicy:
    def __init__(self, error=None):
        self.error, self.seen, self.totals = error, [], {"calls": 0}

    def choose(self, decision):
        if self.error:
            raise self.error
        self.seen.append(decision)
        self.totals["calls"] += 1
        return decision.candidates[-1]

    def choice_metadata(self, decision_id):
        return {"type": "scripted"}
