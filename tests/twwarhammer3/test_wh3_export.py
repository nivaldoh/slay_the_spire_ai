"""Exact model inputs, async plan ownership and evidence integrity in offline exports."""
import hashlib
import json
import shutil
import sys
from types import SimpleNamespace

import pytest

from twwarhammer3.__main__ import main
from twwarhammer3.battle import export

SYSTEM = "Command well.\n\nKeep spacing. é\n"
PROMPT = "Battle notes:\nnone\n\nTime 5 s.\n"
ORDERS = [{"unit": "f1", "type": "attack", "target": "e2"}]
SCENARIO = {"battle_type": "classic", "split": "development"}
LEGACY = ('attempts, feedback = [], ""\nself.call(prompt + feedback, schema)\n'
          'attempt["error"] = str(error)\n'
          'feedback = f"\\n\\nYour previous reply was invalid: {error}. Reply again."')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def attempt(text='{"orders": []}', **kw):
    return {"text": text, "response_id": "r", "status": "completed", "usd": .01,
            "usage": {"output_tokens": 10}, **kw}


def decision(request, prompt=PROMPT, attempts=None, *, kind="llm", orders=None, **metadata):
    behavior = {"type": kind, "model": "gpt-6-sol", "effort": "low", **metadata}
    if prompt is not None:
        behavior.update(prompt=prompt, prompt_sha256=digest(prompt))
    if attempts is not None:
        behavior["attempts"] = attempts
    return {"kind": "decision", "request": request, "time_ms": 5000, "seq": 5,
            "orders": ORDERS if orders is None else orders, "behavior": behavior}


def acknowledgement(request, *, ok=True):
    return {"kind": "ack", "request": request, "latency": {"delay_ms": 800},
            "ack": {"request": request, "applied_ms": 5800,
                    "results": [{"index": 1, "unit": "f1", "ok": ok,
                                 **({} if ok else {"error": "unit_routing"})}]}}


def make_job(tmp_path, events, *, policy="llm_rules", status="won", legacy=False,
             failure=None, error=None, version="v20", name="job", declared=SCENARIO, **config):
    job = tmp_path / name
    ep = job / "episode-0000"
    ep.mkdir(parents=True)
    prompt_name = "system_prompt.md" if legacy else f"{policy}_prompt.md"
    (job / prompt_name).write_text(SYSTEM)
    manifest = {"status": "completed", "source_revision": "a" * 40,
                "source_files": {"src/gameai/llm.py": digest(LEGACY)},
                "config": {"policy": policy, "model": "gpt-6-sol", "effort": "low",
                           "scenario": "battle", "provider": "openai", **config},
                "scenario": declared,
                "deployment": {"pack": {"sha256": "pack-hash"}},
                "track": "obs-v4+terrain/act-v2/live-1x",
                prompt_name.removesuffix(".md") + "_sha256": digest(SYSTEM)}
    result = {"policy": policy, "status": status, "battle_ms": 6000,
              "card": {"version": version}, "failure": failure, "error": error,
              "final": {"friendly": {"men": 1, "men0": 2}, "enemy": {"men": 0, "men0": 2}}}
    (job / "manifest.json").write_text(json.dumps(manifest))
    (job / "environment.json").write_text(json.dumps({"game": {"sha256": "engine-hash"}}))
    (ep / "result.json").write_text(json.dumps(result))
    (ep / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return job


def read_export(directory):
    return [json.loads(line) for line in (directory / "decisions.jsonl").read_text().splitlines()]


def test_exact_historical_retries_orders_ack_outcome_and_provenance(tmp_path, monkeypatch):
    export._legacy_retry_supported.cache_clear()
    monkeypatch.setattr(export.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout=LEGACY.encode()))
    raw = [attempt(" invalid \n", error="bad target é"), attempt(" still invalid ", error="again"),
           attempt(' {"orders": []}\n')]
    refused = {"kind": "invalid", "orders": [{"unit": "f9"}], "error": "unknown unit"}
    job = make_job(tmp_path, [refused, decision("r1", attempts=raw, orders=[]),
                             acknowledgement("r1", ok=False)], legacy=True)
    before = {p: p.read_bytes() for p in job.rglob("*") if p.is_file()}
    output = tmp_path / "export"
    summary = export.export_traces([job, job / "episode-0000", job], output)
    row, = read_export(output)
    assert row["system_prompt"] == SYSTEM and row["user_prompt"] == PROMPT
    assert (row["schema_version"], row["game"], row["group"], row["split"]) == (
        2, "twwarhammer3", "battle", "development")
    assert row["error"] is None and row["provider"] == "openai"
    assert [a["text"] for a in row["attempts"]] == [a["text"] for a in raw]
    assert [a["error"] for a in row["attempts"]] == ["bad target é", "again", None]
    assert not any("system_prompt" in a for a in row["attempts"])
    assert row["labels"] == {"scenario": "battle", "battle_type": "classic", "delay_ms": 0,
                             "rejected_batches": 1, "refused_orders": 1}
    assert row["provenance"]["prompt_trace_line"] == 2
    assert row["attempts"][1]["user_prompt"] == PROMPT + export.RETRY_SUFFIX.format(
        error="bad target é")
    assert row["attempts"][2]["user_prompt"] == PROMPT + export.RETRY_SUFFIX.format(error="again")
    assert "bad target" not in row["attempts"][2]["user_prompt"]
    assert row["attempts"][1]["prompt_source"] == "reconstructed_retry_from_recorded_source"
    step, = row["execution"]
    assert step["orders"] == [] and step["validation"]["orders"] == refused["orders"]
    assert step["acknowledgement"]["ack"] == acknowledgement("r1", ok=False)["ack"]
    assert row["outcome"]["gameplay_outcome"] == "won"
    assert row["outcome"]["measures"]["soldiers"]["friendly"]["remaining"] == 1
    assert "final" not in row["user_prompt"]
    source = summary["sources"][row["provenance"]["source_id"]]
    assert source["manifest"]["deployment"]["pack"]["sha256"] == "pack-hash"
    assert source["environment"]["game"]["sha256"] == "engine-hash"
    assert row["provenance"]["source_revision"] == "a" * 40
    assert all(p.read_bytes() == content for p, content in before.items())
    assert summary["counts"]["records"] == 1
    assert summary["rows_by"] == {"split": {"development": 1}, "group": {"battle": 1},
                                  "provider": {"openai": 1}}
    assert (output / "datacard.md").exists()
    # Stable bytes and identities, independent of destination or duplicate selections.
    export.export_traces([job / "episode-0000"], tmp_path / "again")
    assert (output / "decisions.jsonl").read_bytes() == (
        tmp_path / "again/decisions.jsonl").read_bytes()
    export._legacy_retry_supported.cache_clear()


