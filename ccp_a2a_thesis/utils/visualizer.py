"""Result visualization utilities"""
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List
import numpy as np
from config import (
    CCP_DRIFT_PROBABILITY,
    NUM_TRIALS,
    PLOTS_DIR,
    SEED,
    TASK_CATEGORIES,
)


COLORS = {
    "bg": "#F6FAF9",
    "panel": "#FFFFFF",
    "ink": "#18332F",
    "muted": "#64756F",
    "grid": "#D6E4E0",
    "text": "#D96B6B",
    "ccp": "#21A78B",
    "safety": "#0E7666",
    "warning": "#C98A25",
    "line": "#AFCAC3",
}

class ResultsVisualizer:
    """Create visualizations for experiment results"""
    
    def __init__(self):
        # Create directory if it doesn't exist
        Path(PLOTS_DIR).mkdir(exist_ok=True, parents=True)
        sns.set_theme(style="whitegrid")

    def _trial_count(self, results: Dict) -> int:
        return int(
            results.get("text", {}).get(
                "total_trials",
                NUM_TRIALS * len(TASK_CATEGORIES),
            )
        )

    def _subtitle(self, results: Dict) -> str:
        return (
            f"Simulated 3-agent pipeline | n={self._trial_count(results)} protocol trials "
            f"per condition | tasks={len(TASK_CATEGORIES)} | seed={SEED} | "
            f"CCP drift probability={CCP_DRIFT_PROBABILITY:.0%}"
        )

    def _style_axes(self, fig, ax):
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.grid(True, axis="both", color="#B9C8C4", linewidth=0.8, alpha=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#C9D2CF")
        ax.tick_params(colors=COLORS["ink"])
        ax.yaxis.label.set_color(COLORS["ink"])
        ax.title.set_color(COLORS["ink"])

    def _draw_protocol_bars(
        self,
        metric_name: str,
        ylabel: str,
        means: List[float],
        stds: List[float],
        results: Dict,
        save_name: str,
        value_format: str = "{:.3f}",
    ):
        fig, ax = plt.subplots(figsize=(10, 6.2))
        self._style_axes(fig, ax)

        protocols = ["Text", "CCP"]
        x_positions = np.arange(len(protocols))
        bars = ax.bar(
            x_positions,
            means,
            color=[COLORS["text"], COLORS["ccp"]],
            alpha=0.82,
            edgecolor="none",
            width=0.58,
        )

        ax.set_ylabel(ylabel)
        ax.set_xticks(x_positions, protocols)
        fig.suptitle(
            f"Protocol Comparison: {metric_name}",
            fontsize=16,
            fontweight="normal",
            color="#111111",
            y=0.965,
        )
        fig.text(
            0.5,
            0.912,
            self._subtitle(results),
            ha="center",
            va="center",
            fontsize=8,
            color="#111111",
        )
        ax.set_ylim(0, 1.16)

        for bar, mean, std in zip(bars, means, stds):
            x = bar.get_x() + bar.get_width() / 2
            ax.text(
                x,
                min(mean + 0.035, 1.12),
                f"{value_format.format(mean)}\nstd={std:.3f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="normal",
                color="#111111",
            )

        delta = means[1] - means[0]
        ax.legend(
            bars,
            ["Text (Unstructured Text Risk)", "CCP (Structured CCP Reliability)"],
            loc="lower right",
            frameon=True,
            facecolor="white",
            edgecolor="#D5D5D5",
            fontsize=9,
        )
        fig.text(
            0.09,
            0.035,
            f"CCP - Text delta: {delta:+.3f}",
            ha="left",
            va="center",
            fontsize=9,
            color="#111111",
            bbox={
                "boxstyle": "round,pad=0.25,rounding_size=0.08",
                "facecolor": "white",
                "edgecolor": "#BDBDBD",
                "linewidth": 0.8,
            },
        )

        plt.tight_layout(rect=[0.05, 0.07, 0.98, 0.88])
        save_path = Path(PLOTS_DIR) / save_name
        plt.savefig(save_path, dpi=180, facecolor="white")
        plt.show()
    
    def plot_accuracy_comparison(self, results: Dict):
        """Plot accuracy comparison between protocols"""
        self._draw_protocol_bars(
            metric_name="Task Accuracy",
            ylabel="Task Accuracy",
            means=[results["text"]["mean_accuracy"], results["ccp"]["mean_accuracy"]],
            stds=[results["text"]["std_accuracy"], results["ccp"]["std_accuracy"]],
            results=results,
            save_name="accuracy_comparison.png",
            value_format="{:.1%}",
        )
    
    def plot_crs_comparison(self, results: Dict):
        """Plot Context Retention Score comparison"""
        self._draw_protocol_bars(
            metric_name="Context Retention",
            ylabel="Context Retention Score (CRS)",
            means=[results["text"]["mean_crs"], results["ccp"]["mean_crs"]],
            stds=[results["text"]["std_crs"], results["ccp"]["std_crs"]],
            results=results,
            save_name="crs_comparison.png",
            value_format="{:.3f}",
        )
    
    def plot_drift_analysis(self, trial_results: List[Dict]):
        """Plot drift patterns across tasks"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        fig.patch.set_facecolor(COLORS["bg"])
        
        # Extract drift data
        text_drifts = []
        ccp_drifts = []
        
        for task_result in trial_results:
            for trial in task_result.get('trials', []):
                # Skip if CRS is None or not a number
                text_crs = trial['text'].get('crs', 0)
                ccp_crs = trial['ccp'].get('crs', 0)
                
                if isinstance(text_crs, (int, float)):
                    text_drifts.append(1 - text_crs)
                if isinstance(ccp_crs, (int, float)):
                    ccp_drifts.append(1 - ccp_crs)
        
        if text_drifts:
            axes[0].hist(text_drifts, bins=20, alpha=0.72, label='Text', color=COLORS["text"])
        if ccp_drifts:
            axes[0].hist(ccp_drifts, bins=20, alpha=0.72, label='CCP', color=COLORS["ccp"])
        axes[0].set_xlabel('Context Drift')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Distribution of Context Drift')
        axes[0].legend()
        
        # Box plot
        box_data = [text_drifts if text_drifts else [0], ccp_drifts if ccp_drifts else [0]]
        bp = axes[1].boxplot(box_data, labels=['Text', 'CCP'], patch_artist=True)
        bp['boxes'][0].set_facecolor(COLORS["text"])
        bp['boxes'][1].set_facecolor(COLORS["ccp"])
        axes[1].set_ylabel('Context Drift')
        axes[1].set_title('Drift Comparison')

        for ax in axes:
            self._style_axes(fig, ax)

        fig.suptitle(
            "Protocol Comparison: Context Drift Distribution",
            fontsize=18,
            fontweight="bold",
            color=COLORS["ink"],
        )
        fig.text(
            0.5,
            0.91,
            f"Simulated 3-agent pipeline | n={len(text_drifts)} protocol trials per condition | seed={SEED}",
            ha="center",
            fontsize=10.5,
            color=COLORS["muted"],
        )
        
        plt.tight_layout(rect=[0.03, 0.05, 0.98, 0.88])
        save_path = Path(PLOTS_DIR) / 'drift_analysis.png'
        plt.savefig(save_path, dpi=180, facecolor=fig.get_facecolor())
        plt.show()
