"""Rewards for one fight, from numbers the game shows."""

from __future__ import annotations

HARD_ROOMS = ("MonsterRoomElite", "MonsterRoomBoss")


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

    JUDGEMENT: Potion value — Claude, 2026-11-07: greedy adapters reached the boss with 2.6 potions
    and died holding 2.5 (22 fights, runs/spire-rl-20261107/boss_study.py), so the cost above now
    applies only in ordinary rooms, and a death costs ``fight_wasted`` units per potion still held.
    A larger value spends potions sooner; adapters trained with it rest on this.
    """
    def hp(index: int) -> float:
        return steps[index]["observation"]["hp"] or 0

    scale = config["fight_hp"]
    values = [(hp(t + 1) - hp(t)) / scale for t in range(start, end - 1)]
    if end < len(steps):
        values.append((hp(end) - hp(end - 1)) / scale)
    elif status == "lost":
        held = steps[end - 1]["observation"].get("potions") or 0
        values.append(-hp(end - 1) / scale - config["fight_death"]
                      - config.get("fight_wasted", 0.0) * held)
    else:
        values.append(0.0)

    def potion_cost(t: int) -> float:
        hard = steps[t]["observation"].get("room") in HARD_ROOMS
        used = steps[t].get("label", "").startswith("use potion")
        return config["fight_potion"] if used and not hard else 0.0

    return [value - potion_cost(t) for t, value in zip(range(start, end), values)]
