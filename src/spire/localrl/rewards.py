"""Rewards for one fight, from numbers the game shows."""

from __future__ import annotations


def fight_spans(steps: list[dict]) -> list[tuple[int, int]]:
    """Half-open index ranges of consecutive steps inside one fight."""
    spans, start = [], None
    for index, step in enumerate(steps):
        inside = (step["observation"]["turn"] or 0) > 0
        if inside and start is not None and (step["observation"]["floor"]
                                              != steps[start]["observation"]["floor"]):
            spans.append((start, index))
            start = index
        elif inside and start is None:
            start = index
        elif not inside and start is not None:
            spans.append((start, index))
            start = None
    if start is not None:
        spans.append((start, len(steps)))
    return spans


def fight_rewards(steps: list[dict], start: int, end: int, status: str,
                  config: dict) -> list[float]:
    """One reward per step of a fight: HP lost in it, and the fight's own ending.

    JUDGEMENT: Fight reward — Claude, 2026-11-06: a fight step is credited with what happens
    in that fight, not with floors reached later, whose noise swamps one card play. Reward is the
    HP change over ``fight_hp`` (30 HP is one unit), a death costs ``fight_death`` units, a potion
    used costs ``fight_potion`` units so that potions are not free. Another scale changes what
    the adapter gives up to stay alive; adapters trained with this rest on it. Floors stay the
    evaluation measure, and steps outside fights keep the floor reward.
    """
    def hp(index: int) -> float:
        return steps[index]["observation"]["hp"] or 0

    scale = config["fight_hp"]
    values = [(hp(t + 1) - hp(t)) / scale for t in range(start, end - 1)]
    if end < len(steps):
        values.append((hp(end) - hp(end - 1)) / scale)
    elif status == "lost":
        values.append(-hp(end - 1) / scale - config["fight_death"])
    else:
        values.append(0.0)
    return [value - config["fight_potion"] * steps[t].get("label", "").startswith("use potion")
            for t, value in zip(range(start, end), values)]
