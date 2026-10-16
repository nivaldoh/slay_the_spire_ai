"""Custom battle setup from a scenario: loading, lobby steps and the benchmark checks.

Setup data never enters policy inputs. The fields of a configs/twwarhammer3/scenarios.json
entry, and what reads them:

- ``base``: another entry this one copies. Dicts merge key by key; lists and other values
  replace (``scenarios``).
- ``player`` and ``enemy``: the armies. ``enemy`` is one army, a list of them (free-for-all)
  or null (survival, whose waves the game brings) (``sides``). Each army has:
  ``subculture`` (the race); ``faction`` (pins banner and recruitment cards; without it the
  game picks one); ``units`` (recruitment cards, the lord first, or null for the
  Autogenerate army button); ``mounts`` (zero-based recruitment index to mounted unit key,
  selected and verified in the lobby); ``recruitment_faction`` (card namespace when it
  differs from the selected banner); ``reinforcements`` (null for autogeneration, or an
  explicit list of non-lord unit cards, selected and read back in the lobby).
- ``map``: without it the lobby keeps the last map of the battle type.
- ``battle_type``: the lobby battle type, classic by default; the first observation must
  show its engine type (``expected_mode``).
- ``attacker``: ``"player"`` or ``"enemy"``; the lobby swaps the teams to match, and the
  first observation must show the player's role.
- ``random``: ``load_scenario`` draws a map and each side's race and autogenerates the
  armies. Such an entry may set ``battle_type``, ``attacker``, ``enemies`` (AI sides, 1 by
  default) and ``reinforcements`` (true: every side gets a reinforcing army).
- ``expect``: declares a benchmark, which must pin its map, factions and rosters
  (``validate_declaration``). The lobby sets ``funds``, ``funds_amount`` (with
  funds_custom), ``time_limit_s`` (1200, 2400 or 3600; null for survival/domination,
  whose hidden lobby timer is not a battle deadline) and ``ai_stats_modifier``
  (``menu_checks``) and verifies them together with ``battle_type`` (the engine name the
  top-level battle_type selects, such as land_normal) and ``difficulty``, which the game
  profile keeps (``check_menu``); the battle verifies ``unit_scale``, ``realism`` (also
  the game preference, ``check_preferences``) and ``player_defends`` (``check_battle``).
- ``protected``: unit types whose survival the report and replay measure.
- ``custom``: the versioned battery-evacuation rules, asset ids, extraction zone and
  deadline; optional ``deployment`` maps friendly/enemy ids to authored positions.
  Only public rules/progress enter ``mode.custom``; deployment remains private setup.
- ``name``, ``family``, ``brief``, ``split``, ``status``: report labels (the HTML report
  shows only scenarios with started trials; its reader text is in report_notes.json).
- ``content``, ``frozen_from``, ``substitutions``, ``calibration_change``, ``loadouts``:
  provenance that no code reads; it reaches reports through the manifest's scenario.
"""

import json
import math
import random
import re
import secrets
from collections import Counter

from gameai.provenance import REPO_ROOT
from twwarhammer3.protocol import ProtocolError

SCENARIOS_PATH = REPO_ROOT / "configs/twwarhammer3/scenarios.json"
CATALOGUE_PATH = SCENARIOS_PATH.with_name("custom_battle.json")
# Lobby expressions that guard menu steps ("when") and read or change settings.
LOBBY = "CustomBattleLobbyContext."
PLAYER_ATTACKS = LOBBY + "LocalPlayerSlotContext.TeamContext.IsAttacker"
SETTINGS = LOBBY + "SettingsContext."
NOT_STARTED = "the battle did not start"
# The battle's BattleTypeState for each lobby battle type, as the 2026-10-14 smoke battles
# reported them; classic was checked in b1 acceptance and free-for-all shares land_normal.
ENGINE_TYPES = {
    "classic": "land_normal",
    "conquest": "conquest", "domination": "domination", "free_for_all": "land_normal",
    "ambush": "land_ambush", "river_crossing_battle": "land_bridge",
    "underground_intercept": "underground_intercept",
    "unfortified_settlement": "settlement_unfortified", "siege": "settlement_standard",
    "survival": "survival",
}
TIMERS = {1200: "time_limit_short", 2400: "time_limit_medium", 3600: "time_limit_long"}
LOBBY_FIELDS = {
    "battle_type": "BattleTypeRecordContext.Key",
    "difficulty": "DifficultyLevelSettingContext.Key",
    "funds": "FundTypeSettingContext.Key",
    "time_limit_s": "TimeLimitSeconds",
    "ai_stats_modifier": "BattleAiStatsModifier",
}


