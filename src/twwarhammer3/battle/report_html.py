"""Offline presentation of report.collect output; no statistical recomputation.

The page shows one row per commander (model, reasoning effort, prompt or scripted rule)
within each scenario. A row can hold battles from several harness versions; it counts
them instead of splitting the row, and every battle keeps its own version. A harness is
the code and settings that shape play: presentation-only files are left out of it. The
collector's JSON and text keep the strict, never-pooled groups and paired statistics.

The page shows the core scenarios (`core_candidate` in the notes, one per decision family)
and only their completed battles; a report without a core scenario shows every scenario.
Variants, pilots, incomplete attempts, setup-only launches and diagnostic probes stay in the
data and the collector's JSON, off the page, and their replays are not embedded.

Each scenario has a featured trial: a curated selection, whose record the page states
beside it, else the first model battle, else the first battle, by chronology. Reader-facing
scenario and unit text comes from configs/twwarhammer3/report_notes.json. Recorded game
stills are embedded as WebP, which needs Pillow.
"""

import base64
import gzip
import hashlib
import io
import json
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
                "configs/twwarhammer3/benchmark_jobs.json", "configs/twwarhammer3/scenarios.json")
PROMPTS = {"llm": "prompt with tactical tips", "llm_rules": "rules-only prompt",
           "commander": "writes plans that scripted unit skills carry out"}
VARIANTS = {"llm": "tactical tips", "commander": "plans"}
# Races by the code in a faction key (wh3_dlc23_chd_astragoth -> chd): name, adjective.
RACES = {"brt": ("Bretonnia", "Bretonnian"), "emp": ("Empire", "Empire"),
         "dwf": ("Dwarfs", "Dwarf"), "skv": ("Skaven", "Skaven"),
         "chd": ("Chaos Dwarfs", "Chaos Dwarf"), "grn": ("Greenskins", "Greenskin"),
         "ksl": ("Kislev", "Kislev"), "cth": ("Cathay", "Cathayan"),
         "tze": ("Tzeentch", "Tzeentch"), "kho": ("Khorne", "Khorne"),
         "sla": ("Slaanesh", "Slaanesh"), "nur": ("Nurgle", "Nurgle"),
         "dae": ("Daemons of Chaos", "Daemon"), "chs": ("Warriors of Chaos", "Chaos"),
         "ogr": ("Ogre Kingdoms", "Ogre"), "vmp": ("Vampire Counts", "Vampire Counts"),
         "wef": ("Wood Elves", "Wood Elf"), "hef": ("High Elves", "High Elf"),
         "def": ("Dark Elves", "Dark Elf"), "lzd": ("Lizardmen", "Lizardmen"),
         "tmb": ("Tomb Kings", "Tomb Kings"), "cst": ("Vampire Coast", "Vampire Coast"),
         "bst": ("Beastmen", "Beastmen"), "nor": ("Norsca", "Norscan")}
SCRIPTED = {"attack_nearest": ("Attack nearest", "every unit walks to the nearest visible enemy"),
            "rush_nearest": ("Charge nearest", "every unit runs at the nearest visible enemy"),
            "hold": ("Hold position", "never gives an order"),
            "skills": ("Unit skills", "each unit follows its class's default skill"),
            "twwarhammer3.battle.calibration:CentralDefence": (
                "Central fallback", "scenario diagnostic: gather at one owned victory point"),
            "twwarhammer3.battle.calibration:CoordinatedRush": (
                "Synchronized rush", "scenario diagnostic: delay mobiles to meet the screen"),
            "twwarhammer3.battle.calibration:CasterSkirmish": (
                "Airborne casting", "scenario diagnostic: cast and return to stationary escorts"),
            "twwarhammer3.battle.calibration:FeintFlank": (
                "Feint and flank", "scenario diagnostic: opposite charges and withdrawal"),
            "twwarhammer3.battle.calibration:CrossKite": (
                "Crossfire kiting", "scenario diagnostic: separate horse archers and keep range"),
            "twwarhammer3.battle.calibration:Bodyguard": (
                "Gun bodyguard", "scenario diagnostic: shoot cavalry and intercept beside the gun"),
            "twwarhammer3.battle.calibration:Crossfire": (
                "Flanking fire", "scenario diagnostic: pin one unit and shoot into its flanks"),
            "twwarhammer3.battle.calibration:SpellWindow": (
                "Spell window", "scenario diagnostic: cast only where friends are clear"),
            "twwarhammer3.battle.calibration:HammerAnvil": (
                "Hammer and anvil", "scenario diagnostic: pin, rear-charge, pull out and repeat")}
