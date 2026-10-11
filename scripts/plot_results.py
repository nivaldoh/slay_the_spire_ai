"""Render saved single-scenario reports and PPO diagnostics without loading models."""

import argparse
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_data(comparison_path, distribution_path, gradients_path):
    paths = [comparison_path, distribution_path, gradients_path]
    comparison, distribution, gradients = [json.loads(path.read_text()) for path in paths]
    require(
        comparison["valid"] is True and comparison["same_protocol"] is True,
        "comparison must be valid and use one protocol",
    )
    runs, contracts = comparison["runs"], comparison["comparison_contracts"]
    require(runs and len(contracts) == len(runs), "missing comparison contracts")
    require(all(contract == contracts[0] for contract in contracts), "mixed protocols")
    contract = contracts[0]
    config = contract["config"]
    require(
        config["game_seed"] == "SPIREAI1"
        and config["expected_start_sha256"]
        == "177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4",
        "figure is scoped to the frozen Louse development scenario",
    )
    count = config["episodes"]
    require(type(count) is int and count > 1, "need at least two scheduled episodes")
    series = []
    for run in runs:
        provenance, metrics = run["provenance"], run["metrics"]
        episodes = sorted(run["episodes"], key=lambda item: item["episode"])
        require(
            run["valid"] is True and provenance["status"] == "completed",
            "incomplete or invalid run cannot appear on a complete-score chart",
        )
        require(len(episodes) == metrics["attempts"] == count, "missing scheduled attempts")
        require(
            [item["episode"] for item in episodes] == list(range(count)),
            "duplicate or missing episode IDs",
        )
        require(
            all(provenance["config"][key] == value for key, value in config.items()),
            "run configuration differs from comparison contract",
        )
        require(
            all(
                item["valid"] is True
                and item["status"] in {"won", "lost"}
                and item["combat_start_sha256"] == config["expected_start_sha256"]
                for item in episodes
            ),
            "non-gameplay result or different start",
        )
        hp = [item["ending_hp"] for item in episodes]
        require(
            all(
                type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in hp
            ),
            "invalid terminal HP",
        )
        require(
            all(item["starting_hp"] == 80 for item in episodes),
            "this figure is scoped to the 80-HP starter diagnostic",
        )
        mean_hp = statistics.mean(hp)
        require(
            math.isclose(mean_hp, metrics["mean_ending_hp"], abs_tol=1e-9),
            "reported mean disagrees with episode points",
        )
        require(
            metrics["wins"] == sum(item["status"] == "won" for item in episodes)
            and metrics["losses"] == sum(item["status"] == "lost" for item in episodes)
            and metrics["wins"] + metrics["losses"] == count,
            "outcome counts disagree with episodes",
        )
        require(
            all(
                metrics.get(key, 0) == 0
                for key in (
                    "infrastructure_failures",
                    "unsupported",
                    "invalid_actions",
                    "truncated",
                    "interrupted",
                    "invalid_evidence",
                    "policy_failures",
                )
            ),
            "failure counts must not disappear from a complete-score chart",
        )
        artifact = provenance["config"].get("policy_artifact", {})
        policy = provenance["config"]["policy"]
        label = {"random": "Random", "heuristic": "Heuristic"}.get(policy)
        if policy == "neural":
            label = (
                "Initial NN" if artifact["updates"] == 0 else f"PPO: {artifact['updates']} updates"
            )
        require(label is not None, "unsupported policy label; extend explicitly before plotting")
        series.append(
            {
                "label": label,
                "directory": run["directory"],
                "policy": policy,
                "source_revision": provenance["source_revision"],
                "artifact": artifact,
                "policy_seeds": [config["policy_seed"] + item["episode"] for item in episodes],
                "ending_hp": hp,
                "mean_ending_hp": mean_hp,
                "wins": metrics["wins"],
            }
        )
    require(len({item["directory"] for item in series}) == len(series), "duplicate run")
    neural = [item for item in series if item["policy"] == "neural"]
    initial = [item for item in neural if item["artifact"]["updates"] == 0]
    require(len(initial) == 1, "need exactly one initial neural policy for paired differences")
    require(
        initial[0]["artifact"]["model_sha256"] == distribution["initial_model_sha256"],
        "distribution diagnostic belongs to a different initial model",
    )
    final = [
        item
        for item in neural
        if item["artifact"]["model_sha256"] == distribution["final_model_sha256"]
    ]
    require(len(final) == 1, "distribution final model is absent from comparison")
    rows = gradients["updates"]
    require(
        [row["update"] for row in rows] == list(range(1, len(rows) + 1))
        and len(rows) == final[0]["artifact"]["updates"],
        "gradient update count mismatch",
    )
    require(
        Path(gradients["run"]).name == Path(final[0]["artifact"]["path"]).parents[1].name,
        "gradient diagnostic belongs to a different training run",
    )
    for row in rows:
        values = [
            row["logged"]["approx_kl"],
            row["actual_update_kl"]["mean"],
            *(
                row["gradient_norms"][term]["all"]
                for term in ("policy", "weighted_value", "weighted_entropy")
            ),
        ]
        require(
            all(math.isfinite(value) and value > 0 for value in values),
            "log plots require finite positive diagnostic values",
        )
    require(
        all(
            math.isfinite(distribution[key]) and 0 <= distribution[key] <= 1
            for key in ("mean_total_variation", "mean_final_entropy_fraction")
        ),
        "invalid distribution diagnostic",
    )
    paired = [
        {
            "label": item["label"],
            "policy_seeds": item["policy_seeds"],
            "hp_difference": [b - a for a, b in zip(initial[0]["ending_hp"], item["ending_hp"])],
        }
        for item in neural
        if item is not initial[0]
    ]
    require(paired, "need a trained neural policy for paired differences")
    return {
        "schema_version": 1,
        "scope": (
            f"{count} policy samples on one fixed development scenario; "
            "not independent game scenarios"
        ),
        "comparison_contract": contract,
        "series": series,
        "paired_neural": paired,
        "distribution": {
            key: value
            for key, value in distribution.items()
            if key not in {"largest_changes", "source_evidence_sha256"}
        },
        "gradients": {
            "scope": gradients["scope"],
            "training_episodes": sum(row["episodes"] for row in rows),
            "transitions": sum(row["transitions"] for row in rows),
            "training_source_revision": gradients["training_source_revision"],
            "config": gradients["saved_optimizer_config"],
            "updates": [
                {
                    "update": row["update"],
                    "gradient_norms": row["gradient_norms"],
                    "logged_approx_kl": row["logged"]["approx_kl"],
                    "full_batch_kl": row["actual_update_kl"]["mean"],
                }
                for row in rows
            ],
        },
        "input_sha256": {str(path): sha256(path) for path in paths},
        "script_sha256": sha256(Path(__file__)),
    }


