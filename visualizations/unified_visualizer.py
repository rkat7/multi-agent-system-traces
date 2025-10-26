"""
Unified Trajectory Visualizer

This module provides a unified interface for visualizing traces from
AG2, AppWorld, and HyperAgent systems.

Features:
- Auto-detection of trace format
- Unified API across all three systems
- Comparative analysis across agents
- Batch processing capabilities
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict, Counter

from ag2_visualizer import AG2Visualizer
from appworld_visualizer import AppWorldVisualizer
from hyperagent_visualizer import HyperAgentVisualizer


class UnifiedVisualizer:
    """Unified visualizer for all three agent systems."""

    def __init__(self, base_trace_dir: str = "traces"):
        """
        Initialize unified visualizer.

        Args:
            base_trace_dir: Base directory containing agent trace subdirectories
        """
        self.base_dir = Path(base_trace_dir)

        self.ag2_visualizer = AG2Visualizer(str(self.base_dir / "AG2"))
        self.appworld_visualizer = AppWorldVisualizer(str(self.base_dir / "AppWorld"))
        self.hyperagent_visualizer = HyperAgentVisualizer(str(self.base_dir / "HyperAgent"))

        self.agent_types = {
            'ag2': self.ag2_visualizer,
            'appworld': self.appworld_visualizer,
            'hyperagent': self.hyperagent_visualizer
        }

    def detect_agent_type(self, trace_path: Path) -> Optional[str]:
        """
        Auto-detect which agent system a trace belongs to.

        Args:
            trace_path: Path to trace file

        Returns:
            Agent type string or None if not recognized
        """
        if 'AG2' in str(trace_path):
            return 'ag2'
        elif 'AppWorld' in str(trace_path):
            return 'appworld'
        elif 'HyperAgent' in str(trace_path):
            return 'hyperagent'

        if trace_path.suffix == '.json':
            try:
                import json
                with open(trace_path, 'r') as f:
                    data = json.load(f)

                if 'trajectory' in data and isinstance(data['trajectory'], list):
                    if data['trajectory'] and isinstance(data['trajectory'][0], dict):
                        if 'role' in data['trajectory'][0]:
                            return 'ag2'
                    elif data['trajectory'] and isinstance(data['trajectory'][0], str):
                        if 'HyperAgent' in data['trajectory'][0]:
                            return 'hyperagent'
            except:
                pass

        elif trace_path.suffix == '.txt':
            try:
                with open(trace_path, 'r') as f:
                    content = f.read(500)
                    if 'Supervisor Agent' in content or 'Entering' in content:
                        return 'appworld'
            except:
                pass

        return None

    def visualize_trace(self, trace_path: Union[str, Path],
                       agent_type: Optional[str] = None,
                       output_dir: Optional[str] = None,
                       show: bool = True) -> Dict[str, Any]:
        """
        Visualize a trace with auto-detection of agent type.

        Args:
            trace_path: Path to trace file
            agent_type: Optional explicit agent type
            output_dir: Optional directory to save visualizations
            show: Whether to display visualizations

        Returns:
            Dictionary with trace statistics
        """
        trace_path = Path(trace_path)

        if agent_type is None:
            agent_type = self.detect_agent_type(trace_path)

        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown or undetectable agent type for {trace_path}")

        visualizer = self.agent_types[agent_type]

        return visualizer.generate_trace_report(
            trace_path.name,
            output_dir=output_dir
        )

    def batch_process(self, agent_type: str,
                     max_traces: Optional[int] = None,
                     output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Batch process multiple traces for a specific agent type.

        Args:
            agent_type: Type of agent ('ag2', 'appworld', 'hyperagent')
            max_traces: Maximum number of traces to process
            output_dir: Optional directory to save visualizations

        Returns:
            List of statistics dictionaries
        """
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")

        visualizer = self.agent_types[agent_type]

        if agent_type == 'ag2':
            trace_files = list(visualizer.trace_dir.glob("*.json"))
        elif agent_type == 'appworld':
            trace_files = list(visualizer.trace_dir.glob("*.txt"))
        else:
            trace_files = [f for f in visualizer.trace_dir.glob("*.json") if '_human' in f.name]

        if max_traces:
            trace_files = trace_files[:max_traces]

        results = []
        for trace_file in trace_files:
            print(f"Processing {agent_type}: {trace_file.name}")
            try:
                stats = visualizer.generate_trace_report(
                    trace_file.name,
                    output_dir=f"{output_dir}/{agent_type}" if output_dir else None
                )
                stats['agent_type'] = agent_type
                stats['trace_file'] = trace_file.name
                results.append(stats)
            except Exception as e:
                print(f"Error processing {trace_file.name}: {e}")

        return results

    def compare_agents(self, stats_list: List[Dict[str, Any]],
                      output_path: Optional[str] = None,
                      show: bool = True) -> None:
        """
        Create comparative visualizations across agent types.

        Args:
            stats_list: List of statistics from batch_process
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        if not stats_list:
            print("No statistics to compare.")
            return

        by_agent = defaultdict(list)
        for stats in stats_list:
            by_agent[stats['agent_type']].append(stats)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        agent_names = list(by_agent.keys())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1'][:len(agent_names)]

        # Trajectory length (turns or events)
        avg_lengths = []
        for a in agent_names:
            if 'total_turns' in by_agent[a][0]:
                avg_lengths.append(sum(s['total_turns'] for s in by_agent[a]) / len(by_agent[a]))
            elif 'total_events' in by_agent[a][0]:
                avg_lengths.append(sum(s['total_events'] for s in by_agent[a]) / len(by_agent[a]))
            else:
                avg_lengths.append(0)

        axes[0, 0].bar(agent_names, avg_lengths, color=colors, alpha=0.7, edgecolor='black')
        axes[0, 0].set_ylabel('Average Trajectory Length')
        axes[0, 0].set_title('Average Trajectory Length', fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3, axis='y')

        # Tool/API usage
        avg_tool_usage = []
        for a in agent_names:
            if 'total_api_calls' in by_agent[a][0]:
                avg_tool_usage.append(sum(s['total_api_calls'] for s in by_agent[a]) / len(by_agent[a]))
            elif 'total_tool_calls' in by_agent[a][0]:
                avg_tool_usage.append(sum(s['total_tool_calls'] for s in by_agent[a]) / len(by_agent[a]))
            elif 'code_turns' in by_agent[a][0]:
                avg_tool_usage.append(sum(s['code_turns'] for s in by_agent[a]) / len(by_agent[a]))
            else:
                avg_tool_usage.append(0)

        axes[0, 1].bar(agent_names, avg_tool_usage, color=colors, alpha=0.7, edgecolor='black')
        axes[0, 1].set_ylabel('Average Tool/API Usage')
        axes[0, 1].set_title('Average Tool/API Usage per Trace', fontweight='bold')
        axes[0, 1].grid(True, alpha=0.3, axis='y')

        # Failure modes (only for AG2 and HyperAgent)
        avg_failures = []
        for a in agent_names:
            avg_fail = sum(s.get('failure_modes_present', 0) for s in by_agent[a]) / len(by_agent[a])
            avg_failures.append(avg_fail)

        axes[1, 0].bar(agent_names, avg_failures, color=colors, alpha=0.7, edgecolor='black')
        axes[1, 0].set_ylabel('Average Failure Modes')
        axes[1, 0].set_title('Average Failure Modes Present', fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3, axis='y')

        trace_counts = [len(by_agent[a]) for a in agent_names]
        axes[1, 1].bar(agent_names, trace_counts, color=colors, alpha=0.7, edgecolor='black')
        axes[1, 1].set_ylabel('Number of Traces')
        axes[1, 1].set_title('Traces Processed by Agent Type', fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        plt.suptitle('Multi-Agent System Comparison', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def analyze_failure_patterns(self, agent_type: str,
                                 max_traces: Optional[int] = None,
                                 output_path: Optional[str] = None,
                                 show: bool = True) -> None:
        """
        Analyze failure mode patterns across multiple traces.

        Args:
            agent_type: Type of agent to analyze
            max_traces: Maximum number of traces to analyze
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        if agent_type not in ['ag2', 'hyperagent']:
            print(f"Failure mode analysis not available for {agent_type}")
            return

        visualizer = self.agent_types[agent_type]

        if agent_type == 'ag2':
            trace_files = list(visualizer.trace_dir.glob("*_human.json"))
        else:
            trace_files = list(visualizer.trace_dir.glob("*_human.json"))

        if max_traces:
            trace_files = trace_files[:max_traces]

        failure_counts = Counter()

        for trace_file in trace_files:
            try:
                trace = visualizer.load_trace(trace_file.name)
                failure_modes = trace.get('note', {}).get('options', {})

                for mode, value in failure_modes.items():
                    if value == 'yes':
                        failure_counts[mode] += 1
            except Exception as e:
                print(f"Error processing {trace_file.name}: {e}")

        if not failure_counts:
            print("No failure modes found.")
            return

        fig, ax = plt.subplots(figsize=(12, max(8, len(failure_counts) * 0.3)))

        modes = list(failure_counts.keys())
        counts = list(failure_counts.values())

        y_pos = range(len(modes))
        bars = ax.barh(y_pos, counts, color='#E74C3C', alpha=0.7, edgecolor='black')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(modes, fontsize=9)
        ax.set_xlabel('Number of Traces with Failure Mode', fontsize=12)
        ax.set_title(f"Failure Mode Prevalence - {agent_type.upper()}\n"
                    f"Analyzed {len(trace_files)} traces",
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

        for bar, count in zip(bars, counts):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f' {int(count)}',
                   ha='left', va='center', fontsize=9, fontweight='bold')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()