def scenarios() -> dict:
    """Every entry of scenarios.json, with its ``base`` chain resolved."""
    entries = json.loads(SCENARIOS_PATH.read_text())

    def resolve(name: str) -> dict:
        entry = dict(entries[name])
        base = entry.pop("base", None)
        return merge(resolve(base), entry) if base else entry

    return {name: resolve(name) for name in entries}


def merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        both = isinstance(value, dict) and isinstance(base.get(key), dict)
        merged[key] = merge(base[key], value) if both else value
    return merged


def load_scenario(config: dict) -> dict:
    """The named scenario, or for a ``random`` entry a fresh draw: a map of the entry's
    battle type (classic by default) and each side's race from the catalogue, every army
    autogenerated, the faction (banner colours) left to the game. The seed (drawn when the
    job has none) is stored in the config, so a draw can be repeated; classic draws are the
    same as before battle types existed."""
    scenario = scenarios()[config["scenario"]]
    if not scenario.get("random"):
        return scenario
    if config.get("seed") is None:
        config["seed"] = secrets.randbelow(2**31)
    catalogue = json.loads(CATALOGUE_PATH.read_text())
    rng = random.Random(config["seed"])
    kind = scenario.get("battle_type")
    draw = {"map": rng.choice(catalogue["battle_type_maps"][kind] if kind else catalogue["maps"])}
    armies = [{"subculture": rng.choice(catalogue["races"]), "units": None}
              for _ in range(1 + scenario.get("enemies", 1))]
    if scenario.get("reinforcements"):
        for army in armies:
            army["reinforcements"] = None
    draw["player"], enemies = armies[0], armies[1:]
    draw["enemy"] = enemies[0] if len(enemies) == 1 else enemies or None
    if kind:
        draw["battle_type"] = kind
    if scenario.get("attacker"):
        draw["attacker"] = scenario["attacker"]
    return draw


def sides(scenario: dict) -> list[dict]:
    """The player, then each AI side in slot order."""
    enemy = scenario.get("enemy")
    return [scenario["player"], *(enemy if isinstance(enemy, list) else [enemy] if enemy else [])]


def expected_mode(scenario: dict) -> dict:
    """What the battle's first observation must show for the setup to count: the engine's
    type for a scenario that names its battle type, and the player's role when it names the
    attacker."""
    expect = {}
    if scenario.get("battle_type") in ENGINE_TYPES:
        expect["type"] = ENGINE_TYPES[scenario["battle_type"]]
    if scenario.get("attacker"):
        expect["role"] = "attacker" if scenario["attacker"] == "player" else "defender"
    return expect


