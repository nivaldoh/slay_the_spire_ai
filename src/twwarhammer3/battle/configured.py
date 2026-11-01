"""Compose interchangeable controllers from JSON using the existing team dispatcher."""

import json
from copy import deepcopy
from pathlib import Path
from threading import Event

from gameai.llm import APIError
from twwarhammer3.battle import graph, team


def factory(path, config, *, ledger=None):
    from twwarhammer3.battle import controllers

    path = Path(path).resolve()
    artifact = None
    manifest = path / "manifest.json" if path.is_dir() else path.parent / "manifest.json"
    if path.is_dir() and not manifest.is_file():
        raise ValueError("controller artifact needs manifest.json")
    if (path.is_dir() or path.name == "controller.json") and manifest.is_file():
        from twwarhammer3.battle import graph_author

        metadata = json.loads(manifest.read_text())
        if (path.is_dir() or metadata.get("artifact_type") == graph_author.ARTIFACT_TYPE
                or str(metadata.get("version", "")).startswith(f"{graph_author.ARTIFACT_TYPE}-")):
            spec, artifact = graph_author.load_artifact(manifest.parent)
            path = manifest.parent / "controller.json"
        else:
            spec = json.loads(path.read_text())
    else:
        spec = json.loads(path.read_text())
    leaves = set()

    def prepare(node):
        if not isinstance(node, dict) or not isinstance(node.get("type"), str):
            raise ValueError("controller needs a type")
        kind = node["type"]
        if kind == "graph":
            if set(node) != {"type", "graph"}:
                raise ValueError("graph controller needs type and graph")
            value = node["graph"]
            if isinstance(value, str):
                value = json.loads((path.parent / value).read_text())
            return {"type": kind, "graph": graph.validate(value)}
        if kind == "team":
            if set(node) - {"type", "members", "army_owner", "max_age_ms"}:
                raise ValueError("unknown team settings")
            members = node.get("members")
            if not isinstance(members, dict) or len(members) != 2:
                raise ValueError("configured team needs exactly two members")
            result = {"type": kind, "members": {}, "army_owner": node.get("army_owner"),
                      "max_age_ms": node.get("max_age_ms", graph.MAX_AGE_MS)}
            age = result["max_age_ms"]
            if age is not None and (type(age) is not int or age <= 0):
                raise ValueError("max_age_ms must be positive or null")
            kinds, rests = set(), 0
            for name, member in members.items():
                if not isinstance(member, dict) or set(member) != {"unit_types", "controller"}:
                    raise ValueError("member needs unit_types and controller")
                unit_types = member["unit_types"]
                if unit_types is None:
                    rests += 1
                elif (not isinstance(unit_types, list) or not unit_types
                      or any(not isinstance(t, str) or not t for t in unit_types)
                      or len(set(unit_types)) != len(unit_types) or kinds.intersection(unit_types)):
                    raise ValueError("members need distinct unit_types")
                else:
                    kinds.update(unit_types)
                controller = member["controller"]
                if isinstance(controller, dict) and controller.get("type") == "team":
                    raise ValueError("nested teams are not supported")
                result["members"][name] = {"unit_types": unit_types,
                                            "controller": prepare(controller)}
            if rests > 1 or result["army_owner"] not in (None, *members):
                raise ValueError("invalid army owner or multiple rest members")
            return result
        if kind == "configured" or "," in kind or set(node) != {"type"}:
            raise ValueError("leaf controller needs only a built-in name or module:Class type")
        # All direct model leaves share one normal factory preparation and ledger.
        controllers.rotation({**config, "policy": kind, "episodes": None,
                              "delay_seconds": "0", "rotation_seed": 0})
        leaves.add(kind)
        return {"type": kind}

    frozen = prepare(spec)
    makers = controllers.factories({**config, "policy": ",".join(sorted(leaves))},
                                   _ledger=ledger) if leaves else {}
    config["controller_spec"] = deepcopy(frozen)
    models = {name for name in leaves
              if controllers.policy_parts(name, config)[0] in controllers.MODEL_POLICIES}
    prompts = {
        name: controllers.MODEL_PROMPTS[controllers.policy_parts(name, config)[0]].read_text()
        for name in sorted(models)}

    def build(node, stop=None):
        kind = node["type"]
        if kind == "graph":
            return graph.GraphPolicy(node["graph"])
        if kind == "team":
            stop = Event()
            return team.TeamPolicy({name: (tuple(member["unit_types"]) if member["unit_types"]
                                           is not None else None, build(member["controller"], stop))
                                    for name, member in node["members"].items()},
                                   stop=stop, army_owner=node["army_owner"],
                                   max_age_ms=node["max_age_ms"])
        policy = makers[kind]()
        if stop is not None and isinstance(policy, team.TeamPolicy):
            policy.close()
            raise ValueError("nested teams are not supported")
        api = getattr(policy, "api", None)
        if stop is not None and api is not None:
            send = api.send

            def guarded(body):
                if stop.is_set():
                    raise APIError("team closed; request not sent")
                return send(body)

            api.send = guarded
        return policy

    def make():
        policy = build(frozen)
        policy.card = {**getattr(policy, "card", {}), "configuration": deepcopy(frozen),
                       "configuration_sha256": graph.digest(frozen)}
        if isinstance(policy, team.TeamPolicy):
            policy.card["member_controllers"] = {
                name: controllers.card(frozen["members"][name]["controller"]["type"],
                                       member.policy, config)
                for name, member in policy.members.items()}
        policy.card["paid_calls"] = bool(models)
        policy.card["model_prompts"] = deepcopy(prompts)
        if artifact is not None:
            policy.card["artifact"] = dict(artifact)
        return policy

    return make
