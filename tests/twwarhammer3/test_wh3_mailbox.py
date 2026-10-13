import json

import pytest

from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout


def observation(directory, **fields):
    message = {"schema": 1, "job": "job-a", "battle": "b1", "seq": 1, **fields}
    (directory / "observation.json").write_text(json.dumps(message))
    return message


@pytest.fixture
def mailbox(tmp_path):
    box = Mailbox(tmp_path / "bridge", job="job-a", poll=0.01)
    box.reset()
    return box


def test_reset_removes_every_leftover_message_and_log(tmp_path):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    for name in ("observation.json", "orders.json", "orders.json.tmp", "mod.log", "session.json"):
        (bridge / name).write_text("old")
    Mailbox(bridge, job="job-b").reset()
    assert list(bridge.iterdir()) == []


def test_missing_partial_or_foreign_observations_read_as_none(mailbox):
    assert mailbox.read_observation() is None
    (mailbox.directory / "observation.json").write_text('{"schema": 1, "job": "job-a", "se')
    assert mailbox.read_observation() is None
    observation(mailbox.directory, job="another-job")
    assert mailbox.read_observation() is None
    message = observation(mailbox.directory, seq=4)
    assert mailbox.read_observation() == message


def test_wait_observation_needs_a_newer_seq_of_the_same_battle(mailbox):
    observation(mailbox.directory, seq=4)
    with pytest.raises(MailboxTimeout):
        mailbox.wait_observation(battle="b1", after_seq=4, timeout=0.05)
    message = observation(mailbox.directory, seq=5)
    assert mailbox.wait_observation(battle="b1", after_seq=4, timeout=0.05) == message
    observation(mailbox.directory, battle="b2", seq=1)
    with pytest.raises(BattleRestarted) as restarted:
        mailbox.wait_observation(battle="b1", after_seq=5, timeout=0.05)
    assert restarted.value.observation["battle"] == "b2"


def test_wait_new_battle_skips_the_previous_battle(mailbox):
    observation(mailbox.directory, battle="b1")
    with pytest.raises(MailboxTimeout):
        mailbox.wait_new_battle(not_battle="b1", timeout=0.05)
    assert mailbox.wait_new_battle(not_battle=None, timeout=0.05)["battle"] == "b1"
    message = observation(mailbox.directory, battle="b2")
    assert mailbox.wait_new_battle(not_battle="b1", timeout=0.05) == message


def test_requests_are_numbered_and_wait_for_consumption(mailbox):
    request = mailbox.write_orders("b1", 7, [{"unit": "f1", "type": "halt"}])
    message = json.loads((mailbox.directory / "orders.json").read_text())
    assert message == {
        "schema": 1, "job": "job-a", "battle": "b1", "request": "r1", "based_on": 7,
        "orders": [{"unit": "f1", "type": "halt"}],
    }
    assert request == "r1"
    with pytest.raises(MailboxTimeout, match="consume"):
        mailbox.write_control("b1", "restart", timeout=0.05)
    (mailbox.directory / "orders.json").unlink()
    assert mailbox.write_control("b1", "restart", timeout=0.05) == "r2"
    assert json.loads((mailbox.directory / "orders.json").read_text())["control"] == "restart"
    assert not (mailbox.directory / "orders.json.tmp").exists()


def test_session_and_log_slices(mailbox):
    mailbox.write_session({"speed": 1.0, "pause": False})
    session = json.loads((mailbox.directory / "session.json").read_text())
    assert session == {"schema": 1, "job": "job-a", "speed": 1.0, "pause": False}
    assert mailbox.log_offset() == 0 and mailbox.log_since(0) == ""
    (mailbox.directory / "mod.log").write_text("loaded\n")
    offset = mailbox.log_offset()
    (mailbox.directory / "mod.log").write_text("loaded\napplied r1\n")
    assert mailbox.log_since(offset) == "applied r1\n"


@pytest.mark.parametrize("session", [{"pause": True}, {"speed": 0.5}, {"speed": 2}])
def test_mailbox_refuses_non_realtime_sessions(tmp_path, session):
    mailbox = Mailbox(tmp_path, job="probe")
    with pytest.raises(ValueError, match="unpaused at 1x"):
        mailbox.write_session(session)
    assert not (tmp_path / "session.json").exists()
