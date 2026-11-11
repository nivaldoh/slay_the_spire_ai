"""The Windows-side screenshot in twwarhammer3/engine/windows_capture.py."""
import json
from unittest.mock import Mock

import pytest
from PIL import ImageGrab

from twwarhammer3.engine import windows_capture


def test_passive_capture_refuses_another_foreground_process(tmp_path, monkeypatch):
    user = Mock()
    user.GetForegroundWindow.return_value = 42
    user.GetWindowThreadProcessId.side_effect = lambda _, owner: setattr(owner._obj, "value", 999)
    monkeypatch.setattr(windows_capture.ctypes, "WinDLL", lambda *a, **k: user, raising=False)
    screenshot = Mock()
    monkeypatch.setattr(ImageGrab, "grab", screenshot)
    with pytest.raises(RuntimeError, match="not foreground"):
        windows_capture.capture(123, tmp_path / "shot.png", tmp_path / "observation.json", "j", "b")
    screenshot.assert_not_called()
    assert not (tmp_path / "shot.png").exists()


GAME = 123


def fake_desktop(monkeypatch, owner, windows, grab):
    """user32 whose foreground window is `windows` in turn, owned by process `owner`; `grab`
    replaces the screen grab."""
    user = Mock()
    user.GetForegroundWindow.side_effect = windows
    user.GetWindowThreadProcessId.side_effect = lambda _, pid: setattr(pid._obj, "value", owner)
    monkeypatch.setattr(windows_capture.ctypes, "WinDLL", lambda *a, **k: user, raising=False)
    monkeypatch.setattr(ImageGrab, "grab", grab)

def battle_during_grab(observation, before, after, image):
    """The observation names battle `before`, and `after` once the grab has run."""
    observation.write_text(json.dumps({"job": "j", "battle": before, "time_ms": 1000}))

    def grab(**_):
        observation.write_text(json.dumps({"job": "j", "battle": after, "time_ms": 1250}))
        return image

    return grab

@pytest.mark.parametrize("before,after,windows,error", [
    ("other", "b", [42, 42], "Battle changed before capture"),
    ("b", "b", [42, 43], "Foreground changed during capture"),
    ("b", "next", [42, 42], "Battle changed during capture"),
])
def test_a_capture_is_discarded_when_the_battle_or_foreground_window_changes(
        tmp_path, monkeypatch, before, after, windows, error):
    observation, image = tmp_path / "observation.json", Mock(size=(4, 3))
    fake_desktop(monkeypatch, GAME, windows, battle_during_grab(observation, before, after, image))

    with pytest.raises(RuntimeError, match=error):
        windows_capture.capture(GAME, tmp_path / "shot.png", observation, "j", "b")

    image.save.assert_not_called()

def test_a_capture_of_the_unchanged_battle_is_saved_with_the_observations_around_it(
        tmp_path, monkeypatch):
    observation, image = tmp_path / "observation.json", Mock(size=(4, 3))
    fake_desktop(monkeypatch, GAME, [42, 42], battle_during_grab(observation, "b", "b", image))

    result = windows_capture.capture(GAME, tmp_path / "shot.png", observation, "j", "b")

    image.save.assert_called_once_with(tmp_path / "shot.png")
    assert result["status"] == "captured" and result["file"] == "shot.png"
    assert result["capture_interval_ms"] == [1000, 1250] and result["policy_input"] is False
