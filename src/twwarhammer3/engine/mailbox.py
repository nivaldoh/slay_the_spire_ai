"""The file mailbox between the controller (WSL) and the in-game Lua scripts (Windows).

The directory is ``C:/wh3-agent/bridge``, reached from WSL through ``/mnt/c``. The
controller owns ``session.json`` (read once per battle load), ``orders.json`` (one
outstanding request; the game deletes it after reading) and ``menu.json`` (frontend
steps). The game owns ``observation.json``, rewritten every observation interval,
plus the append-only ``mod.log`` and ``menu.log``. Every message carries the job
name; the game adds a ``battle`` id at each script load and a ``seq`` per
observation, which is how the controller tells restarts and new data apart.

Observation shape::

    {"schema": 1, "job", "battle", "seq", "phase", "time_ms", "speed", "awaiting_orders",
     "remaining_ms", "armies": {"player": {"faction"}, "enemy": {"faction"}},
     "friendly": [unit...], "enemy_roster": [{"id", "type"}...], "enemy": [visible unit...],
     "magic": {"current"?, "reserve"?},
     "army": {"currency"?, "next_unlock"?, "abilities": [{"key", "target", "radius",
              "cooldown_s", "cost"?, "unlocked"?, "button"?, "timer"?, "ready"?,
              "last_issued_ms"?}...]} | null,
     "orders": {"request", "based_on", "applied_ms",
                "results": [{"index", "unit", "ok", "queued", "error"?}]} | null,
     "result": "won" | "lost" | "draw" | null,
     "final": {"friendly": {"men", "men0"}, "enemy": {...}} | null}

``evaluation`` carries both armies' true strength (men, men0, active_men excluding
routing/shattered units, and totals by unit type) and tick-integrated objective ownership.
The Python harness strips it and ``final`` before any controller receives a snapshot.
``final`` freezes these evaluation records at the engine result; on other endings the
harness retains the last evaluation snapshot with its battle timestamp.

A request may carry ``say``, text the battle script shows in the advisor window. An
ability order whose unit is ``"army"`` casts an army ability. Order indexes are
one-based positions in the request, so a unit can receive a behavior
change and a move/attack sequence in one batch. ``queued`` acknowledges submission to
the engine queue, not execution. Friendly records include ``behaviours`` (supported
toggle keys mapped to current booleans), ``abilities`` (owned active keys with can_use,
the engine's permission, and from the UI context system ready, active, recharge_s left,
uses left, target type, mana cost and cooldown_s; plus last_issued_ms),
formation ``width``, last requested ``attack_mode`` and last submitted ``command_queue``.
Friendlies also expose ``morale`` (``fraction`` of best leadership, potentially negative,
and the UI's largest current ``effect``). Flyers have ``flight`` availability
(``can_toggle`` and ``cooldown_s``), alongside ``can_fly`` and actual ``flying`` state.
A ``flight`` order requests ``flying: true`` to take off or ``false`` to land; an
already completed state change is not toggled again. The engine re-checks availability,
and subsequent observations confirm the transition. These additions use the benchmark
track ``obs-v3+terrain/act-v2/live-1x``; earlier tracks lack this feedback/control.

Writers publish whole files (temporary file, then rename); readers treat a missing,
locked or half-parsed file as "not yet".
"""

import json
import os
import time
from pathlib import Path

from twwarhammer3.protocol import BattleRestarted, MailboxTimeout

SCHEMA = 1
FILES = ("session.json", "observation.json", "orders.json", "menu.json", "mod.log", "menu.log")


def require_realtime(session: dict) -> None:
    """All WH3 battles, including probes, run at normal speed without policy pauses."""
    if session.get("pause") or session.get("speed", 1) != 1:
        raise ValueError("WH3 battles must run unpaused at 1x speed")


class Mailbox:
    def __init__(self, directory: Path, *, job: str, poll: float = 0.1):
        self.directory = directory
        self.job = job
        self.poll = poll
        self.requests = 0

    # -- publishing -------------------------------------------------------------------

    def reset(self) -> None:
        """Start a job with no leftovers from an earlier one."""
        self.directory.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            for path in (self.directory / name, self.directory / (name + ".tmp")):
                path.unlink(missing_ok=True)

    def write_session(self, session: dict) -> None:
        require_realtime(session)
        self._publish("session.json", {"schema": SCHEMA, "job": self.job, **session})

    def write_orders(self, battle: str, based_on: int, orders: list[dict], *,
                     say: str | None = None, timeout: float = 15) -> str:
        """Send one request; the previous one must have been consumed first. ``say`` is
        shown in the game's advisor window."""
        body = {"based_on": based_on, "orders": orders}
        if say:
            body["say"] = say
        return self._request(battle, body, timeout)

    def write_control(self, battle: str, control: str, *, timeout: float = 15, **fields) -> str:
        """``restart`` or ``start`` (end deployment)."""
        return self._request(battle, {"control": control, **fields}, timeout)

    def write_menu(self, steps: list[dict]) -> None:
        self._publish("menu.json", {"schema": SCHEMA, "job": self.job, "steps": steps})

    def _request(self, battle: str, body: dict, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while (self.directory / "orders.json").exists():
            if time.monotonic() > deadline:
                raise MailboxTimeout("the game did not consume the previous request")
            time.sleep(self.poll)
        self.requests += 1
        request = f"r{self.requests}"
        message = {"schema": SCHEMA, "job": self.job, "battle": battle, "request": request, **body}
        self._publish("orders.json", message)
        return request

    def _publish(self, name: str, message: dict) -> None:
        path = self.directory / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(message, sort_keys=True), encoding="utf-8")
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                # The game holds the file open for a moment while reading it.
                time.sleep(0.05 * (attempt + 1))
        os.replace(temporary, path)

    # -- reading ----------------------------------------------------------------------

    def read_observation(self) -> dict | None:
        """The current observation of this job, or None when there is none yet."""
        try:
            observation = json.loads((self.directory / "observation.json").read_bytes())
        except (OSError, ValueError):
            return None
        if not isinstance(observation, dict) or observation.get("job") != self.job:
            return None
        return observation

    def wait_new_battle(self, *, not_battle: str | None, timeout: float) -> dict:
        """The first observation of a battle other than ``not_battle``."""
        deadline = time.monotonic() + timeout
        while True:
            observation = self.read_observation()
            if observation is not None and observation.get("battle") != not_battle:
                return observation
            if time.monotonic() > deadline:
                raise MailboxTimeout(f"no battle started within {timeout:g} s")
            time.sleep(self.poll)

    def wait_observation(self, *, battle: str, after_seq: int, timeout: float) -> dict:
        """The newest observation of ``battle`` with ``seq`` beyond ``after_seq``."""
        deadline = time.monotonic() + timeout
        while True:
            observation = self.read_observation()
            if observation is not None:
                if observation.get("battle") != battle:
                    raise BattleRestarted(observation)
                if observation.get("seq", -1) > after_seq:
                    return observation
            if time.monotonic() > deadline:
                raise MailboxTimeout(f"no observation after seq {after_seq} within {timeout:g} s")
            time.sleep(self.poll)

    def log_offset(self, name: str = "mod.log") -> int:
        path = self.directory / name
        return path.stat().st_size if path.exists() else 0

    def log_since(self, offset: int, name: str = "mod.log") -> str:
        path = self.directory / name
        if not path.exists():
            return ""
        return path.read_bytes()[offset:].decode("utf-8", "replace")
