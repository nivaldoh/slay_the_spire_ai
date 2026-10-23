"""Shared synthetic CommunicationMod messages for Spire tests."""


def card(card_id, name=None, cost=1, kind="ATTACK", target=True, playable=True, uuid="u"):
    return {"id": card_id, "name": name or card_id, "cost": cost, "type": kind,
            "has_target": target, "is_playable": playable, "uuid": uuid, "upgrades": 0}


def message(commands, **game):
    state = {"act": 1, "floor": 3, "current_hp": 70, "max_hp": 80, "gold": 99, "seed": 123,
             "relics": [], "potions": [], "deck": [], "screen_type": "NONE", **game}
    return {"ready_for_command": True, "in_game": True, "available_commands": commands,
            "game_state": state}


def combat_message(**combat):
    monsters = [
        {"name": "Louse", "id": "FuzzyLouseNormal", "current_hp": 0, "max_hp": 12,
         "is_gone": True, "half_dead": False, "intent": "NONE", "powers": []},
        {"name": "Jaw Worm", "id": "JawWorm", "current_hp": 30, "max_hp": 44, "block": 0,
         "is_gone": False, "half_dead": False, "intent": "ATTACK", "move_id": 1,
         "move_base_damage": 11, "move_adjusted_damage": 11, "move_hits": 1,
         "powers": [{"id": "Strength", "name": "Strength", "amount": 3, "misc": 9}]},
    ]
    state = {
        "turn": 2, "monsters": monsters,
        "player": {"current_hp": 70, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
        "hand": [card("Strike_R", "Strike", uuid="a"), card("Strike_R", "Strike", uuid="b"),
                 card("Defend_R", "Defend", kind="SKILL", target=False),
                 card("Bash", cost=2, playable=False)],
        "draw_pile": [card("Bash", cost=2, uuid="z"), card("Anger", cost=0, uuid="y")],
        "discard_pile": [], "exhaust_pile": [], **combat,
    }
    potions = [
        {"id": "Fire Potion", "name": "Fire Potion", "can_use": True, "can_discard": True,
         "requires_target": True},
        {"id": "Potion Slot", "name": "Potion Slot", "can_use": False, "can_discard": False},
    ]
    return message(["play", "end", "potion", "key", "click", "wait", "state"],
                   room_phase="COMBAT", combat_state=state, potions=potions)
