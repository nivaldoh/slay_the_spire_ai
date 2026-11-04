"""Offline comparison of what the clients of one native match attempt observed (plan step 4,
docs/twwarhammer3/native-multiplayer.md, and its Verification matrix's comparator row).

Input: an attempt directory the coordinator wrote (engine/link.py). The manifest, the first
line of ``match.jsonl``, names the clients; ``events-<client>.jsonl`` holds that worker's
events, and an event of kind ``observation`` carries one battle observation as
``{"written_ns", "observation"}`` (engine/worker.py, ``Worker.watch``). Its evaluator-only
``native`` section (engine/mailbox.py) lists every unit with ``alliance``, ``army``,
``index``, ``ui_id``, ``type`` and raw ``x`` and ``z``. A client without an events file has
no observations. An identical observation sent twice counts once. One client can
have two different observations at one ``time_ms``: the battle Lua's finish() publishes the
terminal one at the battle time its tick() just published (twwarhammer3_battle.lua); such a
time is repeated and is not compared.

For each pair of clients (A, B in manifest order), at each ``time_ms`` where both have an
observation, units are joined by (alliance, army, index): never by ``type``, which
same-type units share, and never by ``ui_id``, which is not proved equal across peers.
``dx`` is B's ``x`` minus A's (``dz`` likewise), unrounded; a unit is exact only when ``x``,
``z``, ``type`` and ``ui_id`` are all exactly equal. ``owner`` and ``id`` depend on the
client's own side by design and are not compared. A time where either client's ``native``
lists failed reads (``errors``, a failed enumeration) is listed and not compared, so a read
failure is never reported as a unit the other client lacks. The plan's rules followed:
"Same-tick comparison uses completed ticks, not nearest wall-clock samples" and "Do not
invent a floating-point epsilon to hide a failed comparison": a time only one client has is
listed as unavailable for the pair, never interpolated or matched to the nearest sample, and
there is no tolerance. The battle Lua writes numbers with ``%.14g`` (twwarhammer3_json.lua), so
positions that differ only beyond 14 significant digits (one ulp, say) arrive here equal. No
outside repository was followed.

This is weaker than that rule: ``time_ms`` is the battle time each client's Lua read when it
made an observation, not a completed engine tick. Two clients' observations at one
``time_ms`` may come from different ticks. In the multiplayer modes regular observations
follow a fixed battle-time grid that acknowledgements do not move (since 2026-11-03; on
11-03 the clients' times parted at each client's first order), so common times need both
clients' ticks to fall at the same battle times (unverified). A passive
completed-tick collector is a later, separately reviewed step (plan step 4).

Refusal (ValueError): a client's events holding more than one battle id (each client's Lua
makes its own id, so ids never match across clients; one battle per attempt), or an events
line that is not JSON or lacks what the comparison reads (``unreadable``), named by line.

Summary: ``match``, ``attempt``; ``clients``: per client ``battle``, ``observations``
(distinct ones), ``repeated_times``, ``without_native`` (counted, not compared; the seq-0
``Loading`` placeholder is one), ``native_errors`` (observations whose ``native`` lists
failed top-level reads) and ``failed_rows`` (unit rows with ``error``); ``pairs``: per pair
``clients``, ``common_times``, ``compared_times`` (common times where both have one
observation with ``native`` and neither lists ``errors``), ``only`` (client -> times only that
client has), ``repeated`` (client -> common times that are repeated for that client),
``native_error_times`` (client -> common times not compared because that client's
``native`` lists ``errors``), ``units_compared``, ``exact``, ``position_differences``,
``type_mismatches``, ``ui_id_mismatches``, ``missing`` (client -> units absent from that
client's observation at a compared time while the other lists them, a failed row excepted:
a reinforcement row that failed before its alliance was read has none, and as ``r<k>``
numbers reinforcement armies across alliances, its army and index still name the unit),
``failed_rows`` (client -> error rows at compared times), ``max_dx`` and ``max_dz``
(``{"value", "time_ms", "unit"}``, or null when every value is equal),
``first_difference_ms`` (the first compared time with a unit that is missing or not exact)
and ``differences`` (every compared unit that is not exact:
``{"time_ms", "unit": [alliance, army, index], "dx", "dz", "type"?: [A, B], "ui_id"?: [A,
B]}``).

Completed-tick mode (``compare_captures``, schema ``native-v1``): compares each client's
``native.jsonl`` from engine/multiplayer_probe.py, not Lua observations, so it is the plan's
"same tick" rule (docs/twwarhammer3/multiplayer-control-foundation.md, stage 2). Checksums are
compared at every tick of the interval and raw unit rows at every scheduled tick, with no
tolerance and without nearest-tick matching. The interval defaults to everything any client
recorded, so a late start or a stall counts as missing; a declared interval can narrow it.
The verdict is ``conflict`` when a checksum, a raw value, a decided ending, a named packet count
or a client's own repeated records differ; ``inconclusive`` when evidence is missing, only some
clients saw an ending, simulated phases differ (their comparability is not calibrated), a
capture failed, did not stop cleanly, or no tick or no unit row was compared; ``agreed``
otherwise. Tick origins, unit order
and field comparability have no two-client calibration yet, so ``agreed`` covers only the
evidence compared. It is not a synchronization proof.
"""

