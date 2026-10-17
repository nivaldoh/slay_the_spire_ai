"""Offline, lossless model-decision exports from WH3 evidence; never renders new prompts.

One row per model request (including retries), not per executor tick. A commander's
execution spans its adoption through the next adoption. Default-skill ticks before its
first plan are not model actions. Missing historical data stays missing and is labelled.
Rows follow the export-row contract both games share (docs/twwarhammer3/traces.md).
"""

import hashlib
import json
import re
import subprocess
import tempfile
from collections import Counter
from functools import lru_cache
from pathlib import Path

from gameai.llm import reasoning_parts
from gameai.provenance import REPO_ROOT, sha256
from twwarhammer3.battle.controllers import MODEL_POLICIES, policy_parts
from twwarhammer3.battle.report import shared_measures

SCHEMA_VERSION = 2
OUTCOMES = {"won", "lost", "draw"}
RETRY_SUFFIX = "\n\nYour previous reply was invalid: {error}. Reply again."


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _read(path: Path, files: dict) -> dict:
    files[str(path)] = sha256(path)
    return json.loads(path.read_text())


@lru_cache(maxsize=None)
def _legacy_retry_supported(revision: str, source_hash: str) -> bool:
    """Only reconstruct retries from the recorded implementation, never today's renderer."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision or "") or not source_hash:
        return False
    source = subprocess.run(
        ["git", "show", f"{revision}:src/gameai/llm.py"], cwd=REPO_ROOT,
        capture_output=True)
    if source.returncode or hashlib.sha256(source.stdout).hexdigest() != source_hash:
        return False
    text = source.stdout.decode()
    return all(fragment in text for fragment in (
        'attempts, feedback = [], ""', 'self.call(prompt + feedback, schema)',
        'attempt["error"] = str(error)',
        'feedback = f"\\n\\nYour previous reply was invalid: {error}. Reply again."'))


def _new_record(prompt, line: int | None, behavior: dict) -> dict:
    return {"user_prompt": prompt, "prompt_trace_line": line, "attempts": [], "error": None,
            "decision_metadata": {}, "execution": [], "issues": [],
            "model": behavior.get("model"), "effort": behavior.get("effort")}


def _decisions(trace: Path, result: dict) -> tuple[list[dict], int]:
    records, exchanges, acks, requests = [], [], {}, set()
    pending = active = invalid = None
    unattributed = 0
    with trace.open() as handle:
        for line, raw in enumerate(handle, 1):
            try:
                event = json.loads(raw)
            except ValueError as error:
                raise ValueError(f"{trace}:{line}: invalid JSON: {error}") from None
            kind = event.get("kind")
            if kind == "model_exchange":
                exchanges.append((line, event))
            elif kind == "ack":
                request = event["request"]
                if request in acks:
                    raise ValueError(f"{trace}:{line}: duplicate acknowledgement {request}")
                acks[request] = {"trace_line": line, **event}
            elif kind == "invalid":
                invalid = {"trace_line": line, **event}
            elif kind == "decision":
                request = event["request"]
                if request in requests:
                    raise ValueError(f"{trace}:{line}: duplicate request {request}")
                requests.add(request)
                behavior = event.get("behavior") or {}
                commander = behavior.get("type") == "commander"
                if behavior.get("type") not in {"llm", "commander"}:
                    invalid = None
                    continue
                prompt = behavior.get("prompt")
                if prompt is not None and behavior.get("prompt_sha256"):
                    if _text_hash(prompt) != behavior["prompt_sha256"]:
                        raise ValueError(f"{trace}:{line}: prompt hash mismatch")
                if not commander:
                    active = _new_record(prompt, line, behavior)
                    records.append(active)
                elif behavior.get("attempts"):
                    active = pending
                    if active is None:
                        active = _new_record(None, line, behavior)
                        records.append(active)
                    pending = None
                if behavior.get("attempts") and active is not None:
                    active["attempts"] = behavior["attempts"]
                    active["decision_metadata"] = {k: v for k, v in behavior.items()
                                                   if k not in {"prompt", "prompt_sha256",
                                                                "attempts"}}
                if active is not None:
                    step = {k: v for k, v in event.items() if k not in {"kind", "behavior"}}
                    step.update(trace_line=line, validation=invalid)
                    active["execution"].append(step)
                else:
                    unattributed += 1
                if commander and prompt is not None:
                    if pending is not None:
                        raise ValueError(f"{trace}:{line}: overlapping commander requests")
                    pending = _new_record(prompt, line, behavior)
                    records.append(pending)
                invalid = None
    # New traces retain requests that failed, or completed after the last executor tick.
    claimed = set()
    for line, exchange in exchanges:
        matches = [r for r in records if any(a.get("exchange_id") == exchange["id"]
                                             for a in r["attempts"])]
        if not matches:
            matches = [r for r in records if id(r) not in claimed
                       and r["user_prompt"] == exchange["prompt"]]
        if len(matches) > 1:
            raise ValueError(f"{trace}:{line}: ambiguous model exchange {exchange['id']}")
        record = matches[0] if matches else _new_record(exchange["prompt"], line, {})
        if not matches:
            records.append(record)
        claimed.add(id(record))
        error = exchange.get("error")
        record.update(attempts=exchange["attempts"], exchange_id=exchange["id"],
                      exchange_trace_line=line,
                      error={"type": error.get("type"), "message": error.get("message")}
                      if error else None)
    # Old direct failures never wrote their final prompt. Preserve the attempts without
    # pretending the previous successful prompt was the failed one. Commander did log it.
    failure = result.get("failure") or {}
    if failure.get("attempts") and not exchanges:
        record = pending if pending is not None else _new_record(None, None, {})
        if pending is None:
            records.append(record)
        record.update(attempts=failure["attempts"],
                      error={"type": failure.get("kind"), "message": result.get("error")})
    for record in records:
        for step in record["execution"]:
            step["acknowledgement"] = acks.get(step["request"])
            if step["acknowledgement"] is None:
                record["issues"].append("missing_acknowledgement")
    return records, unattributed


def _attempts(record: dict, system: str | None, manifest: dict) -> tuple[list[dict], str | None]:
    """The attempts with each one's exact user prompt, and the system prompt they were sent
    with (the saved prompt file, else the recorded request instructions)."""
    attempts = []
    for index, raw in enumerate(record["attempts"]):
        # A transport failure has no reply; its message is the attempt's error.
        attempt = {"text": None, "status": None, "usage": None,
                   "error": raw.get("transport_error"), **raw}
        request = raw.get("request")
        if request is not None:
            user = request["input"][0]["content"]
            if system is None:
                system = request["instructions"]
            elif request["instructions"] != system:
                raise ValueError("Recorded request differs from the saved system prompt")
            if index == 0 and record["user_prompt"] is not None and user != record["user_prompt"]:
                raise ValueError("Recorded request differs from the saved user prompt")
            origin = "recorded_request"
        else:
            user, origin = record["user_prompt"], "recorded_prompt"
            if index:
                previous = record["attempts"][index - 1]
                supported = _legacy_retry_supported(
                    manifest.get("source_revision"),
                    manifest.get("source_files", {}).get("src/gameai/llm.py", ""))
                if user is not None and "error" in previous and supported:
                    user += RETRY_SUFFIX.format(error=previous["error"])
                    origin = "reconstructed_retry_from_recorded_source"
                else:
                    user, origin = None, "unavailable"
                    record["issues"].append("missing_retry_prompt")
        reasoning = None
        if "output" in raw:
            reasoning = reasoning_parts(raw["output"])
        elif "transport_error" not in raw:
            record["issues"].append("reasoning_not_recorded")
        attempt.update(user_prompt=user, prompt_source=origin, reasoning=reasoning)
        attempts.append(attempt)
    # A request that failed after its last reply (a failed response, a cost stop) did not
    # accept that reply either.
    error = record["error"]
    if error and attempts and attempts[-1]["error"] is None:
        attempts[-1]["error"] = error["message"] or error["type"]
    return attempts, system


def _prompt(job: Path, base: str, manifest: dict, files: dict):
    path, key = job / f"{base}_prompt.md", f"{base}_prompt_sha256"
    if not path.exists():
        # Older jobs saved one prompt only, and did not rotate distinct model policies.
        bases = {name.split("@")[0] for name in manifest["config"]["policy"].split(",")}
        if len(bases & MODEL_POLICIES) == 1:
            path, key = job / "system_prompt.md", "system_prompt_sha256"
    if not path.exists():
        return None, None
    digest = files[str(path)] = sha256(path)
    if manifest.get(key) and digest != manifest[key]:
        raise ValueError(f"{path}: system prompt hash mismatch")
    return path.read_text(), digest


def _version(result: dict, job: Path, base: str) -> tuple[str | None, str]:
    version = result.get("card", {}).get("version")
    if version:
        return version, "controller_card"
    # Old version-job labels are useful, but not authoritative like the prompt hash.
    match = re.search(r"-v(\d+(?:\.\d+)*)-", job.name)
    if match and job.name.startswith(base + "-"):
        return "v" + match[1], "job_name"
    return None, "unavailable"


def _group(job: Path, manifest: dict) -> str:
    """The leak-free split unit: the declared scenario family, else the scenario name. A
    random scenario is one draw per seed, which jobs can repeat."""
    config, scenario = manifest["config"], manifest.get("scenario") or {}
    name = config["scenario"]
    if scenario.get("family"):
        return scenario["family"]
    if name == "random" or name.startswith("random-"):
        return f"{name}/seed-{config['seed']}" if config.get("seed") is not None else job.name
    return name


def _labels(record: dict, manifest: dict, delay_ms: int) -> dict:
    """WH3 facts a dataset builder may filter on without reading ``execution``."""
    steps = record["execution"]
    acks = [step["acknowledgement"]["ack"] for step in steps if step["acknowledgement"]]
    return {"scenario": manifest["config"]["scenario"],
            "battle_type": (manifest.get("scenario") or {}).get("battle_type"),
            "delay_ms": delay_ms,
            "rejected_batches": sum(step["validation"] is not None for step in steps),
            "refused_orders": sum(not result.get("ok") for ack in acks
                                  for result in ack.get("results") or [])}


def episode_records(episode: Path, manifest: dict, files: dict) -> tuple[list[dict], dict]:
    job = episode.parent
    result = _read(episode / "result.json", files)
    base, model, effort = policy_parts(result.get("policy", manifest["config"]["policy"]),
                                      manifest["config"])
    inventory = {"episode": episode.name, "policy": base, "status": result.get("status"),
                 "records": 0, "result": result}
    if base not in MODEL_POLICIES:
        inventory["excluded"] = "not a built-in model controller"
        return [], inventory
    trace = episode / "trace.jsonl"
    files[str(trace)] = sha256(trace)
    system, system_hash = _prompt(job, base, manifest, files)
    records, unattributed = _decisions(trace, result)
    version, version_source = _version(result, job, base)
    scenario = manifest.get("scenario") or {}
    outcome = {"status": result.get("status"),
               "gameplay_outcome": result.get("status") if result.get("status") in OUTCOMES
               else None, "ended_by": result.get("ended_by"), "error": result.get("error"),
               "measures": shared_measures(result, scenario), "final": result.get("final"),
               "objectives": result.get("objectives"), "llm": result.get("llm")}
    group = _group(job, manifest)
    split = "held_out" if scenario.get("split") == "held_out" else "development"
    for index, record in enumerate(records):
        record["attempts"], recorded_system = _attempts(record, system, manifest)
        if recorded_system is None:
            record["issues"].append("missing_system_prompt")
        if record["user_prompt"] is None:
            record["issues"].append("missing_user_prompt")
        if not record["attempts"]:
            record["issues"].append("reply_not_recorded")
        record.update(
            schema_version=SCHEMA_VERSION, game="twwarhammer3", group=group, split=split,
            decision_index=index, policy=base,
            model=record["model"] or model, effort=record["effort"] or effort,
            provider=result.get("card", {}).get("provider") or
            manifest["config"].get("provider", "openai"),
            prompt_version=version, prompt_version_source=version_source,
            system_prompt=recorded_system,
            system_prompt_sha256=_text_hash(recorded_system) if recorded_system is not None
            else None, system_prompt_file_sha256=system_hash,
            user_prompt_sha256=_text_hash(record["user_prompt"])
            if record["user_prompt"] is not None else None,
            scenario=manifest["config"].get("scenario"),
            track=result.get("track", manifest.get("track")),
            delay_ms=result.get("delay_ms", 0), outcome=outcome,
            labels=_labels(record, manifest, result.get("delay_ms", 0)),
            provenance={"source_revision": manifest.get("source_revision"),
                        "episode": episode.name, "trace_sha256": files[str(trace)],
                        "result_sha256": files[str(episode / "result.json")],
                        "prompt_trace_line": record.pop("prompt_trace_line"),
                        "exchange_trace_line": record.pop("exchange_trace_line", None),
                        "controller": result.get("card")})
        record["issues"] = sorted(set(record["issues"]))
    inventory.update(records=len(records), unattributed_executor_ticks=unattributed)
    return records, inventory


def export_traces(paths: list[Path], output: Path, *, prompt_versions: tuple[str, ...] = (),
                  models: tuple[str, ...] = (), prompt_hashes: tuple[str, ...] = ()) -> dict:
    """Write decisions.jsonl, sources.json and a data card into a new directory.

    Inputs may be jobs or episodes. Completed episode results are required. No source
    file is changed; hashes are rechecked before publishing the export.
    """
    if not paths:
        raise ValueError("Select at least one job or episode")
    selected = {}
    for path in paths:
        path = path.resolve()
        job = path if (path / "manifest.json").exists() else path.parent
        if not (job / "manifest.json").exists():
            raise ValueError(f"{path}: not a WH3 job or episode")
        episodes = sorted(job.glob("episode-*")) if path == job else [path]
        selected.setdefault(job, set()).update(p for p in episodes if p.is_dir())
    output = output.resolve()
    if any(output.is_relative_to(job) or job.is_relative_to(output) for job in selected):
        raise ValueError("Export must be outside the source job directories")
    if output.exists():
        raise FileExistsError(f"Export destination already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    files, sources, issues = {}, {}, Counter()
    counts = Counter(records=0, attempts=0, episodes=0, execution_steps=0)
    rows_by = {key: Counter() for key in ("split", "group", "provider")}
    with tempfile.TemporaryDirectory(prefix=".wh3-export-", dir=output.parent) as temporary:
        directory = Path(temporary)
        with (directory / "decisions.jsonl").open("w") as handle:
            for job, episodes in sorted(selected.items()):
                manifest = _read(job / "manifest.json", files)
                if manifest.get("status") == "running":
                    raise ValueError(f"{job}: job manifest is still running; use stopped evidence")
                # The job's name and manifest identify it wherever the checkout is.
                source_id = _text_hash(job.name + "\n" + files[str(job / "manifest.json")])
                environment_path = job / "environment.json"
                environment = _read(environment_path, files) if environment_path.exists() else None
                source = {"path": str(job), "manifest": manifest, "environment": environment,
                          "episodes": []}
                sources[source_id] = source
                for episode in sorted(episodes):
                    if not (episode / "result.json").exists():
                        raise ValueError(f"{episode}: no final result.json; use stopped evidence")
                    records, inventory = episode_records(episode, manifest, files)
                    source["episodes"].append(inventory)
                    counts["episodes"] += 1
                    inventory["exported_records"] = 0
                    for record in records:
                        if prompt_versions and (record["prompt_version"] or "unknown") not in (
                                prompt_versions):
                            continue
                        if models and record["model"] not in models:
                            continue
                        if prompt_hashes and record["system_prompt_sha256"] not in prompt_hashes:
                            continue
                        record["id"] = f"{source_id}/{episode.name}/m{record['decision_index']}"
                        record["provenance"]["source_id"] = source_id
                        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        counts["records"] += 1
                        counts["attempts"] += len(record["attempts"])
                        counts["execution_steps"] += len(record["execution"])
                        inventory["exported_records"] += 1
                        issues.update(record["issues"])
                        for key, counter in rows_by.items():
                            counter[record[key]] += 1
        for path, digest in files.items():
            if sha256(Path(path)) != digest:
                raise ValueError(f"Source changed during export: {path}")
        summary = {"schema_version": SCHEMA_VERSION, "counts": dict(counts),
                   "issues": dict(sorted(issues.items())),
                   "rows_by": {key: dict(sorted(counter.items()))
                               for key, counter in rows_by.items()},
                   "filters": {"prompt_versions": list(prompt_versions), "models": list(models),
                               "prompt_hashes": list(prompt_hashes)},
                   "exporter_sha256": sha256(Path(__file__)),
                   "measures_sha256": sha256(Path(__file__).with_name("report.py")),
                   "files": files, "sources": sources,
                   "decisions_sha256": sha256(directory / "decisions.jsonl")}
        (directory / "sources.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n")
        (directory / "datacard.md").write_text(_data_card(summary))
        directory.rename(output)
    return summary


def _data_card(summary: dict) -> str:
    return f"""# WH3 model-decision export (schema {SCHEMA_VERSION})

