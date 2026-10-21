"""Complete custom battles for any policy: launch once, play episodes, restart between.

A job owns the game for its whole duration. Each episode waits for a new battle id from
the mailbox (the first one after the frontend steps start a custom battle, later ones
after a ``restart`` control), then alternates observations and decisions: one request
in flight at a time. By default the acknowledgement observation starts the next
decision immediately; ``interval_ms`` optionally adds a wait after orders apply. The
battle never waits for a controller: a decide call with no valid reply or a provider error
sends no orders and the controller is asked again (any other controller exception, or a key,
credit or budget stop, ends the episode), and a battle that ended during a decide call keeps
its result unless the call stopped for a key, credit or budget reason. Each acknowledged
decision records the think time and the battle-time delay between the state it saw and the
orders being issued (or queued); one still unacknowledged when the episode ends records
neither. A fast policy decides at the mod's tick rate, so the trace
keeps every decision with orders, an error or new metadata, and quiet ones once per
``observe_ms``. Only an engine-reported result is a gameplay outcome. ``setup`` turns the
scenario into lobby steps and checks.
"""

import json
import re
import shutil
import statistics
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from twwarhammer3.battle.capture import (
    PassiveCapture,
    copy_presentation,
    copy_recording,
    imagery_settings,
    recording_settings,
)
from twwarhammer3.battle.commander import describe_plan
from twwarhammer3.battle.controllers import (
    MODEL_POLICIES,
    MODEL_PROMPTS,
    card,
    policy_parts,
    rotation,
)
from twwarhammer3.battle.digest import strength
from twwarhammer3.battle.llm import describe_orders
from twwarhammer3.battle.setup import (
    NOT_STARTED,
    check_battle,
    check_menu,
    compare_starts,
    expected_mode,
    fill_timeouts,
    fingerprint,
    load_scenario,
    scenario_steps,
    validate_declaration,
)
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

SCORED = {"won", "lost", "draw"}
SOURCES = ("src/gameai", "src/twwarhammer3", "configs/twwarhammer3", "pyproject.toml",
           "uv.lock", ".python-version")
TRACK = "obs-v4+terrain/act-v2/live-1x"
EVALUATOR_VERSION = 2
CAPTION_LIMIT = 400
# The mod reads observe_ms, tick_ms, record_replay and stills; speed and pause let
# ``play --attach`` check that the running game keeps the realtime rule.
SESSION_KEYS = ("speed", "pause", "observe_ms", "tick_ms", "record_replay", "stills")


def session(config: dict) -> dict:
    """session.json: the job's settings and the mod's switches, all on."""
    return {"enabled": True, "autostart": True, "menu": True,
            **{key: config[key] for key in SESSION_KEYS}}