def test_commander_reply_answers_previous_prompt_and_owns_later_executor_orders(tmp_path):
    events = [decision("r1", "first", kind="commander"), acknowledgement("r1"),
              decision("r2", "second", [attempt("plan 1")], kind="commander", plan=[]),
              acknowledgement("r2"), decision("r3", None, kind="commander", orders=[]),
              acknowledgement("r3"),
              decision("r4", "third", [attempt("plan 2")], kind="commander", plan=[]),
              acknowledgement("r4")]
    job = make_job(tmp_path, events, policy="commander", version="v7")
    summary = export.export_traces([job], tmp_path / "export")
    first, second, third = read_export(tmp_path / "export")
    assert first["user_prompt"] == "first" and first["attempts"][0]["text"] == "plan 1"
    assert [s["request"] for s in first["execution"]] == ["r2", "r3"]
    assert second["user_prompt"] == "second" and second["attempts"][0]["text"] == "plan 2"
    assert [s["request"] for s in second["execution"]] == ["r4"]
    assert third["user_prompt"] == "third" and third["execution"] == []
    assert third["issues"] == ["reply_not_recorded"]
    assert next(iter(summary["sources"].values()))["episodes"][0][
        "unattributed_executor_ticks"] == 1


def recorded_attempt(prompt, exchange="m1", **kw):
    return attempt(request={"instructions": SYSTEM, "input": [{"role": "user", "content": prompt}],
                            "text": {"format": {"schema": {"type": "object"}}}},
                   exchange_id=exchange, output=[{"type": "reasoning", "summary": [
                       {"type": "summary_text", "text": "summary\n"}], "content": [
                       {"type": "reasoning_text", "text": "returned text"}]}], **kw)


def test_new_exchange_recovers_late_commander_response_and_reasoning(tmp_path):
    raw = recorded_attempt(PROMPT)
    job = make_job(tmp_path, [decision("r1", kind="commander"), acknowledgement("r1"),
                             {"kind": "model_exchange", "id": "m1", "prompt": PROMPT,
                              "attempts": [raw]}], policy="commander")
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["execution"] == [] and row["issues"] == []
    assert row["attempts"][0]["request"] == raw["request"]
    assert row["attempts"][0]["output"] == raw["output"]
    assert [p["type"] for p in row["attempts"][0]["reasoning"]] == [
        "summary_text", "reasoning_text"]
    assert row["attempts"][0]["user_prompt"] == PROMPT


