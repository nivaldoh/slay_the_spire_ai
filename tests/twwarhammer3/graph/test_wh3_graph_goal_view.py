"""Model preferences retain their own producer identity in the graph view."""


import pytest
from wh3_graph_goal_support import recording, write

from twwarhammer3.battle import graph_view


def test_selection_matches_a_known_model_goal_and_its_recorded_scope(tmp_path):
    episode, _, _ = recording(tmp_path / "episode")
    data = graph_view.collect_episode(episode)
    selected = data["events"][-1]
    assert selected["node"] == "pick" and selected["outputs"]["target"] == "far"
    assert selected["selection"]["goal_line"] == 5
    assert selected["selection"]["preference"]["source"]["seq"] == 1
    assert selected["source"]["seq"] == 2  # selection rechecks a newer public view
    assert "line" in data["graphs"]


@pytest.mark.parametrize("change", ["controller", "battle", "graph", "clock", "goal", "target"])
def test_model_hint_cannot_be_reattributed_to_a_different_producer(tmp_path, change):
    episode, result, rows = recording(tmp_path / "episode")
    adopted = rows[4]["record"]
    selection = rows[6]["record"]["selection"]
    if change == "controller":
        adopted["source"]["controller"] = selection["preference"]["source"]["controller"] = "other"
    elif change == "battle":
        adopted["source"]["battle"] = selection["preference"]["source"]["battle"] = "other"
    elif change == "graph":
        adopted["source"]["graph_sha256"] = "foreign-graph"
        selection["preference"]["source"]["graph_sha256"] = "foreign-graph"
    elif change == "clock":
        adopted["source"]["time_ms"] = selection["preference"]["source"]["time_ms"] = 999
    elif change == "goal":
        rows.pop(4)
    else:
        selection["preference"]["target"] = "near"
    write(episode, result, rows)
    with pytest.raises(ValueError, match="recorded goal producer"):
        graph_view.collect_episode(episode)
