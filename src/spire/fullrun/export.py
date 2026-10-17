"""Offline model-request exports from saved full runs; never renders new prompts.

One row per model request, with every reply attempt, in the export-row contract the WH3
exporter shares. Old traces logged each request only on its decision; since
``model_exchange_version`` 1, ``model_exchange`` events add request bodies, output items
and failed requests. Labels are public facts from decision observations, never from raw
engine messages. Missing historical data stays missing and is labelled as an issue.
"""

import hashlib
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

from gameai.llm import reasoning_parts
from gameai.provenance import sha256

SCHEMA_VERSION = 1
OUTCOMES = {"won", "lost"}
# The prompt renderer moved into fullrun/ on 2026-10-12; older manifests name its old path.
RENDERERS = ("src/spire/fullrun/llm.py", "src/spire/llm.py")
LABELS = ("act", "floor", "current_hp", "max_hp", "gold", "screen_type", "room_type")
# Reserved for evaluation (delegated, 2026-10-17): the tuning loop never plays them.
HELD_OUT_SEEDS = frozenset(f"HELDOUT{n:02d}" for n in range(1, 11))


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _held_out(seed) -> bool:
    """Whether the game would play a held-out seed: it reads a seed in any case, the letter
    O as 0, and as a base-35 number, so leading zeros do not count (SeedHelper.getLong)."""
    return str(seed).upper().replace("O", "0").lstrip("0") in {
        name.replace("O", "0") for name in HELD_OUT_SEEDS}


def _read(path: Path, files: dict) -> dict:
    files[str(path)] = sha256(path)
    return json.loads(path.read_text())


def _exchange_id(attempts: list, where: str) -> str | None:
    ids = {attempt.get("exchange_id") for attempt in attempts or ()} - {None}
    if len(ids) > 1:
        raise ValueError(f"{where}: attempts from several model exchanges")
    return ids.pop() if ids else None


def _requests(trace: Path) -> tuple[list[dict], list[dict]]:
    """Every decision's public label facts, and the model requests in request order.

    A new trace logs a request's exchange just before its decision; their attempts share
    the exchange id. A policy failure repeats its exchange's attempts, or, in old traces,
    is the failed request's only record. An exchange id without its exchange is refused.
    """
    labels, requests, exchanges = [], [], {}
    with trace.open() as handle:
        for line, raw in enumerate(handle, 1):
            try:
                event = json.loads(raw)
            except ValueError as error:
                raise ValueError(f"{trace}:{line}: invalid JSON: {error}") from None
            kind = event.get("kind")
            where = f"{trace}:{line}"
            if kind == "model_exchange":
                if event["id"] in exchanges:
                    raise ValueError(f"{where}: duplicate model exchange {event['id']}")
                exchanges[event["id"]] = {"exchange": event, "exchange_line": line}
                requests.append(exchanges[event["id"]])
            elif kind == "decision":
                observation = event["decision"]["observation"]
                labels.append({**{key: observation.get(key) for key in LABELS},
                               "in_combat": bool(observation.get("combat_state"))})
                behavior = event["behavior"]
                if behavior.get("type") != "llm":
                    continue
                key = _exchange_id(behavior.get("attempts"), where)
                if key is None:
                    request = {}
                    requests.append(request)
                elif key not in exchanges or "decision" in exchanges[key]:
                    raise ValueError(f"{where}: decision without its model exchange {key}")
                else:
                    request = exchanges[key]
                request.update(decision=event, decision_line=line, labels=labels[-1])
            elif kind == "policy_failure":
                failure = event.get("failure") or {}
                key = _exchange_id(failure.get("attempts"), where)
                if key is None:
                    request = {"failure": failure}
                    requests.append(request)
                elif key not in exchanges:
                    raise ValueError(f"{where}: policy failure without its model exchange "
                                     f"{key}")
                else:
                    request = exchanges[key]
                request["failure_line"] = line
    return labels, requests


def _fights(labels: list[dict], status: str) -> None:
    """A fight is a maximal run of consecutive combat decisions on one floor.

    It was won when a later decision is out of combat or the run ended won during it, lost
    when the run ended lost during it, and unknown otherwise (a truncated or failed run).
    """
    fight, count = None, 0
    for label in labels:
        if not label["in_combat"]:
            if fight is not None:
                fight.update(won=True, hp_end=label["current_hp"])
            fight = label["fight"] = None
            continue
        if fight is None or fight["floor"] != label["floor"]:
            fight = {"index": count, "floor": label["floor"], "room_type": label["room_type"],
                     "hp_start": label["current_hp"], "hp_end": None, "won": None}
            count += 1
        label["fight"] = fight
    if fight is not None:
        fight["won"] = {"lost": False, "won": True}.get(status)


