"""Write lobby-only recruitment and equipment readback steps for WH3 scenarios; it launches nothing.

    uv run --locked python scripts/wh3_lobby_readback.py [SCENARIO ...] [--output DIR]

For each scenario (by default the ones listed in --help) this writes the menu steps that
setup.scenario_steps runs in the custom battle lobby, from the maps tab up to but excluding
the Start click, then reads every army back once more as it would start. open-lobby.json
takes the game from the main menu to the lobby; each scenario's file starts in the lobby, so
the files should run in any order and again (no live lobby has tried that yet). Every reading
of scenario_steps stays in: the army checks after each slot, the lobby settings and the siege
equipment. In a benchmark declaration they are all required, so the first failed recruit or
reading stops that file and menu.log shows the value it read. No battle starts, so nothing
check_battle reads, such as the equipment the battle itself reports, is checked here.
The script refuses steps in which it cannot find the Start click, since a start it does not
recognise would stay in the file. A scenario whose steps equal an earlier one's gets no file
of its own. manifest.json records the revision and each scenario as it was read.

The owner starts the game with `twwarhammer3 launch` and sends each file with
`twwarhammer3 menu --steps`; the script prints those commands. Afterwards the lobby keeps the
last file's settings and armies, as after any custom battle setup.
"""

import argparse
import json
import math
import textwrap
from datetime import datetime
from pathlib import Path

from gameai.provenance import REPO_ROOT, git, write_json
from twwarhammer3.battle import setup

# The rosters and equipment slots of the historical evaluations that no live lobby has read
# back (portfolio S9 in runs/siege-evals-20261108); rests on JUDGEMENT
# docs/twwarhammer3/historical-evals.md Live order.
READBACK = {
    "emp-chd-camp-v1": "Belgrade: Flagellants, Free Company, Reiksguard, Warrior Priest and the"
                       " General's mount; Chaos Dwarfs with the Deathshrieker in the AI slot under"
                       " the recruitment faction wh3_dlc23_chd_legion_of_azgorh",
    "ksl-nor-lines-a-v1": "Alesia case a: Tzar Guard and Winged Lancers; Norsca cards by key,"
                          " with no lord",
    "ksl-nor-lines-b-v1": "Alesia case b: the same armies as case a",
    "cth-emp-siege-a-all-v1": "Haengju: the Cathay garrison under wh3_main_cth_cathay_mp; the AI"
                              " attacker's siege equipment cleared to none",
    "cth-emp-siege-a-v1": "Haengju with divisions: the same armies, its reserve acts in battle",
    "ksl-emp-siege-a-v1": "Izmail: Winged Lancers; one Kislev ram in the player attacker's slot",
}
MAPS_TAB = ["tab_buttons", "button_tab_maps"]  # the first step of setup.map_steps
SOURCES = ("configs/twwarhammer3", "src/twwarhammer3/battle/setup.py",
           "scripts/wh3_lobby_readback.py")


def starts_battle(step: dict) -> bool:
    """The lobby's Start button (Ready in a hosted lobby, setup.READY_STEP) or the Ready
    command, which starts a hosted battle once every player is ready."""
    return ("button_start_battle" in (step.get("find") or [])
            or "ToggleReady" in step.get("command", ""))


def readback_steps(scenario: dict) -> tuple[list[dict], list[dict]]:
    """(main menu to the lobby, the lobby up to Start plus a final army readback)."""
    if scenario.get("random") or not all(side.get("units") for side in setup.sides(scenario)):
        raise ValueError("every side needs an explicit roster to read back")
    # JUDGEMENT?: Readback without presets — Claude, 2026-11-09: no build id, so every card is
    # recruited and no game preset is loaded or saved. With it, a preset from an earlier session
    # would replace the recruitment read here, and a saved one would be what play loads next.
    steps = setup.scenario_steps(scenario)
    starts = [index for index, step in enumerate(steps) if starts_battle(step)]
    if not starts:
        raise ValueError("no Start click found in setup.scenario_steps; a step file without"
                         " it might still start the battle")
    lobby = next(index for index, step in enumerate(steps) if step.get("find") == MAPS_TAB)
    final = [{"log": "readback: every army as it would start"}]
    for slot, army in enumerate(setup.sides(scenario)):
        # Not required, so it logs the slot's units before a failed count stops the file.
        final.append({"context": "CcoFrontendRoot", "expression":
                      f"{setup.LOBBY}PlayerSlotList.At({slot}).UnitList.JoinString("
                      'UnitRecordContext.Key + ":" + ExperienceLevel, ";")'})
        final += setup.army_checks(army, slot)
    return steps[:lobby], steps[lobby:starts[0]] + final


def wait_s(steps: list[dict]) -> int:
    """Seconds for `menu --wait`: the longest the frontend can take, which is at most two 500 ms
    callbacks per step, each wait and the whole timeout of every timed step (a failing one
    waits it out), plus 10 s for the request to be picked up."""
    return math.ceil(sum(1 + (step.get("wait_ms", 0) + step.get("timeout_ms", 0)) / 1000
                         for step in steps)) + 10


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Scenarios read back by default:\n" + "\n".join(
            textwrap.fill(f"{name}: {text}", 92, initial_indent="  ", subsequent_indent="    ")
            for name, text in READBACK.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenarios", nargs="*", default=list(READBACK),
                        help="scenarios.json names (default: the list below)")
    parser.add_argument("--output", type=Path, help="a new directory (default: runs/twwarhammer3/"
                        "lobby-readback-<time>)")
    args = parser.parse_args(argv)
    known = setup.scenarios()
    unknown = [name for name in args.scenarios if name not in known]
    if unknown:
        parser.error(f"unknown scenarios: {', '.join(unknown)}")
    output = (args.output or REPO_ROOT / "runs/twwarhammer3"
              / f"lobby-readback-{datetime.now():%Y%m%d-%H%M%S}").resolve()
    if output.exists():
        parser.error(f"{output} exists; name a new directory")
    files, written = {}, {}
    for name in args.scenarios:
        try:
            opening, steps = readback_steps(known[name])
        except ValueError as error:
            parser.error(f"{name}: {error}")
        text = json.dumps(steps, indent=1)
        files[name] = written.setdefault(text, (f"{name}.json", steps))[0]
    output.mkdir(parents=True)
    (output / "open-lobby.json").write_text(json.dumps(opening, indent=1) + "\n")
    for text, (file, _) in written.items():
        (output / file).write_text(text + "\n")
    write_json(output / "manifest.json", {
        "source_revision": git("rev-parse", "HEAD").strip(),
        "source_status": git("status", "--porcelain", "--", *SOURCES),
        "files": files, "scenarios": {name: known[name] for name in args.scenarios}})
    print(f"Wrote {len(written) + 1} step files to {output}; no game was started.")
    for name, file in files.items():
        if file != f"{name}.json":
            print(f"{name}: the same steps as {file}")
    print("\nIn the owner's game window, from the repository root:\n"
          "  uv run python -m twwarhammer3 launch\n"
          "then in a second terminal, one at a time, each ending with 'menu N: done' or 'failed':")
    for file, steps in [("open-lobby.json", opening), *written.values()]:
        print(f"  uv run python -m twwarhammer3 menu --steps {output / file} --wait {wait_s(steps)}"
              f" 2>&1 | tee {output / file.replace('.json', '.log')}")
    print("Ctrl-C in the launch terminal stops the game.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
