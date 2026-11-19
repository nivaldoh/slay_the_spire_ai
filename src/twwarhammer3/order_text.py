"""Order, plan and army descriptions shared by model prompts and job readers."""

import json
import re

from twwarhammer3.protocol import SIEGE_ORDER_TYPES

REPORT_HEADER = "Dropped or rejected since your last plan:\n"


def short_type(key: str) -> str:
    """``wh3_main_kho_inf_chaos_warriors_0`` -> ``chaos_warriors_0``."""
    return re.sub(r"^wh\d?_[a-z0-9]+_[a-z]{3}_[a-z]{3}_", "", key or "?")


def describe_dropped(order) -> str:
    try:
        return describe_orders([order])
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):  # off the schema
        return json.dumps(order)


def describe_orders(orders: list[dict]) -> str:
    if not orders:
        return "no new orders"
    parts = []
    for order in orders:
        run = " run" if order.get("run") else ""
        if order["type"] == "move":
            facing = order.get("facing")
            parts.append(f"{order['unit']} move ({order['x']:.0f}, {order['z']:.0f})"
                         + (f" facing {facing:.0f}" if facing is not None else "")
                         + (f" width {order['width']:.0f}" if order.get("width") else "") + run)
        elif order["type"] == "attack":
            mode = "" if order.get("mode", "auto") == "auto" else f" {order['mode']}"
            parts.append(f"{order['unit']} attack {order['target']}{mode}{run}")
        elif order["type"] == "behaviour":
            parts.append(f"{order['unit']} {order['behaviour']} "
                         + ("on" if order["enabled"] else "off"))
        elif order["type"] == "flight":
            parts.append(f"{order['unit']} " + ("take off" if order["flying"] else "land"))
        elif order["type"] == "ability":
            target = order.get("target") or "self"
            if order.get("x") is not None and order.get("z") is not None:
                target = f"({order['x']:.0f}, {order['z']:.0f})"
            parts.append(f"{order['unit']} ability {order['ability']} at {target}")
        elif order["type"] == "build":
            parts.append(f"{order['unit']} build {order['option']} on {order['slot']}")
        elif order["type"] == "reinforce":
            parts.append(f"{order['unit']} reinforce {short_type(order['reinforcement'])}"
                         f" at zone {order['zone']}")
        elif order["type"] in SIEGE_ORDER_TYPES:
            verb = "besiege" if order["type"] == "besiege" else "attack building"
            parts.append(f"{order['unit']} {verb} {order['target']}{run}")
        else:
            parts.append(f"{order['unit']} halt")
        if order.get("queue"):
            parts[-1] += " [queued]"
    return ", ".join(parts)


def describe_assignment(item: dict) -> str:
    text = f"{item['unit']} {item['skill']}"
    if item.get("target"):
        text += f" {item['target']}"
    if item.get("x") is not None and item.get("z") is not None:
        text += f" ({item['x']:.0f}, {item['z']:.0f})"
    return text


def describe_plan(assignments: list[dict]) -> str:
    return "; ".join(describe_assignment(item) for item in assignments) or "no changes"


def strength(observation: dict) -> str:
    friendly = [u for u in observation.get("friendly", []) if u.get("men")]
    fighting = [u for u in friendly if not {"routing", "shattered"} & set(u.get("state", []))]
    enemy = observation.get("enemy", [])
    roster = len(observation.get("enemy_roster", []))
    return (f"us {len(fighting)}/{len(friendly)}u {sum(u['men'] for u in friendly)}m"
            f"  seen {len(enemy)}/{roster}u {sum(u.get('men', 0) for u in enemy)}m")
