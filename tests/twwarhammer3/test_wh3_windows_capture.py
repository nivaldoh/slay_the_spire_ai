"""The Windows-side screenshot in twwarhammer3/engine/windows_capture.py."""
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