Offline export of saved original-game battles. One JSONL row per model request, with
all reply attempts, in the export-row contract both games share. No training is
performed. Sources are unchanged.

## Contents and provenance

- `decisions.jsonl`: exact saved system/user prompts, raw attempts, validated orders in
  `execution`, engine acknowledgements, episode outcomes and common measures.
- `sources.json`: full source manifests (configuration, source hashes, deployment pins),
  environment snapshots, episode results, input hashes, exporter and measures code hashes,
  filters, coverage and the decisions file hash. Each row references its source id.
- Rows carry game, group, split, model, provider, effort, scenario, controller/prompt
  version, track and delay. Older version labels from job names are labelled as such;
  unknown versions are null. Exact system prompt hashes and source revisions identify
  every recorded format. Row and source ids derive from job names and manifest hashes,
  not from where the evidence is stored.

## Interpretation

`user_prompt` is the initial model prompt. Each attempt's `user_prompt` includes its own
retry feedback; `prompt_source` distinguishes recorded requests, saved initial prompts and
retries reconstructed from the hash-checked historical implementation. Unknown prompts
are null. New attempts include the request body (including the JSON schema) and raw output
items. A transport failure has null text, status and usage. HTTP retries within one
request only expose recorded counts, not unreturned provider responses.

`error` is null when the request ended with an accepted reply, else its `type` and
`message`. An attempt's `error` is null for the accepted reply, else the parser's,
transport's or failed request's message. `labels` count the row's locally rejected
batches and engine-refused orders (for commander, including later executor ticks).

