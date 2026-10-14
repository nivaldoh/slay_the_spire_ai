"""Checks for declared benchmark scenarios; setup data never enters policy inputs."""

import json
import math
import re
from collections import Counter

from twwarhammer3.protocol import ProtocolError

SETTINGS = "CustomBattleLobbyContext.SettingsContext."
TIMERS = {1200: "time_limit_short", 2400: "time_limit_medium", 3600: "time_limit_long"}
LOBBY_FIELDS = {
    "battle_type": "MapContext.BattleTypeString",
    "difficulty": "DifficultyLevelSettingContext.Key",
    "funds": "FundTypeSettingContext.Key",
    "time_limit_s": "TimeLimitSeconds",
    "ai_stats_modifier": "BattleAiStatsModifier",
}


def lobby_fields(scenario: dict) -> dict:
    fields = dict(LOBBY_FIELDS)
    if scenario["expect"].get("funds") == "funds_custom":
        fields["funds_amount"] = "CustomBudgetAmount"
    return fields


def validate_declaration(scenario: dict, config: dict, environment: dict) -> None:
    if not scenario.get("expect"):
        return
    if not scenario.get("map"):
        raise ValueError("benchmark scenario must pin its map")
    enemy = scenario.get("enemy")
    sides = [scenario["player"], *(enemy if isinstance(enemy, list) else [enemy] if enemy else [])]
    for side in sides:
        if not side.get("faction") or not side.get("units"):
            raise ValueError("benchmark armies must pin factions and explicit rosters")
    if config.get("attach") or not config.get("menu"):
        raise ValueError("benchmark setup requires its own launch and menu checks")
    expect = scenario["expect"]
    for key in (*lobby_fields(scenario), "unit_scale", "realism", "player_defends"):
        if key not in expect:
            raise ValueError(f"benchmark scenario is missing expect.{key}")
    timer = expect["time_limit_s"]
    if expect["funds"] == "funds_custom" and not (
            isinstance(expect["funds_amount"], int) and expect["funds_amount"] > 0):
        raise ValueError("custom funds must be a positive integer")
    if timer not in TIMERS or config["episode_timeout"] < timer + 120:
        raise ValueError("benchmark episode timeout must exceed a finite game timer by 120 s")
    if config["run_timeout"] < config["start_timeout"] + config["episodes"] * (
            config["episode_timeout"] + 60):
        raise ValueError("run timeout must cover setup and every episode timeout plus 60 s reset")
    prefs = environment.get("preferences") or {}
    for key, value in (("battle_realism_mode", str(expect["realism"]).lower()),):
        if str(prefs.get(key)) != value:
            raise ProtocolError(f"setup preference {key}: {prefs.get(key)!r}, expected {value!r}")


def menu_checks(scenario: dict) -> list[dict]:
    modifier = float(scenario["expect"]["ai_stats_modifier"])
    if not math.isfinite(modifier) or modifier <= 0:
        raise ValueError("AI stats modifier must be finite and positive")
    timer = TIMERS[scenario["expect"]["time_limit_s"]]
    checks = [{"context": "CcoFrontendRoot", "command": SETTINGS +
               'SetTimeLimitSettingContext(' + SETTINGS +
               f'TimeLimitSettingList.FirstContext(Key == "{timer}"))', "required": True},
              {"context": "CcoFrontendRoot", "command":
               SETTINGS + f"SetBattleAiStatsModifier({modifier:g})", "required": True}]
    checks.append({"context": "CcoFrontendRoot", "command": SETTINGS +
                   'SetFundTypeSettingContext(' + SETTINGS +
                   'FundTypeSettingList.FirstContext(Key == ' +
                   json.dumps(scenario["expect"]["funds"]) + '))', "required": True})
    if scenario["expect"]["funds"] == "funds_custom":
        checks.append({"context": "CcoFrontendRoot", "command": SETTINGS +
                       f'SetCustomFundsAmount("{scenario["expect"]["funds_amount"]}")',
                       "required": True})
    return checks + [{"context": "CcoFrontendRoot", "expression": SETTINGS + field,
             "expect": modifier if key == "ai_stats_modifier" else scenario["expect"][key],
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
        wanted = str(scenario["expect"][key]).lower()
        matches = re.findall(re.escape(SETTINGS + field) + r" = ([^\r\n]+)", log)
        actual = matches[-1].lower() if matches else None
        equal = (actual == wanted if key != "ai_stats_modifier" else
                 actual is not None and math.isclose(float(actual), float(wanted), abs_tol=1e-6))
        if not equal:
            raise ProtocolError(f"setup {key}: {matches!r}, expected {wanted!r}")
        checks[key] = scenario["expect"][key]
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
    enemy = scenario.get("enemy")
    enemies = enemy if isinstance(enemy, list) else [enemy] if enemy else []
    enemy_units = [unit for army in enemies for unit in army["units"]]
    for side, roster, wanted in (
        ("friendly", observation.get("friendly", []), scenario["player"]["units"]),
        ("enemy", observation.get("enemy_roster", []), enemy_units),
    ):
        actual = Counter(unit.get("type") for unit in roster)
        if actual != Counter(wanted):
            missing, extra = dict(Counter(wanted) - actual), dict(actual - Counter(wanted))
            raise ProtocolError(f"setup {side} roster mismatch: missing {missing}, extra {extra}")
        checks[side + "_roster"] = dict(actual)
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
    return checks


def fingerprint(observation: dict) -> dict:
    return {side: {unit["id"]: {key: unit.get(key) for key in ("type", "x", "z", "bearing")}
                   for unit in observation.get(side, [])}
            for side in ("friendly", "enemy")}


def compare_starts(reference: dict, current: dict) -> dict:
    deltas, missing = {}, []
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
    flagged = missing or [key for key, delta in deltas.items()
                          if (delta["distance_m"] or 0) > 1 or (delta["bearing_deg"] or 0) > 10]
    return {"flagged": bool(flagged), "missing_or_changed": missing, "units": deltas}