def render(data, output, png_directory=None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    matplotlib.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "spire-plots-v1",
            "axes.titleweight": "bold",
            "axes.labelcolor": "#253044",
            "text.color": "#253044",
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    if png_directory:
        png_directory.mkdir(parents=True, exist_ok=True)
    data["render_environment"] = {
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "backend": "Agg",
        "font": "DejaVu Sans",
        "freetype": matplotlib.ft2font.__freetype_version__,
    }

    def save(figure, name):
        figure.savefig(
            output / f"{name}.svg", metadata={"Date": None, "Creator": "plot_results.py"}
        )
        if png_directory:
            figure.savefig(
                png_directory / f"{name}.png", dpi=180, metadata={"Software": "plot_results.py"}
            )
        plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(11.8, 5.2), gridspec_kw={"width_ratios": [1.4, 1]})
    figure.subplots_adjust(left=0.07, right=0.97, top=0.76, bottom=0.23, wspace=0.26)
    figure.suptitle("Fixed-Louse development evaluation", x=0.07, y=0.96, ha="left", fontsize=17)
    figure.text(0.07, 0.89, data["scope"], fontsize=10)
    colors = ["#78909C", "#168A7D", "#5178AF", "#735EAD", "#D87A26"]
    for index, item in enumerate(data["series"]):
        count = len(item["ending_hp"])
        offsets = [(j - (count - 1) / 2) * 0.05 for j in range(count)]
        axes[0].scatter(
            [index + offset for offset in offsets],
            item["ending_hp"],
            color=colors[index % len(colors)],
            s=28,
            alpha=0.85,
            zorder=3,
        )
        axes[0].hlines(
            item["mean_ending_hp"],
            index - 0.28,
            index + 0.28,
            color="#172B4D",
            linewidth=2.2,
            zorder=4,
        )
        axes[0].text(index, 86, f"{item['mean_ending_hp']:.2f}", ha="center", fontsize=10)
    axes[0].set(
        title="Episode points and means",
        ylabel="Terminal HP (includes Burning Blood)",
        ylim=(0, 92),
        yticks=range(0, 81, 20),
    )
    axes[0].set_xticks(
        range(len(data["series"])),
        [item["label"].replace(": ", "\n") for item in data["series"]],
        fontsize=9,
    )
    axes[0].grid(axis="y", color="#E3E8EF", linewidth=0.7)
    axes[0].legend(
        handles=[Line2D([0], [0], color="#172B4D", lw=2, label="Mean (number above)")],
        loc="lower left",
        frameon=False,
        fontsize=9,
    )
    for index, item in enumerate(data["paired_neural"]):
        positions = [seed + (index - 0.5) * 0.14 for seed in item["policy_seeds"]]
        axes[1].scatter(
            positions,
            item["hp_difference"],
            label=item["label"],
            s=42,
            marker=["o", "D"][index % 2],
            color=colors[(index + 3) % len(colors)],
            zorder=3,
        )
    axes[1].axhline(0, color="#9EAAB8", lw=1)
    axes[1].set(
        title="Paired neural-policy differences",
        ylabel="Terminal HP minus initial NN",
        xlabel="Policy sampling seed",
    )
    axes[1].set_xticks(
        data["series"][0]["policy_seeds"],
        data["series"][0]["policy_seeds"],
        rotation=45,
        fontsize=9,
    )
    axes[1].set_ylim(min(min(item["hp_difference"]) for item in data["paired_neural"]) - 2, 3)
    axes[1].legend(loc="lower left", frameon=False, fontsize=9)
    wins = [f"{item['wins']}/{len(item['ending_hp'])}" for item in data["series"]]
    figure.text(
        0.07, 0.09, "Wins in displayed order: " + ", ".join(wins) + ". No error bars.", fontsize=9
    )
    figure.text(
        0.07,
        0.045,
        "Heuristic repeats are deterministic. Neural artifacts share one initialization; "
        "paired seeds are not independent training replications.",
        fontsize=9,
    )
    save(figure, "fixed-louse-hp")

    figure, axes = plt.subplots(1, 2, figsize=(11.8, 5.3))
    figure.subplots_adjust(left=0.085, right=0.97, top=0.73, bottom=0.22, wspace=0.28)
    figure.suptitle(
        "PPO diagnostic: action probabilities remain close to uniform",
        x=0.07,
        y=0.96,
        ha="left",
        fontsize=16,
    )
    distribution = data["distribution"]
    figure.text(
        0.07,
        0.885,
        f"On {distribution['states']} saved public states: mean total variation "
        f"{distribution['mean_total_variation']:.4f}; final entropy "
        f"{100 * distribution['mean_final_entropy_fraction']:.3f}% of maximum.",
        fontsize=11,
    )
    figure.text(
        0.07,
        0.835,
        "Correlated trajectory states on the same development scenario; "
        "probability movement does not establish better play.",
        fontsize=9,
    )
    rows = data["gradients"]["updates"]
    updates = [row["update"] for row in rows]
    axes[0].plot(
        updates,
        [row["full_batch_kl"] for row in rows],
        "o-",
        color="#5178AF",
        label="Full batch: before vs after update",
        markersize=4,
    )
    axes[0].plot(
        updates,
        [row["logged_approx_kl"] for row in rows],
        "s--",
        color="#168A7D",
        label="Logged mean minibatch approximation",
        markersize=4,
    )
    axes[0].axhline(
        data["gradients"]["config"]["target_kl"],
        color="#C15F43",
        ls=":",
        label="Configured minibatch KL stop threshold",
    )
    axes[0].set(
        title="Small policy movement per update", ylabel="KL divergence (log scale)", yscale="log"
    )
    config = data["gradients"]["config"]
    for key, label, color in (
        ("policy", "Policy loss", "#5178AF"),
        ("weighted_value", f"Value loss × {config['value_coef']}", "#D87A26"),
        ("weighted_entropy", f"Entropy term × {config['entropy_coef']}", "#168A7D"),
    ):
        axes[1].plot(
            updates,
            [row["gradient_norms"][key]["all"] for row in rows],
            "o-",
            label=label,
            color=color,
            markersize=4,
        )
    axes[1].set(
        title="Full-batch gradients at pre-update weights",
        ylabel="Gradient L2 norm (log scale)",
        yscale="log",
    )
    for axis in axes:
        axis.set(xlabel="Committed PPO update", xticks=updates)
        axis.grid(axis="y", color="#E3E8EF", linewidth=0.7)
        axis.legend(fontsize=8, frameon=False, loc="lower right")
    figure.text(
        0.07,
        0.09,
        "Saved-checkpoint CPU diagnostic; not actual optimizer minibatch gradients. "
        "Adam rescales gradients, so these norms do not determine step size.",
        fontsize=9,
    )
    figure.text(
        0.07, 0.045,
        f"Gradients: {data['gradients']['training_episodes']} training combats, "
        f"{data['gradients']['transitions']} transitions. One fixed development scenario; "
        "no causal or statistical-significance claim.", fontsize=9
    )
    save(figure, "ppo-movement")
    (output / "plot-data.json").write_text(
        json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--distribution", type=Path, required=True)
    parser.add_argument("--gradients", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="SVG and derived JSON directory")
    parser.add_argument("--png-directory", type=Path, help="optional ignored PNG directory")
    args = parser.parse_args()
    data = build_data(args.comparison, args.distribution, args.gradients)
    render(data, args.output, args.png_directory)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "inputs": data["input_sha256"],
                "means": [item["mean_ending_hp"] for item in data["series"]],
            }
        )
    )


if __name__ == "__main__":
    main()
