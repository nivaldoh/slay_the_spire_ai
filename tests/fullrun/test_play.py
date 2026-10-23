"""Full-run lifecycle with a fake bridge and game; these states do not certify the engine."""

import base64
import csv
import json
import os

from fullrun_support import CONFIG, DEATH, MENU, NEOW, ScriptedPolicy
from spire_messages import combat_message, message

from gameai.ledger import BudgetExhausted
from spire.fullrun import play


def unsettled():
    raw = combat_message()
    raw["game_state"]["combat_state"]["monsters"][1]["intent"] = "DEBUG"
    return raw


def test_run_starts_settles_forces_single_choices_and_ends_on_death(tmp_path, harness):
    sessions, sent = harness
    sessions.append([MENU, NEOW, unsettled(), combat_message(), DEATH])
    agent = ScriptedPolicy()
    result = play.play_run(tmp_path / "run", {**CONFIG, "seed": "SEEDA"}, agent)
    assert sent == ["START IRONCLAD 0 SEEDA", "choose 0", "wait 60", "end"]
    assert (result["status"], result["score"], result["current_hp"]) == ("lost", 42, 0)
    assert (result["decisions"], result["policy_calls"], result["settle_waits"]) == (2, 1, 1)
    assert result["llm"] == {"calls": 1}
    trace = [json.loads(line) for line in (tmp_path / "run/trace.jsonl").read_text().splitlines()]
    decisions = [event for event in trace if event["kind"] == "decision"]
    assert [d["behavior"]["type"] for d in decisions] == ["forced", "scripted"]
    assert "seed" not in decisions[1]["decision"]["observation"]


def test_an_opened_settings_screen_is_closed_with_the_cancel_key(tmp_path, harness):
    sessions, sent = harness
    settings = message(["key", "click", "wait", "state"], screen_type="NONE",
                       screen_name="SETTINGS", is_screen_up=True)
    sessions.append([MENU, settings, combat_message(), DEATH])
    result = play.play_run(tmp_path / "run", {**CONFIG, "seed": "SEEDA"}, ScriptedPolicy())
    assert sent == ["START IRONCLAD 0 SEEDA", "key cancel", "end"]
    assert result["status"] == "lost"


def test_budget_exhaustion_ends_the_run_and_stops_the_job(tmp_path, harness):
    sessions, sent = harness
    sessions.append([MENU, combat_message()])
    results = tmp_path / "results.csv"
    manifest = play.play(tmp_path / "job", {**CONFIG, "results": str(results)},
                         policy_factory=lambda: ScriptedPolicy(BudgetExhausted("cap")))
    assert manifest["status"] == "stopped"
    assert [run["status"] for run in manifest["runs"]] == ["budget_exhausted"]
    assert sent == ["START IRONCLAD 0 SEEDA"]
    assert (tmp_path / "job/system_prompt.md").read_text().startswith("You are playing")
    [row] = csv.DictReader(results.open())
    assert (row["job"], row["run"], row["seed"], row["outcome"]) == (
        "job", "run-0000", "SEEDA", "budget_exhausted")


def test_a_failed_model_decision_keeps_its_prompt_and_attempts_in_the_trace(tmp_path, harness):
    from gameai.ledger import Ledger
    from spire.fullrun.llm import LLMPolicy

    sessions, sent = harness
    sessions.append([MENU, combat_message()])
    replies = iter(["not json"] * 3)

    def send(body):
        return {"id": "r", "status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": next(replies)}]}],
            "usage": {"input_tokens": 10, "output_tokens": 5}}

    agent = LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      system_prompt="Play well.")
    result = play.play_run(tmp_path / "run", {**CONFIG, "seed": "SEEDA"}, agent)
    assert result["status"] == "policy_failure" and sent == ["START IRONCLAD 0 SEEDA"]
    trace = [json.loads(line) for line in (tmp_path / "run/trace.jsonl").read_text().splitlines()]
    [exchange] = [event for event in trace if event["kind"] == "model_exchange"]
    assert exchange["prompt"].startswith("Run notes:") and len(exchange["attempts"]) == 3
    assert exchange["attempts"][0]["request"]["instructions"] == "Play well."
    assert exchange["error"]["type"] == "InvalidReply"


def encode(save):
    """The game's save obfuscation (SaveFileObfuscator): base64 of the JSON XORed with "key"."""
    data = json.dumps(save).encode()
    return base64.b64encode(bytes(byte ^ b"key"[i % 3] for i, byte in enumerate(data)))


def test_each_new_autosave_of_the_run_is_copied_once_with_its_floor(tmp_path, harness):
    sessions, sent = harness
    autosave = tmp_path / "game/saves/IRONCLAD.autosave"
    autosave.parent.mkdir(parents=True)
    stamps = iter(range(1, 10))

    def write(data):
        def game_saves():
            autosave.write_bytes(data)
            stamp = next(stamps) * 10**9  # distinct modification times, as real saves have
            os.utime(autosave, ns=(stamp, stamp))
        return game_saves

    floor = encode({"floor_num": 1, "act_num": 1, "seed": 7, "current_room": "MonsterRoom"})
    write(encode({"floor_num": 30}))()  # left over from an earlier run
    # A partly written file, the complete one, then the same save written again.
    sessions.append([MENU, NEOW, write(floor[:12]), combat_message(), write(floor),
                     combat_message(), write(floor), DEATH])
    play.play_run(tmp_path / "run", {**CONFIG, "seed": "SEEDA"}, ScriptedPolicy())
    trace = [json.loads(line) for line in (tmp_path / "run/trace.jsonl").read_text().splitlines()]
    snapshots = [event for event in trace if event["kind"] == "save_snapshot"]
    assert [(s["file"], s["floor"], s["act"], s["seed"], s["room"]) for s in snapshots] == [
        ("saves/0001.autosave", 1, 1, 7, "MonsterRoom")]
    assert (tmp_path / "run/saves/0001.autosave").read_bytes() == floor
    assert play.decode_save(floor)["floor_num"] == 1