def scenario_steps(scenario: dict) -> list[dict]:
    """Menu steps from the main menu to the start of a custom battle.

    The lobby keeps the last battle type, map and slots between battles (a survival battle
    removes the AI slot), so every scenario selects its battle type, and AI slots are added
    or removed until there is one per side, each step guarded by a ``when`` expression.
    Each side picks its race, then its faction if named (the game's pick varied between
    jobs), and clears the army; it then recruits its units by double-click (the last field
    of a lord's card id is 1) or autogenerates them. A benchmark makes every step required.
    """
    steps = [{"log": "custom battle; waiting for the main menu"},
             {"find": ["buttons_holder", "button_battle"], "click": True, "timeout_ms": 240000},
             {"find": ["battle_frame", "button_practice_battle"], "click": True,
              "timeout_ms": 20000}]
    steps += [
        {"find": ["tab_buttons", "button_tab_maps"], "click": True, "timeout_ms": 30000},
        {"wait_ms": 2000},
        {"find": ["map_type_list", "CcoBattleTypeRecord" + scenario.get("battle_type", "classic")],
         "click": True, "timeout_ms": 15000},
        {"wait_ms": 1500},
    ]
    if scenario.get("map"):
        steps += [
            # Entries scrolled out of the list never read as visible, so this does not wait.
            {"find": ["map_listview", "CcoCustomBattleMap" + scenario["map"]], "click": True},
            {"wait_ms": 2500},
            {"dump": "map_list.txt", "depth": 1, "find": ["map_listview", "list_box"]},
        ]
    steps += [{"find": ["tab_buttons", "button_tab_armies"], "click": True, "timeout_ms": 15000},
              {"wait_ms": 2000}]
    if scenario.get("expect"):
        # Apply the declared budget before recruiting or selecting paid mounts.
        steps += menu_checks(scenario)
    armies = sides(scenario)
    for count in range(2, len(armies) + 1):
        steps += [{"find": ["bottom_team_parent", "button_add_ai"], "click": True,
                   "timeout_ms": 15000, "when": f"{LOBBY}PlayerSlotList.Size < {count}"},
                  {"wait_ms": 1500}]
    for slot in range(7, len(armies) - 1, -1):
        steps += [{"find": [f"CcoCustomBattlePlayerSlotslot{slot}", "button_remove"],
                   "click": True, "when": f"{LOBBY}PlayerSlotList.Size > {slot}"}]
    if scenario.get("attacker"):
        swap = PLAYER_ATTACKS if scenario["attacker"] == "enemy" else "!" + PLAYER_ATTACKS
        steps += [{"find": ["team_spacer", "button_swap_attacker_defender"], "click": True,
                   "timeout_ms": 15000, "when": swap},
                  {"wait_ms": 1500}]
    for slot, side in enumerate(armies):
        steps += [
            {"find": ["teams_parent", f"CcoCustomBattlePlayerSlotslot{slot}"], "click": True,
             "timeout_ms": 30000},
            {"wait_ms": 2500},
            {"find": ["faction_pic_mask_parent", "button_select_race"], "click": True,
             "timeout_ms": 15000},
            {"wait_ms": 1500},
            # The race list never reads as visible from the root, so this find does not wait.
            {"find": ["button_select_race", "CcoSubcultureRecord" + side["subculture"]],
             "click": True},
            {"wait_ms": 2500},
        ]
        if side.get("faction"):
            steps += [
                {"find": ["faction_pic_mask_parent", "dropdown_context_scroll"], "click": True,
                 "timeout_ms": 15000},
                {"wait_ms": 1500},
                {"find": ["dropdown_context_scroll", "CcoFactionRecord" + side["faction"]],
                 "click": True},
                {"wait_ms": 2000},
            ]
        steps += [
            {"find": ["button_bar_parent", "button_clear"], "click": True, "timeout_ms": 15000},
            {"wait_ms": 800},
        ]
        if side["units"]:
            # The cards this race offers, so a card that is missing names the ones that exist.
            steps += [{"dump": f"cards_slot{slot}.txt", "depth": 3,
                       "find": ["recruitment_options_list"]}]
        if side["units"] is None:
            steps += [{"find": ["clear_autogen_parent", "button_autogen"], "click": True,
                       "timeout_ms": 15000},
                      {"wait_ms": 3000}]
        if "reinforcements" in side and side["reinforcements"] is None:
            # Domination and survival will not start without a reinforcing army.
            steps += [{"find": ["clear_autogen_reinforcement_parent",
                                "button_clear_reinforcements"], "click": True},
                      {"wait_ms": 800},
                      {"find": ["clear_autogen_reinforcement_parent",
                                "button_autogen_reinforcements"], "click": True,
                       "timeout_ms": 15000},
                      {"wait_ms": 3000}]
        for index, unit in enumerate(side["units"] or []):
            faction = side.get("recruitment_faction", side["faction"])
            card = f"CcoUnitsCustomBattlePermissionRecord{unit}:{faction}:{int(index == 0)}"
            steps += [{"find": [card, "unit_card"], "dblclick": True},
                      {"wait_ms": 600}]
            mounted = (side.get("mounts") or {}).get(str(index))
            if mounted:
                context = f"{LOBBY}PlayerSlotList.At({slot}).UnitList.At({index})."
                steps += [{"context": "CcoFrontendRoot", "command": context +
                           "ChangeMount(" + context + "AvailableMountsList.FirstContext(" +
                           "MountedUnitContext.Key == " + json.dumps(mounted) + "))",
                           "required": True},
                          {"wait_ms": 500},
                          {"context": "CcoFrontendRoot", "expression":
                           context + "UnitRecordContext.Key", "expect": mounted, "required": True}]
        if isinstance(side.get("reinforcements"), list):
            context = f"{LOBBY}PlayerSlotList.At({slot})."
            steps += [
                {"context": "CcoFrontendRoot", "command": context + "ClearReinforcements()"},
                {"context": "CcoFrontendRoot", "command":
                 context + "SetIsRecruitingReinforcements(true)"},
                {"wait_ms": 800},
            ]
            for unit in side["reinforcements"]:
                faction = side.get("recruitment_faction", side["faction"])
                card = f"CcoUnitsCustomBattlePermissionRecord{unit}:{faction}:0"
                steps += [{"find": [card, "unit_card"], "dblclick": True}, {"wait_ms": 600}]
            steps += [
                {"context": "CcoFrontendRoot", "expression": context +
                 'ReinforcingUnitList.JoinString(UnitRecordContext.Key, ";")',
                 "required": True},
                {"context": "CcoFrontendRoot", "command":
                 context + "SetIsRecruitingReinforcements(false)"},
            ]
    steps += [
        {"find": ["teams_parent", "CcoCustomBattlePlayerSlotslot0"], "click": True,
         "timeout_ms": 30000},
        {"wait_ms": 1500},
        {"dump": "army_player.txt", "depth": 1, "find": ["recruited_army_parent", "unit_list"]},
    ]
    if scenario.get("expect"):
        steps += menu_checks(scenario)
        steps = [{**step, "required": True} for step in steps]
    return steps + [
        {"find": ["start_button_frame", "button_start_battle"], "click": True, "timeout_ms": 15000},
        # The frontend unloads when the battle loads; still running, it says why not.
        {"wait_ms": 20000},
        {"context": "CcoFrontendRoot", "id": "", "expression": LOBBY + "ReadyStatusText"},
        {"log": NOT_STARTED},
    ]