def test_new_failed_exchange_preserves_exact_prompt_without_fabricating_actions(tmp_path):
    raw = recorded_attempt(PROMPT, error="invalid JSON")
    job = make_job(tmp_path, [{"kind": "model_exchange", "id": "m1", "prompt": PROMPT,
                              "attempts": [raw], "error": {"type": "InvalidReply"}}],
                   status="policy_failure", failure={"kind": "invalid_reply", "attempts": [raw]})
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["user_prompt"] == PROMPT and row["execution"] == []
    assert row["outcome"]["gameplay_outcome"] is None
    assert row["error"] == {"type": "InvalidReply", "message": None}
    assert row["attempts"][0]["error"] == "invalid JSON"


@pytest.mark.parametrize("status", ["policy_failure", "infrastructure_failure", "interrupted",
                                   "truncated", "budget_exhausted"])
def test_failure_is_not_a_gameplay_loss_and_missing_ack_is_not_an_empty_ack(tmp_path, status):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])], status=status)
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["outcome"]["status"] == status and row["outcome"]["gameplay_outcome"] is None
    assert row["execution"][0]["acknowledgement"] is None
    assert "missing_acknowledgement" in row["issues"]


def test_old_failed_direct_call_never_uses_previous_prompt(tmp_path):
    failure = {"kind": "invalid_reply", "attempts": [attempt("broken", error="Expecting value")]}
    job = make_job(tmp_path, [decision("r1", attempts=[attempt("good")]), acknowledgement("r1")],
                   status="policy_failure", failure=failure,
                   error="No valid reply after declared retries")
    export.export_traces([job], tmp_path / "export")
    good, failed = read_export(tmp_path / "export")
    assert good["user_prompt"] == PROMPT and good["error"] is None
    assert failed["user_prompt"] is None and failed["attempts"][0]["user_prompt"] is None
    assert failed["execution"] == [] and "missing_user_prompt" in failed["issues"]
    assert failed["error"] == {"type": "invalid_reply",
                               "message": "No valid reply after declared retries"}
    assert failed["provenance"]["prompt_trace_line"] is None


def test_failed_requests_mark_their_unaccepted_attempts(tmp_path):
    lost = {"request": recorded_attempt(PROMPT)["request"], "transport_error": "HTTP 503",
            "uncertain_attempts": 0, "exchange_id": "m1"}
    stopped = recorded_attempt("later", exchange="m2")
    events = [{"kind": "model_exchange", "id": "m1", "prompt": PROMPT, "attempts": [lost],
               "error": {"type": "APIError", "message": "HTTP 503"}},
              {"kind": "model_exchange", "id": "m2", "prompt": "later", "attempts": [stopped],
               "error": {"type": "APIError", "message": "Reported cost exceeded reservation"}}]
    job = make_job(tmp_path, events, status="infrastructure_failure")
    export.export_traces([job], tmp_path / "export")
    first, second = read_export(tmp_path / "export")
    assert first["attempts"][0] | {"request": None} == {
        "request": None, "transport_error": "HTTP 503", "uncertain_attempts": 0,
        "exchange_id": "m1", "text": None, "status": None, "usage": None, "error": "HTTP 503",
        "user_prompt": PROMPT, "prompt_source": "recorded_request", "reasoning": None}
    assert first["error"] == {"type": "APIError", "message": "HTTP 503"}
    assert first["issues"] == [] and first["provenance"]["exchange_trace_line"] == 1
    assert second["attempts"][0]["text"] == stopped["text"]
    assert second["attempts"][0]["error"] == "Reported cost exceeded reservation"


@pytest.mark.parametrize("declared, config, group, split, battle_type", [
    ({"family": "cavalry", "split": "held_out", "battle_type": "siege"}, {}, "cavalry",
     "held_out", "siege"),
    ({"family": "cavalry", "split": "development"}, {}, "cavalry", "development", "classic"),
    (None, {}, "battle", "development", "classic"),
    ({"map": "m"}, {"scenario": "random-siege", "seed": 7}, "random-siege/seed-7",
     "development", "classic"),
    ({"map": "m"}, {"scenario": "random"}, "job", "development", "classic"),
])
def test_group_and_split_follow_the_scenario_declaration(tmp_path, declared, config, group,
                                                         split, battle_type):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])], declared=declared, **config)
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert (row["game"], row["group"], row["split"]) == ("twwarhammer3", group, split)
    # Battles are classic unless the scenario declares another type, as in stats.
    assert row["labels"]["battle_type"] == battle_type