def demo_unified_visualizer():
    """Demonstrate unified visualizer capabilities."""
    visualizer = UnifiedVisualizer()

    print("="*60)
    print("UNIFIED AGENT TRAJECTORY VISUALIZER")
    print("="*60)

    print("\n1. Processing AG2 traces...")
    ag2_stats = visualizer.batch_process('ag2', max_traces=5, output_dir='visualizations/unified_output')

    print("\n2. Processing AppWorld traces...")
    appworld_stats = visualizer.batch_process('appworld', max_traces=3, output_dir='visualizations/unified_output')

    print("\n3. Processing HyperAgent traces...")
    hyperagent_stats = visualizer.batch_process('hyperagent', max_traces=3, output_dir='visualizations/unified_output')

    print("\n4. Creating comparative analysis...")
    all_stats = ag2_stats + appworld_stats + hyperagent_stats
    visualizer.compare_agents(all_stats, output_path='visualizations/unified_output/comparison.png', show=False)

    print("\n5. Analyzing failure patterns for AG2...")
    visualizer.analyze_failure_patterns('ag2', max_traces=20,
                                       output_path='visualizations/unified_output/ag2_failure_patterns.png',
                                       show=False)

    print("\n6. Analyzing failure patterns for HyperAgent...")
    visualizer.analyze_failure_patterns('hyperagent', max_traces=20,
                                       output_path='visualizations/unified_output/hyperagent_failure_patterns.png',
                                       show=False)

    print("\n" + "="*60)
    print("Summary Statistics:")
    print("="*60)
    print(f"AG2 traces processed: {len(ag2_stats)}")
    print(f"AppWorld traces processed: {len(appworld_stats)}")
    print(f"HyperAgent traces processed: {len(hyperagent_stats)}")
    print(f"Total traces: {len(all_stats)}")

    if ag2_stats:
        avg_ag2_turns = sum(s['total_turns'] for s in ag2_stats) / len(ag2_stats)
        print(f"AG2 avg turns: {avg_ag2_turns:.1f}")

    if appworld_stats:
        avg_app_events = sum(s['total_events'] for s in appworld_stats) / len(appworld_stats)
        print(f"AppWorld avg events: {avg_app_events:.1f}")

    if hyperagent_stats:
        avg_hyper_events = sum(s['total_events'] for s in hyperagent_stats) / len(hyperagent_stats)
        print(f"HyperAgent avg events: {avg_hyper_events:.1f}")


if __name__ == "__main__":
    demo_unified_visualizer()