def play(output: Path, config: dict, *, makers: dict) -> dict:
    """Run a job; ``makers`` maps each policy name to a constructor of fresh controllers."""
    job_started = time.time()
    require_realtime(config)
    trials = rotation(config)
    scenario = load_scenario(config)
    fill_timeouts(scenario, config)
    validate_declaration(scenario, config)
    environment = collect_diagnostics()
    steps = scenario_steps(scenario, build_id=environment.get("game", {}).get("steam_build_id"))
    revision = committed_revision("attributable battles", SOURCES)
    files = source_fingerprints(SOURCES)
    output.mkdir(parents=True)
    write_json(output / "environment.json", environment)
    manifest = {
        "schema_version": 1,
        "model_exchange_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_revision": revision,
        "source_files": files,
        "config": config,
        "scenario": scenario,
        "trials": trials,
        "track": TRACK,
        "evaluator_version": EVALUATOR_VERSION,
        "status": "running",
        "episodes": [],
        "recorder": recording_settings(config),
        "imagery": imagery_settings(config),
    }
    bases = {policy_parts(name, config)[0] for name in config["policy"].split(",")}
    for name in sorted(bases & MODEL_POLICIES):  # one prompt per base, whatever its models
        prompt = MODEL_PROMPTS[name]
        (output / f"{name}_prompt.md").write_bytes(prompt.read_bytes())
        manifest[f"{name}_prompt_sha256"] = sha256(prompt)
    write_json(output / "manifest.json", manifest)

    def episodes(mailbox: Mailbox) -> str:
        previous = None
        for index, trial in enumerate(trials):
            if source_fingerprints(SOURCES) != manifest["source_files"]:
                raise RuntimeError("Implementation changed during the job; stopped")
            if index:
                mailbox.write_control(previous, "restart")
            directory = output / f"episode-{index:04d}"
            reference = manifest["episodes"][0].get("start") if manifest["episodes"] else None
            try:
                result = play_episode(directory, {**config, **trial, "slot": index},
                                      makers[trial["policy"]], mailbox, not_battle=previous,
                                      scenario=scenario, start_reference=reference)
            finally:
                # KeyboardInterrupt still leaves the started trial in both records.
                if (directory / "result.json").exists():
                    saved = json.loads((directory / "result.json").read_text())
                    manifest["episodes"].append(saved)
                    write_json(output / "manifest.json", manifest)
                    record(Path(config["results"]), output, directory)
            previous = result.get("battle")
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
            config["record_replay"] = live.get("record_replay", False)
            config["stills"] = live.get("stills", False)
            manifest["recorder"] = recording_settings(config)
            manifest["imagery"] = imagery_settings(config)
            write_json(output / "manifest.json", manifest)
            manifest["status"] = episodes(Mailbox(BRIDGE_DIR, job=live["job"]))
        else:
            with RuntimeLock():
                manifest["deployment"] = prepare_runtime()
                write_json(output / "manifest.json", manifest)
                mailbox = Mailbox(BRIDGE_DIR, job=output.name)
                mailbox.reset()
                settings = {**session(config), **({"custom": scenario["custom"]}
                                                 if scenario.get("custom") else {})}
                with (mailbox.owned_session(settings),
                      OwnedGame(output / "game.log", timeout=config["run_timeout"]) as game):
                    manifest["game"] = game.info
                    with PassiveCapture(BRIDGE_DIR, job=mailbox.job, pid=game.info.get("pid", 0),
                                        enabled=config.get("stills", False)):
                        start_frontend(mailbox, config, output, steps)
                        if scenario.get("expect"):
                            manifest["setup_checks"] = check_menu(scenario, output)
                            write_json(output / "manifest.json", manifest)
                        manifest["status"] = episodes(mailbox)
    except ProtocolError as exc:
        manifest.update(status="setup_failure", error=str(exc))
        raise
    except BaseException as exc:
        status = "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else (
            "infrastructure_failure")
        manifest.update(status=status, error=str(exc) or type(exc).__name__,
                        error_type=type(exc).__name__)
        raise
    finally:
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        manifest["wall_seconds"] = time.time() - job_started
        write_json(output / "manifest.json", manifest)
    return manifest


def save_dumps(mailbox: Mailbox, output: Path, steps: list[dict]) -> None:
    log = mailbox.log_since(0, "menu.log")
    for step in steps:
        if (step.get("dump") and f" lines to {step['dump']}" in log
                and (mailbox.directory / step["dump"]).exists()):
            shutil.copyfile(mailbox.directory / step["dump"], output / step["dump"])


def start_frontend(mailbox: Mailbox, config: dict, output: Path, steps: list[dict]) -> None:
    """Wait for the frontend script, then run the custom battle steps to the end.

    Runtime preparation skips startup movies; the first step waits for the main menu
    without desktop input. The frontend script unloads when the battle
    loads, so a battle observation also ends the wait.
    """
    deadline = time.time() + config["start_timeout"]
    while "frontend loaded" not in mailbox.log_since(0, "menu.log"):
        if time.time() > deadline:
            raise MailboxTimeout("the frontend script did not report in")
        time.sleep(1)
    offset = mailbox.log_offset("menu.log")
    request = mailbox.write_menu(steps)
    try:
        while True:
            lines = mailbox.log_since(offset, "menu.log").splitlines()
            (output / "menu.log").write_text(mailbox.log_since(0, "menu.log"))
            if f"menu {request}: failed" in lines:
                reason = next((line for line in reversed(lines) if ": failed:" in line),
                              next((line for line in reversed(lines) if line.startswith("step ")),
                                   "see menu.log"))
                raise ProtocolError("custom battle setup failed: " + reason)
            if any(line.endswith(NOT_STARTED) for line in lines):
                reason = next((line for line in lines if "ReadyStatusText" in line), "")
                reason = re.sub(r"\[\[.*?\]\]", "", reason.split(" = ", 1)[-1])
                raise ProtocolError("custom battle did not start: " + reason)
            if f"menu {request}: done" in lines or mailbox.read_observation() is not None:
                return
            if time.time() > deadline:
                raise MailboxTimeout("the custom battle steps did not finish")
            time.sleep(1)
    finally:
        save_dumps(mailbox, output, steps)