def battle_units(army: dict) -> list[str]:
    """Recruitment cards become their declared mounted variants in battle."""
    units = list(army["units"])
    for index, mounted in (army.get("mounts") or {}).items():
        if (not isinstance(index, str) or not index.isdecimal() or str(int(index)) != index
                or int(index) >= len(units) or not isinstance(mounted, str) or not mounted):
            raise ValueError("mounts must map a zero-based recruitment index to a unit key")
        units[int(index)] = mounted
    return units


def lobby_fields(scenario: dict) -> dict:
    fields = dict(LOBBY_FIELDS)
    if scenario["expect"].get("time_limit_s") is None:
        fields.pop("time_limit_s")
        fields["timer_enabled"] = "IsTimeLimitUsed"
    if scenario["expect"].get("funds") == "funds_custom":
        fields["funds_amount"] = "CustomBudgetAmount"
    return fields


def lobby_value(scenario: dict, key: str):
    # A fort and a survival map both report land_normal as their map type. Verify the
    # selected lobby mode here; expected_mode separately checks the engine mode in battle.
    return (scenario.get("battle_type", "classic") if key == "battle_type"
            else scenario["expect"][key])


def fill_timeouts(scenario: dict, config: dict) -> None:
    """An unset episode timeout is a benchmark's game timer plus 120 s (else 3900 s); an
    unset run timeout is 8 h, or longer if setup and every episode plus a 60 s reset need
    it. These are the least ``validate_declaration`` accepts."""
    if config["episode_timeout"] is None:
        timer = (scenario.get("expect") or {}).get("time_limit_s")
        config["episode_timeout"] = timer + 120 if timer else 3900
    if config["run_timeout"] is None:
        config["run_timeout"] = max(8 * 3600, config["start_timeout"] + config["episodes"] * (
            config["episode_timeout"] + 60))


