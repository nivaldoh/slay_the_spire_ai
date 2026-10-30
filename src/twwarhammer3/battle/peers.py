"""Offline comparison of what the clients of one native match attempt observed (plan step 4,
docs/twwarhammer3/native-multiplayer.md, and its Verification matrix's comparator row).

Input: an attempt directory the coordinator wrote (engine/link.py). The manifest, the first
line of ``match.jsonl``, names the clients; ``events-<client>.jsonl`` holds that worker's
events, and an event of kind ``observation`` carries one battle observation. Its
evaluator-only ``native`` section (engine/mailbox.py) lists every unit with ``alliance``,
``army``, ``index``, ``ui_id``, ``type`` and raw ``x`` and ``z``. A client without an events
file has no observations. An identical observation sent twice counts once.

For each pair of clients (A, B in manifest order), at each ``time_ms`` where both have an
observation, units are joined by (alliance, army, index): never by ``type``, which
same-type units share, and never by ``ui_id``, which is not proved equal across peers.
``dx`` is B's ``x`` minus A's (``dz`` likewise), unrounded; a unit is exact only when ``x``,
``z``, ``type`` and ``ui_id`` are all exactly equal. ``owner`` and ``id`` depend on the
client's own side by design and are not compared. The plan's rules followed: "Same-tick
comparison uses completed ticks, not nearest wall-clock samples" and "Do not invent a
floating-point epsilon to hide a failed comparison": a time only one client has is listed
as unavailable for the pair, never interpolated or matched to the nearest sample, and there
is no tolerance. No outside repository was followed.

This is weaker than that rule: ``time_ms`` is the battle time each client's Lua read when it
made an observation, not a completed engine tick. Two clients' observations at one
``time_ms`` may come from different ticks, and each client's observation schedule starts
at its own first tick, so common times may be few or none (unverified). A passive
completed-tick collector is a later, separately reviewed step (plan step 4).

Refusals (ValueError): a client's events holding more than one battle id (each client's Lua
makes its own id, so ids never match across clients; one battle per attempt) and two
different observations of one client at one ``time_ms``.

Summary: ``match``, ``attempt``; ``clients``: per client ``battle``, ``observations``,
``without_native`` (counted, not compared; the seq-0 ``Loading`` placeholder is one),
``native_errors`` (observations whose ``native`` lists failed top-level reads) and
``failed_rows`` (unit rows with ``error``); ``pairs``: per pair ``clients``, ``common_times``,
``compared_times`` (common times where both have ``native``), ``only`` (client -> times only
that client has), ``units_compared``, ``exact``, ``position_differences``,
``type_mismatches``, ``ui_id_mismatches``, ``missing`` (client -> units absent from that
client's observation at a compared time while the other lists them, a failed row excepted),
``failed_rows`` (client -> error rows at compared times), ``max_dx`` and ``max_dz``
(``{"value", "time_ms", "unit"}``, or null when every value is equal),
``first_difference_ms`` and ``differences`` (every compared unit that is not exact:
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


def observations(directory: Path, client: str) -> tuple[dict, dict]:
    """One client's observations by ``time_ms`` and its counts."""
    path = directory / f"events-{client}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    by_time, battle = {}, None
    for line in lines:
        event = json.loads(line)["event"]
        if event["kind"] != "observation":
            continue
        data = event["data"]
        battle = data["battle"] if battle is None else battle
        if data["battle"] != battle:
            raise ValueError(f"client {client}'s events hold more than one battle id ({battle}, "
                             f"{data['battle']}): one battle per attempt")
        # JUDGEMENT?: repeated time — Claude, 2026-10-30: two different observations of one
        # client at one time_ms refuse the attempt; comparing either one would change the counts.
        known = by_time.setdefault(data["time_ms"], data)
        if known != data:
            raise ValueError(f"client {client} has two different observations at time_ms "
                             f"{data['time_ms']} (seq {known['seq']} and {data['seq']})")
    natives = [data.get("native") for data in by_time.values()]
    return by_time, {
        "battle": battle, "observations": len(by_time), "without_native": natives.count(None),
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
            "units_compared": 0, "exact": 0, "position_differences": 0, "type_mismatches": 0,
            "ui_id_mismatches": 0, "missing": {a: [], b: []}, "failed_rows": {a: 0, b: 0},
            "max_dx": None, "max_dz": None, "first_difference_ms": None, "differences": []}
    for time_ms in common:
        natives = {a: seen_a[time_ms].get("native"), b: seen_b[time_ms].get("native")}
        if None in natives.values():
            continue  # counted in that client's without_native
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
            pair["missing"][client] += [{"time_ms": time_ms, "unit": list(key)}
                                        for key in units[other]
                                        if key not in units[client] and key not in failed[client]]
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
