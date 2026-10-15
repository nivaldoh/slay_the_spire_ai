"""The file mailbox between the controller (WSL) and the in-game Lua scripts (Windows).

The directory is ``C:/wh3-agent/bridge``, reached from WSL through ``/mnt/c``. Writers
publish whole files (a temporary file, then a rename); readers treat a missing, locked or
half-parsed file as "not yet". In messages from the game, a key marked ``?`` below is absent
when unset (Lua nil), and an empty Lua table arrives as ``[]``, even where a filled one is an
object (``evaluation.objectives`` in a battle without capture points, an empty ``magic``).

Files, by writer:
- controller: ``session.json``, read at each script load (``job``, ``enabled``, ``menu``,
  ``autostart``, ``observe_ms``, ``tick_ms``, ``record_replay``, ``stills``; the mod
  ignores ``speed`` and ``pause``, which ``require_realtime`` checks); ``orders.json``, one
  outstanding request that the battle script deletes when read, ``{"schema", "job", "battle",
  "request", "based_on", "orders", "say"?}`` or ``{..., "control": "restart"}`` (replay the
  battle through the results popup's rematch); ``menu.json``, UI steps run by the frontend
  script, or by the battle script during a battle, and deleted when read.
- game: ``observation.json`` (below), rewritten every ``observe_ms`` of battle time and
  after each applied request; the append-only ``mod.log`` (``[battle ms] text``) and
  ``menu.log`` (step results, then ``done``); UI dumps named by ``dump`` steps; per battle,
  ``replay-<battle>.jsonl`` (a presentation frame per second, with ``record_replay``) and
  ``imagery-<battle>.json`` (still requests and unit names, with ``stills``).
- ``battle/capture.py`` (PassiveCapture): ``still-<battle>-<trigger>.png`` and
  ``capture-<battle>-<trigger>.json``.
An episode copies its battle's files when it ends. ``reset`` (``play`` without ``--attach``,
and ``launch``) removes the messages, logs and per-battle files before the game runs. UI
dumps stay; ``play`` copies a dump only when this job's ``menu.log`` reports writing it.

Every message carries the job name. The battle script makes a ``battle`` id at each load
and numbers observations by ``seq``, which is how the controller tells restarts and new
data apart; it drops a request for another job or battle, or repeating its last id.

Observation (``observation``, ``unit_record`` and ``mode_section`` in the battle Lua)::

    {"schema": 1, "job", "battle", "seq", "phase", "time_ms", "speed": 1,
     "awaiting_orders": false, "remaining_ms" (-1 without a countdown),
     "timer"?: {"observed_ms", "remaining_ms", "deadline_ms", "expired", "source"},
     "armies": {"player": {"faction"}, "enemy": {"faction"}},
     "friendly": [unit...], "enemy": [visible unit...],
     "enemy_roster": [{"id", "type", "dead"?, "alliance"?}...],
     "magic": {"current"?, "reserve"?},
     "army"?: {"currency"?, "next_unlock"?, "abilities": [{"key", "target", "radius",
               "cooldown_s", "cost"?, "unlocked"?, "button"?, "timer"?, "ready"?,
               "last_issued_ms"?}...]},
     "mode": {"type", "role"?, "timeout_winner"?, "objectives"? (the battle type's rules
              as text), "capture_points"?, "tickets"?, "tickets_goal"?, "gates"?,
              "reinforcements"?, "spawn_zones"?, "slots"?, "supplies"?},
     "terrain"?: {"x0", "z0", "cell_m", "rows" ("." clear, "#" blocked), "sample_width_m",
                  "sampled_ms", "bounds"},
     "orders"?: {"request", "based_on", "applied_ms",
                 "results": [{"index", "unit", "ok", "queued"?, "error"?}...]},
     "result"?: "won" | "lost" | "draw",
     "setup"?: {...}, "evaluation": {...}, "final"?: {...}}

A battle's first observation is a ``Loading`` placeholder with ``seq`` 0 and no units; then
``phase`` is the engine's (``Deployment``, ``Deployed``, ``VictoryCountdown``, ``Complete``).

A unit has ``id`` (f1..., e1...), ``type``, ``class``, ``commander``, ``can_fly``,
``flying``, ``x``, ``z``, ``bearing``, ``men``, ``men0``, ``hp`` (0-1), ``barrier``?,
``state`` (flags such as routing, shattered, wavering, melee, under_fire, moving, running),
``range``, ``speed`` ([walk, run]), and ``alliance`` for a free-for-all enemy. Friendlies
add ``morale``? (``fraction`` of best leadership, possibly negative, and the UI's largest
``effect``), ``flight``? (flyers: ``can_toggle``, ``cooldown_s``), ``ammo``, ``ammo0``,
``fatigue``, ``width``, ``attack_mode`` and ``command_queue`` (as last requested),
``navigation``? (an unreachable move's reachable alternatives), ``behaviours`` (toggle key
to state), ``abilities`` ({``key``, ``can_use`` (the engine's permission), ``ready``,
``active``, ``recharge_s``?, ``uses``?, ``target``, ``mana``, ``cooldown_s``,
``cast_range``, ``radius``, ``duration_s``, ``last_issued_ms``?}), ``target``? and
``dest``?. A unit that failed to read is ``{"id", "error"}``.

``evaluation``, ``final`` and ``setup`` hold hidden information, and the harness strips all
three before a controller sees a snapshot. ``evaluation`` has both armies' true strength
(``men``, ``men0``, ``active_men`` excluding routing and shattered units, and ``by_type``)
and tick-integrated capture point ownership (``objectives``). ``final`` freezes it at the
engine result; on other endings the harness keeps the last ``evaluation``. ``setup``, sent
until the first request is applied, has the unit scale, realism mode and the armies' AI
stat modifiers and unit stats.

Evaluator ``version: 2`` adds ``units`` to each side: ``registered``, ``destroyed``
(engine reports zero living entities), ``alive``, ``active`` (alive, deployed, not
deploying, routing, shattered or leaving), ``routed`` (routing or shattered), ``leaving``,
``absent`` (not deployed or currently deploying), and ``unknown`` (failed living-entity
query). Routed/leaving/absent are overlapping subsets of alive, not deaths. Registration
deduplicates returning unit ids and includes summons, purchases and waves when registered;
these are not original-army totals. The existing headcounts and ``active_men`` definition
are unchanged. Older results have no whole-unit counts or explicit evaluator version.

``timer`` appears with the result and keeps the last finite countdown sampled on engine
ticks, since ``remaining_ms`` can reset to -1 when the result arrives. ``expired`` compares
the result time with that sample's deadline: an inference, not an engine end cause.

``results`` indexes are one-based positions in the request, so a unit can get a behaviour
change and a move/attack sequence in one batch; ``queued`` acknowledges submission to the
engine queue, not execution. ``twwarhammer3.protocol`` validates the order types. An
``ability`` order whose unit is ``"army"`` casts an army ability; a ``flight`` order asks
for ``flying: true`` (take off) or ``false`` (land), the engine re-checks availability,
and later observations confirm the change.
"""

import json
import os
import time
from pathlib import Path

from twwarhammer3.protocol import BattleRestarted, MailboxTimeout

SCHEMA = 1
FILES = ("session.json", "observation.json", "orders.json", "menu.json", "mod.log", "menu.log")
BATTLE_FILES = ("replay-*", "imagery-*", "still-*", "capture-*")


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
        """Start a job with no leftovers from an earlier one. Only while the game is stopped:
        an earlier job's episodes copied their battle files when they ended."""
        self.directory.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            for path in (self.directory / name, self.directory / (name + ".tmp")):
                path.unlink(missing_ok=True)
        for pattern in BATTLE_FILES:
            for path in self.directory.glob(pattern):
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

    def write_control(self, battle: str, control: str, *, timeout: float = 15) -> str:
        """``restart``: replay the battle through the results popup's rematch."""
        return self._request(battle, {"control": control}, timeout)

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