def validate_declaration(scenario: dict, config: dict) -> None:
    if scenario.get("custom"):
        validate_custom(scenario)
    if not scenario.get("expect"):
        return
    if not scenario.get("map"):
        raise ValueError("benchmark scenario must pin its map")
    for side in sides(scenario):
        if not side.get("faction") or not side.get("units"):
            raise ValueError("benchmark armies must pin factions and explicit rosters")
        battle_units(side)
        if "reinforcements" in side and not (
                isinstance(side["reinforcements"], list) and side["reinforcements"]
                and all(isinstance(unit, str) and unit for unit in side["reinforcements"])):
            raise ValueError("benchmark reinforcement pools must be explicit nonempty rosters")
    if config.get("attach"):
        raise ValueError("benchmark setup requires its own launch and menu checks")
    expect = scenario["expect"]
    if expect.get("battle_type") != ENGINE_TYPES[scenario.get("battle_type", "classic")]:
        raise ValueError("declared engine battle type does not match the selected lobby mode")
    for key in (*lobby_fields(scenario), "time_limit_s", "unit_scale", "realism", "player_defends"):
        if key not in expect:
            raise ValueError(f"benchmark scenario is missing expect.{key}")
    timer = expect["time_limit_s"]
    if expect["funds"] == "funds_custom" and not (
            isinstance(expect["funds_amount"], int) and expect["funds_amount"] > 0):
        raise ValueError("custom funds must be a positive integer")
    if timer is None and scenario.get("battle_type") in {"survival", "domination"}:
        if expect.get("timer_enabled") is not False:
            raise ValueError("timerless benchmark must declare timer_enabled false")
        if config["episode_timeout"] <= 0:
            raise ValueError("timerless battles require a positive episode wall limit")
    elif timer not in TIMERS or config["episode_timeout"] < timer + 120:
        raise ValueError("benchmark episode timeout must exceed a finite game timer by 120 s")
    if config["run_timeout"] < config["start_timeout"] + config["episodes"] * (
            config["episode_timeout"] + 60):
        raise ValueError("run timeout must cover setup and every episode timeout plus 60 s reset")


def validate_custom(scenario: dict) -> None:
    goal = scenario["custom"]
    if goal.get("kind") != "battery_evacuation" or goal.get("version") != 1:
        raise ValueError("unsupported custom objective or version")
    assets = goal.get("assets") or []
    friendly = {f"f{i + 1}" for i in range(len(scenario["player"]["units"]))}
    if len(assets) != 2 or len(set(assets)) != 2 or not set(assets) <= friendly:
        raise ValueError("evacuation requires two distinct friendly asset ids")
    def finite(value):
        return (isinstance(value, (float, int)) and not isinstance(value, bool)
                and math.isfinite(value))
    zone = goal.get("zone") or {}
    if not all(finite(zone.get(key)) for key in ("x", "z", "radius")) or zone["radius"] <= 0:
        raise ValueError("evacuation zone requires finite coordinates and a positive radius")
    deadline = goal.get("deadline_s")
    timer = (scenario.get("expect") or {}).get("time_limit_s")
    if not finite(deadline) or deadline <= 0 or timer is None or deadline >= timer:
        raise ValueError("evacuation deadline must precede the finite native timer")
    if not isinstance(goal.get("rules"), str) or not goal["rules"].strip():
        raise ValueError("custom objective requires public rules")
    for side, placements in goal.get("deployment", {}).items():
        if side not in {"friendly", "enemy"}:
            raise ValueError("unknown deployment side")
        army = scenario["player" if side == "friendly" else "enemy"]
        ids = {f"{'f' if side == 'friendly' else 'e'}{i + 1}" for i in range(len(army["units"]))}
        used = set()
        for placement in placements:
            unit = placement.get("id")
            if unit not in ids or unit in used or not all(
                    finite(placement.get(key)) for key in ("x", "z", "bearing", "width")):
                raise ValueError("invalid or repeated authored deployment")
            if placement["width"] <= 0:
                raise ValueError("deployment width must be positive")
            used.add(unit)