def _attempts(raw_attempts: list, prompt: str | None, system: str | None, issues: set,
              where: str) -> list[dict]:
    attempts = []
    for index, raw in enumerate(raw_attempts):
        # A transport failure has no reply; its message is the attempt's error, as in WH3.
        attempt = {"text": None, "status": None, "usage": None, **raw}
        if "transport_error" in raw:
            attempt["error"] = raw["transport_error"]
        request = raw.get("request")
        if request is not None:
            user, source = request["input"][0]["content"], "recorded_request"
            if system is not None and request["instructions"] != system:
                raise ValueError(f"{where}: recorded request differs from the job's system "
                                 "prompt")
            if index == 0 and prompt is not None and user != prompt:
                raise ValueError(f"{where}: recorded request differs from the saved user "
                                 "prompt")
        elif index == 0 and prompt is not None:
            user, source = prompt, "recorded_prompt"
        else:
            # Old traces kept only the first prompt; retries are never reconstructed.
            user, source = None, "unavailable"
            if index:
                issues.add("missing_retry_prompt")
        reasoning = None
        if "output" in raw:
            reasoning = reasoning_parts(raw["output"])
        elif "transport_error" not in raw:
            issues.add("reasoning_not_recorded")
        attempt.update(user_prompt=user, prompt_source=source, reasoning=reasoning)
        attempts.append(attempt)
    return attempts


def _row(request: dict, job: dict, run: dict) -> dict:
    manifest, config = job["manifest"], job["manifest"]["config"]
    source_files = manifest.get("source_files", {})
    event = request.get("decision")
    behavior = event["behavior"] if event else {}
    exchange = request.get("exchange") or {}
    failure = request.get("failure") or {}
    issues = set()
    prompt = behavior.get("prompt", exchange.get("prompt"))
    if behavior.get("prompt_sha256") and _text_hash(prompt) != behavior["prompt_sha256"]:
        raise ValueError(f"{run['trace']}:{request['decision_line']}: prompt hash mismatch")
    if exchange and prompt != exchange["prompt"]:
        raise ValueError(f"{run['trace']}:{request['exchange_line']}: exchange prompt "
                         "differs from its decision's")
    raw = exchange.get("attempts", behavior.get("attempts", failure.get("attempts", [])))
    line = (request.get("exchange_line") or request.get("decision_line")
            or request.get("failure_line"))
    attempts = _attempts(raw, prompt, job["system_prompt"], issues, f"{run['trace']}:{line}")
    system = job["system_prompt"]
    if system is None:
        system = next((a["request"]["instructions"] for a in attempts if "request" in a), None)
    error = exchange.get("error")
    if failure and not exchange:
        # Old traces name the failure kind; new ones the exception, as exchanges do.
        kind = failure.get("kind")
        error = {"type": {"invalid_reply": "InvalidReply"}.get(kind, kind),
                 "message": run["result"].get("error")}
    if error and attempts and attempts[-1].get("error") is None:
        attempts[-1]["error"] = error["message"]  # the failed call, or a crashed parse
    if exchange and not event and error is None:
        if attempts and attempts[-1].get("error") is None:
            # The reply was accepted, but the run stopped before logging its decision.
            error = {"type": "DecisionNotRecorded",
                     "message": "Accepted reply without a recorded decision"}
        else:
            # Stopped before any reply was accepted: an interrupt leaves no exchange error.
            error = {"type": "Interrupted", "message": "Request stopped without an accepted reply"}
    choice = reply = None
    if event:
        candidates = event["decision"]["candidates"]
        index = next((i for i, c in enumerate(candidates) if c["id"] == event["choice_id"]),
                     None)
        if index is None or behavior.get("selected_index", index) != index:
            raise ValueError(f"{run['trace']}:{request['decision_line']}: choice mismatch")
        choice = {"index": index, **{k: candidates[index][k] for k in ("id", "label", "command")}}
        reply = {"reason": behavior.get("reason"), "notes": behavior.get("notes")}
    else:
        issues.add("decision_not_recorded")
    if system is None:
        issues.add("missing_system_prompt")
    if prompt is None:
        issues.add("missing_user_prompt")
    if not attempts:
        issues.add("reply_not_recorded")
    result = run["result"]
    return {
        "schema_version": SCHEMA_VERSION, "game": "spire", "group": result["seed"],
        "split": "held_out" if _held_out(result["seed"]) else "development",
        "policy": "llm",
        "provider": behavior.get("provider") or config.get("provider", "openai"),
        "model": behavior.get("model") or config.get("model"),
        "effort": behavior.get("effort") or config.get("effort"),
        "harness": job["harness"], "prompt_version": job["harness"],
        "prompt_version_source": "job_name" if job["harness"] else "unavailable",
        "system_prompt": system,
        "system_prompt_sha256": _text_hash(system) if system is not None else None,
        "user_prompt": prompt,
        "user_prompt_sha256": _text_hash(prompt) if prompt is not None else None,
        "attempts": attempts, "error": error,
        "decision": event["decision"] if event else None, "choice": choice, "reply": reply,
        "labels": request["labels"] if event else {},
        "outcome": {"status": result.get("status"),
                    "gameplay_outcome": result.get("status") if result.get("status") in OUTCOMES
                    else None, "act": result.get("act"), "floor": result.get("floor"),
                    "score": result.get("score")},
        "issues": sorted(issues),
        "provenance": {
            "source_id": job["source_id"], "job": job["name"], "run": run["name"],
            "seed": result["seed"], "source_revision": manifest.get("source_revision"),
            "renderer_sha256": next((source_files[path] for path in RENDERERS
                                     if path in source_files), None),
            "monsters_sha256": source_files.get("configs/llm/monsters.json"),
            "unlock_level": run["unlock_level"], "trace_sha256": run["trace_sha256"],
            "result_sha256": run["result_sha256"],
            "exchange_id": exchange.get("id"),
            "decision_trace_line": request.get("decision_line"),
            "exchange_trace_line": request.get("exchange_line"),
            "failure_trace_line": request.get("failure_line")},
    }