`group` is the unit to keep whole when splitting: the declared scenario family, else the
scenario name; a random scenario's group is its name and draw seed. `split` is `held_out`
only for scenarios declared held out. Held-out variants share their family with
development scenarios, so the split, not the group, separates them.

For commander, `execution` contains the logged executor ticks from adoption until the
next adopted plan. Persistent assignments can come from earlier plans: these are hybrid
controller actions, not direct model orders. Initial default-skill ticks are counted in
the source inventory but are not attributed to a model. Late or failed requests can have
no execution. Empty orders and missing acknowledgements are distinct. Validation failures,
salvaged replies, dropped orders and engine refusals are preserved; none is a positive
training target merely because its episode won.

`reasoning` is null when old traces did not retain output items; an empty list means
capture exists but no visible reasoning text was returned. Text parts keep their provider
`type`, `field` and item index. Summaries are not full reasoning. Encrypted output, if
returned, remains opaque. Reasoning never re-enters the policy prompts.

`outcome.gameplay_outcome` is only won/lost/draw; infrastructure/policy failures,
interruptions and truncations remain separate statuses. Outcome measures and source
snapshots may contain evaluation-only information and MUST NOT be added to policy inputs.
Prompts are copied, not regenerated from observations or enriched with hidden state.

## Coverage and limitations

Counts: `{json.dumps(summary['counts'], sort_keys=True)}`.

Rows with each missing-data issue: `{json.dumps(summary['issues'], sort_keys=True)}`.

Rows by split, group and provider: `{json.dumps(summary['rows_by'], sort_keys=True)}`.

Filters: `{json.dumps(summary['filters'], sort_keys=True)}`.

Built-in llm, llm_rules and commander are supported. Scripted/external controllers have
no exported model rows and remain in the inventory. Historical prompts, lost responses
and reasoning cannot be recovered when they were never recorded. A hard process crash
can still lose in-flight requests. No current prompt or outcome is substituted for them.
The sample contains development/tuning battles, losses and invalid replies, not an expert
dataset. Keep whole groups together when designing splits; avoid leakage through shared
histories and repeated starts.

Before post-training or redistribution, review the source provider/model terms for the
intended use (including restrictions on training competing models). Rows produced by
OpenAI models stay out of training sets by default while that review is open; rows from
open-weight models served through OpenRouter may enter them. This export is not
permission or a training license. No credentials or HTTP authorization headers are read.
"""