def test_rows_and_ids_do_not_depend_on_the_checkout_path(tmp_path):
    job = make_job(tmp_path / "a", [decision("r1", attempts=[attempt()])])
    copy = shutil.copytree(job, tmp_path / "b/job")
    first = export.export_traces([job], tmp_path / "one")
    second = export.export_traces([copy], tmp_path / "two")
    assert (tmp_path / "one/decisions.jsonl").read_bytes() == (
        tmp_path / "two/decisions.jsonl").read_bytes()
    assert first["sources"].keys() == second["sources"].keys()
    assert read_export(tmp_path / "one")[0]["id"].endswith("/episode-0000/m0")
    # Rows follow the job names, not where each job is stored.
    other = make_job(tmp_path / "c", [decision("r1", attempts=[attempt()])], name="a-job")
    export.export_traces([job, other], tmp_path / "three")
    export.export_traces([copy, shutil.copytree(other, tmp_path / "0/a-job")], tmp_path / "four")
    assert (tmp_path / "three/decisions.jsonl").read_bytes() == (
        tmp_path / "four/decisions.jsonl").read_bytes()
    assert [row["provenance"]["episode"] for row in read_export(tmp_path / "three")] == [
        "episode-0000"] * 2
    with pytest.raises(ValueError, match="two locations"):
        export.export_traces([job, copy], tmp_path / "five")
    assert not (tmp_path / "five").exists()


@pytest.mark.parametrize("prompt_file", [True, False])
def test_attempts_share_one_checked_system_prompt(tmp_path, prompt_file):
    raw = recorded_attempt(PROMPT)
    raw["request"] = dict(raw["request"], instructions="Other instructions")
    job = make_job(tmp_path, [{"kind": "model_exchange", "id": "m1", "prompt": PROMPT,
                               "attempts": [raw]}])
    if prompt_file:
        with pytest.raises(ValueError, match="saved system prompt"):
            export.export_traces([job], tmp_path / "export")
        return
    (job / "llm_rules_prompt.md").unlink()
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["system_prompt"] == "Other instructions"
    assert row["system_prompt_sha256"] == digest("Other instructions")
    assert "system_prompt" not in row["attempts"][0] and row["issues"] == []
    # Without a saved prompt, a request's attempts must still agree with each other.
    retry = recorded_attempt(PROMPT)
    trace = job / "episode-0000/trace.jsonl"
    trace.write_text(json.dumps({"kind": "model_exchange", "id": "m1", "prompt": PROMPT,
                                 "attempts": [raw, retry]}) + "\n")
    with pytest.raises(ValueError, match="Recorded requests disagree on the system prompt"):
        export.export_traces([job], tmp_path / "export-2")


def test_salvaged_reply_without_exchange_records_its_invalid_reply(tmp_path):
    raw = [attempt("bad", error="cooldown"), attempt('{"orders": []}', error="cooldown")]
    events = [decision("r1", attempts=raw, dropped=["f1 cast: cooldown"]), acknowledgement("r1"),
              decision("r2", None, [attempt()], kind="commander", dropped=[]),
              acknowledgement("r2")]
    job = make_job(tmp_path, events)
    export.export_traces([job], tmp_path / "export")
    salvaged, commander = read_export(tmp_path / "export")
    assert salvaged["error"] == {"type": "InvalidReply", "message": None}
    assert salvaged["execution"][0]["orders"] == ORDERS
    assert salvaged["decision_metadata"]["dropped"] == ["f1 cast: cooldown"]
    # A commander records dropped assignments of a plan it accepted.
    assert commander["error"] is None


def test_unverifiable_retry_does_not_claim_an_exact_prompt(tmp_path):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt(error="bad"), attempt()])])
    export.export_traces([job], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["attempts"][1]["user_prompt"] is None
    assert "missing_retry_prompt" in row["issues"]


@pytest.mark.parametrize("corruption", ["system", "prompt", "trace", "running", "no_result"])
def test_bad_or_unfinished_evidence_fails_without_publishing_partial_export(tmp_path, corruption):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])])
    if corruption == "system":
        (job / "llm_rules_prompt.md").write_text("tampered")
    elif corruption == "prompt":
        path = job / "episode-0000/trace.jsonl"
        path.write_text(path.read_text().replace(digest(PROMPT), "wrong-hash"))
    elif corruption == "trace":
        (job / "episode-0000/trace.jsonl").write_text('{"kind":')
    elif corruption == "running":
        path = job / "manifest.json"
        value = json.loads(path.read_text())
        path.write_text(json.dumps(dict(value, status="running")))
    else:
        (job / "episode-0000/result.json").unlink()
    output = tmp_path / "export"
    with pytest.raises(ValueError):
        export.export_traces([job], output)
    assert not output.exists() and not list(tmp_path.glob(".wh3-export-*"))


