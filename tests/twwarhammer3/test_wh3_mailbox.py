import json
from contextlib import AbstractContextManager

import pytest
from wh3_lua import MOD, load_battle, runtime

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
    for name in ("observation.json", "orders.json", "orders.json.tmp", "mod.log", "session.json",
                 "replay-1-2.5.jsonl", "imagery-1-2.5.json", "imagery-1-2.5.json.tmp",
                 "still-1-2.5-opening.png", "capture-1-2.5-opening.json"):
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


def test_requests_are_distinct_and_wait_for_consumption(mailbox):
    request = mailbox.write_orders("b1", 7, [{"unit": "f1", "type": "halt"}])
    message = json.loads((mailbox.directory / "orders.json").read_text())
    assert message == {
        "schema": 1, "job": "job-a", "battle": "b1", "request": request, "based_on": 7,
        "orders": [{"unit": "f1", "type": "halt"}],
    }
    assert isinstance(request, str) and request
    with pytest.raises(MailboxTimeout, match="consume"):
        mailbox.write_control("b1", "restart", timeout=0.05)
    (mailbox.directory / "orders.json").unlink()
    restart = mailbox.write_control("b1", "restart", timeout=0.05)
    assert restart != request
    assert json.loads((mailbox.directory / "orders.json").read_text()) == {
        "schema": 1, "job": "job-a", "battle": "b1", "request": restart, "control": "restart",
    }
    assert not (mailbox.directory / "orders.json.tmp").exists()


@pytest.fixture
def order_consumer(mailbox):
    # Real files, JSON decoder and poll; only unrelated game callbacks are stubbed.
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute("json = twwarhammer3_json; function run_menu() end; function log() end")
    globals_ = lua.globals()
    globals_.BRIDGE = str(mailbox.directory) + "/"
    globals_.session = lua.table_from({"job": mailbox.job})
    globals_.state = lua.table_from({"battle": "b1"})
    _, poll = load_battle(lua, "read_file", "poll")
    return globals_, poll


def test_new_mailbox_requests_reach_lua_without_disabling_duplicate_rejection(
        mailbox, order_consumer):
    globals_, poll = order_consumer
    path = mailbox.directory / "orders.json"
    replacement = Mailbox(mailbox.directory, job=mailbox.job)
    for box in (mailbox, replacement):
        request = box.write_orders("b1", 7, [{"unit": "f1", "type": "halt"}])
        payload = path.read_text()
        poll()
        assert not path.exists()
        pending = globals_.state.pending
        assert pending is not None, "a new mailbox's request must reach Lua"
        assert pending.request == request and pending.based_on == 7
        assert dict(pending.orders[1]) == {"unit": "f1", "type": "halt"}
        # Simulate consumption, then redelivery of exactly the same request.
        globals_.state.pending = None
        path.write_text(payload)
        poll()
        assert not path.exists()
        assert globals_.state.pending is None, "duplicate delivery must still be rejected"


# JUDGEMENT: Foreign-order check — Codex, 2026-10-23, proposes real files and Lua poll to
# check the documented job/battle boundary and recovery. A live Windows check would also
# cover cross-process delivery; these cases establish component behavior only.
@pytest.mark.parametrize("foreign", [{"job": "another-job"}, {"battle": "old-battle"}],
                         ids=["other-job", "previous-battle"])
def test_lua_rejects_foreign_orders_without_poisoning_the_next_request(
        mailbox, order_consumer, foreign):
    globals_, poll = order_consumer
    current = mailbox.write_orders("b1", 7, [{"unit": "f1", "type": "halt"}])
    poll()
    path = mailbox.directory / "orders.json"
    following = mailbox.write_orders("b1", 8, [{"unit": "f2", "type": "halt"}])
    message = json.loads(path.read_text())

    path.write_text(json.dumps({**message, **foreign}))
    poll()

    assert not path.exists()
    assert globals_.state.pending.request == current
    assert globals_.state.last_request == current
    # Rejection must not reserve the ID and thereby discard its valid delivery later.
    path.write_text(json.dumps(message))
    poll()
    assert not path.exists()
    assert globals_.state.pending.request == following
    assert dict(globals_.state.pending.orders[1]) == {"unit": "f2", "type": "halt"}


def test_session_and_log_slices(mailbox):
    mailbox.write_session({"speed": 1.0, "pause": False})
    session = json.loads((mailbox.directory / "session.json").read_text())
    assert session == {"schema": 1, "job": "job-a", "speed": 1.0, "pause": False}
    assert mailbox.log_offset() == 0 and mailbox.log_since(0) == ""
    (mailbox.directory / "mod.log").write_text("loaded\n")
    offset = mailbox.log_offset()
    (mailbox.directory / "mod.log").write_text("loaded\napplied r1\n")
    assert mailbox.log_since(offset) == "applied r1\n"


@pytest.mark.parametrize("failure", [None, RuntimeError("startup"), KeyboardInterrupt()])
def test_owned_session_outlives_game_teardown_and_cleans_up_after_errors(mailbox, failure):
    path = mailbox.directory / "session.json"
    events = []

    class Game(AbstractContextManager):
        def __enter__(self):
            assert path.exists()
            if isinstance(failure, RuntimeError):
                raise failure
            return self

        def __exit__(self, *_):
            assert path.exists(), "session must stay active until game teardown"
            events.append("stopped")

    def run():
        with mailbox.owned_session({"speed": 1}), Game():
            (mailbox.directory / "mod.log").write_text("evidence")
            if failure:
                raise failure

    if failure:
        with pytest.raises(type(failure)):
            run()
    else:
        run()
    assert not path.exists()
    assert events == ([] if isinstance(failure, RuntimeError) else ["stopped"])
    if not isinstance(failure, RuntimeError):
        assert (mailbox.directory / "mod.log").read_text() == "evidence"


@pytest.mark.parametrize("session", [{"pause": True}, {"speed": 0.5}, {"speed": 2}])
def test_mailbox_refuses_non_realtime_sessions(tmp_path, session):
    mailbox = Mailbox(tmp_path, job="probe")
    with pytest.raises(ValueError, match="unpaused at 1x"):
        mailbox.write_session(session)
    assert not (tmp_path / "session.json").exists()
