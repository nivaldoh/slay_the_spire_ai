"""Inputs and test doubles shared by WH3 tests; expected results stay in each test."""
import json
import re
from collections import deque
from contextlib import nullcontext

from twwarhammer3.engine import runtime
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout

USAGE = {"input_tokens": 100, "output_tokens": 20,
         "input_tokens_details": {"cached_tokens": 0},
         "output_tokens_details": {"reasoning_tokens": 5}}

CONFIG = {"policy": "attack_nearest", "episodes": 1, "scenario": "kho5-dwf5", "speed": 1.0,
          "pause": False, "interval_ms": 5000, "observe_ms": 1000, "tick_ms": 250,
          "record_replay": False, "stills": False, "start_timeout": 5,
          "observation_timeout": 5, "episode_timeout": 100, "run_timeout": 100,
          "attach": False, "results": ""}


class FakeMailbox:
    """Feed a declared sequence to the play loop and record its requests.

    This does not implement file polling, sequence filtering or waiting for a new battle.
    Real mailbox/Lua tests cover those boundaries. ``ack=True`` fabricates feedback for
    the pending request; explicit ``orders`` observations can supply mismatched feedback.
    """

    def __init__(self, observations, *, job="job"):
        self.queue = deque(observations)
        self.job = job
        self.requests = []
        self.controls = []
        self.pending = None
        self.menu = None
        self.directory = None  # no bridge files unless a test makes some
        self.written_ns = None  # no observation file, so no write time
        self.menu_outcome = "step 1: found button_battle, clicked\ndone"

    def reset(self):
        pass

    def write_session(self, session):
        self.session = session

    def owned_session(self, session):
        self.write_session(session)
        return nullcontext()

    def write_menu(self, steps):
        self.menu = steps
        return "menu-r"

    def wait_new_battle(self, *, not_battle, timeout):
        if not self.queue:
            raise MailboxTimeout("no battle")
        return self.queue.popleft()

    def wait_observation(self, *, battle, after_seq, timeout):
        if not self.queue:
            raise MailboxTimeout("no observation")
        item = dict(self.queue.popleft())
        if item["battle"] != battle:
            raise BattleRestarted(item)
        if self.pending and item.pop("ack", False):
            request, orders = self.pending
            self.pending = None
            item["orders"] = {"request": request, "based_on": 0,
                              "applied_ms": item["time_ms"] - 500,
                              "results": [{"unit": o["unit"], "ok": True, "index": i + 1}
                                          for i, o in enumerate(orders)]}
        return item

    def write_orders(self, battle, based_on, orders, say=None):
        request = f"r{len(self.requests) + 1}"
        self.requests.append((battle, based_on, orders))
        self.pending = (request, orders)
        return request

    def write_control(self, battle, control):
        self.controls.append((battle, control))
        return "c"

    def read_observation(self):
        return None

    def log_offset(self, name="mod.log"):
        return 0

    def log_since(self, offset, name="mod.log"):
        if name == "menu.log":
            result = self.menu_outcome + "\n"
            if self.menu_outcome.endswith("done") or self.menu_outcome.endswith("failed"):
                status = "failed" if "failed" in self.menu_outcome else "done"
                result += f"menu menu-r: {status}\n"
            return "frontend loaded\n" + (result if self.menu else "")
        return "[0] loaded battle b1\n"