def play_episode(directory: Path, config: dict, make_policy, mailbox: Mailbox, *,
                 not_battle: str | None, scenario: dict | None = None,
                 start_reference: dict | None = None) -> dict:
    """One episode with a fresh controller from ``make_policy``. The job's ``scenario``
    sets what the first observation with units must show; ``start_reference`` is the first episode's
    starting fingerprint, compared with this one's."""
    require_realtime(config)
    directory.mkdir()
    trace = (directory / "trace.jsonl").open("x", buffering=1)
    started = wall_started = time.time()
    monotonic_started = time.monotonic()
    result = {"episode": directory.name, "status": "interrupted", "decisions": 0, "invalid": 0,
              "started_at": datetime.now(UTC).isoformat(),
              "delays_ms": [], "think_s": [], "policy": config["policy"],
              "slot": config.get("slot"), "delay_ms": config.get("delay_ms", 0),
              "track": TRACK + (f"+age-{config['delay_ms']}ms" if config.get("delay_ms") else "")}
    log_offset = mailbox.log_offset()
    policy = None

    def event(kind: str, **fields) -> None:
        trace.write(json.dumps({"kind": kind, "elapsed": round(time.time() - wall_started, 3),
                                **fields}, sort_keys=True) + "\n")

    try:
        try:
            policy = make_policy()
        except Exception as exc:
            raise PolicyFailure(f"controller construction: {exc}") from exc
        result["card"] = card(config["policy"], policy, config)
        _drive(config, policy, mailbox, not_battle, result, event, started, scenario or {})
    except MailboxTimeout as exc:
        past = time.time() - started > config["episode_timeout"]
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
            try:
                policy_call(policy, "close")  # in-flight calls are waited for and charged
            except Exception as exc:
                result.update(status="policy_failure", error=f"controller close: {exc}")
        record_exchanges(policy, event)
        result["elapsed_seconds"] = round(time.time() - wall_started, 3)
        result["monotonic_seconds"] = round(time.monotonic() - monotonic_started, 3)
        result["llm"] = dict(getattr(policy, "totals", {}))
        result["finished_at"] = datetime.now(UTC).isoformat()
        if config.get("record_replay"):
            result["recording"] = copy_recording(mailbox.directory, directory,
                                                  job=mailbox.job, battle=result.get("battle"))
        if config.get("stills"):
            result["imagery"] = copy_presentation(mailbox.directory, directory,
                                                 job=mailbox.job, battle=result.get("battle"))
        if result.get("start") and start_reference:
            result["start_comparison"] = compare_starts(start_reference, result["start"])
        delays = result["delays_ms"]
        result["delay_s"] = round(statistics.mean(delays) / 1000, 2) if delays else None
        (directory / "mod.log").write_text(mailbox.log_since(log_offset))
        write_json(directory / "result.json", result)
        trace.close()
    return result


def policy_call(policy, method: str, *args):
    try:
        return getattr(policy, method)(*args)
    except (PolicyFailure, BudgetExhausted):
        raise
    except Exception as exc:
        message = f"{method}: {type(exc).__name__}: {exc}"
        # The account's key or credit, or a ledger safety stop: the operator's, no forfeit.
        if isinstance(exc, APIError) and (str(exc).startswith(("HTTP 401", "HTTP 402"))
                                          or str(exc).endswith("and stopped")):
            raise BudgetExhausted(message) from exc
        failure = {"method": method, "error_type": type(exc).__name__}
        if getattr(exc, "attempts", None) is not None:  # an APIError's billed attempts
            failure["attempts"] = exc.attempts
        raise PolicyFailure(message, failure=failure) from exc


