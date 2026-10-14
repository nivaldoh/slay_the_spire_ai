"""Collect the fixed, bounded development inventory in docs/spire/first-combat/research.md.

No resume or implicit replacement seeds. All game work uses ordinary one-episode
rollouts; policies never receive inventory metadata. See docs/spire/first-combat/inventory.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from gameai.provenance import REPO_ROOT as ROOT
from gameai.provenance import committed_revision, source_fingerprints, write_json
from spire.combat.evidence import audit_run, compare_resets
from spire.combat.rollout import rollout
from spire.protocol import OBSERVATION_CONTRACT

SEEDS = tuple(f"SPIREINV{number:02d}" for number in range(1, 13))
FAMILIES = ("cultist", "jaw_worm", "two_louses")
START_SHA256 = "177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4"
PROTOCOL = {
    "engine": "original", "scope": "first_combat",
    "observation_version": OBSERVATION_CONTRACT,
    "prefix_version": "neow-maxhp-or-gold-leftmost-settled-v2",
    "reset": "owned_jvm_restart_then_seeded_start",
}
CONTRACT = {
    "version": "starter-inventory-v1", "purpose": "development", "seeds": list(SEEDS),
    "max_attempts": 24, "time_budget_seconds": 1800,
    "max_actions": 500, "episode_timeout": 180, "bridge_timeout": 45,
    "policy_seed": 1000, "sentinel_seed": "SPIREAI1",
    "sentinel_start_sha256": START_SHA256, "protocol": PROTOCOL,
    "selection": "first_two_preliminarily_eligible_per_family_no_backfill",
    "family_order": list(FAMILIES), "discovery_policy": "heuristic",
    "probe_policy": "end_turn", "infrastructure_retries": 1,
}


class InventoryDeadline(BaseException):
    """Unwind the ordinary game owner without classifying the deadline as a loss."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def files(directory: Path) -> dict:
    return {str(path.relative_to(directory)): digest(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}


def source() -> dict:
    if Path.cwd().resolve() != ROOT:
        raise ValueError(f"Run the inventory from its checkout: {ROOT}")
    return {
        "source_revision": committed_revision("inventory collection"),
        "source_files": source_fingerprints(),
        "driver_sha256": digest(Path(__file__)),
        "research_sha256": digest(ROOT / "docs/spire/first-combat/research.md"),
    }


def engine_pins(directory: Path) -> dict:
    environment = read(directory / "environment.json")
    return {"game": environment["game"]["sha256"],
            "mods": {key: value["sha256"] for key, value in environment["mods"].items()}}


def start_context(directory: Path) -> dict:
    """Read only public room classification from the first policy decision's raw source."""
    raw = {}
    for line in (directory / "episode-0000/trace.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["kind"] == "observation":
            raw = event["raw"].get("game_state", {})
        if event["kind"] == "decision":
            return {key: raw.get(key) for key in ("floor", "room_phase", "room_type")}
    return {}


def eligibility(episode: dict, context: dict) -> dict:
    """Classify only audited public conditions; HP at the ending never selects a seed."""
    reasons = []
    if not episode.get("valid") or episode.get("status") not in {"won", "lost"}:
        return {"eligible": False, "reasons": ["No audited complete combat"], "family": None}
    public = episode["transitions"][0]["observation"]
    monsters = public["combat_state"]["monsters"]
    ids = [monster["id"] for monster in monsters]
    family = ("cultist" if ids == ["Cultist"] else "jaw_worm" if ids == ["JawWorm"]
              else "two_louses" if len(ids) == 2 and all(
                  name in {"FuzzyLouseNormal", "FuzzyLouseDefensive"} for name in ids
              ) else None)
    if family is None:
        reasons.append("Unsupported encounter composition")
    if context != {"floor": 1, "room_phase": "COMBAT", "room_type": "MonsterRoom"}:
        reasons.append("Not an ordinary first-floor MonsterRoom")
    for name, value in {"class": "IRONCLAD", "ascension_level": 0, "current_hp": 80,
                        "max_hp": 80, "gold": 199, "contract": OBSERVATION_CONTRACT}.items():
        if public.get(name) != value:
            reasons.append(f"Starting {name} differs")
    deck = public.get("deck", [])
    if (Counter(card.get("id") for card in deck)
            != Counter({"Strike_R": 5, "Defend_R": 4, "Bash": 1})
            or any(card.get("upgrades") != 0 for card in deck)):
        reasons.append("Not the unupgraded starter deck")
    if [relic.get("id") for relic in public.get("relics", [])] != ["Burning Blood"]:
        reasons.append("Relics differ from Burning Blood alone")
    potions = public.get("potions", [])
    if len(potions) != 3 or any(potion.get("id") != "Potion Slot" for potion in potions):
        reasons.append("Potion slots are not empty")
    known = {"ATTACK", "ATTACK_BUFF", "ATTACK_DEBUFF", "ATTACK_DEFEND", "BUFF",
             "DEBUFF", "STRONG_DEBUFF", "DEFEND", "DEFEND_DEBUFF", "DEFEND_BUFF", "SLEEP"}
    if not episode.get("initial_intents_settled") or any(
        monster.get("intent") not in known for monster in monsters
    ):
        reasons.append("Initial intents are not settled and known")
    neow = [item for item in episode["prefix"] if item.get("event_id") == "Neow Event"]
    if not any(item.get("choice", "").lower() == "obtain 100 gold" for item in neow):
        reasons.append("Prefix did not choose 100 gold")
    if any("max hp" in (item.get("choice_text") or "").lower() for item in neow):
        reasons.append("Prefix chose a max-HP variant")
    maps = [item for item in episode["prefix"] if item.get("screen_type") == "MAP"]
    if len(maps) != 1 or maps[0]["command"].upper() != "CHOOSE 0":
        reasons.append("Prefix did not take the leftmost first node")
    return {"eligible": not reasons, "reasons": reasons, "family": family, "monster_ids": ids}


def equivalent(left: dict, right: dict) -> bool:
    if any(not item.get("valid") or item.get("status") not in {"won", "lost"}
           for item in (left, right)):
        return False
    comparison = compare_resets([left, right])["comparisons"][0]
    return (comparison["initial_state_equal"] and comparison["prefix_equal"]
            and comparison["shared_action_states_equal"]
            and comparison["shared_combat_actions"] == len(left["transitions"])
            == len(right["transitions"]))


def load_reference(directory: Path) -> tuple[dict, dict]:
    audited = audit_run(directory)
    if not audited["valid"] or not audited["episodes"]:
        raise ValueError(f"Invalid sentinel reference: {audited['issues']}")
    episode, manifest = audited["episodes"][0], audited["manifest"]
    config = manifest["config"]
    if (episode["episode"] != 0 or config["policy"] != "heuristic"
            or config["game_seed"] != "SPIREAI1" or config["expected_start_sha256"] != START_SHA256
            or episode["combat_start_sha256"] != START_SHA256
            or any(config[key] != CONTRACT[key] for key in
                   ("policy_seed", "max_actions", "episode_timeout", "bridge_timeout"))
            or any(manifest.get(key) != value for key, value in PROTOCOL.items())
            or not eligibility(episode, start_context(directory))["eligible"]):
        raise ValueError("Reference is not the canonical v1 heuristic episode zero")
    pins = engine_pins(directory)
    evidence = {name: digest(directory / name) for name in (
        "manifest.json", "environment.json", "episode-0000/trace.jsonl",
        "episode-0000/combat_start.json", "episode-0000/result.json", "episode-0000/profile.json",
    )}
    reference = {
        "directory": str(directory.resolve()), "episode": 0, "files": evidence,
        "engine_pins": pins, "source_revision": manifest["source_revision"],
        "policy_source_sha256": manifest["source_files"]["src/spire/policies.py"],
        "public_episode": episode,
    }
    return reference, episode


@contextmanager
def bounded_collection(seconds: float):
    if seconds <= 0:
        raise InventoryDeadline()
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise RuntimeError("Inventory requires an unused process alarm")
    previous = signal.getsignal(signal.SIGALRM)

    def expire(*_):
        raise InventoryDeadline()

    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def assignments() -> list[dict]:
    result = [{"id": "sentinel-before", "stage": "sentinel", "game_seed": "SPIREAI1"}]
    result += [{"id": f"discovery-{seed}", "stage": "discovery", "game_seed": seed}
               for seed in SEEDS]
    result += [{"id": f"repeat-{family}-{slot}", "stage": "repeat", "family": family,
                "slot": slot, "game_seed": None} for family in FAMILIES for slot in (0, 1)]
    result += [{"id": f"probe-{family}", "stage": "probe", "family": family, "game_seed": None}
               for family in FAMILIES]
    result += [{"id": "sentinel-after", "stage": "sentinel", "game_seed": "SPIREAI1"}]
    return [{**item, "status": "unattempted", "attempts": []} for item in result]


def inspect_attempt(directory: Path, config: dict, frozen: dict, pins: dict,
                    context: dict) -> tuple[dict, dict]:
    audit = audit_run(directory)
    details = {"audit_valid": audit["valid"], "issues": list(audit["issues"])}
    manifest = audit["manifest"]
    try:
        if (manifest["config"] != config or any(manifest.get(k) != v for k, v in PROTOCOL.items())
                or manifest["source_revision"] != frozen["source_revision"]
                or manifest["source_files"] != frozen["source_files"]
                or manifest.get("purpose") != "development"
                or manifest.get("inventory_assignment") != context
                or engine_pins(directory) != pins):
            raise ValueError("Child protocol/source/configuration/engine provenance differs")
        if len(audit["episodes"]) != 1:
            raise ValueError("Child does not contain exactly one episode")
        if not (directory / "episode-0000/profile.json").is_file():
            raise ValueError("Missing per-attempt profile snapshot")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        details.update(status="provenance_failure", issues=[*details["issues"], str(exc)])
        return details, {}
    episode = audit["episodes"][0]
    details["status"] = episode["status"] if audit["valid"] else "invalid_evidence"
    details["reported_error"] = episode.get("result", {}).get("error")
    if audit["valid"] and episode.get("combat_start_sha256"):
        if config.get("expected_start_sha256") and (
            episode["combat_start_sha256"] != config["expected_start_sha256"]
        ):
            details.update(status="wrong_start", issues=["Actual start differs from pinned start"])
        if episode["status"] in {"won", "lost"}:
            details["eligibility"] = eligibility(episode, start_context(directory))
        details["combat_start_sha256"] = episode["combat_start_sha256"]
        details["prefix"] = episode["prefix"]
    return details, episode


def inventory(output: Path, reference_run: Path) -> dict:
    """Freeze and execute the accepted schedule once. Existing output is never reused."""
    output = Path(output).resolve()
    frozen = source()
    reference, reference_episode = load_reference(Path(reference_run).resolve())
    if frozen["source_files"]["src/spire/policies.py"] != reference["policy_source_sha256"]:
        raise ValueError("Current heuristic differs from the sentinel reference")
    output.mkdir(parents=True, exist_ok=False)
    (output / "runs").mkdir()
    write_json(output / "contract.json", CONTRACT)
    write_json(output / "reference.json", reference)
    started, monotonic_start = time.time(), time.monotonic()
    deadline = monotonic_start + CONTRACT["time_budget_seconds"]
    state = {
        "schema_version": 1, "status": "running", "stop_reason": None, **frozen,
        "started_unix": started, "deadline_unix": started + CONTRACT["time_budget_seconds"],
        "contract_sha256": digest(output / "contract.json"),
        "reference_sha256": digest(output / "reference.json"),
        "engine_pins": reference["engine_pins"], "assignments": assignments(), "attempts": [],
        "infrastructure_failures": 0, "retry_used": False, "selected": [], "admissions": [],
    }
    episodes, candidates = {}, {family: [] for family in FAMILIES}

    def save():
        write_json(output / "inventory.json", state)

    def remaining():
        return min(deadline - time.monotonic(), state["deadline_unix"] - time.time())

    def unchanged():
        if (source() != frozen or digest(output / "contract.json") != state["contract_sha256"]
                or digest(output / "reference.json") != state["reference_sha256"]):
            raise ValueError("Frozen inventory source/contract/reference changed")
        for attempt in state["attempts"]:
            if files(output / attempt["directory"]) != attempt["files"]:
                raise ValueError("Earlier inventory evidence changed")

    def stop(reason):
        state.update(status="stopped", stop_reason=reason)

    save()  # Immutable inputs, complete conditional schedule and deadline precede all collection.
    try:
        for item in state["assignments"]:
            if item["stage"] == "repeat":
                if not state["selected"]:
                    state["selected"] = [candidate["id"] for family in FAMILIES
                                         for candidate in candidates[family][:2]]
                choices = candidates[item["family"]][:2]
                if item["slot"] >= len(choices):
                    item.update(status="not_scheduled", reason="No selected candidate for slot")
                    continue
                discovery = choices[item["slot"]]
                item.update(game_seed=discovery["game_seed"], discovery_id=discovery["id"])
            elif item["stage"] == "probe":
                choices = [a for a in state["admissions"]
                           if a["encounter_family"] == item["family"]]
                if not choices:
                    item.update(status="not_scheduled", reason="No admitted scenario in family")
                    continue
                item.update(game_seed=choices[0]["game_seed"],
                            discovery_id=choices[0]["discovery_id"])
            save()
            retry_of = None
            while True:
                if remaining() <= 0:
                    stop("deadline")
                    break
                if len(state["attempts"]) >= CONTRACT["max_attempts"]:
                    stop("attempt_limit")
                    break
                unchanged()
                expected = START_SHA256 if item["stage"] == "sentinel" else (
                    episodes[item["discovery_id"]]["combat_start_sha256"]
                    if "discovery_id" in item else None
                )
                available = remaining()
                if available <= 0:
                    stop("deadline")
                    break
                config = {"policy": "end_turn" if item["stage"] == "probe" else "heuristic",
                          "game_seed": item["game_seed"], "policy_seed": CONTRACT["policy_seed"],
                          "episodes": 1, "max_actions": CONTRACT["max_actions"],
                          "episode_timeout": min(CONTRACT["episode_timeout"], available),
                          "bridge_timeout": min(CONTRACT["bridge_timeout"], available),
                          "expected_start_sha256": expected}
                index = len(state["attempts"])
                record = {"index": index, "assignment_id": item["id"], "retry_of": retry_of,
                          "directory": f"runs/attempt-{index:04d}", "config": config,
                          "status": "reserved", "started_unix": time.time(), "files": {}}
                context = {"contract_sha256": state["contract_sha256"],
                           "reference_sha256": state["reference_sha256"],
                           "assignment_id": item["id"], "attempt_index": index,
                           "retry_of": retry_of}
                state["attempts"].append(record)
                item["attempts"].append(index)
                item["status"] = "running"
                save()  # Reservation is durable before rollout can create files or a JVM.
                child = output / record["directory"]
                try:
                    with bounded_collection(remaining()):
                        rollout(child, config)
                except InventoryDeadline:
                    record.update(status="deadline", error="Absolute inventory deadline")
                    stop("deadline")
                except KeyboardInterrupt:
                    record.update(status="interrupted", error="Collection interrupted")
                    raise
                except Exception as exc:
                    record.update(status="collector_error", error=f"{type(exc).__name__}: {exc}")
                    stop("collector_error")
                finally:
                    record["finished_unix"] = time.time()
                    record["collector_overrun_seconds"] = max(0.0, -remaining())
                    manifest_path = child / "manifest.json"
                    if manifest_path.exists():
                        manifest = read(manifest_path)
                        manifest.update(purpose="development", inventory_assignment=context)
                        write_json(manifest_path, manifest)
                    record["files"] = files(child)
                    save()
                if remaining() <= 0:
                    stop("deadline")
                details, episode = inspect_attempt(
                    child, config, frozen, reference["engine_pins"], context
                )
                record["audit"] = details
                if record["status"] == "reserved":
                    record["status"] = details["status"]
                unchanged()
                if state["status"] != "running":
                    item.update(status="rejected", reason=state["stop_reason"])
                    break
                if record["status"] == "provenance_failure":
                    stop("provenance_failure")
                    item.update(status="rejected", reason="provenance_failure")
                    break
                if record["status"] == "infrastructure_failure":
                    state["infrastructure_failures"] += 1
                    if state["retry_used"]:
                        stop("second_infrastructure_failure")
                        item.update(status="rejected", reason="second_infrastructure_failure")
                        break
                    state["retry_used"] = True
                    retry_of = index
                    save()
                    continue
                complete = record["status"] in {"won", "lost"}
                eligible = complete and details["eligibility"]["eligible"]
                if item["stage"] == "sentinel":
                    accepted = eligible and equivalent(reference_episode, episode)
                    item.update(status="verified" if accepted else "rejected")
                    if not accepted:
                        stop("sentinel_mismatch")
                elif item["stage"] == "discovery":
                    item.update(status="eligible" if eligible else "rejected")
                    if eligible:
                        episodes[item["id"]] = episode
                        candidates[details["eligibility"]["family"]].append(item)
                elif item["stage"] == "repeat":
                    accepted = eligible and equivalent(episodes[item["discovery_id"]], episode)
                    item.update(status="admitted" if accepted else "rejected")
                    if accepted:
                        discovery = next(a for a in state["assignments"]
                                         if a["id"] == item["discovery_id"])
                        original = state["attempts"][discovery["attempts"][-1]]
                        state["admissions"].append({
                            "id": item["game_seed"].lower(), "game_seed": item["game_seed"],
                            "expected_start_sha256": expected, "encounter_family": item["family"],
                            "monster_ids": details["eligibility"]["monster_ids"],
                            "discovery_id": item["discovery_id"],
                            "discovery_trace_sha256": original["files"]["episode-0000/trace.jsonl"],
                            "discovery_directory": original["directory"],
                            "repeat_directory": record["directory"],
                        })
                else:
                    item.update(status="verified" if eligible else "rejected")
                    if not eligible:
                        state["admissions"] = [a for a in state["admissions"]
                                               if a["discovery_id"] != item["discovery_id"]]
                if item["status"] == "rejected":
                    item["reason"] = (details.get("eligibility", {}).get("reasons")
                                      or ([details["reported_error"]]
                                          if details.get("reported_error") else [])
                                      or details["issues"]
                                      or ["Incomplete or unequal public replay"])
                break
            save()
            if state["status"] != "running":
                break
        else:
            if remaining() <= 0:
                stop("deadline")
            else:
                state.update(status="completed", stop_reason="schedule_complete")
    except BaseException as exc:
        state.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "stopped",
                     stop_reason=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        for item in state["assignments"]:
            if item["status"] == "running":
                item.update(status="incomplete", reason=state["stop_reason"])
        state["elapsed_seconds"] = time.monotonic() - monotonic_start
        state["post_deadline_seconds"] = max(0.0, -remaining())
        state["admissions_valid"] = state["status"] == "completed"
        state["unattempted"] = [a["id"] for a in state["assignments"]
                                if a["status"] == "unattempted"]
        save()
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path,
                        default=ROOT / "runs/baseline-heuristic-settled-20261011")
    args = parser.parse_args()
    result = inventory(args.output, args.reference)
    print(json.dumps({key: result[key] for key in
                      ("status", "stop_reason", "admissions_valid", "admissions", "unattempted")},
                     sort_keys=True))
    return 0 if result["admissions_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
