"""Offline presentation of report.collect output; no statistical recomputation.

The page shows one row per commander (model, reasoning effort, prompt or scripted rule)
within each scenario. A row can hold battles from several harness versions; it counts
them instead of splitting the row, and every battle keeps its own version. A harness is
the code and settings that shape play: presentation-only files are left out of it. The
collector's JSON and text keep the strict, never-pooled groups and paired statistics.

Each scenario has a featured trial: a curated selection, whose record the page states
beside it, else the first finished model battle, else the first battle, by chronology.
Diagnostic probes stay in the data, off the page. Reader-facing scenario and unit text
comes from configs/twwarhammer3/report_notes.json. Recorded game stills are embedded as
WebP, which needs Pillow.
"""

import base64
import gzip
import hashlib
import io
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import replay
from twwarhammer3.battle.controllers import MODEL_POLICIES, policy_parts

ASSETS = Path(__file__).with_name("report_assets")
NOTES_PATH = REPO_ROOT / "configs/twwarhammer3/report_notes.json"
MAX_STILL_BYTES = 256 * 1024
# Files that only describe or present battles; the scenario declaration is compared itself.
PRESENTATION = ("src/twwarhammer3/battle/report", "src/twwarhammer3/battle/replay.py",
                "src/twwarhammer3/battle/digest.py", "src/twwarhammer3/battle/watch.py",
                "src/twwarhammer3/battle/stats.py", "configs/twwarhammer3/report_notes.json",
                "configs/twwarhammer3/scenarios.json")
PROMPTS = {"llm": "tactical advice in the prompt", "llm_rules": "no tactical advice",
           "commander": "plans for scripted unit skills"}
VARIANTS = {"llm": "tactics", "commander": "plans"}
SCRIPTED = {"attack_nearest": ("Attack nearest", "every unit walks to the nearest visible enemy"),
            "rush_nearest": ("Charge nearest", "every unit runs at the nearest visible enemy"),
            "hold": ("Hold position", "never gives an order"),
            "skills": ("Unit skills", "each unit follows its class's default skill")}
# Unit fields and frame fields the page draws; the job directory keeps the rest.
UNIT_KEEP = ("id", "x", "z", "bearing", "men", "men0", "hp", "state", "target", "ammo", "ammo0")
MODE_KEEP = ("role", "capture_points", "supplies", "tickets")
ROUTE_STEP_M = 6  # a route outline keeps a point once a unit has moved this far


def scenario_name(definition: dict) -> str | None:
    return (definition.get("scenario") or {}).get("name") or definition.get("scenario_name")


def armies(scenario: dict) -> dict:
    """The declared starting armies in a few words."""
    def army(side):
        if not side:
            return None
        if isinstance(side, list):
            return "; ".join(filter(None, map(army, side)))
        faction = side.get("faction") or side.get("subculture") or "Unknown faction"
        faction = re.sub(r"^wh\d?_(?:main|dlc\d+|pro\d+)_(?:sc_)?[a-z]+_", "", faction)
        count = len(side["units"]) if isinstance(side.get("units"), list) else None
        return f"{replay.title(faction)} · {count} units" if count is not None else replay.title(
            faction)

    enemy = army(scenario.get("enemy"))
    if enemy is None and scenario.get("battle_type") == "survival":
        enemy = "Waves"
    return {"friendly": army(scenario.get("player")), "enemy": enemy}


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


def harness(definition: dict, job: dict | None) -> str:
    """A short fingerprint of what shapes play: code outside PRESENTATION, the scenario
    declaration without its prose, game build, interface track and timing, and whether the
    recorder or stills ran. A job without file hashes falls back to its source revision."""
    files = ((job or {}).get("provenance") or {}).get("source_files")
    code = ({path: digest for path, digest in files.items() if not path.startswith(PRESENTATION)}
            if files else definition.get("source"))
    scenario = {key: value for key, value in (definition.get("scenario") or {}).items()
                if key not in ("brief", "status")}
    settings = {key: definition.get(key) for key in ("game", "track", "observe_ms", "tick_ms",
                                                      "interval_ms", "scenario_name")}
    switches = {key: bool((definition.get(key) or {}).get("enabled"))
                for key in ("recorder", "imagery")}
    return hashlib.sha256(_json({"code": code, "scenario": scenario, **settings,
                                 **switches}).encode()).hexdigest()[:8]


