"""Complete custom battles for any policy: launch once, play episodes, restart between.

A job owns the game for its whole duration. Each episode waits for a new battle id from
the mailbox (the first one after the frontend steps start a custom battle, later ones
after a ``restart`` control), then alternates observations and decisions: one request
in flight at a time. By default the acknowledgement observation starts the next
decision immediately; ``interval_ms`` optionally adds a wait after orders apply. Each
decision records the think time and the battle-time delay between the state it saw and the
orders being issued (or queued). A fast policy decides at the mod's tick rate, so the trace
keeps every decision with orders, an error or new metadata, and quiet ones once per
``observe_ms``. Only an engine-reported result is a gameplay outcome.
"""

import json
import random
import re
import secrets
import shutil
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from gameai.ledger import BudgetExhausted
from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from twwarhammer3.battle.stats import record
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox, require_realtime
from twwarhammer3.engine.runtime import BRIDGE_DIR, OwnedGame, RuntimeLock, prepare_runtime
from twwarhammer3.protocol import (
    BattleRestarted,
    IllegalActionError,
    MailboxTimeout,
    PolicyFailure,
    ProtocolError,
    scenario_key,
    validate_orders,
)

SCORED = {"won", "lost", "draw", "policy_failure", "truncated"}
SOURCES = ("src/gameai", "src/twwarhammer3", "configs/twwarhammer3", "pyproject.toml",
           "uv.lock", ".python-version")
SCENARIOS_PATH = Path(__file__).resolve().parents[3] / "configs/twwarhammer3/scenarios.json"
CATALOGUE_PATH = SCENARIOS_PATH.with_name("custom_battle.json")
CAPTION_LIMIT = 400
SESSION_KEYS = ("speed", "pause", "interval_ms", "observe_ms", "tick_ms", "autostart", "menu")
# Lobby expressions that guard menu steps ("when").
LOBBY = "CustomBattleLobbyContext."
PLAYER_ATTACKS = LOBBY + "LocalPlayerSlotContext.TeamContext.IsAttacker"
NOT_STARTED = "the battle did not start"
# The battle's BattleTypeState for each lobby battle type, as the 2026-10-14 smoke battles
# reported them (classic is unverified, and free-for-all shares land_normal).
ENGINE_TYPES = {
    "conquest": "conquest", "domination": "domination", "free_for_all": "land_normal",
    "ambush": "land_ambush", "river_crossing_battle": "land_bridge",
    "underground_intercept": "underground_intercept",
    "unfortified_settlement": "settlement_unfortified", "siege": "settlement_standard",
    "survival": "survival",
}


def play(output: Path, config: dict, *, policy_factory) -> dict:
    require_realtime(config)
    scenario = load_scenario(config)
    steps = scenario_steps(scenario)
    expect = expected_mode(scenario)
    output.mkdir(parents=True)
    write_json(output / "environment.json", collect_diagnostics())
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_revision": committed_revision("attributable battles", SOURCES),
        "source_files": source_fingerprints(SOURCES),
        "config": config,
        "scenario": scenario,
        "status": "running",
        "episodes": [],
    }
    if config["policy"] in ("llm", "commander"):
        from twwarhammer3.battle import commander, llm

        prompt = (commander.PROMPT_PATH if config["policy"] == "commander"
                  else llm.SYSTEM_PROMPT_PATH)
        (output / "system_prompt.md").write_bytes(prompt.read_bytes())
        manifest["system_prompt_sha256"] = sha256(prompt)
    write_json(output / "manifest.json", manifest)
    session = {key: config[key] for key in SESSION_KEYS}

    def episodes(mailbox: Mailbox) -> str:
        previous = None
        for index in range(config["episodes"]):
            if source_fingerprints(SOURCES) != manifest["source_files"]:
                raise RuntimeError("Implementation changed during the job; stopped")
            if index:
                mailbox.write_control(previous, "restart")
            result = play_episode(output / f"episode-{index:04d}", config, policy_factory(),
                                  mailbox, not_battle=previous, expect=expect)
            previous = result.get("battle")
            manifest["episodes"].append(result)
            write_json(output / "manifest.json", manifest)
            record(Path(config["results"]), output, output / f"episode-{index:04d}")
            print(json.dumps({key: result.get(key) for key in (
                "episode", "status", "battle_s", "decisions", "invalid", "delay_s", "error",
            )}, sort_keys=True), flush=True)
            if result["status"] not in SCORED:
                return "stopped"
        return "completed"

    try:
        if config["attach"]:
            # The running game keeps the session it was launched with.
            live = json.loads((BRIDGE_DIR / "session.json").read_text())
            require_realtime(live)
            config.update({key: live[key] for key in SESSION_KEYS if key in live})
            write_json(output / "manifest.json", manifest)
            manifest["status"] = episodes(Mailbox(BRIDGE_DIR, job=live["job"]))
        else:
            with RuntimeLock():
                manifest["deployment"] = prepare_runtime()
                write_json(output / "manifest.json", manifest)
                mailbox = Mailbox(BRIDGE_DIR, job=output.name)
                mailbox.reset()
                mailbox.write_session(session)
                with OwnedGame(output / "game.log", timeout=config["run_timeout"]) as game:
                    manifest["game"] = game.info
                    start_frontend(mailbox, config, output, steps)
                    manifest["status"] = episodes(mailbox)
    except BaseException:
        manifest["status"] = "interrupted"
        raise
    finally:
        write_json(output / "manifest.json", manifest)
    return manifest