def check_preferences(scenario: dict, environment: dict) -> None:
    """A benchmark's realism must match the game preference, which the lobby cannot set."""
    if not scenario.get("expect"):
        return
    actual = (environment.get("preferences") or {}).get("battle_realism_mode")
    wanted = str(scenario["expect"]["realism"]).lower()
    if str(actual) != wanted:
        raise ProtocolError(f"setup preference battle_realism_mode: {actual!r},"
                            f" expected {wanted!r}")


def menu_checks(scenario: dict) -> list[dict]:
    modifier = float(scenario["expect"]["ai_stats_modifier"])
    if not math.isfinite(modifier) or modifier <= 0:
        raise ValueError("AI stats modifier must be finite and positive")
    timer = TIMERS.get(scenario["expect"]["time_limit_s"])
    checks = ([{"context": "CcoFrontendRoot", "command": SETTINGS +
               'SetTimeLimitSettingContext(' + SETTINGS +
               f'TimeLimitSettingList.FirstContext(Key == "{timer}"))', "required": True}]
              if timer else [])
    checks.append({"context": "CcoFrontendRoot", "command":
                   SETTINGS + f"SetBattleAiStatsModifier({modifier:g})", "required": True})
    checks.append({"context": "CcoFrontendRoot", "command": SETTINGS +
                   'SetFundTypeSettingContext(' + SETTINGS +
                   'FundTypeSettingList.FirstContext(Key == ' +
                   json.dumps(scenario["expect"]["funds"]) + '))', "required": True})
    if scenario["expect"]["funds"] == "funds_custom":
        checks.append({"context": "CcoFrontendRoot", "command": SETTINGS +
                       f'SetCustomFundsAmount("{scenario["expect"]["funds_amount"]}")',
                       "required": True})
    return checks + [{"context": "CcoFrontendRoot", "expression": SETTINGS + field,
             "expect": modifier if key == "ai_stats_modifier" else lobby_value(scenario, key),
             "required": True}
            for key, field in lobby_fields(scenario).items()]


def check_menu(scenario: dict, directory) -> dict:
    log = (directory / "menu.log").read_text()
    if re.search(r"not found:|failed:", log):
        raise ProtocolError("setup contains a failed menu step; see menu.log")
    dump = (directory / "map_list.txt").read_text()
    selected = re.findall(r"CcoCustomBattleMap(\S+).*?<selected>", dump)
    if selected != [scenario["map"]]:
        raise ProtocolError(f"setup map is {selected!r}, expected {scenario['map']!r}")
    checks = {"map": selected[0]}
    for key, field in lobby_fields(scenario).items():
        wanted = str(lobby_value(scenario, key)).lower()
        matches = re.findall(re.escape(SETTINGS + field) + r" = ([^\r\n]+)", log)
        actual = matches[-1].lower() if matches else None
        equal = (actual == wanted if key != "ai_stats_modifier" else
                 actual is not None and math.isclose(float(actual), float(wanted), abs_tol=1e-6))
        if not equal:
            raise ProtocolError(f"setup {key}: {matches!r}, expected {wanted!r}")
        checks[key] = lobby_value(scenario, key)
    for slot, army in enumerate(sides(scenario)):
        pool = army.get("reinforcements")
        if isinstance(pool, list):
            expression = (f"{LOBBY}PlayerSlotList.At({slot})."
                          'ReinforcingUnitList.JoinString(UnitRecordContext.Key, ";")')
            values = re.findall(re.escape(expression) + r" = ([^\r\n]*)", log)
            actual = Counter(filter(None, values[-1].split(";"))) if values else Counter()
            if actual != Counter(pool):
                raise ProtocolError(f"setup slot {slot} reinforcement pool: {dict(actual)!r},"
                                    f" expected {pool!r}")
            checks[f"reinforcements_slot{slot}"] = dict(actual)
    return checks


