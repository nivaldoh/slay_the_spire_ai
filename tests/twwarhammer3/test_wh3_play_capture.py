"""Optional presentation errors must not discard an episode's engine result.

Reference: integration.md, Visual recording and presentation: a capture failure becomes
metadata, never an order error. This exercises the real copiers through the fake play loop.
"""
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from twwarhammer3.battle import play
from twwarhammer3.battle.scripted import Hold


@pytest.mark.parametrize("broken", [None, "recording", "imagery", "deep-recording", "deep-imagery"],
                         ids=["valid", "bad-replay-header", "bad-still-filename",
                              "deep-replay-json", "deep-imagery-json"])
def test_optional_capture_failures_preserve_the_saved_engine_ending(tmp_path, broken):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    # Interrupted final replay lines are valid evidence; preserve their original bytes.
    replay = b'{"job":"job","battle":"b1","recorder":1}\n{"partial":'
    raw_replay = b"[" * 100_000 if broken == "deep-recording" else (
        b"[]\n" if broken == "recording" else replay)
    (bridge / "replay-b1.jsonl").write_bytes(raw_replay)
    filename = "still-b1-ending.png"
    (bridge / filename).write_bytes(b"image")
    imagery = json.dumps({
        "job": "job", "battle": "b1", "names": [],  # Lua encodes empty tables as arrays.
        "stills": [{"status": "captured", "trigger": "ending",
                    "file": 3 if broken == "imagery" else filename}],
    })
    (bridge / "imagery-b1.json").write_text("[" * 100_000 if broken == "deep-imagery" else imagery)
    mailbox = FakeMailbox([bridge_observation(0, 0),
                           bridge_observation(1, 1000, result="won")])
    mailbox.directory = bridge

    result = play.play_episode(episode, {**CONFIG, "record_replay": True, "stills": True},
                               Hold, mailbox, not_battle=None)

    assert json.loads((episode / "result.json").read_text()) == result
    assert result["status"] == "won" and result["engine_ending"]["result"] == "won"
    final = json.loads((episode / "trace.jsonl").read_text().splitlines()[-1])
    assert final["kind"] == "result" and final["observation"]["result"] == "won"
    failed = broken.removeprefix("deep-") if broken else None
    for name in ("recording", "imagery"):
        assert result[name]["status"] == ("error" if name == failed else "copied")
        if name == failed:
            assert result[name]["error"]
    if failed != "recording":
        assert (episode / "replay.jsonl").read_bytes() == replay
    if failed != "imagery":
        assert (episode / filename).read_bytes() == b"image"


@pytest.mark.parametrize("option,copier", [("record_replay", "copy_recording"),
                                         ("stills", "copy_presentation")])
def test_optional_copying_does_not_consume_an_operator_interrupt(tmp_path, monkeypatch,
                                                               option, copier):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(play, copier, interrupt)
    mailbox = FakeMailbox([bridge_observation(0, 0),
                           bridge_observation(1, 1000, result="won")])
    with pytest.raises(KeyboardInterrupt):
        play.play_episode(tmp_path / "episode", {**CONFIG, option: True}, Hold, mailbox,
                          not_battle=None)


@pytest.mark.parametrize("ending", ["lost", "draw"])
@pytest.mark.parametrize("metadata,option,filename", [
    ("recording", "record_replay", "replay-b1.jsonl"),
    ("imagery", "stills", "imagery-b1.json"),
])
def test_optional_capture_failures_preserve_losses_and_draws(tmp_path, ending,
                                                           metadata, option, filename):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    (bridge / filename).write_text("[]\n")  # a real malformed sidecar, not a mocked copier
    mailbox = FakeMailbox([bridge_observation(0, 0),
                           bridge_observation(1, 1000, result=ending)])
    mailbox.directory = bridge

    result = play.play_episode(episode, {**CONFIG, option: True}, Hold, mailbox, not_battle=None)

    assert json.loads((episode / "result.json").read_text()) == result
    assert result["status"] == result["engine_ending"]["result"] == ending
    assert result[metadata]["status"] == "error"