def load_scenario(config: dict) -> dict:
    """The named entry of scenarios.json, or for a ``random`` entry a fresh draw: a map and
    each side's race from the catalogue, both armies autogenerated, the faction (banner
    colours) left to the game. The seed (drawn when the job has none) is stored in the
    config, so a draw can be repeated."""
    scenario = json.loads(SCENARIOS_PATH.read_text())[config["scenario"]]
    if not scenario.get("random"):
        return scenario
    if config.get("seed") is None:
        config["seed"] = secrets.randbelow(2**31)
    catalogue = json.loads(CATALOGUE_PATH.read_text())
    rng = random.Random(config["seed"])
    draw = {"map": rng.choice(catalogue["maps"])}
    for side in ("player", "enemy"):
        draw[side] = {"subculture": rng.choice(catalogue["races"]), "units": None}
    return draw


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


def sides(scenario: dict) -> list[dict]:
    """The player, then each AI side in slot order: one enemy, a list of them (free-for-all)
    or none (survival, whose waves the game brings)."""
    enemy = scenario.get("enemy")
    return [scenario["player"], *(enemy if isinstance(enemy, list) else [enemy] if enemy else [])]


def scenario_steps(scenario: dict) -> list[dict]:
    """Menu steps from the main menu to the start of a custom battle.

    Every scenario selects its ``battle_type`` (classic by default), since the lobby keeps
    the last one, and a scenario with a ``map`` selects that map; without one the screen
    keeps the last map of the type. The lobby keeps its slots between
    battles (a survival battle removes the AI slot), so AI slots are added or removed until
    there is one per side, each step guarded by a ``when`` expression. ``attacker``
    ("player" or "enemy") swaps the teams if the player's team has the other role. Each
    side picks its race, then its faction if the scenario names one (without it the game
    picks one, which varied between jobs), and clears the army; it then recruits its units
    by double-click (the first unit is the lord: the last field of a lord's card id is 1),
    or with ``units`` null the game's Autogenerate army button fills it. A side with
    ``reinforcements`` (null: autogenerated) also gets a reinforcing army, which domination
    and survival battles require.
    """
    steps = [{"log": "custom battle; waiting for the main menu"},
             {"find": ["buttons_holder", "button_battle"], "click": True, "timeout_ms": 240000},
             {"find": ["battle_frame", "button_practice_battle"], "click": True,
              "timeout_ms": 20000}]
    # The lobby keeps the last battle type, so it is always selected.
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
        if side["units"] is None:
            steps += [{"find": ["clear_autogen_parent", "button_autogen"], "click": True,
                       "timeout_ms": 15000},
                      {"wait_ms": 3000}]
        if "reinforcements" in side:
            # Domination and survival will not start without a reinforcing army.
            steps += [{"find": ["clear_autogen_reinforcement_parent",
                                "button_clear_reinforcements"], "click": True},
                      {"wait_ms": 800},
                      {"find": ["clear_autogen_reinforcement_parent",
                                "button_autogen_reinforcements"], "click": True,
                       "timeout_ms": 15000},
                      {"wait_ms": 3000}]
        for index, unit in enumerate(side["units"] or []):
            card = f"CcoUnitsCustomBattlePermissionRecord{unit}:{side['faction']}:{int(index == 0)}"
            steps += [{"find": [card, "unit_card"], "dblclick": True, "timeout_ms": 15000},
                      {"wait_ms": 600}]
    return steps + [
        {"find": ["teams_parent", "CcoCustomBattlePlayerSlotslot0"], "click": True,
         "timeout_ms": 30000},
        {"wait_ms": 1500},
        {"dump": "army_player.txt", "depth": 1, "find": ["recruited_army_parent", "unit_list"]},
        {"find": ["start_button_frame", "button_start_battle"], "click": True, "timeout_ms": 15000},
        # The frontend unloads when the battle loads; still running, it says why not.
        {"wait_ms": 20000},
        {"context": "CcoFrontendRoot", "id": "", "expression": LOBBY + "ReadyStatusText"},
        {"log": NOT_STARTED},
    ]


