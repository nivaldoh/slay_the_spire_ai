"""Complete custom battles for any policy: launch once, play episodes, restart between.

A job owns the game for its whole duration. Each episode waits for a new battle id from
the mailbox (the first one after the frontend steps start a custom battle, later ones
after a ``restart`` control), then alternates observations and decisions: one request
in flight at a time. By default the acknowledgement observation starts the next
decision immediately; ``interval_ms`` optionally adds a wait after orders apply. Each
decision records the think time and the battle-time delay between the state it saw and the
orders being issued (or queued). Only an engine-reported result is a gameplay outcome.
"""

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from gameai.ledger import BudgetExhausted
from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from twwarhammer3.battle.stats import record
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
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
SESSION_KEYS = ("speed", "pause", "interval_ms", "observe_ms", "tick_ms", "autostart", "menu")


def play(output: Path, config: dict, *, policy_factory) -> dict:
    steps = scenario_steps(config["scenario"])
    output.mkdir(parents=True)
    write_json(output / "environment.json", collect_diagnostics())
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_revision": committed_revision("attributable battles", SOURCES),
        "source_files": source_fingerprints(SOURCES),
        "config": config,
        "status": "running",
        "episodes": [],
    }
    if config["policy"] == "llm":
        from twwarhammer3.battle.llm import SYSTEM_PROMPT_PATH

        (output / "system_prompt.md").write_bytes(SYSTEM_PROMPT_PATH.read_bytes())
        manifest["system_prompt_sha256"] = sha256(SYSTEM_PROMPT_PATH)
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
                                  mailbox, not_battle=previous)
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


def scenario_steps(name: str) -> list[dict]:
    """Menu steps from the main menu to the start of the named custom battle.

    Each side picks its race and its faction, clears the army and recruits its units by
    double-click; the first unit is the lord (the last field of a lord's card id is 1).
    Without the faction step the game picks one, which varied between jobs. The screen
    keeps the last map, so the map is not set.
    """
    scenario = json.loads(SCENARIOS_PATH.read_text())[name]
    steps = [{"log": f"custom battle {name}; waiting for the main menu"},
             {"find": ["buttons_holder", "button_battle"], "click": True, "timeout_ms": 240000},
             {"find": ["battle_frame", "button_practice_battle"], "click": True,
              "timeout_ms": 20000}]
    for slot, side in enumerate((scenario["player"], scenario["enemy"])):
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
            {"find": ["faction_pic_mask_parent", "dropdown_context_scroll"], "click": True,
             "timeout_ms": 15000},
            {"wait_ms": 1500},
            {"find": ["dropdown_context_scroll", "CcoFactionRecord" + side["faction"]],
             "click": True},
            {"wait_ms": 2000},
            {"find": ["button_bar_parent", "button_clear"], "click": True, "timeout_ms": 15000},
            {"wait_ms": 800},
        ]
        for index, unit in enumerate(side["units"]):
            card = f"CcoUnitsCustomBattlePermissionRecord{unit}:{side['faction']}:{int(index == 0)}"
            steps += [{"find": [card, "unit_card"], "dblclick": True, "timeout_ms": 15000},
                      {"wait_ms": 600}]
    return steps + [
        {"find": ["teams_parent", "CcoCustomBattlePlayerSlotslot0"], "click": True,
         "timeout_ms": 30000},
        {"wait_ms": 1500},
        {"dump": "army_player.txt", "depth": 1, "find": ["recruited_army_parent", "unit_list"]},
        {"find": ["start_button_frame", "button_start_battle"], "click": True, "timeout_ms": 15000},
    ]


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
        if "done" in lines or mailbox.read_observation() is not None:
            return
        if "failed" in lines:
            raise ProtocolError("custom battle setup failed: " + lines[-2])
        if time.monotonic() > deadline:
            raise MailboxTimeout("the custom battle steps did not finish")
        time.sleep(1)


def play_episode(directory: Path, config: dict, policy, mailbox: Mailbox, *,
                 not_battle: str | None) -> dict:
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
        _drive(config, policy, mailbox, not_battle, result, event, started)
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
        result["elapsed_seconds"] = round(time.monotonic() - started, 1)
        result["llm"] = dict(getattr(policy, "totals", {}))
        delays = result["delays_ms"]
        result["delay_s"] = round(statistics.mean(delays) / 1000, 2) if delays else None
        (directory / "mod.log").write_text(mailbox.log_since(log_offset))
        write_json(directory / "result.json", result)
        trace.close()
    return result


def _drive(config, policy, mailbox, not_battle, result, event, started) -> None:
    deadline = started + config["episode_timeout"]
    first = mailbox.wait_new_battle(not_battle=not_battle, timeout=config["start_timeout"])
    battle = result["battle"] = first["battle"]
    seq = first["seq"]
    event("battle", observation=first)
    applied_ms = None
    outstanding = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result.update(status="truncated", reason="episode_timeout")
            return
        observation = mailbox.wait_observation(
            battle=battle, after_seq=seq, timeout=min(config["observation_timeout"], remaining))
        seq = observation["seq"]
        if "scenario" not in result and observation.get("friendly"):
            result["scenario"] = scenario_key(observation)
            result["roster"] = {
                "friendly": [unit.get("type") for unit in observation["friendly"]],
                "enemy": [unit.get("type") for unit in observation.get("enemy_roster", [])],
            }
            event("roster", observation=observation)
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
        if config["pause"] and not observation.get("awaiting_orders"):
            continue
        read_at = time.monotonic()
        event("observation", observation=observation,
              since_previous_applied_ms=(observation["time_ms"] - applied_ms
                                         if applied_ms is not None else None))
        orders = policy.decide(observation)
        try:
            validate_orders(orders, observation)
        except IllegalActionError as exc:
            event("invalid", error=str(exc), orders=orders)
            result["invalid"] += 1
            orders = []
        request = mailbox.write_orders(battle, observation["seq"], orders)
        event("decision", seq=observation["seq"], time_ms=observation["time_ms"],
              request=request, orders=orders, behavior=policy.metadata())
        outstanding = {"request": request, "observed_ms": observation["time_ms"],
                       "read": read_at, "sent": time.monotonic()}
        result["decisions"] += 1
