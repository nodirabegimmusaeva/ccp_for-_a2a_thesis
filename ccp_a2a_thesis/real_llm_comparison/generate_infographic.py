"""Generate a thesis-style infographic from real LLM comparison results."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "real_llm_results.json"
DEFAULT_OUTPUT = ROOT / "results" / "real_llm_infographic.png"

COLORS = {
    "bg": "#FFFFFF",
    "wash": "#F5FAF8",
    "panel": "#FFFFFF",
    "ink": "#18332F",
    "muted": "#657873",
    "faint": "#E8F1EE",
    "grid": "#D6E4E0",
    "text": "#DE6F73",
    "text_dark": "#A9444A",
    "text_soft": "#F5C4C3",
    "ccp": "#2BB39D",
    "ccp_dark": "#127F70",
    "ccp_soft": "#BDE9E2",
    "safety": "#167C6C",
    "warning": "#D0962E",
    "warning_soft": "#F2D79D",
    "line": "#B7D1CA",
    "shadow": "#C8D8D3",
}


def load_results(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def protocol_summary(results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    if "summary" in results:
        return results["summary"]

    text_trials = 0
    ccp_trials = 0
    text_crs = 0.0
    ccp_crs = 0.0
    text_acc = 0.0
    ccp_acc = 0.0
    text_judge = []
    ccp_judge = []
    text_hard = 0
    ccp_hard = 0

    for condition in results.get("conditions", []):
        if "results" not in condition:
            continue
        summary = condition["results"]["summary"]
        t = summary["text"]["total_trials"]
        c = summary["ccp"]["total_trials"]
        text_trials += t
        ccp_trials += c
        text_crs += summary["text"]["mean_crs"] * t
        ccp_crs += summary["ccp"]["mean_crs"] * c
        text_acc += summary["text"]["mean_accuracy"] * t
        ccp_acc += summary["ccp"]["mean_accuracy"] * c
        text_hard += summary["text"].get("hard_violation_trials", 0)
        ccp_hard += summary["ccp"].get("hard_violation_trials", 0)
        if summary["text"].get("mean_judge_score") is not None:
            text_judge.append((summary["text"]["mean_judge_score"], t))
        if summary["ccp"].get("mean_judge_score") is not None:
            ccp_judge.append((summary["ccp"]["mean_judge_score"], c))

    return {
        "text": {
            "mean_crs": text_crs / text_trials if text_trials else 0.0,
            "mean_accuracy": text_acc / text_trials if text_trials else 0.0,
            "mean_judge_score": weighted_mean(text_judge),
            "hard_violation_rate": text_hard / text_trials if text_trials else 0.0,
            "total_trials": text_trials,
        },
        "ccp": {
            "mean_crs": ccp_crs / ccp_trials if ccp_trials else 0.0,
            "mean_accuracy": ccp_acc / ccp_trials if ccp_trials else 0.0,
            "mean_judge_score": weighted_mean(ccp_judge),
            "hard_violation_rate": ccp_hard / ccp_trials if ccp_trials else 0.0,
            "total_trials": ccp_trials,
        },
    }


def weighted_mean(values: List[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if not total_weight:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def condition_rows(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "condition_summary" in results:
        return results["condition_summary"]
    summary = results["summary"]
    return [
        {
            "model": results["metadata"].get("model"),
            "agent_b_mode": results["metadata"].get("agent_b_mode"),
            "hops": results["metadata"].get("hops"),
            "temperature": results["metadata"].get("temperature"),
            "text_mean_crs": summary["text"]["mean_crs"],
            "ccp_mean_crs": summary["ccp"]["mean_crs"],
            "crs_delta": summary["ccp"]["mean_crs"] - summary["text"]["mean_crs"],
            "text_mean_accuracy": summary["text"]["mean_accuracy"],
            "ccp_mean_accuracy": summary["ccp"]["mean_accuracy"],
            "accuracy_delta": summary["ccp"]["mean_accuracy"]
            - summary["text"]["mean_accuracy"],
            "text_hard_violation_rate": summary["text"].get("hard_violation_rate", 0.0),
            "ccp_hard_violation_rate": summary["ccp"].get("hard_violation_rate", 0.0),
            "text_mean_judge_score": summary["text"].get("mean_judge_score"),
            "ccp_mean_judge_score": summary["ccp"].get("mean_judge_score"),
        }
    ]


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_card_pct(value: float) -> str:
    if math.isclose(value, 1.0) or math.isclose(value, 0.0):
        return f"{value * 100:.0f}%"
    return f"{value * 100:.1f}%"


def as_meta_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def draw_system_trace(ax) -> None:
    """Add faint technical routing lines without competing with the data."""
    for y in [0.205, 0.238, 0.27]:
        ax.add_line(
            Line2D(
                [0.055, 0.22, 0.24, 0.39, 0.42, 0.64, 0.66, 0.945],
                [y, y, y + 0.018, y + 0.018, y, y, y + 0.012, y + 0.012],
                color=COLORS["faint"],
                linewidth=1.0,
                solid_capstyle="round",
            )
        )
    for x, y in [(0.24, 0.288), (0.42, 0.252), (0.66, 0.282), (0.83, 0.218)]:
        ax.add_patch(Circle((x, y), 0.003, facecolor=COLORS["panel"], edgecolor=COLORS["line"], linewidth=0.7))


def draw_badge(ax, x: float, y: float, label: str, color: str) -> None:
    patch = FancyBboxPatch(
        (x, y),
        0.064,
        0.032,
        boxstyle="round,pad=0.006,rounding_size=0.012",
        linewidth=0.8,
        edgecolor=color,
        facecolor=COLORS["panel"],
    )
    ax.add_patch(patch)
    ax.text(x + 0.032, y + 0.016, label, ha="center", va="center", fontsize=8.5, color=color, fontweight="bold")


def draw_segment_strip(ax, x: float, y: float, width: float, color: str) -> None:
    segment_count = 28
    gap = width * 0.006
    segment_w = (width - gap * (segment_count - 1)) / segment_count
    for i in range(segment_count):
        alpha = 0.92 if i % 4 else 0.72
        ax.add_patch(
            Rectangle(
                (x + i * (segment_w + gap), y),
                segment_w,
                0.014,
                color=color,
                alpha=alpha,
            )
        )


def draw_card(ax, xy, width, height, title, value, subtitle, color, badge):
    x, y = xy
    ax.add_patch(
        FancyBboxPatch(
            (x + 0.004, y - 0.006),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.022",
            linewidth=0,
            facecolor=COLORS["shadow"],
            alpha=0.12,
        )
    )
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.022",
        linewidth=1.2,
        edgecolor=COLORS["grid"],
        facecolor=COLORS["panel"],
    )
    ax.add_patch(patch)
    draw_segment_strip(ax, x + 0.014, y + height - 0.022, width - 0.028, color)
    draw_badge(ax, x + 0.022, y + height - 0.066, badge, color)
    value_font = 23 if len(value) <= 8 else 18
    ax.text(x + 0.1, y + height - 0.05, title.upper(), color=COLORS["muted"], fontsize=9.5, fontweight="bold")
    ax.text(
        x + 0.1,
        y + 0.052,
        value,
        color=COLORS["ink"],
        fontsize=value_font,
        fontweight="bold",
    )
    ax.text(x + 0.1, y + 0.022, subtitle, color=COLORS["muted"], fontsize=8.8)


def draw_panel(ax, x: float, y: float, width: float, height: float) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.014,rounding_size=0.018",
            linewidth=1.0,
            edgecolor=COLORS["grid"],
            facecolor=COLORS["wash"],
        )
    )


def make_infographic(
    results: Dict[str, Any], output: Path, source_name: str = "real_llm_results.json"
) -> None:
    summary = protocol_summary(results)
    rows = condition_rows(results)
    metadata = results.get("metadata", {})
    created = metadata.get("created_at_local") or datetime.now().astimezone().isoformat()

    fig = plt.figure(figsize=(16, 9), dpi=180)
    fig.patch.set_facecolor(COLORS["bg"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    draw_system_trace(ax)

    ax.text(
        0.055,
        0.935,
        "CCP vs Text: Real-LLM Context Reliability",
        fontsize=25,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.text(
        0.055,
        0.895,
        "Context retention, task compliance, and hard safety violations across live agent hops",
        fontsize=12.2,
        color=COLORS["muted"],
    )
    ax.text(
        0.94,
        0.91,
        f"Machine run time\n{created}",
        ha="right",
        va="center",
        fontsize=9.5,
        color=COLORS["muted"],
    )

    text = summary["text"]
    ccp = summary["ccp"]
    draw_card(
        ax,
        (0.055, 0.72),
        0.205,
        0.15,
        "Text CRS",
        fmt_card_pct(text["mean_crs"]),
        f"n={int(text.get('total_trials', 0))} protocol trials",
        COLORS["text"],
        "TEXT",
    )
    draw_card(
        ax,
        (0.285, 0.72),
        0.205,
        0.15,
        "CCP CRS",
        fmt_card_pct(ccp["mean_crs"]),
        f"Delta {fmt_pct(ccp['mean_crs'] - text['mean_crs'])}",
        COLORS["ccp"],
        "CCP",
    )
    draw_card(
        ax,
        (0.515, 0.72),
        0.205,
        0.15,
        "Judge Score",
        f"{fmt_card_pct(text.get('mean_judge_score', 0.0))} / {fmt_card_pct(ccp.get('mean_judge_score', 0.0))}",
        "Text / CCP task-safe completion",
        COLORS["safety"],
        "JUDGE",
    )
    draw_card(
        ax,
        (0.745, 0.72),
        0.2,
        0.15,
        "Hard Violations",
        f"{fmt_card_pct(text.get('hard_violation_rate', 0.0))} / {fmt_card_pct(ccp.get('hard_violation_rate', 0.0))}",
        "Text / CCP deterministic scan",
        COLORS["warning"],
        "SAFE",
    )

    draw_panel(ax, 0.055, 0.325, 0.47, 0.335)
    chart_ax = fig.add_axes([0.078, 0.365, 0.425, 0.245])
    chart_ax.set_facecolor(COLORS["wash"])
    metrics = [
        ("CRS", text["mean_crs"], ccp["mean_crs"]),
        ("Accuracy", text["mean_accuracy"], ccp["mean_accuracy"]),
        (
            "Judge",
            text.get("mean_judge_score", 0.0),
            ccp.get("mean_judge_score", 0.0),
        ),
        (
            "Safety pass",
            1 - text.get("hard_violation_rate", 0.0),
            1 - ccp.get("hard_violation_rate", 0.0),
        ),
    ]
    x_positions = list(range(len(metrics)))
    width = 0.34
    chart_ax.bar(
        [x - width / 2 for x in x_positions],
        [m[1] for m in metrics],
        width,
        label="Text",
        color=COLORS["text"],
        alpha=0.86,
    )
    chart_ax.bar(
        [x + width / 2 for x in x_positions],
        [m[2] for m in metrics],
        width,
        label="CCP",
        color=COLORS["ccp"],
        alpha=0.92,
    )
    for i, (_, tv, cv) in enumerate(metrics):
        chart_ax.text(i - width / 2, min(tv + 0.025, 1.07), f"{tv:.2f}", ha="center", fontsize=8.5, color=COLORS["ink"])
        chart_ax.text(i + width / 2, min(cv + 0.025, 1.07), f"{cv:.2f}", ha="center", fontsize=8.5, color=COLORS["ink"])
    chart_ax.set_ylim(0, 1.12)
    chart_ax.set_xticks(x_positions, [m[0] for m in metrics])
    chart_ax.set_ylabel("Score", color=COLORS["muted"])
    chart_ax.grid(axis="y", color=COLORS["grid"], linewidth=0.9)
    chart_ax.set_axisbelow(True)
    chart_ax.spines[["top", "right"]].set_visible(False)
    chart_ax.spines[["left", "bottom"]].set_color(COLORS["line"])
    chart_ax.tick_params(colors=COLORS["ink"])
    chart_ax.legend(loc="upper left", bbox_to_anchor=(0, 1.12), frameon=False, ncols=2, fontsize=9)
    chart_ax.set_title(
        "Aggregate protocol comparison",
        loc="left",
        color=COLORS["ink"],
        fontsize=13,
        fontweight="bold",
        pad=16,
    )

    draw_panel(ax, 0.545, 0.325, 0.4, 0.335)
    rows_ax = fig.add_axes([0.565, 0.365, 0.36, 0.245])
    rows_ax.set_axis_off()
    rows_ax.text(
        0,
        1.12,
        "Condition stress map",
        color=COLORS["ink"],
        fontsize=13,
        fontweight="bold",
    )
    rows_ax.text(
        1,
        1.12,
        "CCP - Text CRS",
        ha="right",
        color=COLORS["muted"],
        fontsize=10,
    )

    top_rows = sorted(rows, key=lambda r: r.get("crs_delta", 0.0), reverse=True)[:6]
    row_h = 0.14 if len(top_rows) <= 4 else 0.115
    for i, row in enumerate(top_rows):
        y = 0.86 - i * row_h
        label = (
            f"{row.get('agent_b_mode') or 'mode'}"
            f" | T={row.get('temperature')}"
            f" | hops={row.get('hops')}"
        )
        delta = row.get("crs_delta", 0.0)
        rows_ax.text(0, y, label, color=COLORS["ink"], fontsize=9.5, va="center")
        rows_ax.add_patch(
            FancyBboxPatch(
                (0.48, y - 0.02),
                0.34,
                0.04,
                boxstyle="round,pad=0.004,rounding_size=0.005",
                linewidth=0.6,
                edgecolor=COLORS["grid"],
                facecolor=COLORS["panel"],
            )
        )
        rows_ax.add_patch(Rectangle((0.487, y - 0.012), 0.326, 0.024, color=COLORS["grid"], alpha=0.75))
        bar_w = min(abs(delta) / 0.5, 1.0) * 0.326
        bar_color = COLORS["ccp"] if delta >= 0 else COLORS["text"]
        rows_ax.add_patch(Rectangle((0.487, y - 0.012), max(bar_w, 0.004), 0.024, color=bar_color))
        rows_ax.text(
            1,
            y,
            f"{delta:+.3f}",
            ha="right",
            va="center",
            color=bar_color,
            fontsize=10.5,
            fontweight="bold",
        )

    ax.add_patch(
        FancyBboxPatch(
            (0.055, 0.17),
            0.89,
            0.075,
            boxstyle="round,pad=0.012,rounding_size=0.012",
            linewidth=1.0,
            edgecolor=COLORS["grid"],
            facecolor=COLORS["wash"],
        )
    )
    ax.text(0.073, 0.224, "Reliability encoding", fontsize=9.5, color=COLORS["ink"], fontweight="bold")
    draw_badge(ax, 0.073, 0.181, "TEXT", COLORS["text"])
    draw_badge(ax, 0.143, 0.181, "CCP", COLORS["ccp"])
    draw_badge(ax, 0.213, 0.181, "SAFE", COLORS["warning"])
    note = (
        "Teal marks structured CCP preservation; coral marks unstructured text risk. "
        "Safety pass = 1 - deterministic hard-violation rate."
    )
    ax.text(0.3, 0.197, note, fontsize=9.8, color=COLORS["muted"], va="center")

    footer = (
        f"Model: {as_meta_value(metadata.get('model') or metadata.get('models', 'mixed'))}  |  "
        f"Mode: {as_meta_value(metadata.get('agent_b_mode') or metadata.get('agent_b_modes', 'mixed'))}  |  "
        f"Hops: {as_meta_value(metadata.get('hops') or metadata.get('hops_values', 'mixed'))}  |  "
        f"Generated from {source_name}"
    )
    ax.text(0.055, 0.105, footer, fontsize=8.8, color=COLORS["muted"])

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    results = load_results(args.input)
    make_infographic(results, args.output, source_name=args.input.name)
    print(f"Saved infographic: {args.output}")


if __name__ == "__main__":
    main()