def save_dumps(mailbox: Mailbox, output: Path, steps: list[dict]) -> None:
    for step in steps:
        if step.get("dump") and (mailbox.directory / step["dump"]).exists():
            shutil.copyfile(mailbox.directory / step["dump"], output / step["dump"])


def start_frontend(mailbox: Mailbox, config: dict, output: Path, steps: list[dict]) -> None:
    """Wait for the frontend script, then run the custom battle steps to the end.

    Runtime preparation skips startup movies; the first step waits for the main menu
    without desktop input. The frontend script unloads when the battle
    loads, so a battle observation also ends the wait.
    """
    if not config["menu"]:
        return
    deadline = time.monotonic() + config["start_timeout"]
    while "frontend loaded" not in mailbox.log_since(0, "menu.log"):
        if time.monotonic() > deadline:
            raise MailboxTimeout("the frontend script did not report in")
        time.sleep(1)
    offset = mailbox.log_offset("menu.log")
    mailbox.write_menu(steps)
    while True:
        lines = mailbox.log_since(offset, "menu.log").splitlines()
        (output / "menu.log").write_text(mailbox.log_since(0, "menu.log"))
        if "failed" in lines:
            raise ProtocolError("custom battle setup failed: " + lines[-2])
        if any(line.endswith(NOT_STARTED) for line in lines):
            reason = next((line for line in lines if "ReadyStatusText" in line), "")
            reason = re.sub(r"\[\[.*?\]\]", "", reason.split(" = ", 1)[-1])
            raise ProtocolError("custom battle did not start: " + reason)
        if "done" in lines or mailbox.read_observation() is not None:
            save_dumps(mailbox, output, steps)
            return
        if time.monotonic() > deadline:
            raise MailboxTimeout("the custom battle steps did not finish")
        time.sleep(1)


def play_episode(directory: Path, config: dict, policy, mailbox: Mailbox, *,
                 not_battle: str | None, expect: dict | None = None) -> dict:
    require_realtime(config)
    directory.mkdir()
    trace = (directory / "trace.jsonl").open("x", buffering=1)
    started = time.monotonic()
    result = {"episode": directory.name, "status": "interrupted", "decisions": 0, "invalid": 0,
              "delays_ms": [], "think_s": []}
    log_offset = mailbox.log_offset()

    def event(kind: str, **fields) -> None:
        trace.write(json.dumps({"kind": kind, "elapsed": round(time.monotonic() - started, 3),
                                **fields}, sort_keys=True) + "\n")

    try:
        _drive(config, policy, mailbox, not_battle, result, event, started, expect or {})
    except MailboxTimeout as exc:
        past = time.monotonic() - started > config["episode_timeout"]
        result.update(status="truncated" if past else "infrastructure_failure", error=str(exc))
    except BattleRestarted as exc:
        result.update(status="infrastructure_failure", error=str(exc))
    except PolicyFailure as exc:
        result.update(status="policy_failure", error=str(exc), failure=exc.failure)
    except BudgetExhausted as exc:
        result.update(status="budget_exhausted", error=str(exc))
    except ProtocolError as exc:
        result.update(status="unsupported_or_invalid", error=str(exc))
    except Exception as exc:
        result.update(status="infrastructure_failure", error=str(exc),
                      error_type=type(exc).__name__)
    finally:
        if hasattr(policy, "close"):
            policy.close()  # a call still in flight is waited for and charged
        result["elapsed_seconds"] = round(time.monotonic() - started, 1)
        result["llm"] = dict(getattr(policy, "totals", {}))
        delays = result["delays_ms"]
        result["delay_s"] = round(statistics.mean(delays) / 1000, 2) if delays else None
        (directory / "mod.log").write_text(mailbox.log_since(log_offset))
        write_json(directory / "result.json", result)
        trace.close()
    return result