import collections
import itertools
import json
from pathlib import Path


def unit_key(row: dict) -> tuple:
    # JUDGEMENT: unit join key — orchestrator's card, 2026-10-30: (alliance, army, index) on every
    # peer. If peers number alliances, armies or units from their own side, a calibrated mapping
    # (army_unique_id, a proved ui_id) changes every count here; all agreement counts rest on it.
    return row.get("alliance"), row["army"], row["index"]


# What the comparison reads of a unit row; a failed row has only its error, army and index.
ROW_FIELDS = ("army", "index", "x", "z", "type", "ui_id")


def unreadable(event) -> str | None:
    """Why an events-file line is not an event this comparison can read, or None."""
    try:
        if event["event"]["kind"] != "observation":
            return None
        data = event["event"]["data"]["observation"]
        if not isinstance(data, dict):
            return "the observation is not an object"
        missing = [field for field in ("battle", "time_ms") if field not in data]
        native = data.get("native")
        for n, row in enumerate([] if native is None else native["units"]):
            if not isinstance(row, dict):
                return f"units[{n}] is not an object"
            needed = ROW_FIELDS[:2] if "error" in row else ROW_FIELDS
            missing += [f"units[{n}].{field}" for field in needed if field not in row]
            if "error" not in row and any(field in row and not isinstance(row[field], int | float)
                                          for field in "xz"):
                return f"units[{n}] has a position that is not a number"
    except (KeyError, TypeError) as exc:
        return f"{type(exc).__name__}: {exc}"
    return f"missing {', '.join(missing)}" if missing else None


def observations(directory: Path, client: str) -> tuple[dict, dict]:
    """One client's distinct observations listed by ``time_ms``, and its counts."""
    path = directory / f"events-{client}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    by_time, battle = {}, None
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{path} line {number} is not JSON: {exc}") from exc
        problem = unreadable(event)
        if problem:
            raise ValueError(f"{path} line {number} is not an event the comparison reads:"
                             f" {problem}")
        if event["event"]["kind"] != "observation":
            continue
        data = event["event"]["data"]["observation"]
        battle = data["battle"] if battle is None else battle
        if data["battle"] != battle:
            raise ValueError(f"client {client}'s events hold more than one battle id ({battle}, "
                             f"{data['battle']}): one battle per attempt")
        seen = by_time.setdefault(data["time_ms"], [])
        if data not in seen:
            seen.append(data)
    natives = [data.get("native") for seen in by_time.values() for data in seen]
    return by_time, {
        "battle": battle, "observations": len(natives),
        "repeated_times": sum(len(seen) > 1 for seen in by_time.values()),
        "without_native": natives.count(None),
        "native_errors": sum(bool(native and native.get("errors")) for native in natives),
        "failed_rows": sum("error" in row for native in natives if native
                           for row in native["units"]),
    }