def commander(trial: dict, definition: dict) -> dict:
    """The readable identity of a trial's controller: a row of the comparison."""
    card = trial.get("card") or {}
    try:
        base, model, effort = policy_parts(trial["policy"], definition)
    except ValueError:
        base, model, effort = trial["policy"], None, None
    model, effort = card.get("model") or model, card.get("effort") or effort
    extra = f"+{trial['delay_ms'] / 1000:g} s added observation age" if trial.get(
        "delay_ms") else None

    def detail(*parts):
        return " · ".join(filter(None, [*parts, extra]))

    # `short` tells rows of one name apart in tight spaces: effort, prompt variant (none for
    # rules only) and added age.
    if base in MODEL_POLICIES or card.get("kind") in ("model", "hybrid", "demo"):
        name = model or definition.get("model") or base
        return {"kind": "model", "family": name, "name": name,
                "detail": detail(effort and f"{effort} reasoning", PROMPTS.get(base)),
                "short": detail(effort and f"{effort} reasoning", VARIANTS.get(base)),
                "prompt": PROMPTS.get(base)}
    if base in SCRIPTED:
        name, rule = SCRIPTED[base]
        return {"kind": "scripted", "family": "Scripted", "name": name,
                "detail": detail(f"scripted: {rule}"), "short": detail()}
    return {"kind": "diagnostic", "family": None, "name": "Diagnostic probe",
            "detail": detail(trial["policy"].split(":")[-1]), "short": detail()}


def _share(numerator, denominator) -> float | None:
    if numerator is None or not denominator:
        return None
    return round(min(1, max(0, numerator / denominator)), 4)


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


