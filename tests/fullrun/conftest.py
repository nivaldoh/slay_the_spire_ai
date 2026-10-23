"""Replace game processes and bridge I/O for tests that request the harness fixture."""

from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import Mock

import pytest

from spire.fullrun import play


@pytest.fixture
def harness(monkeypatch, tmp_path):
    sessions, sent = [], []

    class FakeBridge:
        def __init__(self, **kwargs):
            self.address, self.messages = (kwargs["host"], kwargs["port"]), iter(sessions.pop(0))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def receive(self):
            item = next(self.messages)
            while callable(item):  # something the game does between two messages
                item()
                item = next(self.messages)
            return deepcopy(item)

        def send(self, command):
            sent.append(command)

    class FakeGame:
        info = {"pid": 1}

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(play, "BridgeServer", FakeBridge)
    monkeypatch.setattr(play, "OwnedGame", FakeGame)
    monkeypatch.setattr(play, "RuntimeLock", nullcontext)
    monkeypatch.setattr(play, "wsl_bridge_host", Mock(return_value="172.18.0.1"))
    monkeypatch.setattr(play, "prepare_runtime", Mock(return_value={"mods": {}}))
    monkeypatch.setattr(play, "collect_profile", Mock(return_value={"slot": 0}))
    monkeypatch.setattr(play, "GAME_DIR", tmp_path / "game")
    monkeypatch.setattr(play, "collect_diagnostics", lambda: {"schema_version": 1})
    monkeypatch.setattr(play, "committed_revision", lambda purpose, paths: "test")
    monkeypatch.setattr(play, "source_fingerprints", lambda paths: {})
    return sessions, sent
