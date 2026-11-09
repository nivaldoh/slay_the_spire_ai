"""Mailbox sequences with real files and a controlled polling clock; no game launches.

Reference: engine/mailbox.py's job/battle/seq and one-outstanding-request contract.
Pattern: google-deepmind/pysc2, pysc2/env/mock_sc2_env_test.py, test_two_episodes
at 0df53d38c153972f1e368572ba65b1442a0fd41f: exercise transitions in one session.
The clock schedules file changes; it does not establish Windows timing or lock semantics.
"""

import json
from collections import deque
from types import SimpleNamespace

import pytest

from twwarhammer3.engine import mailbox as mailbox_module
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout


# JUDGEMENT: Mailbox transition checks — Codex, 2026-11-03: use real files and scripted
# polling to check the documented transitions. A live two-process check would additionally
# test Windows scheduling and sharing locks; these proposed checks establish neither.
@pytest.fixture
def polling(tmp_path, monkeypatch):
    box = Mailbox(tmp_path, job="current-job", poll=0.25)
    on_poll = deque()
    now = 0.0

    def sleep(seconds):
        nonlocal now
        now += seconds
        assert now < 10, "mailbox failed to finish within the scripted polling window"
        if on_poll:
            on_poll.popleft()()

    monkeypatch.setattr(mailbox_module, "time",
                        SimpleNamespace(monotonic=lambda: now, sleep=sleep))
    return box, on_poll


def publish(box, **fields):
    message = {"schema": 1, "job": box.job, "battle": "b1", "seq": 5, **fields}
    (box.directory / "observation.json").write_text(json.dumps(message), encoding="utf-8")
    return message


@pytest.mark.parametrize("unusable", [
    {"job": "current-job", "battle": "b1", "seq": 3},
    {"job": "current-job", "battle": "b1", "seq": 4},
    {"job": "other-job", "battle": "other-battle", "seq": 99},
    [],
    '{"job":',
], ids=["older", "duplicate", "foreign-newer", "non-object", "partial-json"])
def test_wait_ignores_unusable_observation_then_delivers_newer_one(polling, unusable):
    box, on_poll = polling
    path = box.directory / "observation.json"
    path.write_text(unusable if isinstance(unusable, str) else json.dumps(unusable))
    expected = {"schema": 1, "job": box.job, "battle": "b1", "seq": 5, "time_ms": 2100}
    on_poll.append(lambda: path.write_text(json.dumps(expected)))

    actual = box.wait_observation(battle="b1", after_seq=4, timeout=2)

    assert actual == expected


@pytest.mark.parametrize("waiting_for", ["observation", "new-battle"])
def test_wait_recovers_after_a_transient_read_lock(polling, monkeypatch, waiting_for):
    box, on_poll = polling
    expected = publish(box)
    path = box.directory / "observation.json"
    original_open = mailbox_module.windows.open_shared
    locked = True
    locked_reads = []

    def open_file(target):
        if target == path and locked:
            locked_reads.append(target)
            raise PermissionError("simulated game read lock")
        return original_open(target)

    def unlock():
        nonlocal locked
        locked = False

    monkeypatch.setattr(mailbox_module.windows, "open_shared", open_file)
    on_poll.append(unlock)

    if waiting_for == "observation":
        actual = box.wait_observation(battle="b1", after_seq=4, timeout=2)
    else:
        actual = box.wait_new_battle(not_battle="previous", timeout=2)

    assert actual == expected
    assert locked_reads == [path], "read-lock fault never ran"
    assert not locked


def test_rematch_wait_delivers_loading_at_sequence_zero(polling):
    box, on_poll = polling
    publish(box, seq=90, result="won", phase="Complete")
    expected = {"schema": 1, "job": box.job, "battle": "b2", "seq": 0,
                "phase": "Loading", "friendly": [], "enemy": []}
    on_poll.append(lambda: (box.directory / "observation.json").write_text(json.dumps(expected)))

    actual = box.wait_new_battle(not_battle="b1", timeout=2)

    assert actual == expected


@pytest.mark.parametrize("result", ["won", "lost", "draw"])
def test_terminal_observation_is_delivered_with_its_evidence(polling, result):
    box, on_poll = polling
    publish(box, seq=4)
    expected = {"schema": 1, "job": box.job, "battle": "b1", "seq": 5,
                "phase": "Complete", "result": result, "final": {"player": {"men": 12}}}
    on_poll.append(lambda: (box.directory / "observation.json").write_text(json.dumps(expected)))

    actual = box.wait_observation(battle="b1", after_seq=4, timeout=2)

    assert actual == expected


def test_restart_after_a_stale_observation_carries_the_new_battle(polling):
    box, on_poll = polling
    publish(box, seq=3)
    restarted = {"schema": 1, "job": box.job, "battle": "b2", "seq": 0, "phase": "Loading"}
    on_poll.append(lambda: (box.directory / "observation.json").write_text(json.dumps(restarted)))

    with pytest.raises(BattleRestarted) as caught:
        box.wait_observation(battle="b1", after_seq=4, timeout=2)

    assert caught.value.observation == restarted


@pytest.mark.parametrize("following", ["orders", "restart"])
def test_timeout_preserves_pending_request_until_consumption(polling, following):
    box, on_poll = polling
    first = box.write_orders("b1", 7, [{"unit": "f1", "type": "halt"}])
    path = box.directory / "orders.json"
    pending = path.read_bytes()
    body = ({"based_on": 8, "orders": [{"unit": "f2", "type": "halt"}]}
            if following == "orders" else {"control": "restart"})

    def send():
        if following == "orders":
            return box.write_orders("b1", 8, body["orders"], timeout=1)
        return box.write_control("b1", "restart", timeout=1)

    with pytest.raises(MailboxTimeout, match="consume the previous request"):
        send()

    assert path.read_bytes() == pending, "a failed send must not alter the outstanding order"

    def consume():
        assert path.read_bytes() == pending, "keep the first request until the game reads it"
        path.unlink()

    on_poll.append(consume)
    second = send()

    assert second != first
    assert json.loads(path.read_text()) == {
        "schema": 1, "job": box.job, "battle": "b1", "request": second, **body,
    }