def check_battle(scenario: dict, observation: dict) -> dict:
    expected = scenario["expect"]
    settings = observation.get("setup") or {}
    checks = {}
    for key in ("unit_scale", "realism", "player_defends"):
        if settings.get(key) != expected[key]:
            raise ProtocolError(f"setup {key}: {settings.get(key)!r}, expected {expected[key]!r}")
        checks[key] = settings[key]
    modifiers = settings.get("army_ai_stats_modifiers") or []
    if not modifiers or any(not math.isclose(value, float(expected["ai_stats_modifier"]),
                                             abs_tol=1e-6) for value in modifiers):
        raise ProtocolError(f"setup army AI modifiers: {modifiers!r}, "
                            f"expected {expected['ai_stats_modifier']!r}")
    checks["army_ai_stats_modifiers"] = modifiers
    enemy_units = [unit for army in sides(scenario)[1:] for unit in battle_units(army)]
    for side, roster, wanted in (
        ("friendly", observation.get("friendly", []), battle_units(scenario["player"])),
        ("enemy", observation.get("enemy_roster", []), enemy_units),
    ):
        if side == "enemy" and scenario.get("battle_type") == "survival":
            continue  # Native waves are not the lobby's starting enemy army.
        actual = Counter(unit.get("type") for unit in roster)
        if actual != Counter(wanted):
            missing, extra = dict(Counter(wanted) - actual), dict(actual - Counter(wanted))
            raise ProtocolError(f"setup {side} roster mismatch: missing {missing}, extra {extra}")
        checks[side + "_roster"] = dict(actual)
    if expected["time_limit_s"] is None:
        if observation.get("remaining_ms") != -1:
            raise ProtocolError("setup: timerless mode reported a finite battle countdown")
        checks["time_limit_s"] = None
    pool = scenario["player"].get("reinforcements")
    if isinstance(pool, list):
        actual = Counter(unit["type"] for unit in
                         (observation.get("mode") or {}).get("reinforcements", []))
        if actual != Counter(pool):
            raise ProtocolError(f"setup reinforcement pool: {dict(actual)!r}, expected {pool!r}")
        checks["reinforcements"] = dict(actual)
    for side in ("player", "enemy"):
        army = scenario.get(side)
        if isinstance(army, dict):
            actual = (observation.get("armies", {}).get(side) or {}).get("faction")
            if actual != army["faction"]:
                raise ProtocolError(f"setup {side} faction: {actual!r}, "
                                    f"expected {army['faction']!r}")
    if not (observation.get("terrain") or {}).get("rows"):
        raise ProtocolError("setup: the declared terrain grid is missing")
    checks["terrain_grid"] = True
    if scenario.get("custom"):
        goal = scenario["custom"]
        if not (settings.get("custom") or {}).get("ok"):
            raise ProtocolError(f"custom setup failed: {settings.get('custom')!r}")
        public = (observation.get("mode") or {}).get("custom") or {}
        if (public.get("kind") != goal["kind"] or public.get("version") != goal["version"]
                or public.get("zone") != goal["zone"]
                or public.get("rules") != goal["rules"]
                or public.get("deadline_ms") != goal["deadline_s"] * 1000
                or [asset["id"] for asset in public.get("assets", [])] != goal["assets"]):
            raise ProtocolError("custom objective does not match its declaration")
        units = {unit["id"]: unit for unit in observation["friendly"]}
        if any(units[unit_id].get("class") != "artillery" for unit_id in goal["assets"]):
            raise ProtocolError("designated batteries are not artillery units")
        measured = settings["custom"].get("deployment") or {}
        for side, placements in goal.get("deployment", {}).items():
            actual = {p["id"]: p for p in measured.get(side, [])}
            for wanted in placements:
                found = actual.get(wanted["id"]) or {}
                if (found.get("x") is None or found.get("z") is None
                        or math.hypot(found["x"] - wanted["x"], found["z"] - wanted["z"]) > 2):
                    raise ProtocolError(f"authored deployment failed for {side}/{wanted['id']}")
        bounds = observation["terrain"].get("bounds") or {}
        if not (bounds.get("min_x", math.inf) < goal["zone"]["x"] < bounds.get("max_x", -math.inf)
                and bounds.get("min_z", math.inf) < goal["zone"]["z"]
                < bounds.get("max_z", -math.inf)):
            raise ProtocolError("extraction zone is outside the battlefield")
        checks["custom"] = {"kind": goal["kind"], "version": goal["version"]}
    return checks


