"""Exact model requests, public fight labels and evidence integrity in full-run exports."""

import hashlib
import json
import re
import shutil
import sys

import pytest
from spire_messages import combat_message

from gameai.ledger import Ledger
from spire.__main__ import main
from spire.fullrun import export, play
from spire.fullrun.llm import LLMPolicy
from spire.protocol import PolicyFailure

SYSTEM = "Play well. é\n"
REPLY = '{"choice": 0, "reason": "because", "notes": null}'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def attempt(text=REPLY, **fields):
    return {"response_id": "r", "status": "completed", "text": text, "usd": 0.001,
            "usage": {"input_tokens": 9, "output_tokens": 3}, **fields}


def decision(n, floor=1, hp=70, *, combat=False, screen="MAP", prompt=None, notes=None):
    """An old-format decision event: a forced one, or a model one when given a prompt."""
    observation = {"act": 1, "floor": floor, "current_hp": hp, "max_hp": 80, "gold": 99,
                   "screen_type": "NONE" if combat else screen, "room_type": "MonsterRoom"}
    if combat:
        observation["combat_state"] = {"turn": 1, "player": {"current_hp": hp}}
    candidates = [{"id": f"s:{n}:{i}", "decision_id": f"s:{n}", "command": f"choose {i}",
                   "label": f"option {i}"} for i in range(2)]
    behavior = {"type": "forced"}
    if prompt is not None:
        behavior = {"type": "llm", "model": "gpt-6-luna", "effort": "low", "prompt": prompt,
                    "prompt_sha256": digest(prompt), "attempts": [attempt()],
                    "reason": "because", "selected_index": 0}
        if notes is not None:
            behavior["notes"] = notes
    return {"kind": "decision", "elapsed": n, "choice_id": candidates[0]["id"],
            "decision": {"id": f"s:{n}", "candidates": candidates, "observation": observation},
            "behavior": behavior}


def sent(prompt, instructions=SYSTEM, **fields):
    """A new-format attempt with its recorded request body and output items."""
    request = {"instructions": instructions, "input": [{"role": "user", "content": prompt}]}
    return attempt(request=request, output=[], **fields)


def exchanged(n, prompt, attempts, *, error=None, decided=True, **observed):
    """A new-format request: its model exchange, then its decision unless none was logged."""
    attempts = [dict(a, exchange_id=f"m{n}") for a in attempts]
    events = [{"kind": "model_exchange", "id": f"m{n}", "prompt": prompt,
               "attempts": attempts, **({"error": error} if error else {})}]
    if decided:
        event = decision(n, prompt=prompt, **observed)
        event["behavior"]["attempts"] = attempts
        events.append(event)
    return events


