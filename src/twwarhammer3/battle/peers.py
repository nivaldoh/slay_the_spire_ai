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
``time_ms`` may come from different ticks, and each client's observation schedule starts
at its own first tick, so common times may be few or none (unverified). A passive
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
"""

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
