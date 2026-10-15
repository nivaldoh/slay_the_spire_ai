"""Offline presentation of report.collect output; no statistical recomputation.

Evidence groups remain intact. The comparison selector may place groups beside one
another when only their requested model/effort differs, never pool their samples.
Recorded game stills are embedded as WebP, which needs Pillow.
"""

import base64
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

from twwarhammer3.battle import replay, setup
from twwarhammer3.battle.controllers import MODEL_POLICIES

ASSETS = Path(__file__).with_name("report_assets")
MAX_STILL_BYTES = 256 * 1024


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


def display_data(report: dict, scenarios: dict | None = None) -> dict:
    kind = report.get("evidence_kind", "recorded")
    if kind not in {"recorded", "synthetic"}:
        raise ValueError("unknown evidence kind")
    for item in [*report["groups"], *report.get("jobs", [])]:
        if item.get("evidence_kind", "recorded") != kind:
            raise ValueError("synthetic and recorded evidence must use separate reports")
    data = _portable(report)
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

    for index, job in enumerate(data.get("jobs", [])):
        view = instances.get(job["instance"])
        if view is None:
            definition = job.get("definition")
            if definition is None:
                # Older JSON may lack metadata for setup-only jobs. Keep them in the
                # all-jobs evidence table, without borrowing a current scenario.
                continue
            view = comparison(definition, f"job-{index}")
        view["jobs"].append(index)

    recorded_names = {view["definition"].get("scenario", {}).get("name") for view in comparisons}
    if kind == "recorded":
        for name, scenario in sorted((scenarios or {}).items()):
            if scenario.get("status") and name not in recorded_names:
                comparisons.append({"id": f"comparison-{len(comparisons) + 1}",
                                    "definition": {"scenario": {**scenario, "name": name}},
                                    "groups": [], "jobs": [],
                                    "metadata_origin": "Current catalogue · unrun placeholder"})
    return {"schema": 1, "evidence_kind": kind, "report": data, "comparisons": comparisons,
            "model_policies": sorted(MODEL_POLICIES)}


def render(report: dict, scenarios: dict | None = None) -> str:
    data = display_data(report, scenarios)
    payloads, prompts, trials, directories = {}, {}, {}, {}
    for group_index, group in enumerate(report["groups"]):
        for trial_index, trial in enumerate(group["trials"]):
            key = f"g{group_index}-t{trial_index}"
            job = Path(trial["instance"])
            directory = job / trial["episode"]
            trials[key] = trial
            directories[key] = directory
            payload = None
            if data["evidence_kind"] == "synthetic":
                payload = report.get("replays", {}).get(key)
                if payload and payload.get("evidence_kind") != "synthetic":
                    raise ValueError("synthetic replay must carry its evidence label")
            elif (directory / "trace.jsonl").exists() and (job / "manifest.json").exists():
                payload = replay.build(directory)
                portable_job = data["report"]["groups"][group_index]["trials"][trial_index][
                    "instance"]
                if portable_job not in prompts:
                    prompts[portable_job] = {path.name: path.read_text() for path in
                                             sorted(job.glob("*prompt.md"))}
            if payload is not None:
                payloads[key] = payload

    def chronology(key):
        return (payloads.get(key, {}).get("created_at") or "~",
                trials[key]["episode"], trials[key]["instance"])

    featured = {}
    pictured = set()
    for view in data["comparisons"]:
        keys = [key for key in trials if int(key.split("-", 1)[0][1:]) in view["groups"]]
        completed_models = [key for key in keys if trials[key]["valid"] and (
            (trials[key].get("card") or {}).get("kind") == "model" or
            trials[key]["policy"] in MODEL_POLICIES)]
        featured[view["id"]] = min(completed_models, key=chronology) if completed_models else (
            keys[0] if keys else None)
        for controller in {trials[key]["controller"] for key in keys}:
            same = [key for key in keys if trials[key]["controller"] == controller]
            complete = [key for key in same if trials[key]["valid"]]
            if same:
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
    data.update(replays=payloads, prompts=prompts, featured=featured)
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
    html = render(report, setup.scenarios())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
