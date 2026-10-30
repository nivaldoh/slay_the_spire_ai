"""The file mailbox between the controller (WSL) and the in-game Lua scripts (Windows).

The directory is ``C:/wh3-agent/bridge``, reached from WSL through ``/mnt/c``. Writers
publish whole files (a temporary file, then a rename); the controller treats a missing,
locked or half-parsed observation as "not yet"; the Lua scripts delete ``orders.json`` and
``menu.json`` before parsing and drop one that does not parse. In messages from the game, a
key marked ``?`` below is absent when unset (Lua nil), and an empty Lua table arrives as
``[]``, even where a filled one is an object (``evaluation.objectives`` in a battle without
capture points, an empty ``magic``).

Files, by writer:
- controller: ``session.json``, read at each script load (``job``, ``enabled``, ``menu``,
  ``autostart``, ``observe_ms``, ``tick_ms``, ``record_replay``, ``stills``, optional ``custom``
  (versioned authored objective and private deployment), optional ``multiplayer`` (below); the mod
  ignores ``speed`` and ``pause``, which ``require_realtime`` checks); ``orders.json``, one
  outstanding request that the battle script deletes when read, ``{"schema", "job", "battle",
  "request", "based_on", "orders", "say"?}`` or ``{..., "control": "restart"}`` (replay the
  battle through the results popup's rematch); ``menu.json``, UI steps run by the frontend
  script, or by the battle script during a battle, and deleted when read. Menu requests
  carry ``job``, ``request`` and ``steps``; each consumer rejects foreign jobs and logs
  ``menu <request>: done|failed``. ``menu`` waits for its own completion and returns
  nonzero on failure or timeout. The frontend also retains its standalone ``done`` or
  ``failed`` marker; setup can instead hand off to the first battle observation.
- game: ``observation.json`` (below), rewritten every ``observe_ms`` of battle time and
  after each applied request; the append-only ``mod.log`` (``[battle ms] text``) and
  ``menu.log`` (step results, then ``done`` or ``failed``); UI dumps named by ``dump``
  steps; per battle, ``replay-<battle>.jsonl`` (a presentation frame per second, with
  ``record_replay``) and ``imagery-<battle>.json`` (still requests and unit names, with
  ``stills``).
- ``battle/capture.py`` (PassiveCapture): ``still-<battle>-<trigger>.png`` and
  ``capture-<battle>-<trigger>.json``.
An episode copies its battle's files when it ends. ``reset`` (``play`` without ``--attach``,
and ``launch``) removes the messages, logs and per-battle files before the game runs. UI
dumps stay; ``play`` copies a dump only when this job's ``menu.log`` reports writing it.
Owned launches remove session activation after the game stops, including ordinary errors
and interruption. Attached controllers borrow the session and leave it to its owner.
An uncatchable controller termination can still leave a stale session file.

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
              "reinforcements"?, "spawn_zones"?, "slots"?, "supplies"?,
              "custom"?: {"kind", "version", "rules", "zone": {"x", "z", "radius"},
                          "deadline_ms", "remaining_ms"?, "assets": [{"id", "alive", "in_zone"}],
                          "extracted", "status", "reason"?, "ending"?, "completed_ms"?,
                          "ending_error"?}},
     "terrain"?: {"x0", "z0", "cell_m", "rows" ("." clear, "#" blocked), "sample_width_m",
                  "sampled_ms", "bounds"},
     "orders"?: {"request", "based_on", "applied_ms",
                 "results": [{"index", "unit", "ok", "queued"?, "error"?}...]},
     "result"?: "won" | "lost" | "draw",
     "setup"?: {...}, "evaluation": {...}, "final"?: {...}, "native"?: {...}}

A battle's first observation is a ``Loading`` placeholder with ``seq`` 0 and no units; then
``phase`` is the engine's from ``Deployed`` on (``Deployed``, ``VictoryCountdown``,
``Complete``); no observation is published during ``Deployment``. The obs-v4
``mode.custom`` extension contains only public objective rules and friendly progress.
Authored enemy placements stay in ``setup.custom``. A scripted objective requests an engine
ending, but ``result`` still requires engine confirmation. Its objective status is recorded
separately: a native victory can fail an asset-preservation objective. The play loop, not
the game, adds ``mode.scoring`` (``"contact"``) for a scenario that declares it.

A unit has ``id`` (f1..., e1...), ``type``, ``class``, ``commander``, ``can_fly``,
``flying``, ``x``, ``z``, ``bearing``, ``men``, ``men0``, ``hp`` (0-1), ``barrier``?,
``state`` (flags such as routing, shattered, wavering, melee, under_fire, moving, running),
``range``, ``speed`` ([walk, run]), and ``alliance`` for a free-for-all enemy. Friendlies
add ``morale``? (the UI's leadership ``fraction``, possibly negative or above 1, and the
UI's largest ``effect``), ``flight``? (flyers: ``can_toggle``, ``cooldown_s``), ``ammo``,
``ammo0``, ``fatigue``, ``width``, ``attack_mode``? and ``command_queue``? (as last
requested), ``navigation``? (an unreachable move's reachable alternatives), ``behaviours``
(toggle key to state), ``abilities`` ({``key``, ``can_use`` (the engine's permission),
``ready``, ``active``, ``recharge_s``?, ``uses``?, ``target``, ``mana``, ``cooldown_s``,
``cast_range``, ``radius``, ``duration_s``, ``last_issued_ms``?}), ``target``? and
``dest``?. A unit that failed to read is ``{"id", "error"}``.

``evaluation``, ``final``, ``setup`` and ``native`` hold hidden information, and the harness
strips them (``protocol.HIDDEN_KEYS``) before a controller sees a snapshot. ``evaluation``
has both armies' true strength (``men``, ``men0``, ``active_men`` excluding routing and
shattered units, and ``by_type``) and tick-integrated capture point ownership
(``objectives``). ``final`` freezes it at the engine result; on other endings the harness
keeps the last ``evaluation``. ``setup``, sent until the first request is applied, has the
unit scale, realism mode and the armies' AI stat modifiers and unit stats.
``setup.unit_experience`` holds friendly/enemy lists of ``{type, rank}`` at startup for
scenario and rematch checks; hidden enemy ranks stay private.

Evaluator ``version: 2`` adds ``units`` to each side: ``registered``, ``destroyed``
(engine reports zero living entities), ``alive``, ``active`` (alive, deployed, not
deploying, routing, shattered or leaving), ``routed`` (routing or shattered), ``leaving``,
``absent`` (not deployed or currently deploying), and ``unknown`` (failed living-entity
query). Routed/leaving/absent are overlapping subsets of alive, not deaths. Registration
deduplicates returning unit ids and includes summons, purchases and waves when registered;
these are not original-army totals. The existing headcounts and ``active_men`` definition
are unchanged. Older results have no whole-unit counts or explicit evaluator version.

Experimental native multiplayer (``docs/twwarhammer3/native-multiplayer.md``, steps 4 and 5):
session ``multiplayer`` is ``"observe"`` or ``"control"``. Without it a multiplayer battle
stays inactive; another value, or either mode with ``autostart``, ``custom`` or ``stills``,
leaves the script inactive with a ``mod.log`` line. Either mode also runs in a single-player
battle. Ownership follows ``bm:local_alliance()`` and ``bm:local_army()`` (an army index
within that alliance): ``friendly``, ``magic`` and ``armies.player`` are the local army's
own; the alliance's other armies (and its reinforcement armies) are allies, in neither
``friendly`` nor ``enemy``. Neither mode changes speed, takes controllers at startup, runs
battle-time ``menu.json`` (deleted, logged), shows ``say`` or defines the checkpoint
injection hook. ``observe`` deletes ``orders.json`` unread. ``control`` accepts only an
unqueued ``move`` of a ``friendly`` unit, taking that unit's controller at its first
accepted move; other orders fail with ``unsupported_in_multiplayer`` (allied and enemy ids
with ``unknown_unit``) and ``control`` messages are refused with a log line. ``native``
(both modes, evaluator-only) is ``{"mode", "is_multiplayer", "is_spectator",
"local_alliance", "local_army", "army_unique_id", "errors"?, "units": [{"id"? (f/e/a
alias), "ui_id", "type", "alliance", "army" (index in its alliance, or "r<k>" for
reinforcement army k), "index" (in that army's units), "owner" ("own", "allied", "enemy"),
"x", "z" (raw)}...]}``; a unit whose identity failed to read is ``{"alliance", "army",
"index", "error"}``, and a failed top-level read is listed in ``errors``. These are stub-tested
only: live ``local_army`` values, ``ui_id`` across peers and move replication are unverified.

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

# JUDGEMENT: Evaluation counts — assistant, b1 (2026-10-14), evaluator v2 (2026-10-15): the Lua
# strength() counts active men without routing and shattered units, dead at zero living entities.
# Counting routers as alive changes margins and scores (also report_html.py's Broken share).
# JUDGEMENT?: Multiplayer allied reinforcements — Claude, 2026-10-30, twwarhammer3_battle.lua scan:
# local-alliance reinforcement armies are allies (never friendly or controlled); owning those that
# reinforce local_army() would change what a multiplayer policy sees and may move.
# JUDGEMENT?: Multiplayer action routes — Claude, 2026-10-30, twwarhammer3_battle.lua poll/load:
# "control" also drops battle-time menu.json and leaves twwarhammer3_inject undefined (the card
# said so for "observe"); allowing UI steps or injection adds action routes beyond one move.
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

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
        # A new --attach controller shares the live battle's last-request history.
        self.request_prefix = uuid4().hex
        self.requests = 0
        self.written_ns = None  # the last observation file's write time (read_observation)

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

    @contextmanager
    def owned_session(self, session: dict):
        """Publish activation for an owned launch; exit after the game has stopped.

        The caller holds RuntimeLock. Attached controllers borrow this file and must
        not enter this context. Evidence files remain available after teardown.
        """
        self.write_session(session)
        try:
            yield
        finally:
            (self.directory / "session.json").unlink(missing_ok=True)

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

    def write_menu(self, steps: list[dict]) -> str:
        """Send UI steps; completion is logged as ``menu <request>: done|failed``."""
        request = uuid4().hex
        self._publish("menu.json", {"schema": SCHEMA, "job": self.job,
                                    "request": request, "steps": steps})
        return request

    def _request(self, battle: str, body: dict, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while (self.directory / "orders.json").exists():
            if time.monotonic() > deadline:
                raise MailboxTimeout("the game did not consume the previous request")
            time.sleep(self.poll)
        self.requests += 1
        request = f"{self.request_prefix}-r{self.requests}"
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
        """The current observation of this job, or None when there is none yet.

        ``written_ns`` becomes its file's write time, from the same open file. Under WSL that
        is the NTFS time the Windows clock stamped (in 100 ns units), which WSL's slow clocks
        do not touch."""
        try:
            with (self.directory / "observation.json").open("rb") as file:
                data, written_ns = file.read(), os.fstat(file.fileno()).st_mtime_ns
            observation = json.loads(data)
        except (OSError, ValueError):
            return None
        if not isinstance(observation, dict) or observation.get("job") != self.job:
            return None
        self.written_ns = written_ns
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
