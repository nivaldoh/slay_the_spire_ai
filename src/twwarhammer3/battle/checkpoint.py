"""Battle checkpoints: save a running battle at a tick and later continue it from that tick.

A checkpoint is the game's replay file written mid-battle (setup and every input so far)
plus the Lua random seed from tick 1. `engine/checkpoint_agent.js` restores it when the
replay is opened from the Replays menu: it presents the battle as live, rebuilds it quickly
(inline ticks) while checking every tick's native checksum against the file, and at the
saved tick swaps in live input; from then on the battle runs at 1x. The owner allowed the
fast rebuild before the handover (2026-10-25, AGENTS.md).

`run` plays one source battle (a scenario) or one restore through the normal harness, with
optional saves, Lua (orders, a battle script) and readings at exact completed ticks.
`compare` checks a restore against its source tick by tick. Steam build 25961564 only.

`episode` is the step run of checkpoint RL (docs/twwarhammer3/checkpoint-rl-plan.md): it
also logs every observation it reads, hands the mod at most one order batch at a declared
engine tick (`inject`), ends at the engine's ending or a fault, and writes `attempt.json`
with a status from one closed set. `source_records` turns a source run's saves into library
records; `restore_episode` restores one. Nothing here is verified beyond its tests.
"""
import contextlib
import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path

from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from gameai.windows import windows_path
from gameai.windows_game import conflicting_games
from spire.engine import runtime as spire_runtime
from twwarhammer3.battle import play, setup
from twwarhammer3.engine import pack, runtime
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.protocol import scenario_key, validate_orders

ENGINE = Path(__file__).resolve().parents[1] / "engine"
AGENT = ENGINE / "checkpoint_agent.js"
RUNNER = ENGINE / "checkpoint_frida.py"
WORK = runtime.RUNTIME_DIR / "checkpoint"
# A Windows Python with frida 17 installed (pip install frida==17.*).
FRIDA_PYTHON = Path("/mnt/c/wh3-agent/checkpoint-frida-venv/Scripts/python.exe")
EXE_SHA256 = "9bd58c63bd7fc5c9909b3d3d9b6b7a6ae4eac784369bf91a9e53c3e9f42be496"  # build 25961564
CONFIG = {"speed": 1, "pause": False, "observe_ms": 1000, "tick_ms": 250, "record_replay": False,
          "stills": False, "interval_ms": 0, "delay_ms": 0, "start_timeout": 240,
          "observation_timeout": 20, "run_timeout": 600}
REPLAY_STEPS = [
    {"find": ["buttons_holder", "button_battle"], "click": True, "timeout_ms": 240000,
     "required": True},
    {"find": ["battle_frame", "button_replays"], "click": True, "timeout_ms": 15000,
     "required": True},
    {"wait_ms": 2000},
    {"find": ["sp_replays", "list_panel", "list_box", "item0"], "click": True, "timeout_ms": 5000,
     "required": True},
    {"find": ["sp_replays", "button_watch"], "click": True, "timeout_ms": 5000, "required": True},
]


def events(run: Path) -> list[dict]:
    return [json.loads(line) for line in (run / "native/native.jsonl").read_text().splitlines()]


def saved(run: Path, name: str) -> dict:
    """The checkpoint record a source run saved: what a restore needs to recognise it."""
    row = next(e for e in events(run) if e.get("event") == "saved" and e["name"] == name)
    return {key: row[key] for key in ("name", "tick", "checksum", "lua_seed", "seed_at_tick")}


@contextlib.contextmanager
def only_replay(name: str):
    """For one run, leave the named replay alone in the game's list (item0); yields its hash.

    The other replays wait in replays/checkpoint-aside/ and return afterwards.
    """
    replays = runtime.user_dir() / "replays"
    target, aside = replays / (name + ".replay"), replays / "checkpoint-aside"
    if not target.exists():
        raise FileNotFoundError(target)
    aside.mkdir(exist_ok=True)
    if any(aside.iterdir()):
        raise RuntimeError(f"replays from an interrupted run are still in {aside}")
    others = [path for path in replays.glob("*.replay") if path != target]
    try:
        for path in others:
            shutil.move(path, aside / path.name)
        yield sha256(target)
    finally:
        interrupted = None
        while True:
            try:
                for path in others:
                    displaced = aside / path.name
                    if displaced.exists():
                        shutil.move(displaced, path)
                    elif not path.exists():
                        raise FileNotFoundError(displaced)
                if aside.exists():
                    aside.rmdir()
                break
            except KeyboardInterrupt as error:
                interrupted = error
        if interrupted is not None:
            raise interrupted


def run(plan: dict, output: Path) -> dict:
    """One source battle (plan["scenario"]) or restore (plan["checkpoint"]); returns the manifest.

    A scenario is a configured name or an inline declaration, recorded with the plan.
    Plan keys: save_at [{tick, name}], lua_at [{tick, label, lua}], readings {every, lua},
    stop_tick, lobby_steps (additional UI steps just before starting a source battle).
    A restore's lua_at may hold only tick-1 setup and orders after the checkpoint:
    earlier inputs come from the replay.
    """
    restore = plan.get("checkpoint")
    if restore and any(1 < item["tick"] <= restore["tick"] for item in plan.get("lua_at", [])):
        raise ValueError("a restore runs Lua only at tick 1 and after its checkpoint")
    with only_replay(restore["name"]) if restore else contextlib.nullcontext() as replay_sha256:
        return run_in_game(plan, output, replay_sha256)


def run_in_game(plan: dict, output: Path, replay_sha256: str | None) -> dict:
    with launched(plan, output, replay_sha256, CONFIG, LIMITS) as (manifest, native, agent, _):
        manifest["ending"] = wait(native / "native.jsonl", agent, plan["stop_tick"])
        manifest["completed"] = True
    return manifest


# The constants run() has always used: the supervisor's game limit, the agent's lifetime.
LIMITS = {"game_timeout_s": CONFIG["run_timeout"], "agent_seconds": 560}


