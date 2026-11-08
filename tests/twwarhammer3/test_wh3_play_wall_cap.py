"""The wall cap in twwarhammer3/battle/play.py when it is reached while the job waits for the
next observation, against the shared fake mailbox. The cap reached in the loop is covered with
the benchmark outcomes in test_wh3_benchmark_outcome.py."""
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from twwarhammer3.battle import cards, play
from twwarhammer3.battle.scripted import Hold
from twwarhammer3.protocol import PolicyFailure


class _CleanupFails(Hold):
    def close(self):  # as TeamPolicy.close does for a member failure it collected
        raise PolicyFailure("team cleanup: member m1 bug")


@pytest.mark.parametrize("make, status, error", [
    (Hold, "truncated", "no observation"),
    (_CleanupFails, "policy_failure", "controller close: team cleanup: member m1 bug"),
])
def test_a_wall_cap_during_the_observation_wait_is_an_episode_timeout(tmp_path, make, status,
                                                                      error):
    # The battle starts, then the wait for the next observation runs out after the deadline
    # (the real wait is cut to the time left), so play sees a MailboxTimeout past the cap.
    mailbox = FakeMailbox([bridge_observation(0, 0)])
    play.play_episode(tmp_path / "e", {**CONFIG, "episode_timeout": -1}, make, mailbox,
                      not_battle=None)
    result = json.loads((tmp_path / "e/result.json").read_text())
    assert (result["status"], result["error"], result.get("reason")) == (
        status, error, "episode_timeout")
    assert (cards.benchmark_outcome(result), cards.outcome(result)) == ("unresolved", "forfeit")
