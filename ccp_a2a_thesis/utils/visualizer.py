"""Result visualization utilities"""
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List
import numpy as np
from config import PLOTS_DIR

class ResultsVisualizer:
    """Create visualizations for experiment results"""
    
    def __init__(self):
        # Create directory if it doesn't exist
        Path(PLOTS_DIR).mkdir(exist_ok=True, parents=True)
        sns.set_style("whitegrid")
    
    def plot_accuracy_comparison(self, results: Dict):
        """Plot accuracy comparison between protocols"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        protocols = ['Text', 'CCP']
        means = [results['text']['mean_accuracy'], results['ccp']['mean_accuracy']]
        stds = [results['text']['std_accuracy'], results['ccp']['std_accuracy']]
        
        bars = ax.bar(protocols, means, yerr=stds, capsize=10, 
                      color=['#ff6b6b', '#4ecdc4'], alpha=0.8)
        
        ax.set_ylabel('Accuracy')
        ax.set_title('Protocol Comparison: Task Accuracy')
        ax.set_ylim(0, 1.1)
        
        # Add value labels
        for bar, mean in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                   f'{mean:.1%}', ha='center', fontweight='bold')
        
        plt.tight_layout()
        # Fix: Use Path.joinpath instead of /
        save_path = Path(PLOTS_DIR) / 'accuracy_comparison.png'
        plt.savefig(save_path, dpi=150)
        plt.show()
    
    def plot_crs_comparison(self, results: Dict):
        """Plot Context Retention Score comparison"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        protocols = ['Text', 'CCP']
        means = [results['text']['mean_crs'], results['ccp']['mean_crs']]
        stds = [results['text']['std_crs'], results['ccp']['std_crs']]
        
        bars = ax.bar(protocols, means, yerr=stds, capsize=10,
                      color=['#ff6b6b', '#4ecdc4'], alpha=0.8)
        
        ax.set_ylabel('Context Retention Score (CRS)')
        ax.set_title('Protocol Comparison: Context Retention')
        ax.set_ylim(0, 1.1)
        
        for bar, mean in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                   f'{mean:.3f}', ha='center', fontweight='bold')
        
        plt.tight_layout()
        # Fix: Use Path.joinpath instead of /
        save_path = Path(PLOTS_DIR) / 'crs_comparison.png'
        plt.savefig(save_path, dpi=150)
        plt.show()
    
    def plot_drift_analysis(self, trial_results: List[Dict]):
        """Plot drift patterns across tasks"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
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
            axes[0].hist(text_drifts, bins=20, alpha=0.7, label='Text', color='#ff6b6b')
        if ccp_drifts:
            axes[0].hist(ccp_drifts, bins=20, alpha=0.7, label='CCP', color='#4ecdc4')
        axes[0].set_xlabel('Context Drift')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Distribution of Context Drift')
        axes[0].legend()
        
        # Box plot
        box_data = [text_drifts if text_drifts else [0], ccp_drifts if ccp_drifts else [0]]
        bp = axes[1].boxplot(box_data, labels=['Text', 'CCP'], patch_artist=True)
        bp['boxes'][0].set_facecolor('#ff6b6b')
        bp['boxes'][1].set_facecolor('#4ecdc4')
        axes[1].set_ylabel('Context Drift')
        axes[1].set_title('Drift Comparison')
        
        plt.tight_layout()
        save_path = Path(PLOTS_DIR) / 'drift_analysis.png'
        plt.savefig(save_path, dpi=150)
        plt.show()