def track_objectives(result: dict, observation: dict) -> None:
    """Share of time each victory point and key building was held, from the mod's
    per-tick integrals, plus final supplies and tickets. Acknowledgements separately count
    accepted builds and reinforcement purchases."""
    mode = observation.get("mode") or {}
    if mode.get("custom"):
        result["custom_objective"] = mode["custom"]
    victory = any(point.get("victory") for point in mode.get("capture_points") or [])
    if not victory and mode.get("supplies") is None and not mode.get("tickets"):
        return
    measures = result.setdefault("objectives", {"victory_held": None})
    if mode.get("supplies") is not None:
        measures["supplies_left"] = mode["supplies"]
    if mode.get("tickets"):
        measures["tickets"] = {row["side"]: row["tickets"] for row in mode["tickets"]}
        if mode.get("tickets_goal") is not None:
            measures["tickets_goal"] = mode["tickets_goal"]
    totals = (observation.get("evaluation") or {}).get("objectives") or {}
    observed = [value for value in totals.values() if value["observed_ms"] > 0]
    if observed:
        measures["method"] = "engine_tick_time_weighted"
        measures["points"] = totals
        measures["victory_held"] = statistics.mean(
            value["held_ms"] / value["observed_ms"] for value in observed)
        # A settlement's centre (siege or minor settlement), which the owner saw left empty.
        keys = [value for value in observed if "key_building" in value["key"]]
        if keys:
            measures["key_held"] = statistics.mean(
                value["held_ms"] / value["observed_ms"] for value in keys)


def caption(observation: dict, behavior: dict, orders: list[dict]) -> str | None:
    """Advisor text for a decision that carries a model's reply: what it saw and decided."""
    if not behavior.get("reason"):
        return None
    seconds = observation["time_ms"] / 1000
    if "plan" in behavior:
        head = (f"{seconds:.0f} s: {behavior['model']} plan from the state at"
                f" {seconds - behavior['plan_age_s']:.0f} s")
        decided = describe_plan(behavior["plan"])
    else:
        head = f"{seconds:.0f} s: {behavior.get('model', 'model')} saw {strength(observation)}"
        decided = describe_orders(orders)
    return f"{head}\n{behavior['reason']}\n{decided}"[:CAPTION_LIMIT]


def _start(result: dict, observation: dict, scenario: dict, event) -> None:
    """Record the first observation with units and check it against the scenario."""
    result["scenario"] = scenario_key(observation)
    result["roster"] = {
        "friendly": [unit.get("type") for unit in observation["friendly"]],
        "enemy": [unit.get("type") for unit in observation.get("enemy_roster", [])],
    }
    event("roster", observation=observation)
    mode = observation.get("mode") or {}
    result["mode"] = {key: mode.get(key) for key in ("type", "role")}
    result["start"] = fingerprint(observation)
    result["start_time_ms"] = observation["time_ms"]
    if scenario.get("expect"):
        result["setup_checks"] = check_battle(scenario, observation)
        result["setup"] = observation.get("setup")
    for key, wanted in expected_mode(scenario).items():
        if mode.get(key) != wanted:
            raise ProtocolError(f"setup: the battle's {key} is {mode.get(key)!r},"
                                f" the scenario wants {wanted!r}")


def record_exchanges(policy, event) -> None:
    api = getattr(policy, "api", None)
    if hasattr(api, "drain_exchanges"):
        for exchange in api.drain_exchanges():
            event("model_exchange", **exchange)