def fingerprint(observation: dict) -> dict:
    fields = ("type", "x", "z", "bearing", "men", "men0", "hp", "ammo", "ammo0", "barrier",
              "can_fly", "flying")
    start = {side: {unit["id"]: {key: unit.get(key) for key in fields}
                    for unit in observation.get(side, [])}
             for side in ("friendly", "enemy")}
    for unit in observation.get("friendly", []):
        start["friendly"][unit["id"]]["abilities"] = sorted(
            ({key: ability.get(key) for key in ("key", "target", "mana", "uses", "cooldown_s",
                                               "cast_range", "radius", "duration_s")}
             for ability in unit.get("abilities") or []), key=lambda ability: ability["key"])
    mode = observation.get("mode") or {}
    start["resources"] = {"magic": observation.get("magic"), "supplies": mode.get("supplies"),
                          "tickets": mode.get("tickets")}
    if "reinforcements" in mode:
        start["resources"]["reinforcements"] = mode["reinforcements"]
    if "custom" in mode:
        start["resources"]["custom"] = {key: mode["custom"].get(key)
                                       for key in ("kind", "version", "zone", "deadline_ms")}
        start["resources"]["custom_deployment"] = (
            observation.get("setup", {}).get("custom", {}).get("deployment"))
    return start


def compare_starts(reference: dict, current: dict) -> dict:
    deltas, missing, changes = {}, [], {}
    if reference.get("resources") != current.get("resources"):
        changes["resources"] = {"before": reference.get("resources"),
                                "after": current.get("resources")}
    for side in ("friendly", "enemy"):
        for unit_id in reference.get(side, {}).keys() | current.get(side, {}).keys():
            before, after = reference.get(side, {}).get(unit_id), current.get(side, {}).get(unit_id)
            key = f"{side}/{unit_id}"
            if before is None or after is None or before["type"] != after["type"]:
                missing.append(key)
                continue
            position = (math.hypot(before["x"] - after["x"], before["z"] - after["z"])
                        if all(v is not None for v in
                               (before["x"], before["z"], after["x"], after["z"])) else None)
            angle = (abs((before["bearing"] - after["bearing"] + 180) % 360 - 180)
                     if before["bearing"] is not None and after["bearing"] is not None else None)
            deltas[key] = {"distance_m": position, "bearing_deg": angle}
            for field in ("men", "men0", "hp", "ammo", "ammo0", "barrier", "abilities",
                          "can_fly", "flying"):
                if before.get(field) != after.get(field):
                    changes[f"{key}/{field}"] = {"before": before.get(field),
                                                "after": after.get(field)}
    flagged = missing or [key for key, delta in deltas.items()
                          if (delta["distance_m"] or 0) > 1 or (delta["bearing_deg"] or 0) > 10]
    return {"flagged": bool(flagged or changes), "missing_or_changed": missing,
            "units": deltas, "resource_or_loadout_changes": changes}
