"""Live verification agreed 2026-10-19; two WH3 launches, no paid model or scored battle.

    uv run --locked python tests/twwarhammer3/check_wh3_army_setup.py --output runs/...

Cold-build and save a mounted, mixed-class army with duplicate Swordsmen at ranks 0/3/9.
Exercise increases and decreases, clear both armies, restart, load the presets and compare
lobby types/counts/ranks and battle-start ranks/stats. Runs unpaused at 1x. Re-running
deletes only the two content-addressed presets for this exact diagnostic scenario.
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from gameai.provenance import git, sha256, source_fingerprints, write_json
from twwarhammer3.battle import setup
from twwarhammer3.battle.play import SOURCES, start_frontend
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.engine.runtime import BRIDGE_DIR, OwnedGame, RuntimeLock, prepare_runtime

SWORD = "wh_main_emp_inf_swordsmen"


def scenario():
    result = setup.scenarios()["grn-chariot-emp-swordsmen"]
    result["name"] = "army-setup-verification"
    result["expect"]["funds_amount"] = 10000
    result["player"] = {
        "subculture": "wh_main_sc_emp_empire", "faction": "wh_main_emp_empire",
        "units": ["wh_main_emp_cha_general_0", SWORD, "wh_main_emp_inf_handgunners",
                  SWORD, SWORD], "mounts": {"0": "wh_main_emp_cha_general_2"},
        "experience": {"2": 1, "3": 3, "4": 9},
    }
    result["enemy"]["units"] = [SWORD] * 3
    result["enemy"]["experience"] = {"1": 3, "2": 9}
    return result


def context_step(**kwargs):
    return {"context": "CcoFrontendRoot", "required": True, **kwargs}


def lobby_stats_steps():
    return [context_step(expression=f"{setup.LOBBY}PlayerSlotList.At({slot}).UnitList."
            'JoinString(UnitRecordContext.Key + ":" + ExperienceLevel + ":" + '
            'UnitDetailsContext.StatList.JoinString(Key + "=" + Value, "/"), ";")')
            for slot in (0, 1)]


def stats_rows(text):
    return [(unit, {key: float(value) for key, value in
                    (stat.split("=") for stat in stats.split("/"))})
            for unit, stats in (row.split(":", 1) for row in text.split(";"))]


def check_stats(log, observation):
    """Use the independently read lobby stats as the reference for battle startup."""
    lobby = []
    for line in log.splitlines():
        if '.UnitList.JoinString(UnitRecordContext.Key + ":" + ExperienceLevel' in line:
            rows = line.split(" = ", 1)[1].split(";")
            lobby.append([(row.split(":", 2)[0], int(row.split(":", 2)[1]),
                           stats_rows(row.split(":", 1)[0] + ":" + row.split(":", 2)[2])[0][1])
                          for row in rows])
    assert len(lobby) == 2, "both lobby stat readbacks required"
    battle = observation["setup"]["unit_base_stats"].split("@@")
    assert len(battle) == 2
    evidence = []
    for before, army in zip(lobby, battle, strict=True):
        after = stats_rows(army.split("@", 1)[1])
        keys = ("stat_melee_attack", "stat_melee_defence", "stat_morale")
        expected = Counter((unit, *(stats[k] for k in keys)) for unit, _, stats in before)
        actual = Counter((unit, *(stats[k] for k in keys)) for unit, stats in after)
        assert actual == expected, (actual, expected)
        swords = {rank: stats for unit, rank, stats in before if unit == SWORD}
        assert set(swords) == {0, 3, 9}
        for key in keys:
            assert swords[0][key] < swords[3][key] < swords[9][key], (key, swords)
        evidence.append({rank: {k: s[k] for k in keys} for rank, s in swords.items()})
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    environment = collect_diagnostics()
    spec = scenario()
    build = environment["game"]["steam_build_id"]
    write_json(args.output / "environment.json", environment)
    write_json(args.output / "scenario.json", spec)
    write_json(args.output / "sources.json", {
        "files": source_fingerprints(SOURCES), "check_sha256": sha256(Path(__file__)),
        "source_revision": git("rev-parse", "HEAD").strip(),
        "source_status": git("status", "--porcelain", "--", *SOURCES),
    })
    checks = {}
    for phase in ("save", "load"):
        output = args.output / phase
        output.mkdir()
        steps = setup.scenario_steps(spec, build_id=build)
        start = next(i for i, step in enumerate(steps)
                     if step.get("find") == ["start_button_frame", "button_start_battle"])
        extra = lobby_stats_steps()
        if phase == "save":
            # Use the implemented setter in both directions, including the rank-zero boundary.
            extra = [{"experience": [{"type": SWORD, "rank": r} for r in (0, rank, 9)],
                      "slot": 1, "required": True} for rank in (9, 0, 3)] + (
                          setup.army_checks(spec["enemy"], 1) + extra)
            extra += [context_step(command=setup.LOBBY +
                                   f"PlayerSlotList.At({slot}).ClearMainArmy()")
                      for slot in (0, 1)]
            extra += [context_step(expression=setup.LOBBY +
                                   f"PlayerSlotList.At({slot}).UnitList.Size",
                                   expect=0) for slot in (0, 1)]
            steps = steps[:start] + extra
            # Force the cold path on every repetition; never touch unrelated user presets.
            delete = []
            for army in setup.sides(spec):
                name = json.dumps(setup.army_preset_name(spec, army, build))
                delete.append(context_step(command=setup.PRESETS +
                    f"ArmyPresetList(0).FirstContext(Name == {name}).Delete()",
                    when=setup.PRESETS + f"ArmyPresetExists({name})"))
            steps[3:3] = delete
        else:
            steps[start:start] = extra
        write_json(output / "steps.json", steps)
        with RuntimeLock():
            write_json(output / "deployment.json", prepare_runtime())
            mailbox = Mailbox(BRIDGE_DIR, job=args.output.name + "-" + phase)
            mailbox.reset()
            mailbox.write_session({"menu": True, "enabled": True, "autostart": True,
                                   "observe_ms": 250, "tick_ms": 250, "speed": 1,
                                   "pause": False, "record_replay": False, "stills": False})
            with OwnedGame(output / "game.log", timeout=900) as game:
                write_json(output / "game.json", game.info)
                print(phase + ": running lobby steps", flush=True)
                start_frontend(mailbox, {"start_timeout": 600}, output, steps)
                log = (output / "menu.log").read_text()
                checks[phase] = setup.check_menu(spec, output)
                verb = "SaveArmyPresetForPlayerSlot" if phase == "save" else "LoadForPlayerSlot"
                assert sum("command " in line and verb in line for line in log.splitlines()) == 2
                if phase == "load":
                    assert "double-clicked" not in log, "warm path rebuilt an army"
                    deadline = time.monotonic() + 120
                    observation = mailbox.read_observation()
                    while not observation or not observation.get("setup"):
                        if time.monotonic() >= deadline:
                            raise TimeoutError("no battle-start setup")
                        time.sleep(.25)
                        observation = mailbox.read_observation()
                    write_json(output / "observation.json", observation)
                    checks["battle"] = setup.check_battle(spec, observation)
                    checks["rank_stats"] = check_stats(log, observation)
                    assert observation["speed"] == 1
                print(phase + ": checks passed", flush=True)
    write_json(args.output / "checks.json", checks)


if __name__ == "__main__":
    main()