def _acknowledge(result: dict, outstanding: dict, ack: dict, policy, event) -> int:
    """Count an acknowledged request, pass it to the policy; returns when it applied."""
    latency = {
        "think_s": round(outstanding["sent"] - outstanding["read"], 3),
        "roundtrip_s": round(time.time() - outstanding["read"], 3),
        "delay_ms": ack["applied_ms"] - outstanding["observed_ms"],
    }
    result["invalid"] += sum(1 for item in ack.get("results", []) if not item.get("ok"))
    result["delays_ms"].append(latency["delay_ms"])
    for item in ack.get("results", []):
        kind = outstanding["orders"][item["index"] - 1]["type"] if item.get("index") else ""
        if item.get("ok") and kind in ("build", "reinforce") and "objectives" in result:
            result["objectives"][kind] = result["objectives"].get(kind, 0) + 1
            if kind == "reinforce":
                unit_type = outstanding["orders"][item["index"] - 1]["reinforcement"]
                counts = result["objectives"].setdefault("reinforcements_by_type", {})
                counts[unit_type] = counts.get(unit_type, 0) + 1
    result["think_s"].append(latency["think_s"])
    if outstanding["logged"]:
        event("ack", request=ack["request"], ack=ack, latency=latency)
    feedback = {**ack, **outstanding["refusal"]} if outstanding["refusal"] else ack
    policy_call(policy, "acknowledge", feedback, latency)
    return ack["applied_ms"]


