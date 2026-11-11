"""Small graph inputs shared by graph, composition and team tests."""

from twwarhammer3.battle import graph


def move_graph():
    return {"version": graph.VERSION, "entry": "move", "nodes": {
        "move": {"op": "move", "inputs": {"units": ["u"], "point": {"x": 20, "z": 0}},
                 "next": {"succeeded": "end", "failed": "end", "cancelled": "end"}},
        "end": {"op": "end", "inputs": {}, "next": {}}}}


def attack_graph(op="engage"):
    return {"version": graph.VERSION, "entry": "owned", "nodes": {
        "owned": {"op": "owned", "inputs": {},
                  "next": {"succeeded": "pick", "empty": "owned"}},
        "pick": {"op": "select_target", "inputs": {"units": {"ref": "owned.units"}},
                 "next": {"succeeded": "act", "empty": "owned"}},
        "act": {"op": op, "inputs": {"units": {"ref": "owned.units"},
                                       "target": {"ref": "pick.target"}},
                "next": {"succeeded": "owned", "failed": "owned", "cancelled": "owned"}}}}
