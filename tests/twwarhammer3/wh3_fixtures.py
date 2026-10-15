"""Builders that several WH3 test files share. A builder only one file uses stays in that file."""
import json
import re

from twwarhammer3.engine import runtime

USAGE = {"input_tokens": 100, "output_tokens": 20,
         "input_tokens_details": {"cached_tokens": 0},
         "output_tokens_details": {"reasoning_tokens": 5}}


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
    ``ack`` makes test_wh3_play's FakeMailbox attach the pending orders' acknowledgement."""
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