@contextlib.contextmanager
def launched(plan: dict, output: Path, replay_sha256: str | None, config: dict, limits: dict):
    """Launch the game with the agent, start the battle; yields (manifest, native, agent,
    mailbox). The manifest is written when the game has closed, also after an error."""
    restore = plan.get("checkpoint")
    for item in plan.get("save_at", []):
        if (runtime.user_dir() / "replays" / (item["name"] + ".replay")).exists():
            raise FileExistsError(f"replay {item['name']} already exists")
    output.mkdir(parents=True)
    environment = collect_diagnostics()
    write_json(output / "environment.json", environment)
    if environment["blockers"]:
        raise RuntimeError(environment["blockers"])
    if environment["game"]["sha256"] != EXE_SHA256:
        raise RuntimeError("the checkpoint agent supports Steam build 25961564 only")
    if conflicting_games(Path(spire_runtime.WINDOWS_GAME_DIR), spire_runtime.CONFLICTS):
        raise RuntimeError("Slay the Spire is running")
    scenario = plan.get("scenario")
    steps = REPLAY_STEPS if restore else setup.scenario_steps(
        setup.scenarios()[scenario] if isinstance(scenario, str) else scenario,
        build_id=environment["game"]["steam_build_id"])
    if plan.get("lobby_steps"):
        if restore:
            raise ValueError("lobby_steps apply only to source battles")
        start = next(i for i, step in enumerate(steps)
                     if step.get("find") == ["start_button_frame", "button_start_battle"])
        steps[start:start] = plan["lobby_steps"]
    hooks = ("save_at", "lua_at", "readings", "stop_tick")
    agent_config = {"lua_chunk": "twwarhammer3_battle", "checkpoints": [restore] if restore else [],
                    **{key: plan[key] for key in hooks if key in plan}}
    write_json(output / "agent-config.json", agent_config)
    write_json(output / "plan.json", plan)
    manifest = {"plan": plan, "replay_sha256": replay_sha256, "config": config, "spend_usd": 0,
                "source_revision": committed_revision("battle checkpoints", play.SOURCES),
                "source_files": source_fingerprints(play.SOURCES), "agent_sha256": sha256(AGENT),
                "completed": False}
    if limits != LIMITS:
        manifest["limits"] = limits
    # Windows Python reads and writes on C:, like the runtime's other scripts; the agent's
    # log is copied into the run at the end.
    native = WORK / output.name
    with runtime.RuntimeLock():
        manifest["deployment"] = runtime.prepare_runtime()
        native.mkdir(parents=True)
        for path in (AGENT, RUNNER):
            shutil.copy2(path, WORK / path.name)
        shutil.copy2(output / "agent-config.json", native / "agent-config.json")
        mailbox = Mailbox(runtime.BRIDGE_DIR, job=output.name)
        mailbox.reset()
        try:
            with (mailbox.owned_session(play.session(config)),
                  runtime.OwnedGame(output / "game.log", timeout=limits["game_timeout_s"]) as game):
                manifest["game"] = game.info
                with (output / "frida.log").open("w") as frida_log:
                    agent = subprocess.Popen(
                        [str(FRIDA_PYTHON), windows_path(WORK / RUNNER.name),
                         "--pid", str(game.info["pid"]), "--agent", windows_path(WORK / AGENT.name),
                         "--config", windows_path(native / "agent-config.json"),
                         "--output", windows_path(native),
                         "--seconds", str(limits["agent_seconds"])],
                        stdout=frida_log, stderr=subprocess.STDOUT)
                    try:
                        deadline = time.monotonic() + 30
                        while not (native / "ready").exists():
                            if agent.poll() is not None or time.monotonic() > deadline:
                                raise RuntimeError("checkpoint agent did not start; see frida.log")
                            time.sleep(0.2)
                        play.start_frontend(mailbox, config, output, steps)
                        yield manifest, native, agent, mailbox
                    finally:
                        (native / "STOP").touch()
                        try:
                            agent.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            agent.kill()
                        for name in ("mod.log", "menu.log"):
                            if (runtime.BRIDGE_DIR / name).exists():
                                shutil.copy2(runtime.BRIDGE_DIR / name, output / name)
                        shutil.copytree(native, output / "native")
                        shutil.rmtree(native)
        except BaseException as error:
            manifest["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            manifest["closed"] = not runtime.running_pids()
            write_json(output / "manifest.json", manifest)


def wait(log: Path, agent: subprocess.Popen, stop_tick: int) -> dict:
    """Follow the agent until it reports done; raise on its errors or a native fault."""
    deadline = time.monotonic() + 150 + stop_tick * 0.1
    with log.open() as stream:
        while time.monotonic() < deadline:
            line = stream.readline()
            if not line:
                if agent.poll() is not None:
                    raise RuntimeError("checkpoint agent exited early; see native.jsonl")
                time.sleep(0.1)
                continue
            event = json.loads(line)
            if event.get("event") in ("error", "frida_error", "detached"):
                raise RuntimeError(f"checkpoint agent: {event}")
            if event.get("event") == "done":
                return event
    raise TimeoutError(f"tick {stop_tick} not reached")


def differences(a, b, path=""):
    """Paths where two readings differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            yield from differences(a.get(key), b.get(key), f"{path}.{key}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            yield from differences(x, y, f"{path}[{i}]")
    elif a != b:
        yield path


def compare(source: list[dict], restore: list[dict]) -> dict:
    """Per-tick checksums and readings of a restore against its source run's events."""
    def table(rows, kind, field):
        return {row["tick"]: row[field] for row in rows if row.get("event") == kind}

    s_ticks, r_ticks = table(source, "tick", "checksum"), table(restore, "tick", "checksum")
    s_read, r_read = table(source, "reading", "value"), table(restore, "reading", "value")
    shared = sorted(set(s_ticks) & set(r_ticks))
    mismatched = [t for t in shared if s_ticks[t] != r_ticks[t]]
    readings = {t: list(differences(s_read[t], r_read[t]))
                for t in sorted(set(s_read) & set(r_read))}
    restored = next((row for row in restore if row.get("event") == "restored"), None)
    return {"restored_at": restored and restored["tick"],
            "seed_matches": restored and restored["lua_seed_matches"],
            "ticks": len(shared), "last_tick": shared[-1] if shared else None,
            "checksum_mismatches": len(mismatched),
            "first_mismatch": mismatched[0] if mismatched else None,
            "readings": len(readings), "readings_unequal": [t for t, d in readings.items() if d],
            "first_reading_difference": next(([t, d[:5]] for t, d in readings.items() if d), None)}


# --- Checkpoint RL step runs (docs/twwarhammer3/checkpoint-rl-plan.md) ---------------------

READING_LUA = r'''
local function get(obj, name, ...)
  local f = obj and obj[name]; if not f then return nil end
  local ok, value = pcall(f, obj, ...); if ok then return value end
end
local function ctx(id, expression, context)
  local ok, value = pcall(function()
    return common.get_context_value(context or "CcoBattleUnit", id, expression) end)
  if ok then return value end
end
local ABILITIES = 'BattleAbilityList.JoinString(SetupAbilityContext.RecordKey + "|" + '
  .. 'CanCurrentlyPerform + "|" + RechargeTimeRemainingSecs + "|" + IsActive, ";")'
local EFFECTS = 'ActiveEffectList(true).JoinString(AbilityContext.RecordKey + "|" + '
  .. 'PhaseRecordContext.Key + "|" + StartTimeSeconds + "|" + TimeRemainingSeconds, ";")'
local STATS = 'UnitDetailsContext.StatList.JoinString(Key + "=" + Value + "/" + ValueBase, ";")'
local units, armies = {}, {}
for side = 1, 2 do
  local army = bm:alliances():item(side):armies():item(1)
  armies[#armies + 1] = {side = side, winds = get(army, "winds_of_magic_current"),
    reserve = get(army, "winds_of_magic_reserve")}
  local list = army:units()
  for i = 1, list:count() do
    local u = list:item(i); local id = tostring(get(u, "unique_ui_id"))
    local p, d = get(u, "position"), get(u, "ordered_position")
    local target = get(u, "current_target")
    units[#units + 1] = {side = side, index = i, id = id, type = get(u, "type"),
      x = p and p:get_x(), y = p and p:get_y(), z = p and p:get_z(), bearing = get(u, "bearing"),
      width = get(u, "ordered_width"), dest_x = d and d:get_x(), dest_z = d and d:get_z(),
      men = get(u, "number_of_men_alive"), hp = get(u, "unary_hitpoints"),
      ammo = get(u, "ammo_left"),
      kills = get(u, "number_of_enemies_killed"), fatigue = tostring(get(u, "fatigue_state")),
      target = target and tostring(get(target, "unique_ui_id")) or nil,
      morale = ctx(id, 'MoralePercent + "|" + MoraleGreatestEffect'),
      abilities = ctx(id, ABILITIES), effects = ctx(id, EFFECTS), stats = ctx(id, STATS),
      flying = get(u, "is_currently_flying"),
      fire_at_will = get(u, "is_behaviour_active", "fire_at_will"), moving = get(u, "is_moving"),
      melee = get(u, "is_in_melee"), routing = get(u, "is_routing"),
      wavering = get(u, "is_wavering")}
  end
end
local s = checkpoint_script
return twwarhammer3_json.encode({time_ms = bm.battle:time_elapsed_ms(),
  remaining_s = bm.battle:remaining_conflict_time(), phase = bm:get_current_phase_name(),
  mode = ctx("", "BattleTypeState", "CcoBattleRoot"),
  attacker = ctx("", "SetupContext.IsPlayerAttacker", "CcoBattleRoot"),
  units = units, armies = armies,
  script = s and {fires = s.fires, times = s.times, draws = s.draws, orders = s.orders} or nil})
'''
STATUSES = ("won", "lost", "draw", "stopped", "restore_failure", "restore_fault",
            "injection_failed", "infrastructure", "interrupted")
SCORED = ("won", "lost", "draw")
FAULTS = ("error", "frida_error", "detached")
# Launch, menu and load before the battle (about 43 s in checkpoint-check-20261025c), then
# the rebuild (about 640 ticks/s there, at observe_ms 1000); stage 1 measures them at 300.
OVERHEAD_S, REBUILD_S_PER_TICK, MARGIN_S = 60, 0.005, 60
SAVE_SETTLE_S = 10


def digest(value) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def projected_hash(observation: dict, scenario: dict | None = None) -> str:
    """The hash two launches' views of one engine state share."""
    return digest(play.context_projection(play.public(observation, scenario or {})))


def grid_ms(tick_ms: int) -> int:
    """The mod's tick period: its repeat callback runs on the first 100 ms engine tick at or
    after tick_ms (250 configured, so 300; applied_ms ≡ 100 mod 300 in the screen1 traces)."""
    return math.ceil(tick_ms / 100) * 100


def mod_start_ms(mod_log: str) -> int:
    """The battle time of the mod's start, from its log line ``[4900] started: ...``."""
    line = next(line for line in mod_log.splitlines() if "] started:" in line)
    return int(line[1:line.index("]")])


def off_grid(observations: list[dict], start_ms: int, grid: int) -> list[int]:
    """Times of logged observations off the mod's grid; the Loading placeholder (seq 0) and
    the result observation (published by the phase-change callback) are not on it."""
    return [o["time_ms"] for o in observations
            if o.get("phase") != "Loading" and not o.get("result")
            and (o["time_ms"] - start_ms) % grid]


def decision_times(start_ms: int, grid: int, save_tick: int, tick: int) -> tuple[int, int]:
    """For an injection at engine tick ``tick``: the context's time (the grid time just before
    it) and the expected applied_ms (the next grid time). A tick on the grid is refused, not
    moved: the hook and the mod's tick would share an engine tick in an unknown order.

    JUDGEMENT: dispatch — Claude, 2026-10-26: exact-tick injection off the mod's grid (δ 2,
    observe_ms 300), versus a mailbox hold field or the mailbox with recorded jitter.
    Determinism of every reward and the fault detection of every stage rest on this.
    """
    at = 100 * tick
    if (at - start_ms) % grid == 0:
        raise ValueError(f"tick {tick} is on the mod's grid ({start_ms} + k × {grid} ms)")
    context = start_ms + (at - start_ms) // grid * grid
    if context <= 100 * save_tick:
        raise ValueError(f"the context of tick {tick} ({context} ms) precedes the handover")
    return context, context + grid


# After the injected batch nothing is sent: native orders and the game's own unit behaviour
# continue (hold without its request traffic).
# JUDGEMENT: continuation — Claude, 2026-10-25: no orders after an injection, versus a
# scripted continuation; competes with checkpoint-rl.md `candidate_task`. Every branch
# outcome and therefore every reward rests on this.
def inject_lua(message: dict) -> str:
    text = json.dumps(message, separators=(",", ":"))
    if "]==]" in text:
        raise ValueError("the message cannot be quoted as a Lua long string")
    return f"return twwarhammer3_inject([==[{text}]==])"


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def read_rows(run: Path) -> list[dict]:
    return jsonl(run / "native/native.jsonl")


def read_observations(run: Path) -> list[dict]:
    """observations.jsonl rows: {read_wall, native_rows, observation}."""
    return jsonl(run / "observations.jsonl")


def seq_gaps(logged: list[dict], grid: int | None = None) -> list[list[int]]:
    """[after, before] pairs of seq numbers the reader skipped.

    With ``grid``, one gap is not a reader miss: the mod's tick publishes an observation and
    the phase-change callback then publishes the result in the same engine tick (finish()),
    so the result overwrites it at once. That gap is exactly one seq, right before the result,
    whose time is one grid step after the previous observation (stage 1, 2026-10-26).

    JUDGEMENT?: result_collapse — Claude, 2026-10-26: this gap is named after the stage 1
    restores failed the plan's "no seq gap" rule only on it; versus keeping the plan's rule
    (then every restore that ends by a phase change fails). Stage 1's pass rests on this.
    """
    rows = [row["observation"] for row in logged]
    return [[a["seq"], b["seq"]] for a, b in zip(rows, rows[1:]) if b["seq"] != a["seq"] + 1
            and not (grid and b.get("result") and b["seq"] == a["seq"] + 2
                     and b["time_ms"] == a["time_ms"] + grid)]


def classify(rows: list[dict], logged: list[dict], plan: dict, runner_end: dict | None) -> dict:
    """The attempt's status from the agent's event stream and the observation log.

    Rows are placed relative to the end by their position in native.jsonl; an end at the
    result observation is placed by the rows the reader had when it logged that observation.
    """
    restore, injection = plan.get("checkpoint"), plan.get("injection")
    result = next((row for row in logged if row["observation"].get("result")), None)
    done = next((i for i, row in enumerate(rows) if row.get("event") == "done"), None)
    end = result["native_rows"] if result else done + 1 if done is not None else len(rows)
    fault = next(((i, row) for i, row in enumerate(rows[:end]) if row.get("event") in FAULTS), None)
    late = [row for row in rows[end:] if row.get("event") in ("error", "frida_error")
            or (row.get("event") == "detached" and row.get("reason") != "application-requested")]
    verdict = {"end_row": end, "late_fault": late or None, "status": None, "reason": None}
    if restore:
        restored = next((i for i, row in enumerate(rows) if row.get("event") == "restored"
                         and row.get("name") == restore["name"]
                         and row.get("tick") == restore["tick"]), None)
        if restored is None or (fault and fault[0] < restored):
            row = fault[1] if fault and (restored is None or fault[0] < restored) else None
            return {**verdict, "status": "restore_failure",
                    "reason": row or "no restored event with the record's name and tick"}
    if fault:
        row, at = fault[1], injection and injection["tick"]
        lua_before = any(r.get("event") == "lua" and r.get("tick") == at
                         for r in rows[:fault[0]])
        if (row.get("event") == "error" and at is not None and row.get("tick") == at
                and not lua_before):
            return {**verdict, "status": "injection_failed", "reason": row.get("message")}
        return {**verdict, "status": "restore_fault" if restore else "infrastructure",
                "reason": row}
    if result:
        ending = play.engine_ending(result["observation"])
        return {**verdict, "status": ending["result"], "engine_ending": ending}
    if done is not None:
        return {**verdict, "status": "stopped"}
    return {**verdict, "status": "infrastructure",
            "reason": (runner_end or {}).get("by", "no ending")}


def checksums(rows: list[dict]) -> dict[int, int]:
    return {row["tick"]: row["checksum"] for row in rows if row.get("event") == "tick"}


def first_divergence(a: dict[int, int], b: dict[int, int], start: int = 0) -> int | None:
    return next((t for t in sorted(set(a) & set(b)) if t >= start and a[t] != b[t]), None)


def witness(order: dict, unit: dict | None, window: list[dict], dest_m: float) -> str | None:
    """'shown', 'unchanged' (the context already showed it) or None: the ordered unit's
    public state shows the order within the window."""
    def shows(record):
        if record is None:
            return False
        if order["type"] == "attack":
            return record.get("target") == order["target"]
        if order["type"] == "move":
            dest = record.get("dest")
            return (dest is not None
                    and math.hypot(dest[0] - order["x"], dest[1] - order["z"]) <= dest_m)
        if order["type"] == "halt":
            return "moving" not in record.get("state", [])
        return True

    def unit_in(observation):
        return next((u for u in observation.get("friendly", [])
                     if u.get("id") == order["unit"]), None)

    if any(shows(unit_in(o)) for o in window):
        return "unchanged" if shows(unit) else "shown"
    return None


# JUDGEMENT: witness — Claude, 2026-10-26: 5 s window, dest within 1 m, an already-shown value
# or no divergence accepted (flagged); versus requiring fresh evidence or failing such attempts.
# Which injections count as executed, and so carry a reward, rests on this.
WITNESS = {"window_ms": 5000, "dest_m": 1.0}


def attribute(rows: list[dict], logged: list[dict], reference_rows: list[dict],
              injection: dict) -> dict:
    """Whether the injected batch is what ran, one clause at a time (plan, stage 1).

    ``injection``: tick, request, based_on, orders, context_ms, context_hash, applied_ms and
    the context observation. Returns {status, clause, reason, flags, ...}; status None passes.
    """
    observations = [row["observation"] for row in logged]
    out = {"status": None, "clause": None, "reason": None, "flags": [], "applied_ms": None,
           "first_divergence": None, "witness": {}}

    def fail(status, clause, reason=None):
        return {**out, "status": status, "clause": clause, "reason": reason}

    seen = [o for o in observations if o["time_ms"] == injection["context_ms"]
            and o.get("phase") == "Deployed" and not o.get("result")]
    if not seen:
        gap = any(a["time_ms"] < injection["context_ms"] < b["time_ms"]
                  for a, b in zip(observations, observations[1:]))
        return fail("infrastructure", "context", "reader miss" if gap else "no context observation")
    if projected_hash(seen[0]) != injection["context_hash"]:
        return fail("injection_failed", "context", "context differs from the reference")
    lua = next((r for r in rows if r.get("event") == "lua" and r.get("label") == "inject"
                and r.get("tick") == injection["tick"]), None)
    value = lua and lua.get("value")
    if not isinstance(value, dict) or value.get("accepted") is not True:
        return fail("injection_failed", "accepted", lua and lua.get("value"))
    ack = next((o["orders"] for o in observations if (o.get("orders") or {}).get("request")
                == injection["request"]), None)
    if ack is None or ack.get("based_on") != injection["based_on"]:
        return fail("injection_failed", "acknowledged", ack)
    out["applied_ms"] = ack["applied_ms"]
    results = ack.get("results") or []
    if len(results) != len(injection["orders"]):
        return fail("injection_failed", "results", f"{len(results)} results for "
                    f"{len(injection['orders'])} orders")
    if not all(r.get("ok") for r in results):
        refused = [r for r in results if not r.get("ok")]
        return fail("injection_failed", "results", {"refused": refused})
    if ack["applied_ms"] != injection["applied_ms"]:
        return fail("injection_failed", "applied_ms", f"applied at {ack['applied_ms']},"
                    f" expected {injection['applied_ms']}")
    # The mod applies a pending request before it checks the engine's decision on the same
    # tick, so an acknowledgement in the result observation itself had no effect.
    # JUDGEMENT: ending_margin — Claude, 2026-10-25: applied strictly before the result
    # observation (margin 0), versus a positive margin. Which attempts near the ending keep a
    # reward rests on this.
    ending = next((o for o in observations if o.get("result")), None)
    if ending and not ack["applied_ms"] < ending["time_ms"]:
        return fail("injection_failed", "before_ending", "acknowledged by the result observation")
    applied_tick = ack["applied_ms"] // 100
    mine, theirs = checksums(rows), checksums(reference_rows)
    early = first_divergence(mine, theirs)
    if early is not None and early < applied_tick:
        return fail("injection_failed", "divergence_before_apply", f"diverged at tick {early}")
    out["first_divergence"] = early
    if not injection["orders"]:
        if early is not None:
            return fail("injection_failed", "noop", f"the empty batch diverged at tick {early}")
        return out
    if early is None:
        out["flags"].append("no_effect")
    window = [o for o in observations
              if ack["applied_ms"] <= o["time_ms"] <= ack["applied_ms"] + WITNESS["window_ms"]]
    context_units = {u.get("id"): u for u in injection["context"].get("friendly", [])}
    for order in injection["orders"]:
        shown = witness(order, context_units.get(order["unit"]), window, WITNESS["dest_m"])
        if shown is None:
            return fail("injection_failed", "witness", order)
        out["witness"][order["unit"]] = shown
    if "unchanged" in out["witness"].values():
        out["flags"].append("witness: unchanged")
    return out


def limits_for(plan: dict) -> dict:
    """The plan's limits; refused when they cannot contain the rung's remaining battle time
    plus the launch overhead and a margin."""
    limits = {**LIMITS, **plan.get("limits", {})}
    remaining_s = plan["remaining_ms"] / 1000
    rebuild_s = REBUILD_S_PER_TICK * (plan.get("checkpoint") or {}).get("tick", 0)
    need = remaining_s + OVERHEAD_S + rebuild_s + MARGIN_S
    short = [key for key in ("game_timeout_s", "agent_seconds", "episode_timeout_s")
             if limits.get(key, 0) < need]
    if short:
        raise ValueError(f"limits {short} cannot contain {remaining_s:.0f} s of battle plus"
                         f" {need - remaining_s:.0f} s")
    return limits


def limits_covering(record: dict) -> dict:
    """Limits that contain a record's timer bound: a restore may run to the timer."""
    need = (record["remaining_ms"] / 1000 + OVERHEAD_S + REBUILD_S_PER_TICK * record["tick"]
            + MARGIN_S)
    return {"episode_timeout_s": round(need + 30), "agent_seconds": round(need + 60),
            "game_timeout_s": round(need + 120)}


def follow(log_path: Path, agent: subprocess.Popen, mailbox: Mailbox, output: Path,
           plan: dict, limits: dict) -> dict:
    """Read the agent's events and every new observation until the battle ends, a fault,
    ``done``, the agent exits or the time limit. Returns how it ended."""
    deadline = time.time() + limits["episode_timeout_s"]
    saves = {item["tick"] for item in plan.get("save_at", [])}
    rows, buffer, checked, last_seq, ended = [], "", 0, None, None
    with log_path.open() as stream, (output / "observations.jsonl").open("x", buffering=1) as log:
        while True:
            # Rows are drained after the observation is read, so its native_rows include
            # every row written before it was published: an end is never placed early.
            observation = mailbox.read_observation()
            buffer += stream.read()
            *lines, buffer = buffer.split("\n")
            rows += [json.loads(line) for line in lines if line]
            if observation is not None and observation.get("seq") != last_seq:
                last_seq = observation["seq"]
                log.write(json.dumps({"read_wall": time.time(), "native_rows": len(rows),
                                      "observation": observation}) + "\n")
                if observation.get("result") and ended is None:
                    tick = max((r["tick"] for r in rows if r.get("event") == "tick"), default=0)
                    ended = {"by": "result", "tick": tick, "settle": time.time() + SAVE_SETTLE_S,
                             "saves": sorted(s for s in saves if s < tick)}
            if ended:
                written = {r["tick"] for r in rows if r.get("event") == "saved"}
                if set(ended["saves"]) <= written or time.time() > ended["settle"]:
                    ended["not_saved"] = sorted(saves - written)
                    del ended["settle"]
                    return ended
            else:
                for row in rows[checked:]:
                    if row.get("event") in FAULTS:
                        return {"by": "fault", "row": row}
                    if row.get("event") == "done":
                        return {"by": "done", "tick": row["tick"]}
                checked = len(rows)
            if agent.poll() is not None:
                return {"by": "agent_exit"}
            if time.time() > deadline:
                return {"by": "timeout"}
            time.sleep(0.05)


def refuse(plan: dict) -> None:
    """Refusals that need no game: a missing Frida venv, a taken save name, a bad injection."""
    if not FRIDA_PYTHON.exists():
        raise FileNotFoundError(f"no Frida venv at {FRIDA_PYTHON}")
    replays = runtime.user_dir() / "replays"
    taken = {p.stem for p in replays.glob("*.replay")} | {
        p.stem for p in (replays / "checkpoint-aside").glob("*.replay")}
    names = [item["name"] for item in plan.get("save_at", [])]
    if set(names) & taken or len(set(names)) != len(names):
        raise FileExistsError(f"save names taken: {sorted(set(names) & taken)}")
    injection = plan.get("injection")
    if injection:
        record = plan["checkpoint"]
        context_ms, applied_ms = decision_times(plan["mod_start_ms"], plan["grid_ms"],
                                                record["tick"], injection["tick"])
        if (context_ms, applied_ms) != (injection["context_ms"], injection["applied_ms"]):
            raise ValueError("the injection's declared times do not follow the grid rule")
        validate_orders(injection["orders"], play.public(injection["context"], {}))


def episode(plan: dict, output: Path, replay_sha256: str | None = None, *,
            release=None) -> dict:
    """One step run: a source battle (plan["scenario"]) or a restore (plan["checkpoint"]),
    observations logged, at most one injected batch, to the engine ending or a fault.

    Plan keys beyond run()'s: observe_ms (300 in every step run), injection {tick, request,
    based_on, orders, context, context_ms, context_hash, applied_ms}, reference (the
    no-injection attempt directory attribution compares with), remaining_ms, mod_start_ms,
    grid_ms, limits {game_timeout_s, agent_seconds, episode_timeout_s}. Writes attempt.json;
    ``release`` (restore_episode's replay cleanup) runs first and its fields join it.
    """
    refuse(plan)
    limits = limits_for(plan)
    injection = plan.get("injection")
    if injection:
        message = {"request": injection["request"], "based_on": injection["based_on"],
                   "orders": injection["orders"]}
        plan = {**plan, "lua_at": [*plan.get("lua_at", []), {
            "tick": injection["tick"], "label": "inject", "lua": inject_lua(message)}]}
    config = {**CONFIG, "observe_ms": plan.get("observe_ms", CONFIG["observe_ms"])}
    attempt = {"plan": plan, "replay_sha256": replay_sha256, "status": "infrastructure",
               "memory_available_kib": memory_available_kib(), "started_wall": time.time()}
    try:
        with launched(plan, output, replay_sha256, config, limits) as (manifest, native, agent,
                                                                      mailbox):
            attempt["runner_end"] = follow(native / "native.jsonl", agent, mailbox, output,
                                           plan, limits)
            manifest["completed"] = True
        attempt["manifest"] = {key: manifest.get(key) for key in
                               ("source_revision", "agent_sha256", "deployment", "closed")}
    except KeyboardInterrupt:
        attempt.update(status="interrupted", runner_end={"by": "interrupt"})
        raise
    except Exception as error:
        attempt["runner_end"] = {"by": "exception", "error": f"{type(error).__name__}: {error}"}
        raise
    finally:
        attempt["saved_replays"] = move_saves(plan, output)
        attempt["ended_wall"] = time.time()
        if release:
            attempt.update(release())
        ended_by = attempt.get("runner_end", {}).get("by")
        if attempt["status"] != "interrupted" and ended_by != "exception":
            attempt.update(assess(output, plan, attempt["runner_end"]))
        if output.exists():
            write_json(output / "attempt.json", attempt)
    return attempt


def move_saves(plan: dict, output: Path) -> list[str]:
    replays, moved = runtime.user_dir() / "replays", []
    for item in plan.get("save_at", []):
        path = replays / (item["name"] + ".replay")
        if path.exists():
            (output / "replays").mkdir(parents=True, exist_ok=True)
            shutil.move(path, output / "replays" / path.name)
            moved.append(path.name)
    return moved


def memory_available_kib() -> int | None:
    line = next((line for line in Path("/proc/meminfo").read_text().splitlines()
                 if line.startswith("MemAvailable:")), None)
    return int(line.split()[1]) if line else None


def assess(output: Path, plan: dict, runner_end: dict) -> dict:
    """Status, ending, restore evidence and attribution of a finished step run."""
    rows, logged = read_rows(output), read_observations(output)
    verdict = classify(rows, logged, plan, runner_end)
    restore = plan.get("checkpoint")
    found = {"gaps": seq_gaps(logged), "observations": len(logged)}
    if (output / "mod.log").exists():
        found["mod_start_ms"] = mod_start_ms((output / "mod.log").read_text())
    restored = next((i for i, r in enumerate(rows) if r.get("event") == "restored"), None)
    if restore and restored is not None:
        after = [r for r in logged if r["native_rows"] > restored]
        found["gaps_after_handover"] = seq_gaps(after, plan.get("grid_ms"))
        found["rebuild_observations"] = len(logged) - len(after)
        found["checksums_after_handover"] = sum(1 for r in rows[restored:]
                                                if r.get("event") == "tick")
        reading = next((r["value"] for r in rows if r.get("event") == "reading"
                        and r.get("tick") == restore["tick"]), None)
        if "reading" in plan:
            found["handover_reading_equal"] = (reading is not None
                                               and not list(differences(plan["reading"], reading)))
            if not found["handover_reading_equal"] and verdict["status"] in SCORED:
                verdict.update(status="restore_fault", reason="handover reading differs")
    live = [r for r in logged if restored is None or r["native_rows"] > restored]
    live = [r for r in live if r["observation"].get("phase") == "Deployed"
            and not r["observation"].get("result")]
    if len(live) > 1 and live[-1]["read_wall"] > live[0]["read_wall"]:
        found["clock_ratio"] = round((live[-1]["observation"]["time_ms"]
                                      - live[0]["observation"]["time_ms"]) / 1000
                                     / (live[-1]["read_wall"] - live[0]["read_wall"]), 3)
    walls = {r["event"]: r["wall_time"] for r in rows
             if r.get("event") in ("ready", "restoring", "battle_started", "restored")}
    found["walls"] = walls
    grid = plan.get("grid_ms")
    if grid and "mod_start_ms" in found:
        found["off_grid"] = off_grid([r["observation"] for r in logged],
                                     found["mod_start_ms"], grid)
    out = {**verdict, "restore_evidence": found}
    injection = plan.get("injection")
    if injection and verdict["status"] in SCORED + ("stopped",):
        reference = Path(plan["reference"])
        out["attribution"] = attribute(rows, logged, read_rows(reference), injection)
        if out["attribution"]["status"]:
            out.update(status=out["attribution"]["status"], reason=out["attribution"]["reason"])
    out["reward"] = reward(out)
    return out


def reward(attempt: dict) -> int | None:
    """1 for an engine win, 0 for a loss or draw, timer endings included, read from the
    attempt's engine_ending; no reward unless its status is an engine result. Rests on
    JUDGEMENT docs/twwarhammer3/checkpoint-rl.md terminal_reward."""
    if attempt.get("status") not in SCORED:
        return None
    result = attempt["engine_ending"]["result"]
    if result != attempt["status"]:
        raise ValueError(f"status {attempt['status']} but the engine ended {result}")
    return 1 if result == "won" else 0


AGENT_FIELDS = ("name", "tick", "checksum", "lua_seed", "seed_at_tick")


def pack_sha256() -> str:
    """The hash of the pack prepare_runtime would install now."""
    return hashlib.sha256(pack.pack_bytes(runtime.mod_files())).hexdigest()


def source_records(source: Path, library: Path, *, root: str, late_margin_s: float) -> list[dict]:
    """Library records for a finished source step run: one directory per save, holding
    record.json and the replay as <name>-<sha12>.replay. A save at or after the source's
    engine ending is recorded unusable; ``late`` marks saves at least late_margin_s before it.

    JUDGEMENT: rung_selection — Claude, 2026-10-25: readings every 100 ticks, saves every 300
    ticks from 600, late rung 60 s before the ending; versus other spacings. Which states are
    rungs rests on this.
    """
    attempt = json.loads((source / "attempt.json").read_text())
    ending = attempt.get("engine_ending")
    if not ending:
        raise ValueError(f"the source run ended {attempt['status']}, with no engine ending")
    plan, rows = attempt["plan"], read_rows(source)
    readings = {r["tick"]: r["value"] for r in rows if r.get("event") == "reading"}
    scenario = plan["scenario"]
    first = next(r["observation"] for r in read_observations(source)
                 if r["observation"].get("friendly"))
    records = []
    for row in rows:
        if row.get("event") != "saved":
            continue
        replay = source / "replays" / f"{row['name']}.replay"
        replay_sha256 = sha256(replay)
        record = {**{key: row[key] for key in AGENT_FIELDS},
                  "root": root, "replay_sha256": replay_sha256,
                  "replay": f"{row['name']}-{replay_sha256[:12]}.replay",
                  "source": str(source), "source_control": plan.get("source_control"),
                  "scenario": scenario, "scenario_sha256": digest(
                      setup.scenarios()[scenario] if isinstance(scenario, str) else scenario),
                  "scenario_key": scenario_key(first),
                  "exe_sha256": EXE_SHA256, "pack_sha256": attempt["manifest"]["deployment"][
                      "pack"]["sha256"], "agent_sha256": attempt["manifest"]["agent_sha256"],
                  "source_revision": attempt["manifest"]["source_revision"],
                  "remaining_ms": round(readings[row["tick"]]["remaining_s"] * 1000),
                  "reading": readings[row["tick"]], "source_ending": ending,
                  "mod_start_ms": attempt["restore_evidence"]["mod_start_ms"],
                  "grid_ms": plan["grid_ms"], "observe_ms": plan["observe_ms"],
                  "usable": 100 * row["tick"] < ending["battle_ms"],
                  "late": ending["battle_ms"] - 100 * row["tick"] >= late_margin_s * 1000}
        directory = library / str(row["tick"])
        directory.mkdir(parents=True)
        shutil.copy2(replay, directory / record["replay"])
        write_json(directory / "record.json", record)
        records.append(record)
    return records


def checkpoint_root(declaration: dict, library: Path) -> dict:
    """``rl checkpoint``: play a root's source battle with saves and readings, then write its
    library records under library/<root>/. Declaration: root, scenario, saves {first, every,
    last} (engine ticks), readings_every, late_margin_s, limits, source_control.

    JUDGEMENT: source_control — Claude, 2026-10-25: a hold source, else one injected batch,
    versus a mailbox-played source. Which battle states the rungs are and whether `noop`
    reproduces a win rest on this.
    """
    root, saves = declaration["root"], declaration["saves"]
    if declaration.get("source_control", {"policy": "hold"}) != {"policy": "hold"}:
        raise ValueError("only a hold source (no orders) is implemented")
    # Readings fall on ticks divisible by readings_every; every save tick must be one.
    if saves["first"] % declaration["readings_every"] or saves["every"] % declaration[
            "readings_every"]:
        raise ValueError("save ticks must carry a reading")
    scenario = setup.scenarios()[declaration["scenario"]]
    plan = {"scenario": declaration["scenario"], "source_control": {"policy": "hold"},
            "save_at": [{"tick": tick, "name": f"{root}-{tick}"}
                        for tick in range(saves["first"], saves["last"] + 1, saves["every"])],
            "readings": {"every": declaration["readings_every"], "lua": READING_LUA},
            "observe_ms": 300, "grid_ms": grid_ms(CONFIG["tick_ms"]),
            "remaining_ms": 1000 * scenario["expect"]["time_limit_s"] + 5000,
            "limits": declaration["limits"]}
    directory = library / root
    attempt = episode(plan, directory / "source")
    records = source_records(directory / "source", directory, root=root,
                             late_margin_s=declaration["late_margin_s"])
    return {"attempt": attempt, "records": records}


def late_rung(library: Path) -> Path:
    """The record of the latest usable save at least late_margin_s before the ending."""
    records = [(json.loads(path.read_text()), path) for path in library.glob("*/record.json")]
    eligible = [(r["tick"], path) for r, path in records if r["usable"] and r["late"]]
    if not eligible:
        raise ValueError(f"no usable late save in {library}")
    return max(eligible)[1]


def restore_episode(record_path: Path, plan: dict, output: Path) -> dict:
    """Restore a library record as a step run: copy its replay in, check its hash, leave it
    alone in the Replays list, run the episode; afterwards re-hash and remove the copy. A
    copy that changed marks the library entry SUSPECT, refusing later restores."""
    record = json.loads(record_path.read_text())
    directory = record_path.parent
    if (directory / "SUSPECT").exists():
        raise ValueError(f"{directory} is marked suspect: {(directory / 'SUSPECT').read_text()}")
    if not record["usable"]:
        raise ValueError(f"{record['name']} was saved at or after the source's ending")
    for key, value in (("exe_sha256", EXE_SHA256), ("pack_sha256", pack_sha256()),
                       ("agent_sha256", sha256(AGENT))):
        if record[key] != value:
            raise ValueError(f"the record's {key} differs from this environment")
    if sha256(directory / record["replay"]) != record["replay_sha256"]:
        raise ValueError(f"{record['replay']} differs from its record")
    target = runtime.user_dir() / "replays" / record["replay"]
    if target.exists():
        raise FileExistsError(target)

    def release():
        after = sha256(target) if target.exists() else None
        target.unlink(missing_ok=True)
        if after != record["replay_sha256"]:
            (directory / "SUSPECT").write_text(f"the copy changed during {output}\n")
        return {"replay_unchanged": after == record["replay_sha256"]}

    full = {**plan, "checkpoint": {key: record[key] for key in AGENT_FIELDS},
            "record": str(record_path), "remaining_ms": record["remaining_ms"],
            "mod_start_ms": record["mod_start_ms"], "grid_ms": record["grid_ms"],
            "reading": record["reading"]}
    shutil.copy2(directory / record["replay"], target)
    try:
        if sha256(target) != record["replay_sha256"]:
            raise ValueError("the copied replay differs from its record")
        with only_replay(target.stem):
            return episode(full, output, record["replay_sha256"], release=release)
    finally:
        target.unlink(missing_ok=True)


def context_of(reference: Path, context_ms: int) -> dict:
    """The public observation at ``context_ms`` of a reference attempt's stream."""
    seen = [row["observation"] for row in read_observations(reference)
            if row["observation"]["time_ms"] == context_ms
            and row["observation"].get("phase") == "Deployed"
            and not row["observation"].get("result")]
    if not seen:
        raise ValueError(f"{reference} logged no observation at {context_ms} ms")
    return play.public(seen[0], {})


def injection_for(reference: Path, record: dict, orders: list[dict], request: str,
                  tick: int | None = None) -> dict:
    """An injection at ``tick`` (default the save tick + 2) whose context is the reference
    attempt's observation the grid rule picks."""
    tick = tick or record["tick"] + 2
    context_ms, applied_ms = decision_times(record["mod_start_ms"], record["grid_ms"],
                                            record["tick"], tick)
    context = context_of(reference, context_ms)
    return {"tick": tick, "request": request, "based_on": context["seq"], "orders": orders,
            "context": context, "context_ms": context_ms, "applied_ms": applied_ms,
            "context_hash": projected_hash(context)}


def observation_table(logged: list[dict], after_ms: int, until_ms: int | None) -> dict:
    return {row["observation"]["time_ms"]: [row["observation"]["seq"],
                                            projected_hash(row["observation"])]
            for row in logged if row["observation"].get("phase") != "Loading"
            and row["observation"]["time_ms"] > after_ms
            and (until_ms is None or row["observation"]["time_ms"] <= until_ms)}


def compare_attempts(a: Path, b: Path, after_ms: int) -> dict:
    """Two step runs after ``after_ms`` (the handover): compare()'s fields up to the earlier
    engine-ending tick, the logged observations (seq and projected hash per time), endings."""
    endings = [json.loads((run / "attempt.json").read_text()).get("engine_ending")
               for run in (a, b)]
    end_ms = min((e["battle_ms"] for e in endings if e), default=None)
    end = end_ms // 100 if end_ms is not None else None

    def clip(rows):
        return [r for r in rows if end is None or r.get("tick") is None or r["tick"] <= end]

    rows = [read_rows(a), read_rows(b)]
    result = compare(*(clip(r) for r in rows))
    for kind in ("tick", "reading"):
        result[f"{kind}s_uncompared"] = sum(
            1 for r in rows[0] + rows[1] if r.get("event") == kind and end is not None
            and r["tick"] > end)
    readings = [{r["tick"] for r in clip(x) if r.get("event") == "reading"} for x in rows]
    result["readings_one_side"] = sorted(readings[0] ^ readings[1])
    tables = [observation_table(read_observations(run), after_ms, end_ms) for run in (a, b)]
    shared = sorted(set(tables[0]) & set(tables[1]))
    result["observations"] = len(shared)
    result["observations_one_side"] = sorted(set(tables[0]) ^ set(tables[1]))
    result["observations_unequal"] = [t for t in shared if tables[0][t] != tables[1][t]]
    result["endings_equal"] = endings[0] == endings[1]
    result["endings"] = endings
    return result