class FakeSend:
    """Stands in for the Responses API transport: answers each request with the next text."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        text = self.replies.pop(0)
        return {"id": "resp", "status": "completed", "usage": USAGE,
                "output": [{"type": "message", "content": [{"type": "output_text",
                                                             "text": text}]}]}


def observation(time_ms=30000, visible=("e1",)):
    """What a model controller sees: a Khorne lord and warriors against dwarf warriors (e1)
    and a grudge thrower (e2), of which the ids in ``visible`` are in sight."""
    enemy = [{"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0", "class": "infantry",
              "x": 100.0, "z": 200.0, "bearing": 180, "men": 90, "men0": 100, "hp": 0.9,
              "state": ["moving"]},
             {"id": "e2", "type": "wh_main_dwf_art_grudge_thrower", "class": "artillery",
              "x": 150.0, "z": 260.0, "bearing": 180, "men": 4, "men0": 4, "hp": 1.0,
              "state": []}]
    return {
        "schema": 1, "job": "j", "battle": "b", "seq": 3, "phase": "Deployed",
        "time_ms": time_ms, "speed": 1, "remaining_ms": 3000000, "awaiting_orders": False,
        "armies": {"player": {"faction": "wh3_main_kho_khorne"},
                   "enemy": {"faction": "wh_main_dwf_dwarfs"}},
        "friendly": [
            {"id": "f1", "type": "wh3_main_kho_cha_herald_of_khorne_0", "class": "lord",
             "commander": True, "x": 10.0, "z": -40.0, "bearing": 0, "men": 1, "men0": 1,
             "hp": 1.0, "ammo": 0, "ammo0": 0, "range": 0, "speed": [2.0, 4.0],
             "fatigue": "fresh", "state": ["idle"]},
            {"id": "f2", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry",
             "commander": False, "x": 0.0, "z": -40.0, "bearing": 0, "men": 110, "men0": 120,
             "hp": 0.93, "ammo": 0, "ammo0": 0, "range": 0, "speed": [1.8, 3.6],
             "fatigue": "active", "state": ["moving"], "dest": [0.0, 20.0]},
        ],
        "enemy_roster": [{"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0"},
                         {"id": "e2", "type": "wh_main_dwf_art_grudge_thrower"}],
        "enemy": [unit for unit in enemy if unit["id"] in visible],
        "orders": None, "result": None,
    }


def bridge_observation(seq, time_ms, *, battle="b1", phase="Deployed", result=None, ack=False,
                       awaiting=False, enemy=True):
    """A small mailbox observation for the job loop: f1 in melee with e1 at (50, 50).
    ``ack`` makes FakeMailbox attach the pending orders' acknowledgement."""
    final = {"friendly": {"men": 50, "men0": 100}, "enemy": {"men": 9, "men0": 90}}
    return {
        "schema": 1, "job": "job", "battle": battle, "seq": seq, "phase": phase,
        "time_ms": time_ms, "speed": 1, "awaiting_orders": awaiting, "remaining_ms": 100000,
        "armies": {"player": {"faction": "kho"}, "enemy": {"faction": "dwf"}},
        "friendly": [{"id": "f1", "type": "kho_inf_a", "class": "infantry", "x": 0.0, "z": 0.0,
                      "men": 100, "men0": 100, "hp": 1.0, "state": ["melee"], "target": "e1"}],
        "enemy_roster": [{"id": "e1", "type": "dwf_inf_b"}],
        "enemy": [{"id": "e1", "type": "dwf_inf_b", "class": "infantry", "x": 50.0, "z": 50.0,
                   "men": 90, "men0": 90, "hp": 1.0, "state": []}] if enemy else [],
        "orders": None, "result": result, "ack": ack, "final": final if result else None,
    }


def make_job(tmp_path, name, results, *, revision="r1"):
    """A finished job for the report collector: one episode per (policy, margin, status)."""
    job = tmp_path / name
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "config": {"policy": "hold,skills"}, "scenario": {"name": "frozen"},
        "source_revision": revision, "setup_checks": {"map": "checked"},
    }))
    for index, (policy, margin, status) in enumerate(results):
        episode = job / f"episode-{index:04d}"
        episode.mkdir()
        (episode / "result.json").write_text(json.dumps({
            "policy": policy, "status": status, "elapsed_seconds": 100,
            "setup_checks": {"rosters": "checked"},
            "final": {"friendly": {"men0": 100, "active_men": 50 + margin * 100},
                      "enemy": {"men0": 100, "active_men": 50}},
        }))
    return job


def configured_job(tmp_path, name, model="model-a", effort="low", **changes):
    """A one-episode llm_rules job with the configuration and game identity the HTML report
    compares; ``changes`` update its manifest."""
    job = make_job(tmp_path, name, [("llm_rules", .3, "won")])
    path = job / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(track="obs-v3/act-v2/live-1x")
    manifest["config"].update(model=model, effort=effort, observe_ms=1000, tick_ms=250,
                              interval_ms=0)
    manifest.update(changes)
    path.write_text(json.dumps(manifest))
    (job / "environment.json").write_text(json.dumps({
        "game": {"steam_build_id": "123", "sha256": "game-hash"}}))
    return job


def embedded(html):
    """The data an HTML report page embeds."""
    return json.loads(re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)[1])


def fake_install(root, monkeypatch):
    """Point engine.runtime at a fake Steam install, profile and mod under ``root``."""
    game = root / "steamapps/common/game"
    game.mkdir(parents=True)
    (game / "Warhammer3.exe").write_bytes(b"not the game")
    (root / "steamapps/appmanifest_1142710.acf").write_text('"buildid"\t\t"25823491"\n')
    monkeypatch.setitem(runtime.PINS, "steam_build_id", "25823491")
    source = root / "mod/script/battle/mod"
    source.mkdir(parents=True)
    (source / "twwarhammer3_battle.lua").write_text("out('loaded')")
    preferences = root / "profile/scripts/preferences.script.txt"
    preferences.parent.mkdir(parents=True)
    preferences.write_bytes(b"fe_game_intro_video_enabled true; # intro #\r\ngfx_unit_size 2;\r\n")
    monkeypatch.setattr(runtime, "user_dir", lambda: root / "profile")
    monkeypatch.setattr(runtime, "conflicting_games", lambda game_dir, rules: [])
    monkeypatch.setattr(runtime, "GAME_DIR", game)
    monkeypatch.setattr(runtime, "STEAM_MANIFEST", root / "steamapps/appmanifest_1142710.acf")
    monkeypatch.setattr(runtime, "RUNTIME_DIR", root / "mnt/c/wh3-agent")
    monkeypatch.setattr(runtime, "BRIDGE_DIR", root / "mnt/c/wh3-agent/bridge")
    monkeypatch.setattr(runtime, "MOD_SOURCE", root / "mod")
    monkeypatch.setattr(runtime.windows, "windows_path", lambda path: "C:/wh3-agent/mods")
    return root


