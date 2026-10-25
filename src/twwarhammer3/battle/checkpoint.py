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
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

from gameai.provenance import committed_revision, sha256, source_fingerprints, write_json
from gameai.windows import windows_path
from gameai.windows_game import conflicting_games
from spire.engine import runtime as spire_runtime
from twwarhammer3.battle import play, setup
from twwarhammer3.engine import runtime
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox

ENGINE = Path(__file__).resolve().parents[1] / "engine"
AGENT = ENGINE / "checkpoint_agent.js"
RUNNER = ENGINE / "checkpoint_frida.py"
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


def only_replay(name: str, parked: Path) -> str:
    """Leave the named replay as the only one in the game's list (item0); park the rest."""
    replays = runtime.user_dir() / "replays"
    target = replays / (name + ".replay")
    if not target.exists():
        raise FileNotFoundError(target)
    for other in replays.glob("*.replay"):
        if other != target:
            parked.mkdir(parents=True, exist_ok=True)
            shutil.move(other, parked / other.name)
    return sha256(target)


def run(plan: dict, output: Path) -> dict:
    """One source battle (plan["scenario"]) or restore (plan["checkpoint"]); returns the manifest.

    Plan keys: save_at [{tick, name}], lua_at [{tick, label, lua}], readings {every, lua},
    stop_tick. A restore's lua_at may hold only tick-1 setup and orders after the checkpoint:
    earlier inputs come from the replay.
    """
    restore = plan.get("checkpoint")
    if restore and any(1 < item["tick"] <= restore["tick"] for item in plan.get("lua_at", [])):
        raise ValueError("a restore runs Lua only at tick 1 and after its checkpoint")
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
    if restore:
        replay_sha256 = only_replay(restore["name"], output / "parked-replays")
        steps = REPLAY_STEPS
    else:
        replay_sha256 = None
        steps = setup.scenario_steps(setup.scenarios()[plan["scenario"]],
                                     build_id=environment["game"]["steam_build_id"])
    hooks = ("save_at", "lua_at", "readings", "stop_tick")
    agent_config = {"lua_chunk": "twwarhammer3_battle", "checkpoints": [restore] if restore else [],
                    **{key: plan[key] for key in hooks if key in plan}}
    write_json(output / "agent-config.json", agent_config)
    write_json(output / "plan.json", plan)
    manifest = {"plan": plan, "replay_sha256": replay_sha256, "config": CONFIG, "spend_usd": 0,
                "source_revision": committed_revision("battle checkpoints", play.SOURCES),
                "source_files": source_fingerprints(play.SOURCES), "agent_sha256": sha256(AGENT),
                "completed": False}
    native = output / "native"
    native.mkdir()
    with runtime.RuntimeLock():
        manifest["deployment"] = runtime.prepare_runtime()
        mailbox = Mailbox(runtime.BRIDGE_DIR, job=output.name)
        mailbox.reset()
        try:
            with (mailbox.owned_session(play.session(CONFIG)),
                  runtime.OwnedGame(output / "game.log", timeout=CONFIG["run_timeout"]) as game):
                manifest["game"] = game.info
                with (output / "frida.log").open("w") as frida_log:
                    agent = subprocess.Popen(
                        [str(FRIDA_PYTHON), windows_path(RUNNER), "--pid", str(game.info["pid"]),
                         "--agent", windows_path(AGENT),
                         "--config", windows_path(output / "agent-config.json"),
                         "--output", windows_path(native)],
                        stdout=frida_log, stderr=subprocess.STDOUT)
                    try:
                        deadline = time.monotonic() + 30
                        while not (native / "ready").exists():
                            if agent.poll() is not None or time.monotonic() > deadline:
                                raise RuntimeError("checkpoint agent did not start; see frida.log")
                            time.sleep(0.2)
                        play.start_frontend(mailbox, CONFIG, output, steps)
                        manifest["ending"] = wait(native / "native.jsonl", agent, plan["stop_tick"])
                        manifest["completed"] = True
                    finally:
                        (native / "STOP").touch()
                        try:
                            agent.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            agent.kill()
                        for name in ("mod.log", "menu.log"):
                            if (runtime.BRIDGE_DIR / name).exists():
                                shutil.copy2(runtime.BRIDGE_DIR / name, output / name)
        except BaseException as error:
            manifest["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            manifest["closed"] = not runtime.running_pids()
            write_json(output / "manifest.json", manifest)
    return manifest


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