# Unit fields and frame fields the page draws; the job directory keeps the rest.
UNIT_KEEP = ("id", "x", "z", "bearing", "men", "men0", "hp", "state", "target", "ammo", "ammo0")
MODE_KEEP = ("role", "capture_points", "supplies", "tickets", "tickets_goal", "custom")
TRACK_STEP_MS = 5000  # an army track keeps one centroid per this much battle time
STEP_MS = 5000  # the battle development series samples losses and counts orders this often
ORDER_KINDS = ("move", "attack", "ability", "build", "reinforce")  # the rest count as "other"
# The game's custom battle modes in page order (land battles first, then the objective modes,
# sieges and settlements before survival and the points modes, the rarer layouts last), each
# with its section title and its name for one battle. Sieges split by the player's role, as
# their objectives differ. A mode without scenarios yet keeps its place on the page.
MODES = [("land", "Land battles", "land battle"),
         ("siege_defence", "Siege defence", "siege defence"),
         ("siege_attack", "Siege attack", "siege attack"),
         ("settlement", "Minor settlement battles", "minor settlement battle"),
         ("survival", "Survival battles", "survival battle"),
         ("conquest", "Conquest", "conquest battle"),
         ("domination", "Domination", "domination battle"),
         ("ambush", "Ambush battles", "ambush battle"),
         ("chokepoint", "Chokepoint battles", "chokepoint battle"),
         ("subterranean", "Subterranean battles", "subterranean battle"),
         ("free_for_all", "Free-for-all battles", "free-for-all battle")]
LOBBY_MODES = {"classic": "land", "unfortified_settlement": "settlement",
               "river_crossing_battle": "chokepoint", "underground_intercept": "subterranean"}


def mode_of(scenario: dict) -> str:
    """A scenario's game mode: its lobby battle type (classic by default), a siege by role."""
    kind = scenario.get("battle_type") or "classic"
    if kind == "siege":
        return "siege_attack" if scenario.get("attacker") == "player" else "siege_defence"
    return LOBBY_MODES.get(kind, kind)


def scenario_name(definition: dict) -> str | None:
    return (definition.get("scenario") or {}).get("name") or definition.get("scenario_name")