def opening() -> dict:
    """A siege defence at 30 s with every section the renderer has."""
    return {
        "time_ms": 30000, "speed": 1, "remaining_ms": 870000, "phase": "Deployed",
        "terrain": {"x0": -48, "z0": -48, "cell_m": 32, "sample_width_m": 8,
                    "rows": ["..##", "...#", "...."]},
        "mode": {
            "type": "settlement_standard", "role": "defender", "timeout_winner": "us",
            "objectives": "Hold the victory point until the timer runs out.",
            "tickets": [{"side": "us", "tickets": 600, "per_s": 2},
                        {"side": "enemy", "tickets": 150, "per_s": 0}],
            "tickets_goal": 1000,
            "capture_points": [
                {"id": "c1", "name": "Victory Point", "x": 0, "z": 64, "holder": "us",
                 "percent": 100, "victory": True},
                {"id": "c2", "name": "Key Building", "x": 96, "z": 0, "holder": None,
                 "percent": 40, "contested": True}],
            "gates": [{"name": "Gatehouse", "x": 0, "z": -64, "hp": 80, "destroyed": False}],
            "supplies": 900,
            "reinforcements": [{"type": "wh3_main_kho_inf_chaos_warriors_0", "cost": 600}],
            "spawn_zones": [{"id": 3, "x": 0, "z": 96, "usable": True}],
            "slots": [{"id": "s1", "type": "tower", "x": -32, "z": 0, "usable": True,
                       "options": [{"name": "tower_arrow_1", "cost": 300}]}],
        },
        "army": {"currency": 120, "next_unlock": 200, "abilities": [
            {"key": "horn_of_khorne", "target": "Ground", "radius": 35, "cooldown_s": 90,
             "unlocked": True, "ready": True}]},
        "magic": {"current": 23.5, "reserve": 40},
        "friendly": [
            {"id": "f1", "type": "wh3_main_kho_cha_bloodthirster_0", "class": "lord",
             "commander": True, "x": 0.0, "z": 40.0, "bearing": 180, "men": 1, "men0": 1,
             "hp": 0.9, "ammo": 0, "ammo0": 0, "range": 0, "speed": [3.0, 5.5],
             "fatigue": "fresh", "state": ["idle"], "can_fly": True, "flying": False,
             "flight": {"can_toggle": True, "cooldown_s": 0},
             "barrier": {"hp": 300, "max_hp": 600},
             "morale": {"fraction": 0.85, "effect": "Winning combat"},
             "abilities": [
                 {"key": "roar", "target": "Self", "cooldown_s": 60, "can_use": True,
                  "ready": True},
                 {"key": "blood_rage", "target": "Self", "can_use": True, "ready": False,
                  "recharge_s": 21.6, "last_issued_ms": 20000}]},
            {"id": "f2", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry",
             "x": -20.0, "z": 30.0, "bearing": 180, "men": 110, "men0": 120, "hp": 0.92,
             "ammo": 0, "ammo0": 0, "range": 0, "speed": [1.8999999761581, 3.6],
             "fatigue": "active", "state": ["moving"], "dest": [-20.0, 0.0], "width": 30,
             "attack_mode": "melee", "behaviours": {"defend": False}},
            {"id": "f3", "type": "wh3_main_kho_veh_skullcannon_0", "class": "missile_chariot",
             "x": 20.0, "z": 50.0, "bearing": 180, "men": 7, "men0": 7, "hp": 1.0,
             "ammo": 18, "ammo0": 20, "range": 200, "speed": [4.0, 6.0], "fatigue": "fresh",
             "state": []},
            {"id": "f4", "type": "wh3_main_kho_mon_khornataurs_0", "class": "monster",
             "men": 0, "men0": 6},
        ],
        "enemy": [
            {"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0", "class": "infantry",
             "x": 10.0, "z": -40.0, "bearing": 0, "men": 90, "men0": 100, "hp": 0.9,
             "speed": [1.5, 3.0], "state": ["moving"]},
            {"id": "e2", "type": "wh_main_grn_inf_orc_boyz", "class": "infantry",
             "alliance": 3, "x": 150.0, "z": 0.0, "bearing": 270, "men": 120, "men0": 120,
             "hp": 1.0, "state": ["idle"], "target": "e1"},
            {"id": "e3", "type": "wh_main_dwf_art_grudge_thrower", "class": "artillery",
             "x": 0.0, "z": -200.0, "bearing": 0, "men": 4, "men0": 4, "hp": 1.0,
             "range": 400, "state": []},
        ],
        "enemy_roster": [
            {"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0"},
            {"id": "e2", "type": "wh_main_grn_inf_orc_boyz", "alliance": 3},
            {"id": "e3", "type": "wh_main_dwf_art_grudge_thrower"},
            {"id": "e4", "type": "wh_main_dwf_inf_quarrellers_0", "dead": True},
        ],
    }
