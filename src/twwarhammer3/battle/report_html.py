"""Offline presentation of report.collect output; no statistical recomputation.

Evidence groups remain intact. A comparison view may place groups beside one another
when only their requested model/effort differs, never pool their samples. Views are
grouped by scenario, each with a featured trial chosen by the curated notes or by
chronology, never by outcome. Reader-facing scenario and unit text comes from
configs/twwarhammer3/report_notes.json. Recorded game stills are embedded as WebP,
which needs Pillow.
"""

import base64
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import replay
from twwarhammer3.battle.controllers import MODEL_POLICIES, policy_parts

ASSETS = Path(__file__).with_name("report_assets")
NOTES_PATH = REPO_ROOT / "configs/twwarhammer3/report_notes.json"
MAX_STILL_BYTES = 256 * 1024
# Definition fields a comparison view can differ in, in reading order; plain settings
# are written with their label.
DIFFERENCES = ("source", "game", "track", "recorder", "imagery", "observe_ms", "tick_ms",
               "interval_ms", "scenario")
SETTINGS = {"track": "track {}", "observe_ms": "observation interval {} ms",
            "tick_ms": "mod tick {} ms", "interval_ms": "wait after orders {} ms"}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _portable(report: dict) -> dict:
    """Replace local paths with stable evidence identifiers, including paired keys."""
    instances = {job["instance"] for job in report.get("jobs", [])}
    instances.update(trial["instance"] for group in report["groups"] for trial in group["trials"])
    names = {}
    for instance in sorted(instances):
        name = Path(instance).name
        if sum(Path(other).name == name for other in instances) > 1:
            name += "-" + hashlib.sha256(instance.encode()).hexdigest()[:8]
        names[instance] = name

    def visit(value):
        if isinstance(value, dict):
            return {names.get(key, key): visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, str):
            if value in names:
                return names[value]
            if value.startswith(("/", "C:\\")):
                return "src/" + value.split("/src/", 1)[1] if "/src/" in value else Path(
                    value.replace("\\", "/")).name
        return value

    return visit(report)


def _compatibility(definition: dict, fallback: str) -> str:
    shared = {key: value for key, value in definition.items() if key not in {"model", "effort"}}
    # Missing provenance is not proof of compatibility with a different group.
    required = ("scenario", "source", "game", "track", "observe_ms", "tick_ms", "interval_ms")
    game = shared.get("game") or {}
    if (any(shared.get(key) is None for key in required)
            or not all(shared.get(key) for key in ("scenario", "source", "track"))
            or not game.get("sha256") or not game.get("steam_build_id")):
        shared["unknown_provenance_group"] = fallback
    return _json(shared)