def run_records(directory: Path, job: dict, files: dict) -> tuple[list[dict], dict]:
    result = _read(directory / "result.json", files)
    profile = deployment = None
    if (directory / "profile.json").exists():
        profile = _read(directory / "profile.json", files)
    if (directory / "deployment.json").exists():
        deployment = _read(directory / "deployment.json", files)
    trace = directory / "trace.jsonl"
    files[str(trace)] = sha256(trace)
    level = (profile or {}).get("ironclad_unlock_level")
    run = {"name": directory.name, "trace": trace, "result": result,
           "unlock_level": int(level) if str(level).isdigit() else None,
           "trace_sha256": files[str(trace)],
           "result_sha256": files[str(directory / "result.json")]}
    labels, requests = _requests(trace)
    _fights(labels, result.get("status"))
    records = []
    for index, request in enumerate(requests):
        record = _row(request, job, run)
        record.update(id=f"{job['source_id']}/{directory.name}/m{index}", request_index=index)
        records.append(record)
    inventory = {"run": directory.name, "seed": result.get("seed"),
                 "status": result.get("status"), "result": result, "profile": profile,
                 "deployment": deployment, "decisions": len(labels),
                 "fights": len({label["fight"]["index"] for label in labels if label["fight"]}),
                 "requests": len(records)}
    return records, inventory


def _job(path: Path, files: dict) -> dict:
    manifest = _read(path / "manifest.json", files)
    if manifest.get("scope") != "full_run":
        raise ValueError(f"{path}: not a full-run job")
    if manifest.get("status") == "running":
        raise ValueError(f"{path}: job manifest is still running; use stopped evidence")
    system = None
    prompt = path / "system_prompt.md"
    if prompt.exists():
        digest = files[str(prompt)] = sha256(prompt)
        if manifest.get("system_prompt_sha256") and digest != manifest["system_prompt_sha256"]:
            raise ValueError(f"{prompt}: system prompt hash mismatch")
        system = prompt.read_text()
    environment = None
    if (path / "environment.json").exists():
        environment = _read(path / "environment.json", files)
    # Harness labels come from job names, as in the results register; not authoritative.
    harness = re.search(r"-v(\d+(?:\.\d+)*)-", path.name)
    return {"name": path.name, "manifest": manifest, "environment": environment,
            "system_prompt": system, "harness": f"v{harness[1]}" if harness else None,
            "source_id": _text_hash(path.name + "\n" + files[str(path / "manifest.json")])}