def make_job(tmp_path, runs, *, name="llm-luna-v10-dev-20261013", status="completed"):
    job = tmp_path / name
    job.mkdir(parents=True)
    (job / "system_prompt.md").write_text(SYSTEM)
    manifest = {"scope": "full_run", "status": status, "source_revision": "a" * 40,
                "source_files": {"src/spire/llm.py": "renderer-hash",
                                 "configs/llm/monsters.json": "monsters-hash"},
                "config": {"model": "gpt-6-luna", "effort": "low"},
                "system_prompt_sha256": digest(SYSTEM), "runs": []}
    (job / "manifest.json").write_text(json.dumps(manifest))
    (job / "environment.json").write_text(json.dumps({"game": {"sha256": "engine-hash"}}))
    for index, (events, result) in enumerate(runs):
        run = job / f"run-{index:04d}"
        run.mkdir()
        (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        (run / "result.json").write_text(json.dumps(result))
        (run / "profile.json").write_text(json.dumps({"status": "ok",
                                                      "ironclad_unlock_level": "3"}))
    return job


def read_export(directory):
    return [json.loads(line) for line in (directory / "decisions.jsonl").read_text().splitlines()]


def old_job(tmp_path, **kwargs):
    lost = [
        decision(0, 0, 80, screen="EVENT", prompt="neow", notes="n"),
        # A raw engine message is never a label source.
        {"kind": "observation", "sequence": 2, "raw": {"game_state": {"current_hp": 1}}},
        decision(1, 1, 80, combat=True, prompt="hallway"),
        decision(2, 1, 75, combat=True),
        decision(3, 1, 72, screen="COMBAT_REWARD"),
        # An event fight, the event screen, then a second fight on the same floor.
        decision(4, 2, 72, combat=True, prompt="first"),
        decision(5, 2, 60, screen="EVENT"),
        decision(6, 2, 60, combat=True, prompt="second"),
    ]
    invalid = [attempt("bad", error="Expecting value"), attempt("bad", error="Expecting value"),
               attempt("[1]", error="choice must be an integer from 0 to 1")]
    failed = [decision(0, 1, 80, combat=True, prompt="fine"),
              {"kind": "policy_failure",
               "failure": {"kind": "invalid_reply", "attempts": invalid}}]
    return make_job(tmp_path, [
        (lost, {"seed": "RUNDEV1", "status": "lost", "act": 1, "floor": 2, "score": 42}),
        (failed, {"seed": "RUNDEV2", "status": "policy_failure", "act": 1, "floor": 1,
                  "error": "No valid reply after declared retries"}),
    ], **kwargs)


def test_old_traces_export_requests_public_fight_labels_and_provenance(tmp_path):
    job = old_job(tmp_path)
    before = {p: p.read_bytes() for p in job.rglob("*") if p.is_file()}
    summary = export.export_runs([job, job / "run-0001"], tmp_path / "export")
    rows = read_export(tmp_path / "export")
    assert [r["user_prompt"] for r in rows] == ["neow", "hallway", "first", "second", "fine",
                                                None]
    neow, hallway, first, second, fine, failure = rows
    source = neow["provenance"]["source_id"]
    assert [r["id"] for r in rows] == [f"{source}/run-0000/m{i}" for i in range(4)] + [
        f"{source}/run-0001/m{i}" for i in range(2)]
    assert neow["system_prompt"] == SYSTEM and neow["system_prompt_sha256"] == digest(SYSTEM)
    assert (neow["game"], neow["group"], neow["split"], neow["policy"]) == (
        "spire", "RUNDEV1", "development", "llm")
    assert (neow["provider"], neow["model"], neow["harness"], neow["prompt_version"]) == (
        "openai", "gpt-6-luna", "v10", "v10")
    one, = neow["attempts"]
    assert (one["user_prompt"], one["prompt_source"], one["reasoning"]) == (
        "neow", "recorded_prompt", None)
    assert neow["issues"] == ["reasoning_not_recorded"] and neow["error"] is None
    assert neow["choice"] == {"index": 0, "id": "s:0:0", "label": "option 0",
                              "command": "choose 0"}
    assert neow["reply"] == {"reason": "because", "notes": "n"}
    assert neow["decision"]["candidates"][1]["label"] == "option 1"
    assert neow["outcome"] == {"status": "lost", "gameplay_outcome": "lost", "act": 1,
                               "floor": 2, "score": 42}
    assert neow["labels"]["fight"] is None and not neow["labels"]["in_combat"]
    assert neow["provenance"] | {"source_id": None, "trace_sha256": None,
                                 "result_sha256": None} == {
        "source_id": None, "job": job.name, "run": "run-0000", "seed": "RUNDEV1",
        "source_revision": "a" * 40, "renderer_sha256": "renderer-hash",
        "monsters_sha256": "monsters-hash", "unlock_level": 3, "trace_sha256": None,
        "result_sha256": None, "exchange_id": None, "decision_trace_line": 1,
        "exchange_trace_line": None, "failure_trace_line": None}
    # Fights: won (HP at the next decision), an event's two fights, then the losing one.
    assert hallway["labels"]["current_hp"] == 80
    assert hallway["labels"]["fight"] == {"index": 0, "floor": 1, "room_type": "MonsterRoom",
                                          "hp_start": 80, "hp_end": 72, "won": True}
    assert first["labels"]["fight"] | {"index": 1, "hp_end": 60, "won": True} == first[
        "labels"]["fight"]
    assert second["labels"]["fight"] | {"index": 2, "hp_end": None, "won": False} == second[
        "labels"]["fight"]
    # A failed run's last fight has no known result. The failed request kept no prompt.
    assert fine["labels"]["fight"]["won"] is None
    assert fine["outcome"]["gameplay_outcome"] is None
    assert failure["decision"] is failure["choice"] is failure["reply"] is None
    assert failure["error"] == {"type": "InvalidReply",
                                "message": "No valid reply after declared retries"}
    assert [a["user_prompt"] for a in failure["attempts"]] == [None, None, None]
    assert failure["attempts"][-1]["error"] == "choice must be an integer from 0 to 1"
    assert failure["issues"] == ["decision_not_recorded", "missing_retry_prompt",
                                 "missing_user_prompt", "reasoning_not_recorded"]
    assert failure["provenance"]["failure_trace_line"] == 2 and failure["labels"] == {}
    assert summary["counts"] | {"records": 6, "attempts": 8, "runs": 2, "jobs": 1,
                                "records_with_error": 1} == summary["counts"]
    inventory = summary["sources"][source]["runs"]
    assert [(r["run"], r["decisions"], r["fights"], r["requests"]) for r in inventory] == [
        ("run-0000", 7, 3, 4), ("run-0001", 1, 1, 2)]
    assert summary["sources"][source]["environment"]["game"]["sha256"] == "engine-hash"
    assert "81 points from level 4" in (tmp_path / "export/datacard.md").read_text()
    assert all(p.read_bytes() == content for p, content in before.items())
    # Identical bytes and ids from another location: ids do not depend on paths.
    elsewhere = shutil.copytree(job, tmp_path / "elsewhere" / job.name)
    export.export_runs([elsewhere], tmp_path / "again")
    assert (tmp_path / "again/decisions.jsonl").read_bytes() == (
        tmp_path / "export/decisions.jsonl").read_bytes()
    # So the same job from two locations would repeat every id: it is refused.
    with pytest.raises(ValueError, match="selected twice"):
        export.export_runs([job, elsewhere], tmp_path / "twice")


def test_new_traces_keep_retry_prompts_reasoning_and_failed_requests(tmp_path):
    replies = iter(["not json", '{"choice": 1, "reason": "safer", "notes": "keep"}',
                    "bad", "bad", "bad"])

    def send(body):
        return {"id": "r", "status": "completed", "usage": {"input_tokens": 10,
                                                            "output_tokens": 5},
                "output": [{"type": "reasoning", "summary": [{"type": "summary_text",
                                                              "text": "think"}]},
                           {"type": "message", "content": [{"type": "output_text",
                                                            "text": next(replies)}]}]}

    def traced(budget, decide):
        policy = LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "spend.jsonl", budget),
                           send=send, system_prompt=SYSTEM)
        events = []
        decide(policy, lambda kind, **fields: events.append({"kind": kind, **fields}))
        return events

    def failing(policy, event):
        counters = {"policy_calls": 0, "decisions": 0}
        play._decide(combat_message(), policy, "s", 1, counters, event)
        with pytest.raises(PolicyFailure) as failure:
            play._decide(combat_message(), policy, "s", 2, counters, event)
        event("policy_failure", failure=failure.value.failure)

    def broke(policy, event):
        with pytest.raises(Exception, match="Spent"):
            play._decide(combat_message(), policy, "s", 1, {"policy_calls": 0}, event)

    job = make_job(tmp_path, [
        (traced(1.0, failing), {"seed": "RUNDEV1", "status": "policy_failure"}),
        (traced(0.0, broke), {"seed": "RUNDEV2", "status": "budget_exhausted"}),
    ])
    manifest = json.loads((job / "manifest.json").read_text())
    (job / "manifest.json").write_text(json.dumps({**manifest, "model_exchange_version": 1}))
    summary = export.export_runs([job], tmp_path / "export")
    chosen, invalid, budget = read_export(tmp_path / "export")
    prompt = chosen["user_prompt"]
    assert prompt.startswith("Run notes:") and chosen["system_prompt"] == SYSTEM
    first, second = chosen["attempts"]
    assert first["user_prompt"] == prompt and first["error"].startswith("Expecting value")
    assert second["user_prompt"] == (prompt + "\n\nYour previous reply was invalid: "
                                     + first["error"] + ". Reply again.")
    assert second["prompt_source"] == "recorded_request" and "error" not in second
    assert second["request"]["instructions"] == SYSTEM
    assert second["reasoning"] == [{"type": "summary_text", "text": "think", "item_index": 0,
                                    "field": "summary"}]
    assert chosen["choice"]["index"] == 1 and chosen["reply"] == {"reason": "safer",
                                                                  "notes": "keep"}
    assert chosen["labels"]["fight"]["won"] is None and chosen["issues"] == []
    assert (chosen["provenance"]["exchange_id"], chosen["provenance"]["exchange_trace_line"],
            chosen["provenance"]["decision_trace_line"]) == ("m1", 1, 2)
    # The failed request is one row, matched to its policy_failure line, never two.
    assert invalid["decision"] is None and invalid["error"]["type"] == "InvalidReply"
    assert invalid["user_prompt"].startswith("Run notes:") and len(invalid["attempts"]) == 3
    assert invalid["attempts"][-1]["error"] and invalid["issues"] == ["decision_not_recorded"]
    assert (invalid["provenance"]["exchange_trace_line"],
            invalid["provenance"]["failure_trace_line"]) == (3, 4)
    assert budget["attempts"] == [] and budget["error"]["type"] == "BudgetExhausted"
    assert budget["issues"] == ["decision_not_recorded", "reply_not_recorded"]
    assert summary["counts"] | {"records": 3, "records_with_error": 2,
                                "records_without_decision": 2} == summary["counts"]
    # Filters: alternatives within one, all of them across kinds.
    for filters, kept in [({"providers": ("openrouter",)}, 0),
                          ({"models": ("gpt-6-luna", "x"), "prompt_hashes": (digest(SYSTEM),)},
                           3),
                          ({"models": ("gpt-6-luna",), "prompt_hashes": ("other",)}, 0)]:
        output = tmp_path / f"filtered-{len(list(tmp_path.glob('filtered-*')))}"
        counts = export.export_runs([job], output, **filters)["counts"]
        assert (counts["records"], counts["filtered_out"]) == (kept, 3 - kept)
        if not kept:
            assert "runs with exported rows: `{}`" in (output / "datacard.md").read_text()


