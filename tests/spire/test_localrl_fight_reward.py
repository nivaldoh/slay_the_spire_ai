"""Fight rewards against small runs worked out by hand."""

from spire.localrl import rewards

CONFIG = {"fight_hp": 30.0, "fight_death": 2.0, "fight_potion": 0.1}


def step(turn, hp, floor=3, label="play Strike"):
    return {"observation": {"turn": turn, "hp": hp, "floor": floor}, "label": label}


def test_spans_split_at_the_end_of_a_fight_and_at_a_new_floor():
    steps = [step(0, 80), step(1, 80), step(1, 75), step(0, 75), step(1, 75, floor=4),
             step(2, 70, floor=4), step(1, 70, floor=5)]
    assert rewards.fight_spans(steps) == [(1, 3), (4, 6), (6, 7)]


def test_hp_lost_in_a_won_fight_runs_up_to_the_first_step_after_it():
    steps = [step(1, 60), step(1, 54, label="use potion Block Potion"), step(0, 48)]
    values = rewards.fight_rewards(steps, 0, 2, "lost", CONFIG)
    assert values == [-0.2, -0.2 - 0.1]


def test_dying_costs_the_hp_left_and_the_death_penalty():
    steps = [step(1, 15), step(1, 6)]
    values = rewards.fight_rewards(steps, 0, 2, "lost", CONFIG)
    assert values == [-0.3, -0.2 - 2.0]


def test_a_truncated_fight_has_no_ending_reward():
    assert rewards.fight_rewards([step(1, 15)], 0, 1, "truncated", CONFIG) == [0.0]


def test_a_potion_costs_only_in_an_ordinary_room_and_dying_with_one_costs_more():
    config = {**CONFIG, "fight_wasted": 0.5}

    def fight(room, label):
        return [{"observation": {"hp": 30, "room": room, "potions": 2, "turn": 1},
                 "label": label},
                {"observation": {"hp": 30, "room": room, "potions": 1, "turn": 1},
                 "label": "end turn"}]

    used = "use potion Fire Potion"
    ordinary = rewards.fight_rewards(fight("MonsterRoom", used), 0, 2, "lost", config)
    boss = rewards.fight_rewards(fight("MonsterRoomBoss", used), 0, 2, "lost", config)
    assert ordinary[0] == -0.1 and boss[0] == 0.0
    assert boss[1] == -1.0 - 2.0 - 0.5  # 30 HP lost, the death, one potion unused