def export_runs(paths: list[Path], output: Path, *, models: tuple[str, ...] = (),
                providers: tuple[str, ...] = (), prompt_hashes: tuple[str, ...] = ()) -> dict:
    """Write decisions.jsonl, sources.json and a data card into a new directory.

    Inputs may be jobs or runs; each run needs its final result.json. No source file is
    changed, and every input hash is rechecked before the export is published.
    """
    if not paths:
        raise ValueError("Select at least one job or run")
    selected = {}
    for path in paths:
        path = path.resolve()
        job = path if (path / "manifest.json").exists() else path.parent
        if not path.is_dir() or not (job / "manifest.json").exists():
            raise ValueError(f"{path}: not a full-run job or run")
        runs = sorted(job.glob("run-*")) if path == job else [path]
        selected.setdefault(job, set()).update(p for p in runs if p.is_dir())
    output = output.resolve()
    if any(output.is_relative_to(job) or job.is_relative_to(output) for job in selected):
        raise ValueError("Export must be outside the source job directories")
    if output.exists():
        raise FileExistsError(f"Export destination already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    files, sources, issues, rows = {}, {}, Counter(), Counter()
    counts = Counter(jobs=0, runs=0, records=0, attempts=0, records_with_error=0,
                     records_without_decision=0, filtered_out=0)
    with tempfile.TemporaryDirectory(prefix=".spire-export-", dir=output.parent) as temporary:
        directory = Path(temporary)
        with (directory / "decisions.jsonl").open("w") as handle:
            for path, runs in sorted(selected.items(), key=lambda item: (item[0].name, item[0])):
                job = _job(path, files)
                if job["source_id"] in sources:
                    raise ValueError(f"{path}: job {job['name']} is selected twice (same name "
                                     "and manifest)")
                source = sources[job["source_id"]] = {
                    "job": job["name"], "path": str(path), "manifest": job["manifest"],
                    "environment": job["environment"], "runs": []}
                counts["jobs"] += 1
                for run in sorted(runs):
                    if not (run / "result.json").exists():
                        raise ValueError(f"{run}: no final result.json; use stopped evidence")
                    records, inventory = run_records(run, job, files)
                    source["runs"].append(inventory)
                    counts["runs"] += 1
                    inventory["exported_records"] = 0
                    for record in records:
                        if ((models and record["model"] not in models)
                                or (providers and record["provider"] not in providers)
                                or (prompt_hashes
                                    and record["system_prompt_sha256"] not in prompt_hashes)):
                            counts["filtered_out"] += 1
                            continue
                        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        counts["records"] += 1
                        counts["attempts"] += len(record["attempts"])
                        counts["records_with_error"] += record["error"] is not None
                        counts["records_without_decision"] += record["decision"] is None
                        inventory["exported_records"] += 1
                        issues.update(record["issues"])
                        rows[f"{record['provider']}/{record['model']}"] += 1
        for path, digest in files.items():
            if sha256(Path(path)) != digest:
                raise ValueError(f"Source changed during export: {path}")
        summary = {"schema_version": SCHEMA_VERSION, "counts": dict(counts),
                   "issues": dict(sorted(issues.items())), "records_by_model": dict(rows),
                   "filters": {"models": list(models), "providers": list(providers),
                               "prompt_hashes": list(prompt_hashes)},
                   "exporter_sha256": sha256(Path(__file__)), "files": files,
                   "sources": sources, "decisions_sha256": sha256(directory / "decisions.jsonl")}
        (directory / "sources.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n")
        (directory / "datacard.md").write_text(_data_card(summary))
        directory.rename(output)
    return summary


def _data_card(summary: dict) -> str:
    runs = [run for source in summary["sources"].values() for run in source["runs"]
            if run["exported_records"]]
    statuses = Counter(run["status"] for run in runs)
    levels = Counter(str((run["profile"] or {}).get("ironclad_unlock_level")) for run in runs)
    openai = sum(n for key, n in summary["records_by_model"].items()
                 if key.startswith("openai/"))
    return f"""# Slay the Spire full-run model-request export (schema {SCHEMA_VERSION})

Offline export of saved original-engine runs (Ironclad, Ascension 0). One JSONL row per
model request, with all reply attempts. No training or train/test split is performed.
Sources are unchanged.

## Contents and provenance

- `decisions.jsonl`: the exact saved system and user prompts, every raw attempt, the
  public decision the policy saw (`decision`: observation, candidates, id), the engine
  command chosen (`choice`), the reply's reason and notes, public labels and the run
  outcome. Rows follow the export-row contract shared with WH3: `group` is the game seed
  and `split` is `held_out` for the reserved evaluation seeds `HELDOUT01` to `HELDOUT10`
  (in any spelling the game reads as the same seed), otherwise `development`.
- `sources.json`: full job manifests (configuration, source fingerprints, revision),
  environment snapshots, each run's result, profile and deployment, input file hashes,
  the exporter hash, filters, counts, issues and the hash of `decisions.jsonl`. Each row's
  `provenance.source_id` (job name and manifest hash) references its job.
- `harness` and `prompt_version` are the job-name label (`-vN-`), as in the results
  register, not an authoritative version; the system prompt hash and source revision are.

## Interpretation

`user_prompt` is the request's initial prompt; each attempt's `user_prompt` is what that
attempt sent, retry feedback included. Traces before model-exchange capture
(`manifest.model_exchange_version` absent) kept the first prompt but not retry prompts,
request bodies or output items: such retry prompts are null (`missing_retry_prompt`) and
`reasoning` is null (`reasoning_not_recorded`). An empty reasoning list means capture
existed but no visible reasoning was returned. OpenAI returns reasoning summaries, not
full reasoning. Reasoning never re-enters the prompts.

A request that ended without an accepted reply (invalid replies, an API failure, a budget
stop) has a non-null `error`, no `decision` and no `choice`; its last attempt carries the
error. `error.type` is the exception name (`InvalidReply`, `APIError`, `BudgetExhausted`,
...) in every trace format. A reply that was accepted but whose decision was never logged
(the run stopped in between) has the error `DecisionNotRecorded`, which its attempts do
not carry; a request stopped before any reply was accepted has `Interrupted`. A transport
failure's attempt has null `text`, `status` and `usage`; its error is the transport
message. Every row without a decision has an error. `reply.notes` is the notes text as
applied (cut to 2,000 characters), null when the reply kept the previous notes. Forced
single-choice decisions made no request and have no row, but count towards labels.

`outcome.gameplay_outcome` is only `won` or `lost`; truncations, interruptions and
infrastructure or policy failures keep their status. A run's outcome does not make each
of its choices a good training target.

## Labels

`labels` holds public facts from the row's decision observation: act, floor, HP, max HP,
gold, screen and room type, and whether it is in combat. `fight` (null outside combat) is
a maximal run of consecutive combat decisions on one floor, numbered from 0 within the
run. `won` is true when a later decision is out of combat or the run was won during the
fight, false when the run was lost during it, and null otherwise (a truncated or failed
run). `hp_start` is the HP at the fight's first decision, after any damage taken before
it; `hp_end` is the HP at the next out-of-combat decision, after end-of-combat healing
such as Burning Blood's, and null when no decision follows the fight. An escape (Smoke
Bomb) counts as won; an event's two fights on one floor (the Colosseum) are two fights.
Labels never read raw engine messages, so they hold no hidden state.

## Coverage and limitations

Counts: `{json.dumps(summary['counts'], sort_keys=True)}`.

Rows by provider and model: `{json.dumps(summary['records_by_model'], sort_keys=True)}`.

Rows with each issue: `{json.dumps(summary['issues'], sort_keys=True)}`.

Statuses of the runs with exported rows: `{json.dumps(dict(statuses), sort_keys=True)}`.

Filters: `{json.dumps(summary['filters'], sort_keys=True)}`.

Ironclad unlock level per run with exported rows (`None`: profile unreadable):
`{json.dumps(dict(levels), sort_keys=True)}`. Every readable profile saved by 2026-10-17
is at unlock level 3, and the profile was then 81 points from level 4. A new unlock level
adds cards and relics to the reward, shop and event pools, so runs at different levels
are not the same task: check `provenance.unlock_level` before mixing them. Development
seeds were replayed across harness versions, so rows of one seed share game situations:
split by `group`.

Provider terms: {openai} rows here were produced by OpenAI models. By default they must
not enter a training set; the owner has not decided whether the provider's terms allow
it. Rows from open-weight models served through OpenRouter may. This export is not
permission or a training license. No credentials or authorization headers are read.
"""
