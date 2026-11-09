"""scripts/wh3_lobby_readback.py: lobby steps up to Start, with every reading and no Start click."""

import copy
import importlib.util
import json
import re

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import setup

SPEC = importlib.util.spec_from_file_location("wh3_lobby_readback_script",
                                              REPO_ROOT / "scripts/wh3_lobby_readback.py")
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


def mentions_start(step):
    return "button_start_battle" in json.dumps(step) or step.get("log") == setup.NOT_STARTED


def unrequired(step):
    return {key: value for key, value in step.items() if key != "required"}


def assert_wait_covers(printed, path, steps):
    # The frontend runs one step per 500 ms callback after its waits and timeouts, so a shorter
    # --wait gives up before 'menu N: done' (twwarhammer3_frontend.lua, the step loop).
    wait = re.search(rf"--steps {re.escape(str(path))} --wait (\d+) ", printed)
    assert wait, path
    least = sum((step.get("wait_ms", 0) + step.get("timeout_ms", 0)) / 1000 + 0.5
                for step in steps)
    assert int(wait.group(1)) >= least, path


def test_each_file_keeps_every_lobby_step_before_start_and_rereads_the_armies(tmp_path, capsys):
    output = tmp_path / "readback"
    script.main(["--output", str(output)])
    printed = capsys.readouterr().out
    manifest = json.loads((output / "manifest.json").read_text())
    opening = json.loads((output / "open-lobby.json").read_text())
    assert sorted(manifest["files"]) == sorted(script.READBACK)
    assert_wait_covers(printed, output / "open-lobby.json", opening)
    for name, file in manifest["files"].items():
        scenario = setup.scenarios()[name]
        steps = json.loads((output / file).read_text())
        # Each file starts in the lobby with the maps tab, so the files run in any order.
        lobby = setup.map_steps(scenario)
        assert unrequired(steps[0]) == lobby[0], name
        assert not any(unrequired(step) in lobby for step in opening), name
        written = opening + steps
        full = setup.scenario_steps(scenario)
        start = next(index for index, step in enumerate(full) if mentions_start(step))
        assert written[:start] == full[:start], name
        assert not any(mentions_start(step) for step in written), name
        rest = written[start:]
        for slot, army in enumerate(setup.sides(scenario)):
            assert all(check in rest for check in setup.army_checks(army, slot)), (name, slot)
        assert_wait_covers(printed, output / file, steps)


def test_a_swapped_unit_key_changes_what_the_files_expect():
    def expected(scenario):
        _, steps = script.readback_steps(scenario)
        return {step["expression"]: step["expect"] for step in steps if "expect" in step}

    for name in script.READBACK:
        original = setup.scenarios()[name]
        swapped = copy.deepcopy(original)
        units = swapped["enemy"]["units"]
        units[-1] = next(unit for unit in swapped["player"]["units"] if unit not in units)
        assert expected(swapped) != expected(original), name


def test_steps_with_no_start_click_it_knows_are_refused(monkeypatch):
    steps = setup.scenario_steps(setup.scenarios()["ksl-emp-siege-a-v1"])
    renamed = [{**step, "find": ["start_button_frame", "button_begin"]}
               if "button_start_battle" in (step.get("find") or []) else step for step in steps]
    monkeypatch.setattr(setup, "scenario_steps", lambda scenario: renamed)
    with pytest.raises(ValueError, match="no Start click"):
        script.readback_steps(setup.scenarios()["ksl-emp-siege-a-v1"])


def test_an_unknown_scenario_is_refused_and_nothing_is_written(tmp_path, capsys):
    with pytest.raises(SystemExit):
        script.main(["emp-chd-camp-v1", "emp-chd-camp-v9", "--output", str(tmp_path / "out")])
    assert "emp-chd-camp-v9" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
