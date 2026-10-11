"""Public transit choices for one fixed, starter-only two-combat segment."""

from collections import Counter
from collections.abc import Mapping

from spire.protocol import (
    IllegalActionError,
    NotReadyError,
    StaleActionError,
    UnsupportedStateError,
)

GAME_SEED = "SPIREAI1"
INITIAL_START_SHA256 = "177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4"
TRANSIT_VERSION = "ironclad-two-combat-transit-v1"


def require(condition, message):
    if not condition:
        raise UnsupportedStateError(message)


def persistent_state(raw):
    """Keep only persistent public fields; reject all unimplemented loadouts."""
    require(raw.get("in_game") is True, "Continuation requires an active game")
    game = raw["game_state"]
    require(
        game.get("class") == "IRONCLAD"
        and game.get("ascension_level") == 0
        and game.get("act") == 1,
        "Continuation requires Ironclad A0 Act 1",
    )
    hp, maximum, gold = (game.get(key) for key in ("current_hp", "max_hp", "gold"))
    require(
        type(hp) is int and type(maximum) is int and maximum == 80 and 0 <= hp <= 80,
        "Continuation requires valid HP with maximum 80",
    )
    require(type(gold) is int and gold >= 0, "Invalid public gold")
    cards = game.get("deck", [])
    require(
        all(card.get("upgrades") == 0 and card.get("misc", 0) == 0 for card in cards)
        and Counter(card.get("id") for card in cards)
        == Counter({"Strike_R": 5, "Defend_R": 4, "Bash": 1}),
        "Continuation requires the unchanged unupgraded starter deck",
    )
    relics = game.get("relics", [])
    require(
        len(relics) == 1
        and relics[0].get("id") == "Burning Blood"
        and relics[0].get("counter") == -1,
        "Only unchanged Burning Blood is supported",
    )
    potions = game.get("potions", [])
    require(
        len(potions) == 3 and all(p.get("id") == "Potion Slot" for p in potions),
        "Potions must remain three empty slots",
    )
    return {
        "current_hp": hp,
        "max_hp": maximum,
        "gold": gold,
        "deck": sorted(card["id"] for card in cards),
        "relics": [{"id": "Burning Blood", "counter": -1}],
        "potions": ["Potion Slot"] * 3,
    }


def validate_combat(raw):
    persistent_state(raw)
    game = raw["game_state"]
    require(
        game.get("floor") in (1, 2)
        and game.get("room_type") == "MonsterRoom"
        and game.get("room_phase") == "COMBAT"
        and game.get("screen_type") == "NONE",
        "Only ordinary first/second-floor combat is supported",
    )
    ids = [m.get("id") for m in game.get("combat_state", {}).get("monsters", [])]
    require(
        ids in (["Cultist"], ["JawWorm"])
        or (len(ids) == 2 and set(ids) <= {"FuzzyLouseNormal", "FuzzyLouseDefensive"}),
        f"Unsupported continuation encounter: {ids}",
    )


def _rewards(game):
    rewards = []
    for item in game.get("screen_state", {}).get("rewards", []):
        kind = item.get("reward_type")
        require(kind in {"GOLD", "CARD", "POTION", "RELIC"}, "Unsupported reward type")
        public = {"reward_type": kind}
        if kind == "GOLD":
            require(type(item.get("gold")) is int and item["gold"] > 0, "Invalid GOLD amount")
            public["gold"] = item["gold"]
        if kind in {"POTION", "RELIC"}:
            require(isinstance(item.get(kind.lower()), Mapping), "Reward lacks public identity")
            public[kind.lower()] = {"id": item[kind.lower()]["id"]}
        rewards.append(public)
    require(
        game.get("choice_list", []) == [r["reward_type"].lower() for r in rewards],
        "Reward list and CHOOSE ordinals disagree",
    )
    return rewards


def transit_decision(raw, *, session_id, sequence):
    if raw.get("ready_for_command") is not True:
        raise NotReadyError("Transit requires a stable ready observation")
    require(
        isinstance(session_id, str) and session_id and type(sequence) is int and sequence > 0,
        "Invalid transit decision identity",
    )
    public = persistent_state(raw)
    game = raw["game_state"]
    require(
        game.get("floor") == 1
        and game.get("room_phase") == "COMPLETE"
        and game.get("room_type") == "MonsterRoom",
        "Transit must follow combat one",
    )
    commands = raw.get("available_commands", [])
    screen = game.get("screen_type")
    decision_id = f"{session_id}:{sequence}"
    public.update(
        contract=TRANSIT_VERSION,
        screen_type=screen,
        floor=1,
        act=1,
        excluded_actions=["card_rewards", "potions", "relic_rewards", "other_routes"],
    )
    candidates = []

    def candidate(kind, command, index=None, choice=None):
        candidates.append(
            {
                "id": f"{decision_id}:{kind}:{index}",
                "decision_id": decision_id,
                "kind": kind,
                "command": command,
                "index": index,
                "choice": choice,
            }
        )

    if screen == "COMBAT_REWARD":
        public["rewards"] = _rewards(game)
        for index, reward in enumerate(public["rewards"]):
            if reward["reward_type"] == "GOLD":
                require("choose" in commands, "GOLD choice is unavailable")
                candidate("gold", f"CHOOSE {index}", index, reward)
        require("proceed" in commands, "Reward PROCEED is unavailable")
        candidate("proceed", "PROCEED")
    elif screen == "MAP":
        screen_state = game.get("screen_state", {})
        current = screen_state.get("current_node", {})
        require(
            current.get("x") == 0
            and current.get("y") == 0
            and screen_state.get("boss_available") is False
            and screen_state.get("first_node_chosen") is True,
            "MAP must be at the declared first node",
        )
        nodes = [
            {key: node.get(key) for key in ("x", "y", "symbol")}
            for node in screen_state.get("next_nodes", [])
        ]
        require(
            game.get("choice_list") == [f"x={node['x']}" for node in nodes],
            "MAP choices and next-node ordinals disagree",
        )
        matches = [
            (index, node)
            for index, node in enumerate(nodes)
            if node == {"x": 1, "y": 1, "symbol": "M"}
        ]
        require(len(matches) == 1 and "choose" in commands, "Canonical next combat is unavailable")
        public.update(current_node={"x": 0, "y": 0}, next_nodes=nodes)
        index, node = matches[0]
        candidate("map", f"CHOOSE {index}", index, node)
    else:
        raise UnsupportedStateError(f"Unsupported continuation screen: {screen}")
    return {"id": decision_id, "observation": public, "candidates": candidates}


def choose_transit(decision):
    """The disclosed controller takes gold first, then follows its one fixed edge."""
    return next(
        (action for action in decision["candidates"] if action["kind"] == "gold"),
        decision["candidates"][-1],
    )


def validate_transit_action(decision, action):
    identity = action.get("id") if isinstance(action, dict) else action
    if not isinstance(identity, str) or not identity.startswith(decision["id"] + ":"):
        raise StaleActionError("Transit action belongs to another observation")
    for candidate in decision["candidates"]:
        if candidate["id"] == identity:
            if isinstance(action, dict) and action != candidate:
                raise IllegalActionError("Transit action differs from its current candidate")
            return candidate
    raise IllegalActionError("Transit action is not a permitted current candidate")