def test_export_will_not_overwrite_or_write_inside_evidence(tmp_path):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])])
    with pytest.raises(ValueError, match="outside"):
        export.export_traces([job], job / "derived")
    with pytest.raises(ValueError, match="outside"):
        export.export_traces([job], tmp_path)
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        export.export_traces([job], destination)


def test_cli_filters_versions_and_models_and_inventories_scripted_episodes(tmp_path, monkeypatch):
    a = make_job(tmp_path, [decision("r1", attempts=[attempt()])], name="a")
    b = make_job(tmp_path, [], name="b", policy="hold")
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([str(a), str(b)]))
    destination = tmp_path / "export"
    monkeypatch.setattr(sys, "argv", ["wh3", "export", "--jobs-file", str(jobs),
                        "--output", str(destination), "--prompt-version", "v20",
                        "--model", "gpt-6-sol", "--prompt-sha256", digest(SYSTEM)])
    assert main() == 0
    assert len(read_export(destination)) == 1
    export.export_traces([a], tmp_path / "filtered", prompt_versions=("v18",))
    assert read_export(tmp_path / "filtered") == []
    export.export_traces([a], tmp_path / "wrong-hash", prompt_hashes=("wrong",))
    assert read_export(tmp_path / "wrong-hash") == []
    source = json.loads((destination / "sources.json").read_text())
    assert any(s["episodes"][0].get("excluded") for s in source["sources"].values())


def test_legacy_version_label_is_disclosed_and_unknown_is_filterable(tmp_path):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])], policy="llm", version=None,
                   legacy=True, name="llm-luna-v2-demo")
    export.export_traces([job], tmp_path / "export", prompt_versions=("v2",))
    row, = read_export(tmp_path / "export")
    assert row["prompt_version"] == "v2" and row["prompt_version_source"] == "job_name"
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])], version=None)
    export.export_traces([job], tmp_path / "unknown", prompt_versions=("unknown",))
    assert len(read_export(tmp_path / "unknown")) == 1


def test_source_changed_mid_export_is_detected(tmp_path, monkeypatch):
    job = make_job(tmp_path, [decision("r1", attempts=[attempt()])])
    original = export.episode_records

    def changed(*args):
        value = original(*args)
        with (job / "episode-0000/trace.jsonl").open("a") as handle:
            handle.write('{}\n')
        return value

    monkeypatch.setattr(export, "episode_records", changed)
    with pytest.raises(ValueError, match="Source changed"):
        export.export_traces([job], tmp_path / "export")
    assert not (tmp_path / "export").exists()


@pytest.mark.parametrize("policy_name", ["llm_rules", "commander"])
def test_play_captures_exchanges_for_export_including_unadopted_final_plan(tmp_path, policy_name):
    from test_wh3_play import CONFIG, FakeMailbox
    from wh3_fixtures import USAGE, bridge_observation

    from gameai.ledger import Ledger
    from twwarhammer3.battle.commander import CommanderPolicy
    from twwarhammer3.battle.llm import LLMPolicy
    from twwarhammer3.battle.play import play_episode

    bodies = []
    reply = {"orders": [], "assignments": [], "abilities": [], "reason": "wait", "notes": None}

    def send(body):
        bodies.append(body)
        return {"usage": USAGE, "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(reply)}]}]}

    policy = CommanderPolicy if policy_name == "commander" else LLMPolicy
    agent = policy("gpt-6-sol", "low", Ledger(tmp_path / "ledger", 1),
                   send=send, system_prompt=SYSTEM)
    job = make_job(tmp_path, [], policy=policy_name)
    config = dict(CONFIG, policy=policy_name, model="gpt-6-sol", effort="low")
    mailbox = FakeMailbox([bridge_observation(0, 0, phase="Loading"),
                           bridge_observation(1, 1000),
                           bridge_observation(2, 2000, ack=True, result="won")])
    episode = job / "episode-0001"
    result = play_episode(episode, config, lambda: agent, mailbox, not_battle=None)
    assert result["status"] == "won" and len(bodies) == 1
    export.export_traces([episode], tmp_path / "export")
    row, = read_export(tmp_path / "export")
    assert row["attempts"][0]["request"] == bodies[0]
    assert row["system_prompt"] == SYSTEM
    assert row["user_prompt"] == bodies[0]["input"][0]["content"]
    assert row["attempts"][0]["text"] == json.dumps(reply)
    assert row["issues"] == []
    assert len(row["execution"]) == (0 if policy_name == "commander" else 1)