def caption(observation: dict, behavior: dict, orders: list[dict]) -> str | None:
    """Advisor text for a decision that carries a model's reply: what it saw and decided."""
    if not behavior.get("reason"):
        return None
    from twwarhammer3.battle.commander import describe_plan
    from twwarhammer3.battle.digest import _strength
    from twwarhammer3.battle.llm import describe_orders

    seconds = observation["time_ms"] / 1000
    if "plan" in behavior:
        head = (f"{seconds:.0f} s: {behavior['model']} plan from the state at"
                f" {seconds - behavior['plan_age_s']:.0f} s")
        decided = describe_plan(behavior["plan"])
    else:
        head = f"{seconds:.0f} s: {behavior.get('model', 'model')} saw {_strength(observation)}"
        decided = describe_orders(orders)
    return f"{head}\n{behavior['reason']}\n{decided}"[:CAPTION_LIMIT]


def _drive(config, policy, mailbox, not_battle, result, event, started, expect) -> None:
    deadline = started + config["episode_timeout"]
    first = mailbox.wait_new_battle(not_battle=not_battle, timeout=config["start_timeout"])
    battle = result["battle"] = first["battle"]
    seq = first["seq"]
    event("battle", observation=first)
    applied_ms = None
    outstanding = None
    logged_ms, logged_behavior = None, None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result.update(status="truncated", reason="episode_timeout")
            return
        observation = mailbox.wait_observation(
            battle=battle, after_seq=seq, timeout=min(config["observation_timeout"], remaining))
        if observation.get("awaiting_orders") or observation.get("speed", 1) != 1:
            raise ProtocolError("WH3 observation is not from an unpaused 1x battle")
        seq = observation["seq"]
        if "scenario" not in result and observation.get("friendly"):
            result["scenario"] = scenario_key(observation)
            result["roster"] = {
                "friendly": [unit.get("type") for unit in observation["friendly"]],
                "enemy": [unit.get("type") for unit in observation.get("enemy_roster", [])],
            }
            event("roster", observation=observation)
            mode = observation.get("mode") or {}
            result["mode"] = {key: mode.get(key) for key in ("type", "role")}
            for key, wanted in expect.items():
                if mode.get(key) != wanted:
                    raise ProtocolError(f"setup: the battle's {key} is {mode.get(key)!r},"
                                        f" the scenario wants {wanted!r}")
        ack = observation.get("orders")
        if outstanding and ack and ack.get("request") == outstanding["request"]:
            latency = {
                "think_s": round(outstanding["sent"] - outstanding["read"], 3),
                "roundtrip_s": round(time.monotonic() - outstanding["read"], 3),
                "delay_ms": ack["applied_ms"] - outstanding["observed_ms"],
            }
            result["invalid"] += sum(1 for item in ack.get("results", []) if not item.get("ok"))
            result["delays_ms"].append(latency["delay_ms"])
            result["think_s"].append(latency["think_s"])
            if outstanding["logged"]:
                event("ack", request=ack["request"], ack=ack, latency=latency)
            policy.acknowledge(ack, latency)
            applied_ms = ack["applied_ms"]
            outstanding = None
        if observation.get("result"):
            result.update(status=observation["result"], battle_ms=observation.get("time_ms"),
                          battle_s=round(observation.get("time_ms", 0) / 1000),
                          final=observation.get("final"))
            event("result", observation=observation)
            return
        if outstanding or observation.get("phase") != "Deployed":
            continue
        if applied_ms is not None and observation["time_ms"] < applied_ms + config["interval_ms"]:
            continue
        read_at = time.monotonic()
        since = observation["time_ms"] - applied_ms if applied_ms is not None else None
        try:
            orders, invalid = policy.decide(observation), None
        except BaseException:
            event("observation", observation=observation, since_previous_applied_ms=since)
            raise
        try:
            validate_orders(orders, observation)
        except IllegalActionError as exc:
            invalid = {"error": str(exc), "orders": orders}
            result["invalid"] += 1
            orders = []
        behavior = policy.metadata()
        # A fast policy decides at the tick rate: quiet decisions are logged once per
        # observe_ms, and every decision with orders, an error or new metadata is logged.
        logged = (orders or invalid or behavior != logged_behavior or logged_ms is None
                  or observation["time_ms"] - logged_ms >= config["observe_ms"])
        if logged:
            event("observation", observation=observation, since_previous_applied_ms=since)
            if invalid:
                event("invalid", **invalid)
        say = caption(observation, behavior, orders) if config.get("show") else None
        request = mailbox.write_orders(battle, observation["seq"], orders, say=say)
        if logged:
            event("decision", seq=observation["seq"], time_ms=observation["time_ms"],
                  request=request, orders=orders, behavior=behavior)
            logged_ms, logged_behavior = observation["time_ms"], behavior
        outstanding = {"request": request, "observed_ms": observation["time_ms"],
                       "read": read_at, "sent": time.monotonic(), "logged": bool(logged)}
        result["decisions"] += 1