def webp(path: Path) -> dict:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Embedding game stills needs Pillow: uv sync --locked installs it "
                           "(dev group), or install the report extra") from exc
    with Image.open(path) as source:
        original_size = source.size
        image = source.convert("RGB")
        image.thumbnail((1600, 1000))
        while True:
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=78, method=6)
            if buffer.tell() <= MAX_STILL_BYTES:
                break
            image.thumbnail((max(1, image.width * 4 // 5), max(1, image.height * 4 // 5)))
    return {"image": "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "original_size": list(original_size), "size": list(image.size),
            "bytes": len(buffer.getvalue())}


def stills(episode: Path, entries: list[dict], *, embed: bool) -> list[dict]:
    """Retain failed captures and metadata, even when only featured images are embedded."""
    output = []
    for entry in entries:
        item = {**entry, "policy_input": False}
        filename = entry.get("file")
        if filename and embed:
            try:
                item.update(webp(episode / filename), status="embedded")
            except (OSError, ValueError) as exc:
                item.update(status="error",
                            error=f"{type(exc).__name__}: cannot convert {filename}")
        elif filename:
            item["status"] = "metadata_only_nonfeatured_trial"
        output.append(item)
    return output


def _group(key: str) -> int:
    return int(key[1:].split("-")[0])  # "g2-t5" -> 2


def _model_trial(trial: dict) -> bool:
    return ((trial.get("card") or {}).get("kind") == "model"
            or policy_parts(trial["policy"], {})[0] in MODEL_POLICIES)


def _title(note: dict, scenario: dict) -> str:
    return (note.get("title") or scenario.get("family") or scenario.get("name")
            or "No scenario recorded")


def _chronology(report: dict):
    """Trials by key, and their order by job start, then episode: never by outcome."""
    created = {job["instance"]: job.get("created_at") for job in report.get("jobs", [])}
    trials = {f"g{g}-t{t}": trial for g, group in enumerate(report["groups"])
              for t, trial in enumerate(group["trials"])}
    return trials, lambda key: (created.get(trials[key]["instance"]) or "~",
                                trials[key]["episode"], trials[key]["instance"])


def _differences(definition: dict, reference: dict) -> list[str]:
    """What a comparison view changes relative to its scenario's reference view."""
    changes = []
    for key in DIFFERENCES:
        value, base = definition.get(key), reference.get(key)
        if value == base:
            continue
        if key in ("recorder", "imagery"):
            on = bool((value or {}).get("enabled"))
            if on == bool((base or {}).get("enabled")):
                continue  # a setting change that does not turn it on or off
        if key == "source":
            changes.append("a different code revision")  # the full revision is in Run settings
        elif key == "game":
            changes.append(f"game build {(value or {}).get('steam_build_id')}")
        elif key == "recorder":
            changes.append((f"{1000 / value['interval_ms']:g} Hz replay recorder on"
                            if value.get("interval_ms") else "replay recorder on") if on
                           else "no replay recorder (positions only at the controller's "
                                "observations)")
        elif key == "imagery":
            changes.append("game stills on (scripted camera moves during the battle)" if on
                           else "no game stills (the first set also moved the game camera "
                                "during the battle to take them)")
        elif key == "scenario":
            changes.append("scenario definition differs")
        else:
            changes.append(SETTINGS[key].format(value))
    return changes


def _controller(view: dict, report: dict) -> tuple[set, set]:
    """Model controller source hashes and prompt hashes of the jobs a view's trials ran in."""
    trials = [trial for index in view["groups"] for trial in report["groups"][index]["trials"]]
    instances = {trial["instance"] for trial in trials}
    cards = {(trial.get("card") or {}).get("source_sha256") for trial in trials
             if _model_trial(trial)}
    prompts = {value for job in report.get("jobs", []) if job["instance"] in instances
               for value in ((job.get("provenance") or {}).get("prompt_sha256") or {}).values()}
    return cards, prompts


def _same_controller(view: dict, reference: dict, report: dict) -> bool | None:
    """False when the known code or prompt hashes differ, True when both are known and
    match, None otherwise."""
    matches = [ours == theirs for ours, theirs in zip(_controller(view, report),
                                                      _controller(reference, report))
               if ours and theirs and None not in ours | theirs]
    return False if False in matches else True if len(matches) == 2 else None


def display_data(report: dict, notes: dict | None = None) -> dict:
    kind = report.get("evidence_kind", "recorded")
    if kind not in {"recorded", "synthetic"}:
        raise ValueError("unknown evidence kind")
    for item in [*report["groups"], *report.get("jobs", [])]:
        if item.get("evidence_kind", "recorded") != kind:
            raise ValueError("synthetic and recorded evidence must use separate reports")
    data = _portable(report)
    notes = notes or {}
    comparisons, keys, instances = [], {}, {}

    def comparison(definition, fallback):
        key = _compatibility(definition, fallback)
        if key not in keys:
            keys[key] = len(comparisons)
            comparisons.append({"id": f"comparison-{len(comparisons) + 1}",
                                "definition": {key: value for key, value in definition.items()
                                               if key not in {"model", "effort"}},
                                "groups": [], "jobs": [],
                                "metadata_origin": "Recorded job manifest"})
        return comparisons[keys[key]]

    for index, group in enumerate(data["groups"]):
        view = comparison(group["definition"], f"group-{index}")
        view["groups"].append(index)
        for trial in group["trials"]:
            instances[trial["instance"]] = view
        # Never silently give an already-pooled summary a single controller identity.
        for row in group["controllers"]:
            cards = {_json({key: (trial.get("card") or {}).get(key) for key in
                            ("kind", "model", "effort", "source_sha256", "timing")})
                for trial in group["trials"]
                if trial["controller"] == row["controller"]}
            if len(cards) > 1:
                raise ValueError(f"mixed controller identities in {row['controller']}")

    jobs = data.get("jobs", [])
    for index, job in enumerate(jobs):
        view = instances.get(job["instance"])
        if view is None:
            definition = job.get("definition")
            if definition is None:
                # Older JSON may lack metadata for setup-only jobs. Keep them in the
                # all-jobs evidence table, without borrowing a current scenario.
                continue
            view = comparison(definition, f"job-{index}")
        view["jobs"].append(index)

    for view in comparisons:
        dates = [jobs[index].get("created_at") for index in view["jobs"]]
        source = view["definition"].get("source")
        view.update(created_at=min((date for date in dates if date), default=None),
                    source_short=(str(source)[:7]
                                  if re.fullmatch(r"[0-9a-f]{7,40}", str(source)) else None),
                    differences=[], same_controller=None, reference=False)

    # Scenarios with at least one started trial, each with its featured trial.
    trials, chronology = _chronology(data)
    runs, scenario_notes = notes.get("runs") or {}, notes.get("scenarios") or {}
    by_name = {}
    for index, view in enumerate(comparisons):
        if view["groups"]:
            by_name.setdefault(view["definition"].get("scenario", {}).get("name"), []).append(index)
    scenarios = []
    for name, indexes in by_name.items():
        scenario = comparisons[indexes[0]]["definition"].get("scenario") or {}
        note = scenario_notes.get(name) or {}
        group_view = {group: index for index in indexes for group in comparisons[index]["groups"]}
        options = [key for key in trials if _group(key) in group_view]
        selected = [key for key in options if (runs.get(
            f"{trials[key]['instance']}/{trials[key]['episode']}") or {}).get("selected") is True]
        models = [key for key in options if trials[key]["valid"] and _model_trial(trials[key])]
        reason, pool = next((reason, pool) for reason, pool in (
            ("selected", selected), ("first_model_run", models), ("first_run", options)) if pool)
        featured = min(pool, key=chronology)
        reference = comparisons[group_view[_group(featured)]]
        reference["reference"] = True  # the run set holding the featured run
        for index in indexes:
            if comparisons[index] is not reference:
                comparisons[index]["differences"] = _differences(
                    comparisons[index]["definition"], reference["definition"])
            comparisons[index]["same_controller"] = _same_controller(
                comparisons[index], reference, data)
        scenarios.append({
            "id": f"scenario-{len(scenarios) + 1}", "name": name,
            "title": _title(note, scenario),
            "question": note.get("question"),
            "challenge": note.get("challenge") or scenario.get("brief"),
            "brief": scenario.get("brief"), "expect": scenario.get("expect"),
            "comparisons": indexes, "featured": featured, "featured_reason": reason,
            "setup_only_jobs": []})
    scenarios.sort(key=lambda entry: (entry["featured_reason"] != "selected", str(entry["name"])))

    # Jobs that stopped before any battle: beside their scenario, or on their own.
    started = {trial["instance"] for trial in trials.values()}
    setup_only = []
    for index, job in enumerate(jobs):
        if job["instance"] in started:
            continue
        scenario = (job.get("definition") or {}).get("scenario") or {}
        name = scenario.get("name")
        entry = next((entry for entry in scenarios if entry["name"] == name), None)
        if entry:
            entry["setup_only_jobs"].append(index)
        else:
            setup_only.append({"job": index, "scenario": name,
                               "title": _title(scenario_notes.get(name) or {}, scenario)})
    return {"schema": 1, "evidence_kind": kind, "report": data, "comparisons": comparisons,
            "scenarios": scenarios, "setup_only": setup_only,
            "model_policies": sorted(MODEL_POLICIES)}  # base names: a trial's may add @MODEL


def render(report: dict, notes: dict | None = None) -> str:
    data = display_data(report, notes)
    runs = (notes or {}).get("runs") or {}
    trials, chronology = _chronology(data["report"])
    payloads, prompts, directories = {}, {}, {}
    for group_index, group in enumerate(report["groups"]):
        for trial_index, trial in enumerate(group["trials"]):
            key = f"g{group_index}-t{trial_index}"
            job = Path(trial["instance"])
            directory = job / trial["episode"]
            directories[key] = directory
            payload = None
            if data["evidence_kind"] == "synthetic":
                payload = report.get("replays", {}).get(key)
                if payload and payload.get("evidence_kind") != "synthetic":
                    raise ValueError("synthetic replay must carry its evidence label")
            elif (directory / "trace.jsonl").exists() and (job / "manifest.json").exists():
                payload = replay.build(directory, notes=notes)
                if trials[key]["instance"] not in prompts:
                    prompts[trials[key]["instance"]] = {path.name: path.read_text() for path in
                                                        sorted(job.glob("*prompt.md"))}
            if payload is not None:
                run = runs.get(f"{trials[key]['instance']}/{trial['episode']}") or {}
                payloads[key] = {**payload, "highlights": run.get("highlights") or [],
                                 "selected": run.get("selected") is True}

    pictured = set()
    for view in data["comparisons"]:
        keys = [key for key in trials if _group(key) in view["groups"]]
        for controller in {trials[key]["controller"] for key in keys}:
            same = [key for key in keys if trials[key]["controller"] == controller]
            complete = [key for key in same if trials[key]["valid"]]
            pictured.add(min(complete or same, key=chronology))
    for key, payload in payloads.items():
        still_path = directories[key] / "stills.json"
        if data["evidence_kind"] == "recorded" and still_path.exists():
            payload["stills"] = stills(directories[key], json.loads(still_path.read_text()),
                                       embed=key in pictured)
    payloads = {key: base64.b64encode(gzip.compress(_json(payload).encode(), mtime=0)).decode()
                for key, payload in payloads.items()}
    # Replay evidence has its own compressed envelope; collector statistics stay intact.
    data["report"].pop("replays", None)
    data.update(replays=payloads, prompts=prompts)
    encoded = _json(data)
    for character, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                               ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        encoded = encoded.replace(character, escaped)
    script = (ASSETS / "replay.js").read_text() + "\n" + (ASSETS / "report.js").read_text()
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    replacements = {"@@STYLE@@": (ASSETS / "report.css").read_text(), "@@DATA@@": encoded,
                    "@@SCRIPT@@": script, "@@SCRIPT_HASH@@": digest}
    # Replace only template tokens, never tokens that might occur in evidence text.
    template = (ASSETS / "report.html").read_text()
    return re.sub(r"@@[A-Z_]+@@", lambda match: replacements[match[0]], template)


def write(path: Path, report: dict) -> None:
    html = render(report, json.loads(NOTES_PATH.read_text()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