def armies(scenario: dict) -> dict:
    """The declared starting armies in a few words, by race: "9 Chaos Dwarf units defending
    against 16 Greenskin units"."""
    def army(side):
        if not side:
            return None
        if isinstance(side, list):
            return " and ".join(filter(None, map(army, side)))
        key = side.get("faction") or side.get("subculture") or ""
        code = re.match(r"wh\d?_(?:main|dlc\d+|pro\d+)_(?:sc_)?([a-z]{3})_", key)
        name = (RACES[code[1]][1] if code and code[1] in RACES else
                replay.title(re.sub(r"^wh\d?_(?:main|dlc\d+|pro\d+)_(?:sc_)?[a-z]+_", "", key))
                or "Unknown")
        count = len(side["units"]) if isinstance(side.get("units"), list) else None
        return f"{count} {name} unit{'s' * (count != 1)}" if count is not None else f"{name} army"

    friendly, enemy = army(scenario.get("player")), army(scenario.get("enemy"))
    if enemy is None and scenario.get("battle_type") == "survival":
        enemy = "endless waves"
    attacker = scenario.get("attacker")
    defends = (scenario.get("expect") or {}).get("player_defends")
    if defends is None and scenario.get("battle_type") == "survival":
        defends = True  # the waves come to the player
    verb = ("defending against" if attacker == "enemy" or (attacker is None and defends)
            else "attacking" if attacker == "player" or defends is False else "against")
    return {"friendly": friendly, "enemy": enemy,
            "line": f"{friendly} {verb} {enemy}" if friendly and enemy else friendly or enemy}


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
                if key not in ("brief", "status", "family")}
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
    provider = card.get("provider") or definition.get("provider", "openai")
    gateway = "via OpenRouter" if provider == "openrouter" else None
    extra = f"+{trial['delay_ms'] / 1000:g} s added observation age" if trial.get(
        "delay_ms") else None

    def detail(*parts):
        return ", ".join(filter(None, [*parts, extra]))

    # `short` tells rows of one name apart in tight spaces: effort, prompt variant (none for
    # rules only) and added age.
    if base in MODEL_POLICIES or card.get("kind") in ("model", "hybrid", "demo"):
        name = model or definition.get("model") or base
        display = {"z-ai/glm-5.3": "GLM-5.3", "moonshotai/kimi-k3": "Kimi K3",
                   "stepfun/step-5-preview": "Step 5 Preview"}.get(name, name)
        return {"kind": "model", "family": name, "name": display,
                "detail": detail(effort and f"{effort} reasoning", PROMPTS.get(base), gateway),
                "short": detail(effort and f"{effort} reasoning", VARIANTS.get(base), gateway),
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
                            ("kind", "model", "effort", "provider", "routing",
                             "source_sha256", "timing")})
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
        # Enemy soldiers still fighting at the end; battles that recorded casualties only
        # count the living ("killed" basis), so their progress counts the dead alone.
        standing = enemy.get("active")
        basis = None
        if standing is None and enemy.get("remaining") is not None:
            standing, basis = enemy["remaining"], "killed"
        battles[key] = {
            "commander": commander(trial, definition),
            "harness": harness(definition, jobs.get(trial["instance"])),
            "date": (jobs.get(trial["instance"]) or {}).get("created_at"),
            # Progress: the share of the enemy's registered soldiers dead or no longer
            # fighting (fleeing, shattered, leaving or undeployed) when the battle ended.
            "progress": None if None in (standing, enemy.get("registered")) else
            _share(enemy["registered"] - standing, enemy["registered"]),
            "progress_basis": basis,
            "own_left": _share(own.get("remaining"), own.get("registered")),
        }
        scenario = definition.get("scenario") or {}
        measures = trial.get("measures") or {}
        custom = measures.get("custom_objective")
        if scenario.get("custom"):
            battles[key].update(
                progress=_share((custom or {}).get("extracted"),
                                len((custom or {}).get("assets") or [])),
                progress_basis="evacuation",
                objective_outcome=(custom or {}).get("status", "unavailable"))
        elif mode_of(scenario) in {"conquest", "domination"}:
            resources = measures.get("resources") or {}
            battles[key].update(progress=_share((resources.get("tickets") or {}).get("us"),
                                                resources.get("tickets_goal")),
                                progress_basis="tickets")
        # A siege defence scores like a land battle: holding every point scored 92-99 in
        # lost battles too, so ownership time stays a measure, not the score.
        elif mode_of(scenario) in {"siege_attack", "settlement"}:
            points = (measures.get("objective_time") or {}).get("points") or []
            held = sum(p["held_s"] for p in points)
            observed = sum(p["observed_s"] for p in points)
            battles[key].update(progress=_share(held, observed), progress_basis="objective_time")
        elif mode_of(scenario) == "survival":
            # Endless waves have no finite enemy denominator or known completion target.
            battles[key].update(progress=None, progress_basis="duration")
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
    # The core scenarios, when the report has any; else every scenario (an ad hoc report).
    core = {name for name in by_name if (scenario_notes.get(name) or {}).get("core_candidate")}
    scenarios = []
    for name, every in by_name.items():
        # Completed battles only. Diagnostic probes test tooling, not commanding.
        keys = [key for key in every if trials[key]["valid"]
                and battles[key]["commander"]["kind"] != "diagnostic"]
        if not keys or (core and name not in core):
            continue
        definition = group_of(keys[0])["definition"]
        scenario = definition.get("scenario") or {}
        note = scenario_notes.get(name) or {}
        selected = [key for key in keys if (runs.get(
            f"{trials[key]['instance']}/{trials[key]['episode']}") or {}).get("selected") is True]
        models = [key for key in keys if battles[key]["commander"]["kind"] == "model"]
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
            "heading": note.get("heading"),
            "family": note.get("family") or scenario.get("family"),
            "short": note.get("short") or _title(note, {**scenario, "name": name}),
            "noun": note.get("noun"),
            "core_candidate": note.get("core_candidate", False),
            "challenge": note.get("challenge") or scenario.get("brief"),
            "footnote": note.get("footnote"),
            "mode": mode_of(scenario),
            "split": scenario.get("split"), "status": scenario.get("status"),
            "difficulty": (scenario.get("expect") or {}).get("difficulty"),
            "battle_type": scenario.get("battle_type") or "unrecorded",
            "armies": armies(scenario), "battles": keys,
            "rows": sorted(rows.values(), key=lambda item: (
                order[item["kind"]], item["name"],  # numbers in natural order: +6 s before +10 s
                [int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", item["detail"])])),
            "controlled": controlled(keys),
            "featured": min(pool, key=chronology), "featured_reason": reason})
    # By game mode, then in the notes' order; scenarios without notes after them, by name.
    modes = [key for key, _, _ in MODES]
    listed = list(scenario_notes)
    scenarios.sort(key=lambda entry: (
        modes.index(entry["mode"]) if entry["mode"] in modes else len(modes),
        listed.index(entry["name"]) if entry["name"] in listed else len(listed),
        str(entry["name"])))

    # What the page leaves out: every other battle, and the launches that stopped before one.
    shown = {key for entry in scenarios for key in entry["battles"]}
    started = {trial["instance"] for trial in trials.values()}
    omitted = {"battles": sorted((key for key in trials if key not in shown), key=chronology),
               "setup_only": [index for index, job in enumerate(data.get("jobs", []))
                              if job["instance"] not in started]}
    return {"schema": 3, "evidence_kind": kind, "report": data, "battles": battles,
            "scenarios": scenarios, "omitted": omitted,
            "modes": [{"key": key, "title": title, "name": name} for key, title, name in MODES]}


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
    """How old each batch of new orders' battlefield view was when the game took it, and the
    age of each commander plan's view when the plan was adopted (its executor's other ticks
    act on fresh views but follow that older plan)."""
    applied = [d for d in payload["decisions"] if d.get("applied_ms") is not None]
    plans = [d for d in applied if d.get("plan_age_s") is not None]
    batches = [d for d in payload["decisions"] if d["orders"] and d.get("age_s") is not None]
    return {"ages": [_round(d["age_s"]) for d in batches],
            "plans": [_round(d["plan_age_s"]) for d in plans]}


def route(payload: dict) -> dict:
    """Where the friendly army went, as the centroid of its units still fighting at the start
    of every 5 s of battle time, and where each enemy unit was first seen."""
    def placed(u):
        return isinstance(u.get("x"), (int, float)) and isinstance(u.get("z"), (int, float))

    track, first_seen, due = [], {}, 0
    for frame in payload["frames"]:
        for u in frame["enemy"]:
            if placed(u):
                first_seen.setdefault(u["id"], [round(u["x"]), round(u["z"])])
        up = [u for u in frame["friendly"] if placed(u) and u.get("men") != 0
              and not {"routing", "shattered"} & set(u.get("state") or [])]
        if frame["time_ms"] >= due and up:
            step = frame["time_ms"] // TRACK_STEP_MS
            track.append([step * TRACK_STEP_MS // 1000, round(sum(u["x"] for u in up) / len(up)),
                          round(sum(u["z"] for u in up) / len(up))])
            due = (step + 1) * TRACK_STEP_MS
    return {"track": track, "enemy": [{"at": point} for point in first_seen.values()]}


def development(payload: dict) -> dict:
    """How the battle went, every 5 s of battle time and at its end, from the recorded frames
    alone: the soldiers each side had lost (friendly units in full; enemy units as last seen,
    a seen unit the enemy roster marks dead losing all its soldiers; unseen ones not counted),
    and the commander's orders the game accepted in each 5 s, by kind."""
    frames = payload["frames"]
    end = frames[-1]["time_ms"]
    times = [*range(0, end, STEP_MS), end]
    units, lost, index = {}, {"own": [], "enemy": []}, 0
    for t in times:
        while index < len(frames) and frames[index]["time_ms"] <= t:
            frame = frames[index]
            for side in ("friendly", "enemy"):
                for u in frame[side]:
                    if isinstance(u.get("men"), int) and isinstance(u.get("men0"), int):
                        units[u["id"]] = [side, u["men0"], u["men"]]
            for u in frame.get("enemy_roster") or []:
                if u.get("dead") is True and u.get("id") in units:
                    units[u["id"]][2] = 0
            index += 1
        for name, side in (("own", "friendly"), ("enemy", "enemy")):
            lost[name].append(sum(max(0, men0 - men) for owner, men0, men in units.values()
                                  if owner == side))
    orders = {}
    for decision in payload["decisions"]:
        if decision.get("applied_ms") is None:
            continue
        step = min(len(times) - 1, int(decision["applied_ms"] // STEP_MS))
        for item, accepted in zip(decision["orders"], decision["steps"]):
            if accepted["status"] in replay.ACCEPTED:
                kind = item["order"].get("type")
                kind = kind if kind in ORDER_KINDS else "other"
                orders.setdefault(kind, [0] * len(times))[step] += 1
    return {"step_s": STEP_MS // 1000, "end_s": round(end / 1000, 1), **lost, "orders": orders}


def start(payload: dict) -> dict:
    """Where the armies began, for the scenario index: the units of the first frame that places
    friendly units (enemy units only as far as visible then)."""
    first = next((frame for frame in payload["frames"] if frame["friendly"]),
                 {"friendly": [], "enemy": []})
    return {side: [[round(u["x"]), round(u["z"])] for u in first[side]
                   if isinstance(u.get("x"), (int, float)) and isinstance(u.get("z"), (int, float))]
            for side in ("friendly", "enemy")}


def render(report: dict, notes: dict | None = None) -> str:
    data = display_data(report, notes)
    runs = (notes or {}).get("runs") or {}
    trials, chronology = _chronology(data["report"])
    shown = {key for scenario in data["scenarios"] for key in scenario["battles"]}
    payloads, prompts, directories = {}, {}, {}
    for group_index, group in enumerate(report["groups"]):
        for trial_index, trial in enumerate(group["trials"]):
            key = f"g{group_index}-t{trial_index}"
            if key not in shown:  # its replay would never open
                continue
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
                                                route=route(payloads[key]),
                                                development=development(payloads[key]))

    # One map outline per scenario for the index and the route maps: the featured battle's,
    # else any; the armies' starting positions from the featured battle.
    for scenario in data["scenarios"]:
        terrains = [payloads[key].get("terrain") for key in [scenario["featured"],
                                                             *scenario["battles"]]
                    if key in payloads]
        scenario["terrain"] = next(filter(None, terrains), None)
        featured = payloads.get(scenario["featured"])
        scenario["start"] = start(featured) if featured and featured["frames"] else None
    # Stills: each featured battle, and the earliest battle of each commander in each scenario.
    pictured = {scenario["featured"] for scenario in data["scenarios"]}
    for scenario in data["scenarios"]:
        for row in scenario["rows"]:
            pictured.add(min(row["battles"], key=chronology))
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