def test_token_logprobs_are_requested_kept_once_in_the_trace_and_exported_aside(tmp_path):
    # The shape of the 2026-10-23 live probe: per output token, its logprob, bytes and top
    # alternatives, on the output_text part.
    tokens = [{"token": t, "logprob": -0.1, "bytes": list(t.encode()),
               "top_logprobs": [{"token": t, "bytes": list(t.encode()), "logprob": -0.1}]}
              for t in ('{"', "choice", '":', " ", "1", ', "reason": "safer", "notes": null}')]
    bodies = []

    def send(body):
        bodies.append(body)
        return {"id": "r", "status": "completed",
                "usage": {"input_tokens": 10, "output_tokens": 5, "cost": 0.0001},
                "output": [{"type": "message", "content": [{
                    "type": "output_text", "logprobs": tokens,
                    "text": '{"choice": 1, "reason": "safer", "notes": null}'}]}]}

    policy = LLMPolicy("qwen/qwen3.6-35b-a3b", "none", Ledger(tmp_path / "spend.jsonl", 1.0),
                       send=send, system_prompt=SYSTEM, provider="openrouter")
    events = []
    play._decide(combat_message(), policy, "s", 1, {"policy_calls": 0, "decisions": 0},
                 lambda kind, **fields: events.append({"kind": kind, **fields}))
    assert (bodies[0]["logprobs"], bodies[0]["top_logprobs"]) == (True, 10)
    exchange, decided = events
    assert exchange["attempts"][0]["output"][0]["content"][0]["logprobs"] == tokens
    assert not {"request", "output"} & set(decided["behavior"]["attempts"][0])
    job = make_job(tmp_path, [(events, {"seed": "DATA001", "status": "lost"})])
    manifest = json.loads((job / "manifest.json").read_text())
    (job / "manifest.json").write_text(json.dumps({**manifest, "model_exchange_version": 2}))
    summary = export.export_runs([job], tmp_path / "export")
    [row] = read_export(tmp_path / "export")
    [kept] = row["attempts"]
    assert kept["output"][0]["content"][0].keys() == {"type", "text"}
    assert kept["logprob_tokens"] == 6 and kept["request"] == bodies[0]
    assert row["choice"]["index"] == 1 and row["provider"] == "openrouter"
    [line] = (tmp_path / "export/logprobs.jsonl").read_text().splitlines()
    assert json.loads(line) == {"id": row["id"], "attempt": 0, "item_index": 0,
                                "part_index": 0, "logprobs": tokens}
    assert summary["counts"]["attempts_with_logprobs"] == 1 and row["issues"] == []
    spelled = [{"token": t, "logprob": 0.0} for t in ('{"choice": 1', ', "x"}', "<|im_end|>")]
    assert export.logprobs_complete('{"choice": 1, "x"}', [{"logprobs": spelled}])
    # A dropped token, as the backend once dropped "<" after a digit.
    assert not export.logprobs_complete('{"choice": 1, "x"}', [{"logprobs": spelled[1:]}])
    assert summary["logprobs_sha256"] == hashlib.sha256(line.encode() + b"\n").hexdigest()