def display_data(report: dict, notes: dict | None = None) -> dict:
    kind = report.get("evidence_kind", "recorded")
    if kind not in {"recorded", "synthetic"}:
        raise ValueError("unknown evidence kind")
    for item in [*report["groups"], *report.get("jobs", [])]:
        if item.get("evidence_kind", "recorded") != kind:
            raise ValueError("synthetic and recorded evidence must use separate reports")
    data = _portable(report)
    notes = notes or {}
    jobs = {job["instance"]: job for job in data.get("jobs", [])}
    for group in data["groups"]:
        # Never silently give an already-pooled summary a single controller identity. A trial
        # whose controller failed to build has no card, so it claims no identity.
        for row in group["controllers"]:
            cards = {_json({key: trial["card"].get(key) for key in
                            ("kind", "model", "effort", "source_sha256", "timing")})
                     for trial in group["trials"]
                     if trial["controller"] == row["controller"] and trial.get("card")}
            if len(cards) > 1:
                raise ValueError(f"mixed controller identities in {row['controller']}")

    trials, chronology = _chronology(data)
    battles, by_name = {}, {}

    def group_of(key):  # "g2-t5" -> group 2
        return data["groups"][int(key[1:].split("-")[0])]
    for key in sorted(trials, key=chronology):
        trial = trials[key]
        definition = group_of(key)["definition"]
        soldiers = (trial.get("measures") or {}).get("soldiers") or {}
        enemy, own = soldiers.get("enemy") or {}, soldiers.get("friendly") or {}
        battles[key] = {
            "commander": commander(trial, definition),
            "harness": harness(definition, jobs.get(trial["instance"])),
            "date": (jobs.get(trial["instance"]) or {}).get("created_at"),
            # Progress: the share of the enemy's registered soldiers dead or no longer
            # fighting (fleeing, shattered, leaving or undeployed) when the battle ended.
            "progress": None if None in (enemy.get("active"), enemy.get("registered")) else
            _share(enemy["registered"] - enemy["active"], enemy["registered"]),
            "own_left": _share(own.get("remaining"), own.get("registered")),
        }
        by_name.setdefault(scenario_name(definition), []).append(key)

    def row(key):
        return battles[key]["commander"]["name"], battles[key]["commander"]["detail"]

    def controlled(keys):
        """The scenario's closest thing to a controlled comparison: the same two or more
        commanders, each playing in every one of two or more launches of one harness. Of
        the candidates (commanders shared by two launches), the most launches, then the most
        commanders; None without any. `once`: each played exactly once per launch."""
        launches = defaultdict(lambda: defaultdict(list))
        for key in keys:
            launches[battles[key]["harness"]][trials[key]["instance"]].append(key)
        best = (1, 0, [], [])
        for by_launch in launches.values():
            sets = [set(map(row, keys)) for keys in by_launch.values()]
            for commanders in {frozenset(a & b) for i, a in enumerate(sets) for b in sets[i + 1:]}:
                if len(commanders) < 2:
                    continue
                shared = [keys for keys in by_launch.values() if commanders <= set(map(row, keys))]
                score = (len(shared), len(commanders))
                if score > best[:2]:
                    best = (*score, shared, commanders)
        if not best[2]:
            return None
        chosen = [[key for key in keys if row(key) in best[3]] for keys in best[2]]
        return {"launches": best[0], "once": all(len(keys) == best[1] for keys in chosen),
                "battles": sorted((key for keys in chosen for key in keys), key=chronology)}

    runs, scenario_notes = notes.get("runs") or {}, notes.get("scenarios") or {}
    scenarios, hidden = [], []
    for name, every in by_name.items():
        # Diagnostic probes test tooling, not commanding: kept in the data, not on the page.
        keys = [key for key in every if battles[key]["commander"]["kind"] != "diagnostic"]
        hidden += [key for key in every if key not in keys]
        if not keys:
            continue
        definition = group_of(keys[0])["definition"]
        scenario = definition.get("scenario") or {}
        note = scenario_notes.get(name) or {}
        selected = [key for key in keys if (runs.get(
            f"{trials[key]['instance']}/{trials[key]['episode']}") or {}).get("selected") is True]
        models = [key for key in keys
                  if trials[key]["valid"] and battles[key]["commander"]["kind"] == "model"]
        reason, pool = next((reason, pool) for reason, pool in (
            ("selected", selected), ("first_model_run", models), ("first_run", keys)) if pool)
        rows = {}
        for key in keys:
            rows.setdefault(row(key), {**battles[key]["commander"], "battles": []})[
                "battles"].append(key)
        order = {"model": 0, "scripted": 1}
        for item in rows.values():
            item["harnesses"] = len({battles[key]["harness"] for key in item["battles"]})
        scenarios.append({
            "id": f"scenario-{len(scenarios) + 1}", "name": name,
            "title": _title(note, {**scenario, "name": name}),
            "question": note.get("question"),
            "challenge": note.get("challenge") or scenario.get("brief"),
            "group": note.get("group") or ("Other battle types (pilots)"
                                           if not scenario.get("family")
                                           else "Specialist scenarios"),
            "split": scenario.get("split"), "status": scenario.get("status"),
            "difficulty": (scenario.get("expect") or {}).get("difficulty"),
            "battle_type": scenario.get("battle_type") or "unrecorded",
            "armies": armies(scenario), "battles": keys,
            "rows": sorted(rows.values(), key=lambda item: (
                order[item["kind"]], item["name"],  # numbers in natural order: +6 s before +10 s
                [int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", item["detail"])])),
            "controlled": controlled(keys),
            "featured": min(pool, key=chronology), "featured_reason": reason,
            "setup_only_jobs": []})
    # The notes' order, by group; scenarios without notes after them, by name.
    groups = list(dict.fromkeys(note.get("group") for note in scenario_notes.values()))
    listed = list(scenario_notes)
    scenarios.sort(key=lambda entry: (
        groups.index(entry["group"]) if entry["group"] in groups else len(groups),
        listed.index(entry["name"]) if entry["name"] in listed else len(listed),
        str(entry["name"])))

    # Jobs that stopped before any battle: beside their scenario, or on their own.
    started = {trial["instance"] for trial in trials.values()}
    setup_only = []
    for index, job in enumerate(data.get("jobs", [])):
        if job["instance"] in started:
            continue
        scenario = (job.get("definition") or {}).get("scenario") or {}
        name = scenario_name(job.get("definition") or {})
        entry = next((entry for entry in scenarios if entry["name"] == name), None)
        if entry:
            entry["setup_only_jobs"].append(index)
        else:
            setup_only.append({"job": index, "scenario": name,
                               "title": _title(scenario_notes.get(name) or {},
                                               {**scenario, "name": name})})
    return {"schema": 2, "evidence_kind": kind, "report": data, "battles": battles,
            "scenarios": scenarios, "setup_only": setup_only, "diagnostics": hidden}


def _round(value, digits=1):
    return round(value, digits) if isinstance(value, float) else value


def compact(payload: dict) -> dict:
    """The replay fields the page draws, with coordinates to 0.1 m."""
    def unit(u):
        kept = {key: u[key] for key in UNIT_KEEP if key in u}
        for key in ("x", "z"):
            kept[key] = _round(kept.get(key))
        if "hp" in kept:
            kept["hp"] = _round(kept["hp"], 3)
        return kept

    frames = []
    for frame in payload["frames"]:
        kept = {key: frame[key] for key in ("time_ms", "seq", "enemy_roster", "source")
                if key in frame}
        kept.update(friendly=[unit(u) for u in frame["friendly"]],
                    enemy=[unit(u) for u in frame["enemy"]])
        if frame.get("mode"):
            kept["mode"] = {key: frame["mode"][key] for key in MODE_KEEP if key in frame["mode"]}
        frames.append(kept)
    decisions = [{**decision, "displacements": [
        {**move, "metres": _round(move["metres"]), "from": [_round(v) for v in move["from"]],
         "to": [_round(v) for v in move["to"]]} for move in decision.get("displacements", [])]}
        for decision in payload["decisions"]]
    return {**payload, "frames": frames, "decisions": decisions}


def timing(payload: dict) -> dict:
    """Per batch of new orders: how old its battlefield view was when the game took it, and,
    with the 1 Hz recorder only, the farthest any unit moved between that view and the first
    frame after (sparser frames would overstate it). Commander plans keep their own age.
    `replies` pairs each applied reply's view time with its application time (battle clock,
    0.1 s); for the commander, only its plan adoptions, each view plan age before them."""
    applied = [d for d in payload["decisions"] if d.get("applied_ms") is not None]
    # The asynchronous commander's model speaks only when a plan is adopted (plan_age_s);
    # its executor's other ticks act on fresh views but follow that older plan.
    plans = [d for d in applied if d.get("plan_age_s") is not None]
    replies = [[round(d["time_ms"] - 1000 * (d.get("plan_age_s") or 0), -2), d["applied_ms"]]
               for d in plans or applied]
    batches = [d for d in payload["decisions"] if d["orders"] and d.get("age_s") is not None]
    moved = [max((m["metres"] for m in d["displacements"]), default=0) for d in batches
             if d.get("after_frame") is not None] if payload.get("recorder_version") else []
    return {"ages": [_round(d["age_s"]) for d in batches],
            "plans": [_round(d["plan_age_s"]) for d in plans],
            "moved": [round(value) for value in moved], "replies": replies}


def route(payload: dict) -> dict:
    """Each friendly unit's observed path, thinned to a point every few metres, how it ended,
    and where each enemy unit was first seen: the outline of a whole battle."""
    paths, first_seen, last = {}, {}, {}
    for frame in payload["frames"]:
        for side in ("friendly", "enemy"):
            for u in frame[side]:
                if not (isinstance(u.get("x"), (int, float)) and isinstance(u.get("z"), (int,
                                                                                         float))):
                    continue
                last[u["id"]] = u
                if side == "enemy":
                    first_seen.setdefault(u["id"], [round(u["x"]), round(u["z"])])
                    continue
                path = paths.setdefault(u["id"], [])
                if not path or math.dist(path[-1], (u["x"], u["z"])) >= ROUTE_STEP_M:
                    path.append([round(u["x"]), round(u["z"])])
    def end(uid):
        u = last[uid]
        return ("down" if u.get("men") == 0 else
                "fled" if {"routing", "shattered"} & set(u.get("state") or []) else "up")

    for uid, path in paths.items():
        point = [round(last[uid]["x"]), round(last[uid]["z"])]
        if path[-1] != point:
            path.append(point)
    return {"friendly": [{"end": end(uid), "path": path} for uid, path in paths.items()],
            "enemy": [{"at": point} for point in first_seen.values()]}


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
                payloads[key] = {**compact(payload), "highlights": run.get("highlights") or []}
                if payload["frames"]:
                    data["battles"][key].update(timing=timing(payloads[key]),
                                                route=route(payloads[key]))

    # One map outline per scenario for the route thumbnails: the featured battle's, else any.
    for scenario in data["scenarios"]:
        terrains = [payloads[key].get("terrain") for key in [scenario["featured"],
                                                             *scenario["battles"]]
                    if key in payloads]
        scenario["terrain"] = next(filter(None, terrains), None)
    # Stills: each featured battle, and the earliest completed battle of each commander in
    # each scenario.
    pictured = {scenario["featured"] for scenario in data["scenarios"]}
    for scenario in data["scenarios"]:
        for row in scenario["rows"]:
            complete = [key for key in row["battles"] if trials[key]["valid"]]
            pictured.add(min(complete or row["battles"], key=chronology))
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
