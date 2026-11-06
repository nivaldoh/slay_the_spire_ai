"""The link at speed: a decision always answers the newest state, whatever the game sends."""

import threading

import pytest

from spire.localrl.link import Link


class FakeBridge:
    """Hands out queued messages, then waits, as a quiet socket does."""

    timeout = 0.2

    def __init__(self, messages):
        self.messages, self.sent, self.release = list(messages), [], threading.Event()
        self._connection = self

    def settimeout(self, value):
        pass

    def accept(self):
        pass

    def receive(self):
        while not self.messages:
            if self.release.wait(0.001):
                raise RuntimeError("closed")
        return self.messages.pop(0)

    def send(self, command):
        self.sent.append(command)
        if command == "state":
            self.messages.append(ready("after"))


def ready(name):
    return {"ready_for_command": True, "name": name}


def test_a_second_state_for_one_command_does_not_leave_the_loop_behind():
    link = Link(FakeBridge([ready("stale"), ready("newest")]), gap=0.01)
    assert link.receive()["name"] == "newest"
    link.bridge.release.set()


def test_a_rejected_command_reads_the_state_again_and_loses_its_step():
    bridge = FakeBridge([{"error": "Invalid command: end"}])
    lost = []
    link = Link(bridge, gap=0.01)
    link.dropped = lost.append
    assert link.receive()["name"] == "after"
    assert bridge.sent == ["state"] and lost == [None]
    bridge.release.set()


def test_a_decision_on_a_state_that_moved_is_not_sent():
    bridge = FakeBridge([ready("first")])
    lost = []
    link = Link(bridge, gap=0.01)
    link.dropped = lost.append
    assert link.receive()["name"] == "first"
    link.inbox.put(ready("moved on"))
    link.send("play 1")
    assert bridge.sent == [] and lost == ["play 1"]
    assert link.receive()["name"] == "moved on"
    bridge.release.set()


def test_silence_is_a_timeout_and_a_reader_failure_reaches_the_run():
    from spire.engine.bridge import BridgeTimeout

    bridge = FakeBridge([])
    link = Link(bridge, gap=0.01)
    with pytest.raises(BridgeTimeout):
        link.receive()
    bridge.release.set()
    with pytest.raises(RuntimeError, match="closed"):
        link.receive()


def test_at_normal_speed_the_link_only_passes_messages_through():
    bridge = FakeBridge([ready("one"), {"error": "Invalid command: end"}])
    link = Link(bridge)
    assert link.receive()["name"] == "one"
    assert "error" in link.receive()
    link.send("play 1")
    assert bridge.sent == ["play 1"]