def compare_pair(a: str, seen_a: dict, b: str, seen_b: dict) -> dict:
    """Compare two clients' observations at the times both have (module docstring)."""
    # JUDGEMENT: same time — orchestrator's card, 2026-10-30: equal observation time_ms, not the
    # plan's completed ticks; a completed-tick collector would pair other readings. Every count
    # here rests on it.
    common = sorted(seen_a.keys() & seen_b.keys())
    pair = {"clients": [a, b], "common_times": len(common), "compared_times": 0,
            "only": {a: sorted(seen_a.keys() - seen_b.keys()),
                     b: sorted(seen_b.keys() - seen_a.keys())},
            "repeated": {a: [time_ms for time_ms in common if len(seen_a[time_ms]) > 1],
                         b: [time_ms for time_ms in common if len(seen_b[time_ms]) > 1]},
            "native_error_times": {a: [], b: []},
            "units_compared": 0, "exact": 0, "position_differences": 0, "type_mismatches": 0,
            "ui_id_mismatches": 0, "missing": {a: [], b: []}, "failed_rows": {a: 0, b: 0},
            "max_dx": None, "max_dz": None, "first_difference_ms": None, "differences": []}
    for time_ms in common:
        # JUDGEMENT?: repeated time — Claude after review, 2026-10-30: a time where either
        # client has two different observations is listed in `repeated` and not compared.
        # Comparing the lower seq (the regular one before finish()'s) would add these times.
        if len(seen_a[time_ms]) > 1 or len(seen_b[time_ms]) > 1:
            continue
        natives = {a: seen_a[time_ms][0].get("native"), b: seen_b[time_ms][0].get("native")}
        if None in natives.values():
            continue  # counted in that client's without_native
        # JUDGEMENT?: failed read — Claude after review, 2026-10-30: a time where either client's
        # native lists errors is listed in native_error_times and not compared. Comparing it would
        # count the units the failing side could not read as missing there.
        failing = [client for client, native in natives.items() if native.get("errors")]
        for client in failing:
            pair["native_error_times"][client].append(time_ms)
        if failing:
            continue
        pair["compared_times"] += 1
        units, failed = {a: {}, b: {}}, {a: set(), b: set()}
        for client, native in natives.items():
            for row in native["units"]:
                if "error" in row:
                    failed[client].add(unit_key(row))
                    pair["failed_rows"][client] += 1
                else:
                    units[client][unit_key(row)] = row
        for client, other in ((a, b), (b, a)):
            gone = [{"time_ms": time_ms, "unit": list(key)}
                    for key in units[other] if key not in units[client]
                    and key not in failed[client] and (None, *key[1:]) not in failed[client]]
            pair["missing"][client] += gone
            if gone and pair["first_difference_ms"] is None:  # a missing unit differs too
                pair["first_difference_ms"] = time_ms
        for key, row_a in units[a].items():
            row_b = units[b].get(key)
            if row_b is None:
                continue
            pair["units_compared"] += 1
            difference = {"time_ms": time_ms, "unit": list(key),
                          "dx": row_b["x"] - row_a["x"], "dz": row_b["z"] - row_a["z"]}
            for field in ("x", "z"):
                delta, largest = difference["d" + field], pair["max_d" + field]
                if row_a[field] != row_b[field] and (largest is None
                                                     or abs(delta) > largest["value"]):
                    pair["max_d" + field] = {"value": abs(delta), "time_ms": time_ms,
                                             "unit": list(key)}
            position = row_a["x"] != row_b["x"] or row_a["z"] != row_b["z"]
            pair["position_differences"] += position
            for field in ("type", "ui_id"):
                if row_a[field] != row_b[field]:
                    difference[field] = [row_a[field], row_b[field]]
                    pair[f"{field}_mismatches"] += 1
            # JUDGEMENT?: exact — Claude, 2026-10-30: equal x, z, type and ui_id; ui_id is not
            # proved equal across peers, and if it differs by client no unit is exact. Exact on x,
            # z and type (ui_id still counted) changes exact, differences and first_difference_ms.
            if not position and "type" not in difference and "ui_id" not in difference:
                pair["exact"] += 1
                continue
            pair["differences"].append(difference)
            if pair["first_difference_ms"] is None:
                pair["first_difference_ms"] = time_ms
    return pair


