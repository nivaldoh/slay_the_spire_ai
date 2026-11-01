"""Compose interchangeable controllers from JSON using the existing team dispatcher."""

import json
from copy import deepcopy
from functools import partial
from pathlib import Path
from threading import Event

from gameai.ledger import Ledger
from gameai.llm import APIError, Model, api_key, post
from gameai.providers import get_provider, routing, validate
from twwarhammer3.battle import graph, graph_goals, team


def load(path, config):
    """Resolve and validate data without credentials, budgets, models or game access."""
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
    leaves, goal_models = set(), set()

    def prepare(node):
        if not isinstance(node, dict) or not isinstance(node.get("type"), str):
            raise ValueError("controller needs a type")
        kind = node["type"]
        if kind in ("graph", "graph_llm"):
            allowed = {"type", "graph"}
            if kind == "graph_llm":
                allowed |= {"model", "effort", "task", "max_requests"}
            if set(node) - allowed or not {"type", "graph"} <= set(node):
                raise ValueError("graph controller needs type and graph")
            value = node["graph"]
            if isinstance(value, str):
                value = json.loads((path.parent / value).read_text())
            result = {"type": kind, "graph": graph.validate(value)}
            if kind == "graph_llm":
                graph_goals.validate_graph(value)
                provider = config.get("provider", "openai")
                model = node.get("model", config.get("model")
                                 or next(iter(get_provider(provider).prices)))
                effort = node.get("effort", config.get("effort") or "low")
                if not isinstance(model, str) or not isinstance(effort, str):
                    raise ValueError("goal model and effort must be text")
                validate(provider, model, effort)
                limit = node.get("max_requests")
                if limit is not None and (type(limit) is not int or limit <= 0):
                    raise ValueError("max_requests must be positive or null")
                if not isinstance(node.get("task", ""), str):
                    raise ValueError("goal task must be text")
                result.update(model=model, effort=effort, task=node.get("task", ""),
                              max_requests=limit)
                goal_models.add((model, effort))
            return result
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
    config["controller_spec"] = deepcopy(frozen)
    return frozen, leaves, goal_models, artifact


def factory(path, config, *, ledger=None):
    from twwarhammer3.battle import controllers

    frozen, leaves, goal_models, artifact = load(path, config)
    models = {name for name in leaves
              if controllers.policy_parts(name, config)[0] in controllers.MODEL_POLICIES}
    provider = config.get("provider", "openai")
    if models or goal_models:
        if config.get("budget_usd") is None:
            raise ValueError("model controllers require --budget-usd")
        if provider == "openrouter" and config["budget_usd"] > 50:
            raise ValueError("OpenRouter's cumulative budget cannot exceed $50")
        if ledger is None:
            ledger = Ledger(Path(config["ledger"]), config["budget_usd"], must_exist=True)
    makers = controllers.factories({**config, "policy": ",".join(sorted(leaves))},
                                   _ledger=ledger) if leaves else {}
    prompts = {
        name: controllers.MODEL_PROMPTS[controllers.policy_parts(name, config)[0]].read_text()
        for name in sorted(models)}
    goal_send = None
    if goal_models:
        goal_send = partial(post, api_key(provider), attempts=1, provider=provider,
                            record_transport=True, timeout_s=graph_goals.READ_TIMEOUT_S)
        prompts.update({f"graph_llm@{model}/{effort}": graph_goals.PROMPT_PATH.read_text()
                        for model, effort in sorted(goal_models)})
        config.setdefault("model_routing", {}).update({
            model: routing(provider, model) for model, _ in goal_models})

    def build(node, stop=None):
        kind = node["type"]
        if kind == "graph":
            return graph.GraphPolicy(node["graph"])
        if kind == "graph_llm":
            api = Model(node["model"], node["effort"], ledger, send=goal_send, provider=provider,
                        instructions=prompts[f"graph_llm@{node['model']}/{node['effort']}"],
                        max_output_tokens=graph_goals.MAX_OUTPUT_TOKENS, record_exchanges=True)
            return graph_goals.GraphGoals(node["graph"], api, task=node["task"], stop=stop,
                                          max_requests=node["max_requests"])
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
        policy.card["paid_calls"] = bool(models or goal_models)
        policy.card["model_prompts"] = deepcopy(prompts)
        if artifact is not None:
            policy.card["artifact"] = dict(artifact)
        return policy

    return make
