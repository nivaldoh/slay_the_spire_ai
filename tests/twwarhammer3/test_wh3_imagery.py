import base64
import io

import pytest

from twwarhammer3.battle import imagery, visual_probe


def test_stills_resize_preserve_provenance_and_report_failures(tmp_path):
    image = pytest.importorskip("PIL.Image")
    source = tmp_path / "opening.tga"
    image.new("RGB", (2000, 1500), "blue").save(source)
    entries = [{"file": "opening.tga", "time_ms": 1000, "visibility": "unverified"},
               {"file": "missing.tga", "time_ms": 2000}, {"file": "../private.png"},
               {"status": "capture_failed", "error": "unsupported API"}]
    output = imagery.stills(tmp_path, entries, embed=True)
    assert output[0]["original_size"] == [2000, 1500]
    assert max(output[0]["size"]) <= 1600 and output[0]["size"][1] <= 1000
    assert output[0]["time_ms"] == 1000 and output[0]["policy_input"] is False
    assert output[0]["visibility"] == "unverified"
    data = base64.b64decode(output[0]["image"].split(",")[1])
    with image.open(io.BytesIO(data)) as decoded:
        assert decoded.format == "WEBP"
    assert output[1]["status"] == output[2]["status"] == "error"
    assert output[3]["status"] == "capture_failed"
    assert "image" not in imagery.stills(tmp_path, entries, embed=False)[0]


def test_probe_commands_are_scripted_and_keep_normal_game_timing(tmp_path):
    for case in ("off", "on", "imagery"):
        command = visual_probe.command(tmp_path / case, case)
        assert command[command.index("--policy") + 1] == "rush_nearest"
        assert "--pause" not in command and "--speed" not in command
        assert ("--record-replay" in command) == (case != "off")


def test_probe_rejects_existing_output_before_touching_runtime(tmp_path):
    with pytest.raises(ValueError, match="new directory"):
        visual_probe.run(tmp_path, "imagery")


def test_imagery_probe_is_valid_lua51():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime()
    compile_lua = lua.eval("function(source) return assert(loadstring(source)) end")
    assert compile_lua(visual_probe.LUA)