def test_new_trace_edge_rows_keep_errors_out_of_training_targets(tmp_path):
    transport = {"request": sent("lost")["request"], "transport_error": "timed out",
                 "uncertain_attempts": 1}
    won = [*exchanged(1, "boss", [sent("boss")], floor=50, hp=30, combat=True),
           decision(2, 50, 12, combat=True)]
    failed = [*exchanged(1, "lost", [transport, transport], decided=False,
                         error={"type": "APIError", "message": "timed out"}),
              *exchanged(2, "accepted", [sent("accepted")], decided=False),
              # Interrupted mid-retry and before any reply: neither exchange has an error.
              *exchanged(3, "mid", [sent("mid", text="bad", error="Expecting value")],
                         decided=False),
              *exchanged(4, "early", [], decided=False)]
    job = make_job(tmp_path, [
        (won, {"seed": "RUNDEV1", "status": "won", "act": 3, "floor": 50, "score": 900}),
        (failed, {"seed": "RUNDEV2", "status": "interrupted"})])
    export.export_runs([job], tmp_path / "export")
    boss, api, accepted, mid, early = read_export(tmp_path / "export")
    # A run won during its last fight wins that fight; no later decision gives its end HP.
    assert boss["labels"]["fight"] == {"index": 0, "floor": 50, "room_type": "MonsterRoom",
                                       "hp_start": 30, "hp_end": None, "won": True}
    assert boss["outcome"]["gameplay_outcome"] == "won" and boss["error"] is None
    assert boss["issues"] == [] and boss["attempts"][0]["reasoning"] == []
    # A transport failure, retried or last, keeps its error and sent prompt; it had no reply.
    assert api["error"] == {"type": "APIError", "message": "timed out"}
    assert [{k: a[k] for k in ("text", "status", "usage", "error", "user_prompt", "reasoning")}
            for a in api["attempts"]] == 2 * [
        {"text": None, "status": None, "usage": None, "error": "timed out",
         "user_prompt": "lost", "reasoning": None}]
    assert api["issues"] == ["decision_not_recorded"]
    # An accepted reply whose decision was never logged is not a training target.
    assert accepted["error"]["type"] == "DecisionNotRecorded" and accepted["choice"] is None
    assert accepted["attempts"][-1].get("error") is None
    assert accepted["provenance"]["exchange_id"] == "m2"
    # A request that accepted no reply is never labelled as an accepted one.
    assert mid["error"]["type"] == early["error"]["type"] == "Interrupted"
    assert mid["attempts"][-1]["error"] == "Expecting value" and early["attempts"] == []


