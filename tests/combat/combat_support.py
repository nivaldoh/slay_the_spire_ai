"""Shared first-combat messages and an opt-in fake rollout boundary.

Pattern: Hugging Face datasets tests/utils.py keeps helpers outside collected tests;
tests/fullrun/fullrun_support.py does the same here. No game launches here.
"""

from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gameai import provenance
from spire.combat import rollout
from spire.engine import doctor


def combat_message():
    return {
        "ready_for_command": True,
        "in_game": True,
        "available_commands": ["play"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "floor": 1,
            "current_hp": 80,
            "room_phase": "COMBAT",
            "room_type": "MonsterRoom",
            "screen_type": "NONE",
            "combat_state": {
                "turn": 1,
                "player": {"current_hp": 80, "max_hp": 80, "energy": 1, "block": 0},
                "hand": [
                    {
                        "id": "Strike_R",
                        "cost": 1,
                        "has_target": True,
                        "is_playable": True,
                    }
                ],
                "monsters": [
                    {
                        "id": "Cultist",
                        "current_hp": 6,
                        "max_hp": 50,
                        "block": 0,
                        "is_gone": False,
                        "half_dead": False,
                        "intent": "BUFF",
                    }
                ],
            },
        },
    }



def terminal_message(outcome="won"):
    state = {
        "floor": 1,
        "current_hp": 80 if outcome == "won" else 0,
        "room_phase": "COMPLETE",
        "room_type": "MonsterRoom",
        "screen_type": "COMBAT_REWARD",
    }
    if outcome == "lost":
        state.update(screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False})
    return {
        "ready_for_command": True,
        "in_game": True,
        "available_commands": ["proceed"],
        "game_state": state,
    }



@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(sessions=[], bridges=[], games=[], received=0, clock=0.0)

    class FakeBridge:
        def __init__(self, **kwargs):
            self.address = (kwargs["host"], kwargs["port"])
            self.messages = iter(state.sessions.pop(0))
            self.commands = []
            self.closed = False
            state.bridges.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def receive(self):
            state.received += 1
            message = next(self.messages)
            if callable(message):
                message = message()
            if isinstance(message, BaseException):
                raise message
            return deepcopy(message)

        def send(self, command):
            self.commands.append(command)

    class FakeGame:
        info = {"pid": 12345}

        def __init__(self, *args, **kwargs):
            self.closed = False
            state.games.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

    monkeypatch.setattr(rollout, "BridgeServer", FakeBridge)
    monkeypatch.setattr(rollout, "OwnedGame", FakeGame)
    monkeypatch.setattr(rollout, "RuntimeLock", nullcontext)
    monkeypatch.setattr(rollout, "wsl_bridge_host", Mock(return_value="172.18.34.183"))
    monkeypatch.setattr(rollout, "prepare_runtime", Mock(return_value={"mods": {}}))
    monkeypatch.setattr(
        rollout,
        "collect_profile",
        Mock(
            return_value={
                "slot": 0,
                "ironclad_unlock_level": "3",
                "unlock_file_sha256": "profile-before-episode",
            }
        ),
    )
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {"schema_version": 1})
    monkeypatch.setattr(rollout.time, "monotonic", lambda: state.clock)

    def git_output(command, **kwargs):
        return "test-revision\n" if command[:3] == ["git", "rev-parse", "HEAD"] else ""

    monkeypatch.setattr(provenance.subprocess, "check_output", git_output)
    return state

