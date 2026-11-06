"""The bridge as a run loop sees it, at 1x and at training speed."""

from __future__ import annotations

import queue
import threading
import time

from spire.engine.bridge import BridgeTimeout
from spire.protocol import BridgeCommandError, ProtocolError

MENU_SECONDS = 60
# A Neow blessing that adds or transforms a card without a card screen seems to act when its
# effect ends, and the game accepts the next command before that. At 1x the card never reached
# the deck on 2 of 12 seeds (LRLEVAL17 and 23 of the 2026-11-06 replay). At speed this gap of real
# time is seconds of game time, so a command after a screen choice comes once the effect is over.
SPEED_GAP_SECONDS = 0.12
# A second state for one command comes within a few frames of the first.
STATE_QUIET_SECONDS = 0.015


class Link:
    """The bridge, with the main-menu state put back for the next run to read first.

    At speed a thread reads the bridge all the time and a decision always answers the newest
    state. CommunicationMod can send two ready states for one command (a Smoke Bomb's escape,
    LRDEV003, 2026-11-06). Read one at a time, the extra state leaves the run loop a message
    behind for the rest of the run, answering screens that are gone. At 1x nothing changes.
    """

    def __init__(self, bridge, gap: float = 0):
        self.bridge, self.waiting, self.gap = bridge, None, gap
        self.free_at = 0.0
        self.last_command = ""
        self.dropped = None  # called with (command, error) for a decision with no effect
        self.superseded = None  # called with a state a newer one replaced before it was read
        if gap:
            self.inbox = queue.Queue()
            threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        """Runs without a socket timeout: long pauses are normal between runs, and a timed-out
        reader cannot be used again. ``_next`` keeps the timeout instead."""
        try:
            self.bridge.accept()
            self.bridge._connection.settimeout(None)
            while True:
                self.inbox.put(self.bridge.receive())
        except Exception as error:
            self.inbox.put(error)

    def _next(self) -> dict:
        if not self.gap:
            return self.bridge.receive()
        try:
            message = self.inbox.get(timeout=self.bridge.timeout)
        except queue.Empty:
            raise BridgeTimeout("timed out waiting for a complete game state") from None
        if isinstance(message, Exception):
            raise message
        return message

    def _newest(self, message: dict) -> dict:
        """This message, or what followed it within ``STATE_QUIET_SECONDS``."""
        while True:
            try:
                newer = self.inbox.get(timeout=STATE_QUIET_SECONDS)
            except queue.Empty:
                return message
            if isinstance(newer, Exception):
                raise newer
            if "error" in message:
                if self.dropped:
                    self.dropped(self.last_command, message["error"])
            elif self.superseded:
                self.superseded(message)
            message = newer

    def receive(self) -> dict:
        message, self.waiting = self.waiting, None
        message = message or self._next()
        if not self.gap:
            return message
        message = self._newest(message)
        while (self.last_command.startswith("START") and "error" not in message
               and not message.get("in_game")):  # a menu state from before the run began
            message = self._newest(self._next())
        while "error" in message:  # the game did nothing: read the state again
            if self.last_command.startswith("START"):  # no run began, so nothing can follow
                raise BridgeCommandError(message["error"])
            if self.dropped:
                self.dropped(self.last_command, message["error"])
            self.bridge.send("state")
            message = self._newest(self._next())
        return message

    def send(self, command: str) -> None:
        if self.gap:
            time.sleep(max(self.free_at - time.monotonic(), 0))
            if command.startswith("START"):  # a late menu state decided nothing
                while not self.inbox.empty():
                    self._next()
            elif not self.inbox.empty():  # the state moved while the model thought
                self.waiting = self._next()
                if self.dropped:
                    self.dropped(command, None)
                return
            if not command.startswith(("play", "end", "potion")):
                self.free_at = time.monotonic() + self.gap
            self.last_command = command
        self.bridge.send(command)

    def to_menu(self) -> None:
        """From the death or victory screen back to the main menu."""
        deadline = time.monotonic() + MENU_SECONDS
        self.last_command = ""
        self.bridge.send("proceed")
        while time.monotonic() < deadline:
            message = self._next()
            if "error" in message:
                raise BridgeCommandError(message["error"])
            if not message.get("ready_for_command"):
                continue
            if not message.get("in_game"):
                self.waiting = message
                return
            if "proceed" not in message.get("available_commands", ()):
                raise ProtocolError(f"Cannot leave {message.get('available_commands')}")
            self.bridge.send("proceed")
        raise ProtocolError("The main menu did not return")