def test_reserved_evaluation_seeds_are_held_out(tmp_path):
    # The game reads O as 0 and ignores case and leading zeros: these are all held-out seeds.
    seeds = ("HELDOUT01", "RUNDEV1", "HELDOUT10", "held0ut02", "00HELDOUT03", "HELDOUT11")
    job = make_job(tmp_path, [(exchanged(1, "a", [sent("a")]), {"seed": seed, "status": "lost"})
                              for seed in seeds])
    export.export_runs([job], tmp_path / "export")
    assert [r["split"] for r in read_export(tmp_path / "export")] == [
        "held_out", "development", "held_out", "held_out", "held_out", "development"]
    assert len(export.HELD_OUT_SEEDS) == 10


def test_inconsistent_new_traces_are_refused_with_their_trace_line(tmp_path):
    request = exchanged(1, "p", [sent("p")])
    stray = {"kind": "policy_failure",
             "failure": {"kind": "invalid_reply", "attempts": request[0]["attempts"]}}
    cases = [
        (exchanged(1, "p", [sent("p", instructions="Other.\n")]),
         ":1: recorded request differs from the job's system prompt"),
        (exchanged(1, "p", [sent("q")]), ":1: recorded request differs from the saved user"),
        ([{**request[0], "prompt": "q"}, request[1]],
         ":1: exchange prompt differs from its decision's"),
        (request[1:], ":1: decision without its model exchange m1"),
        ([*request, request[1]], ":3: decision without its model exchange m1"),
        ([stray], ":1: policy failure without its model exchange m1"),
    ]
    for index, (events, message) in enumerate(cases):
        job = make_job(tmp_path / f"case-{index}", [(events, {"seed": "S", "status": "lost"})])
        with pytest.raises(ValueError, match=re.escape("trace.jsonl" + message)):
            export.export_runs([job], tmp_path / f"export-{index}")