def _drive(config, policy, mailbox, not_battle, result, event, started, scenario) -> None:
    deadline = started + config["episode_timeout"]
    first = mailbox.wait_new_battle(not_battle=not_battle, timeout=config["start_timeout"])
    battle = result["battle"] = first["battle"]
    seq = first["seq"]
    event("battle", observation=first)
    applied_ms = None
    outstanding = None
    logged_ms, logged_behavior = None, None
    history = deque()
    delay_ms = config.get("delay_ms", 0)
    active_wall_start = None
    setup_wait_started_ms = None
    while True:
        # The newest observation is read before the deadline applies: an ended battle is
        # never truncated.
        remaining = max(deadline - time.time(), 0)
        observation = mailbox.wait_observation(
            battle=battle, after_seq=seq, timeout=min(config["observation_timeout"], remaining))
        if observation.get("awaiting_orders") or observation.get("speed", 1) != 1:
            raise ProtocolError("WH3 observation is not from an unpaused 1x battle")
        seq = observation["seq"]
        if observation.get("evaluation"):
            result["final"] = observation["evaluation"]
            result["final_time_ms"] = observation["time_ms"]
        result["battle_ms"] = observation["time_ms"]
        result["remaining_ms"] = observation.get("remaining_ms")
        if "scenario" not in result and observation.get("friendly"):
            pool = (scenario.get("player") or {}).get("reinforcements")
            if (isinstance(pool, list) and pool
                    and not (observation.get("mode") or {}).get("reinforcements")
                    and not observation.get("result")):
                # The native pool context appears shortly after Deployed. No controller
                # sees an unverified empty pool; the battle continues at 1x while it loads.
                if setup_wait_started_ms is None:
                    setup_wait_started_ms = observation["time_ms"]
                if observation["time_ms"] - setup_wait_started_ms < 5000:
                    event("setup_wait", reason="reinforcement_pool_not_ready",
                          observation=observation)
                    continue
            active_wall_start = time.time()
            _start(result, observation, scenario, event)
        track_objectives(result, observation)
        goal = (observation.get("mode") or {}).get("custom") or {}
        if goal.get("ending_error"):
            raise ProtocolError("custom ending failed: " + goal["ending_error"])
        if (goal.get("ending") == "scripted" and not observation.get("result")
                and observation["time_ms"] > goal["completed_ms"] + 5000):
            raise ProtocolError("custom ending was not confirmed by the engine within 5 s")
        # The result is read only after the call that straddled it returned, so the clock
        # ratio stops at the last observation of the running battle.
        if active_wall_start is not None and not observation.get("result"):
            duration = time.time() - active_wall_start
            result["active_wall_s"] = duration
            result["clock_ratio"] = ((observation["time_ms"] - result["start_time_ms"]) / 1000
                                     / duration if duration > 0 else None)
        ack = observation.get("orders")
        if outstanding and ack and ack.get("request") == outstanding["request"]:
            applied_ms = _acknowledge(result, outstanding, ack, policy, event)
            outstanding = None
        if observation.get("result"):
            timer = observation.get("timer") or {}
            result.update(status=observation["result"], battle_ms=observation.get("time_ms"),
                          battle_s=round(observation.get("time_ms", 0) / 1000),
                          final=observation.get("final") or result.get("final"),
                          timer=timer or None,
                          ended_by="time_limit" if observation.get("remaining_ms") == 0
                          or timer.get("expired") is True
                          else "engine_result")
            if (observation.get("mode") or {}).get("custom", {}).get("ending") == "scripted":
                result["ended_by"] = "custom_objective"
            event("result", observation=observation)
            return
        if time.time() > deadline:
            result.update(status="truncated", reason="episode_timeout")
            return
        # Evaluation contains hidden enemy totals. It never enters the controller or
        # its delayed input queue, even on a non-gameplay ending.
        public = {key: value for key, value in observation.items()
                  if key not in ("evaluation", "final", "setup")}
        if observation.get("phase") == "Deployed":
            history.append(public)
        if outstanding or observation.get("phase") != "Deployed":
            continue
        if applied_ms is not None and observation["time_ms"] < applied_ms + config["interval_ms"]:
            continue
        cutoff = observation["time_ms"] - delay_ms
        while len(history) > 1 and history[1]["time_ms"] <= cutoff:
            history.popleft()
        if not history or history[0]["time_ms"] > cutoff:
            continue
        basis = history[0]
        read_at = time.time()
        since = observation["time_ms"] - applied_ms if applied_ms is not None else None
        failure = None
        try:
            orders = policy_call(policy, "decide", basis)
        except PolicyFailure as exc:
            failure = exc
        except BaseException:
            event("observation", observation=basis, since_previous_applied_ms=since)
            raise
        finally:
            record_exchanges(policy, event)
        # The mod publishes the result observation last, so a battle that ended during the
        # call shows it now: the result stands and whatever the call returned is not sent.
        if (mailbox.read_observation() or {}).get("result"):
            continue
        if failure:
            event("observation", observation=basis, since_previous_applied_ms=since)
            if failure.__cause__ is not None and not isinstance(failure.__cause__, APIError):
                raise failure  # an exception in the controller's own code ends the episode
            # No valid reply or a provider error: no orders, and the next state asks again.
            event("forfeit", seq=basis["seq"], error=str(failure), failure=failure.failure)
            continue
        invalid = refusal = None
        try:
            validate_orders(orders, basis)
        except IllegalActionError as exc:
            invalid = {"error": str(exc), "orders": orders}
            result["invalid"] += 1
            refusal = {
                "validation_error": str(exc),
                "results": [{"index": index + 1, "unit": order.get("unit"), "ok": False,
                             "error": str(exc)} for index, order in enumerate(orders)
                            if isinstance(order, dict)] if isinstance(orders, list) else [],
            }
            orders = []
        behavior = policy_call(policy, "metadata")
        # A fast policy decides at the tick rate: quiet decisions are logged once per
        # observe_ms, and every decision with orders, an error or new metadata is logged.
        logged = (orders or invalid or behavior != logged_behavior or logged_ms is None
                  or observation["time_ms"] - logged_ms >= config["observe_ms"])
        if logged:
            event("observation", observation=basis, since_previous_applied_ms=since,
                  decision_time_ms=observation["time_ms"])
            if invalid:
                event("invalid", **invalid)
        say = caption(basis, behavior, orders) if config.get("show") else None
        request = mailbox.write_orders(battle, basis["seq"], orders, say=say)
        if logged:
            event("decision", seq=basis["seq"], time_ms=basis["time_ms"],
                  decision_time_ms=observation["time_ms"],
                  request=request, orders=orders, behavior=behavior)
            logged_ms, logged_behavior = observation["time_ms"], behavior
        outstanding = {"request": request, "observed_ms": basis["time_ms"], "orders": orders,
                       "read": read_at, "sent": time.time(), "logged": bool(logged),
                       "refusal": refusal}
        result["decisions"] += 1