def compare(directory: Path) -> dict:
    """The summary of one attempt directory (module docstring)."""
    directory = Path(directory)
    with open(directory / "match.jsonl", encoding="utf-8") as handle:
        manifest = json.loads(handle.readline())["manifest"]
    clients = list(manifest["clients"])
    loaded = {client: observations(directory, client) for client in clients}
    return {"match": manifest["match"], "attempt": manifest["attempt"],
            "clients": {client: counts for client, (_, counts) in loaded.items()},
            "pairs": [compare_pair(a, loaded[a][0], b, loaded[b][0])
                      for a, b in itertools.combinations(clients, 2)]}


NATIVE_SCHEMA = "native-v1"
# As multiplayer_probe.js; rests on JUDGEMENT docs/twwarhammer3/multiplayer-control-foundation.md
# Raw witness.
WITNESS_EVERY = 10
FAILURE_EVENTS = ("probe_error", "frida_error", "capture_error", "detach_error", "detached")
# The passive hooks miss the adapter's engine call, so its row stands for the packet it wrote.
OPERATION_COMMANDS = {"ready_deployment": 699787935}  # BCQ_ARMY_ORDER_END_DEPLOYMENT_PHASE


def load_capture(path: Path, *, generation: int | None = None) -> dict:
    """One battle of one client's native.jsonl: ticks, witnesses, command packets, failures.
    A capture with several battles needs ``generation``; a torn final line counts as an
    unclean stop, a torn earlier line refuses."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    rows, torn = [], False
    for number, line in enumerate(lines, 1):
        try:
            rows.append(json.loads(line))
        except ValueError as exc:
            if number != len(lines):
                raise ValueError(f"{path} line {number} is not JSON: {exc}") from exc
            torn = True
    found = {row["generation"] for row in rows if row.get("event") == "completed_tick"}
    if generation is None:
        if len(found) > 1:
            raise ValueError(f"{path} holds battles {sorted(found)}: name a generation")
        generation = next(iter(found), None)
    capture = {"ticks": {}, "phases": {}, "witness": {}, "packet_rows": [], "conflicts": [],
               "failures": [], "generation": generation,
               "ending": None,
               "stopped": not torn and any(row.get("event") == "capture_stopped"
                                           and not row.get("failed") for row in rows)}
    current = None
    for row in rows:
        event = row.get("event")
        if event in FAILURE_EVENTS:
            capture["failures"].append(row)
        current = row.get("generation", current)  # adapter rows carry none: the battle running
        if current != generation:
            continue
        if event == "completed_tick":
            tick = row["tick"]
            if capture["ticks"].setdefault(tick, row["checksum"]) != row["checksum"]:
                capture["conflicts"].append({"tick": tick, "kind": "checksum"})
            if capture["phases"].setdefault(tick, row.get("sim_phase")) != row.get("sim_phase"):
                capture["conflicts"].append({"tick": tick, "kind": "phase"})
        elif event == "witness":
            units = {tuple(unit[:3]): unit[3:] for unit in row["units"]}
            if capture["witness"].setdefault(row["tick"], units) != units:
                capture["conflicts"].append({"tick": row["tick"], "kind": "witness"})
        elif event == "battle_decided":
            capture["ending"] = {"tick": row["tick"], "winner": row["winner"]}
        elif event == "command_packet":
            capture["packet_rows"].append(row)
        elif event == "operation_result" and row.get("status") == "submitted":
            operation = row.get("operation", "ready_deployment")
            capture["packet_rows"].append({"id": OPERATION_COMMANDS[operation],
                                           "last_completed_tick": row.get("last_completed_tick")})
    return capture


def boundaries(capture: dict) -> dict:
    ticks = capture["ticks"]
    return {"first_tick": min(ticks, default=None), "last_tick": max(ticks, default=None),
            "ticks": len(ticks), "witness_ticks": len(capture["witness"]),
            "first_phase": capture["phases"].get(min(ticks, default=None)),
            "last_phase": capture["phases"].get(max(ticks, default=None)),
            "ending": capture["ending"],
            "failures": len(capture["failures"]), "stopped": capture["stopped"]}


def compare_captures(captures: dict[str, dict], *, start: int | None = None,
                     end: int | None = None,
                     expected_packets: dict[str, dict[int, int]] | None = None) -> dict:
    """Completed-tick comparison of loaded captures, client -> ``load_capture`` (docstring).
    ``expected_packets``: client -> command id -> count, for ``submission_problems``."""
    if len(captures) < 2:
        raise ValueError("a comparison needs at least two clients")
    names = list(captures)
    edges = {client: boundaries(capture) for client, capture in captures.items()}
    known = [edge for edge in edges.values() if edge["ticks"]]
    low = start if start is not None else min((e["first_tick"] for e in known), default=None)
    high = end if end is not None else max((e["last_tick"] for e in known), default=None)
    summary = {"schema": NATIVE_SCHEMA, "clients": edges, "interval": [low, high],
               "missing_ticks": {client: [] for client in names},
               "missing_witness": {client: [] for client in names},
               "checksum_conflicts": [], "phase_differences": [], "unit_conflicts": [],
               "submission_problems": {}, "ticks_compared": 0,
               "witness_ticks_compared": 0, "units_compared": 0,
               "own_conflicts": {client: capture["conflicts"]
                                 for client, capture in captures.items()}}
    interval = range(low, high + 1) if low is not None and high is not None else range(0)
    for client, counts in (expected_packets or {}).items():
        summary["submission_problems"][client] = submission_problems(
            captures[client], counts, interval)
    for tick in interval:
        for client, capture in captures.items():
            if tick not in capture["ticks"]:
                summary["missing_ticks"][client].append(tick)
        present = [capture["ticks"][tick] for capture in captures.values()
                   if tick in capture["ticks"]]
        if len(present) == len(names):
            summary["ticks_compared"] += 1
        if len(set(present)) > 1:
            summary["checksum_conflicts"].append(
                {"tick": tick, "values": {client: capture["ticks"].get(tick)
                                          for client, capture in captures.items()}})
        phases = {client: capture["phases"].get(tick) for client, capture in captures.items()
                  if tick in capture["phases"]}
        if len(set(phases.values())) > 1:
            summary["phase_differences"].append({"tick": tick, "values": phases})
        if tick % WITNESS_EVERY:
            continue
        for client, capture in captures.items():
            if tick not in capture["witness"]:
                summary["missing_witness"][client].append(tick)
        tables = {client: capture["witness"][tick] for client, capture in captures.items()
                  if tick in capture["witness"]}
        if len(tables) < len(names):
            continue
        summary["witness_ticks_compared"] += 1
        for unit in sorted(set().union(*tables.values()), key=str):
            rows = {client: table.get(unit) for client, table in tables.items()}
            summary["units_compared"] += 1
            if len({None if row is None else tuple(row) for row in rows.values()}) > 1:
                summary["unit_conflicts"].append({"tick": tick, "unit": list(unit), "rows": rows})
    failed = any(edge["failures"] or not edge["stopped"] for edge in edges.values())
    missing = any(summary["missing_ticks"].values()) or any(summary["missing_witness"].values())
    endings = {(edge["ending"]["tick"], edge["ending"]["winner"])
               if edge["ending"] and edge["ending"]["tick"] in interval else None
               for edge in edges.values()}
    if (summary["checksum_conflicts"] or summary["unit_conflicts"]
            or any(summary["own_conflicts"].values()) or len(endings - {None}) > 1
            or any(summary["submission_problems"].values())):
        summary["verdict"] = "conflict"
    elif (failed or missing or len(endings) > 1 or summary["phase_differences"]
          or not (summary["ticks_compared"] and summary["units_compared"])):
        summary["verdict"] = "inconclusive"
    else:
        summary["verdict"] = "agreed"
    return summary


def submission_problems(capture: dict, expected: dict[int, int], interval=None) -> list[dict]:
    """Native packet counts against what a client was told to send, by command id: a duplicate
    can leave positions identical, so counts are checked apart from movement. Only the named
    ids count, since the engine sends commands of its own (foundation-ref8: seven kinds). A
    packet after completed tick t belongs to t + 1 when ``interval`` limits the count."""
    observed = collections.Counter(
        row["id"] for row in capture["packet_rows"]
        if interval is None or row["last_completed_tick"] is None
        or row["last_completed_tick"] + 1 in interval)
    return [{"id": command, "expected": count, "observed": observed[command]}
            for command, count in expected.items() if observed[command] != count]
