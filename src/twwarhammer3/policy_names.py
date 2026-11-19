"""Policy names stored in WH3 jobs and results."""

MODEL_POLICIES = frozenset({"llm", "llm_rules", "commander", "team_llm_rules"})


def policy_parts(name: str, config: dict) -> tuple[str, str | None, str | None]:
    """A policy name's base name and the model and effort it plays with: a model policy's
    ``@MODEL[/EFFORT]`` suffix, else the job's; None for other policies. Readers of recorded
    jobs use it too, so only rotation and factories check the suffix against today's prices."""
    base, separator, suffix = name.partition("@")
    if base not in MODEL_POLICIES:
        if separator:
            raise ValueError(f"{name}: only {', '.join(sorted(MODEL_POLICIES))} take @MODEL")
        return name, None, None
    # OpenRouter IDs already contain a slash (vendor/model); effort is the final suffix.
    model, effort = suffix, ""
    if suffix.count("/") > (1 if config.get("provider") == "openrouter" else 0):
        model, _, effort = suffix.rpartition("/")
    return base, model or config.get("model"), effort or config.get("effort")