def test_traces_that_contradict_themselves_are_refused_with_their_trace_line(tmp_path):
    request = exchanged(1, "p", [sent("p")])
    split = [{**request[0]}, {**request[1], "behavior": {
        **request[1]["behavior"],
        "attempts": [*request[1]["behavior"]["attempts"], dict(attempt(), exchange_id="m2")]}}]
    other_choice = [request[0], {**request[1], "behavior": {**request[1]["behavior"],
                                                            "selected_index": 1}}]
    cases = [
        (split, ":2: attempts from several model exchanges"),
        ([request[0], request[0], request[1]], ":2: duplicate model exchange m1"),
        (other_choice, ":2: choice mismatch"),
    ]
    for index, (events, message) in enumerate(cases):
        job = make_job(tmp_path / f"case-{index}", [(events, {"seed": "S", "status": "lost"})])
        with pytest.raises(ValueError, match=re.escape("trace.jsonl" + message)):
            export.export_runs([job], tmp_path / f"export-{index}")
    job = make_job(tmp_path / "torn", [(request, {"seed": "S", "status": "lost"})])
    with (job / "run-0000/trace.jsonl").open("a") as trace:
        trace.write('{"kind": "decis\n')
    with pytest.raises(ValueError, match=re.escape("trace.jsonl:3: invalid JSON")):
        export.export_runs([job], tmp_path / "export-torn")
    combat = make_job(tmp_path / "combat", [(request, {"seed": "S", "status": "lost"})])
    manifest = json.loads((combat / "manifest.json").read_text())
    (combat / "manifest.json").write_text(json.dumps({**manifest, "scope": "first_combat"}))
    with pytest.raises(ValueError, match="not a full-run job$"):
        export.export_runs([combat], tmp_path / "export-combat")
    with pytest.raises(ValueError, match="Select at least one job or run"):
        export.export_runs([], tmp_path / "export-none")
    assert not (tmp_path / "export-none").exists()


def test_unfinished_changed_or_misplaced_evidence_is_refused(tmp_path, monkeypatch):
    job = old_job(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        export.export_runs([job], job / "export")
    (tmp_path / "taken").mkdir()
    with pytest.raises(FileExistsError):
        export.export_runs([job], tmp_path / "taken")
    (tmp_path / "job.log").write_text("log")
    with pytest.raises(ValueError, match="not a full-run job"):
        export.export_runs([tmp_path / "job.log"], tmp_path / "export")
    running = old_job(tmp_path / "running", status="running")
    with pytest.raises(ValueError, match="still running"):
        export.export_runs([running], tmp_path / "export")
    (job / "run-0001/result.json").unlink()
    with pytest.raises(ValueError, match="no final result.json"):
        export.export_runs([job / "run-0001"], tmp_path / "export")
    original = export._requests

    def changing(trace):
        value = original(trace)
        (trace.parent / "profile.json").write_text("{}")
        return value

    monkeypatch.setattr(export, "_requests", changing)
    with pytest.raises(ValueError, match="Source changed during export"):
        export.export_runs([job / "run-0000"], tmp_path / "export")
    monkeypatch.undo()
    trace = job / "run-0000/trace.jsonl"
    trace.write_text(trace.read_text().replace('"prompt": "neow"', '"prompt": "edited"'))
    with pytest.raises(ValueError, match="prompt hash mismatch"):
        export.export_runs([job / "run-0000"], tmp_path / "export")
    (job / "system_prompt.md").write_text("Edited.\n")
    with pytest.raises(ValueError, match="system prompt hash mismatch"):
        export.export_runs([job / "run-0000"], tmp_path / "export")
    assert not (tmp_path / "export").exists() and not list(tmp_path.glob(".spire-export-*"))


def test_cli_exports_and_reports_refusals(tmp_path, monkeypatch, capsys):
    job = old_job(tmp_path)
    output = tmp_path / "exports/first"
    monkeypatch.setattr(sys, "argv", ["spire", "export", str(job), "--output", str(output),
                                      "--provider", "openai"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["counts"]["records"] == 6
    with pytest.raises(SystemExit):
        main()
    assert "already exists" in capsys.readouterr().err
