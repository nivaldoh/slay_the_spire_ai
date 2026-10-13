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
     "orders": {"request", "based_on", "applied_ms",
                "results": [{"index", "unit", "ok", "queued", "error"?}]} | null,
     "result": "won" | "lost" | "draw" | null,
     "final": {"friendly": {"men", "men0"}, "enemy": {...}} | null}

``final`` is both armies' true strength, published only with the result (after the last
decision), for evaluation.

Order indexes are one-based positions in the request, so a unit can receive a behavior
change and a move/attack sequence in one batch. ``queued`` acknowledges submission to
the engine queue, not execution. Friendly records include ``behaviours`` (supported
toggle keys mapped to current booleans), ``abilities`` (owned active keys, can_use and
last_issued_ms; can_use does not report cooldown),
formation ``width``, last requested ``attack_mode`` and last submitted ``command_queue``.

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
        self._publish("session.json", {"schema": SCHEMA, "job": self.job, **session})

    def write_orders(self, battle: str, based_on: int, orders: list[dict], *,
                     timeout: float = 15) -> str:
        """Send one request; the previous one must have been consumed first."""
        return self._request(battle, {"based_on": based_on, "orders": orders}, timeout)

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
