"""
AG2 Trajectory Visualizer

This module provides visualization tools for AG2 agent traces.
AG2 traces are JSON files containing multi-agent conversations for math problem solving.

Structure:
- Turn-based dialogue between agents (mathproxyagent, assistant, verifier, executor)
- Each turn has: content, role, name
- Human annotations with failure modes
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime


class AG2Visualizer:
    """Visualizes AG2 agent trajectories and tool usage patterns."""

    def __init__(self, trace_dir: str = "traces/AG2"):
        """
        Initialize AG2 visualizer.

        Args:
            trace_dir: Path to directory containing AG2 trace files
        """
        self.trace_dir = Path(trace_dir)
        self.agent_colors = {
            'mathproxyagent': '#FF6B6B',
            'assistant': '#4ECDC4',
            'Agent_Verifier': '#45B7D1',
            'Agent_Code_Executor': '#96CEB4',
            'user': '#FFEAA7'
        }

    def load_trace(self, trace_file: str) -> Dict[str, Any]:
        """
        Load a single AG2 trace file.

        Args:
            trace_file: Name of trace file (with or without .json extension)

        Returns:
            Parsed trace dictionary
        """
        if not trace_file.endswith('.json'):
            trace_file += '.json'

        trace_path = self.trace_dir / trace_file

        with open(trace_path, 'r') as f:
            return json.load(f)

    def extract_conversation_flow(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract conversation flow from trace.

        Args:
            trace: Loaded trace dictionary

        Returns:
            List of conversation turns with metadata
        """
        trajectory = trace.get('trajectory', [])

        flow = []
        for idx, turn in enumerate(trajectory):
            flow.append({
                'turn_index': idx,
                'agent_name': turn.get('name', 'unknown'),
                'role': turn.get('role', 'unknown'),
                'content': turn.get('content', []),
                'content_length': len(' '.join(turn.get('content', []))),
                'has_code': any('```' in str(c) for c in turn.get('content', []))
            })

        return flow

    def extract_failure_modes(self, trace: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract human-annotated failure modes from trace.

        Args:
            trace: Loaded trace dictionary

        Returns:
            Dictionary mapping failure mode names to yes/no values
        """
        return trace.get('note', {}).get('options', {})

    def visualize_conversation_timeline(self, trace: Dict[str, Any],
                                       output_path: Optional[str] = None,
                                       show: bool = True) -> None:
        """
        Create a timeline visualization of the conversation flow.

        Args:
            trace: Loaded trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        flow = self.extract_conversation_flow(trace)

        fig, ax = plt.subplots(figsize=(14, 8))

        for turn in flow:
            agent = turn['agent_name']
            color = self.agent_colors.get(agent, '#95A5A6')

            ax.barh(turn['turn_index'], turn['content_length'],
                   left=0, color=color, alpha=0.7, edgecolor='black')

            marker = 'D' if turn['has_code'] else 'o'
            ax.plot(turn['content_length'], turn['turn_index'],
                   marker=marker, color='black', markersize=8)

            ax.text(10, turn['turn_index'], f"{agent}",
                   va='center', fontsize=9, fontweight='bold')

        legend_elements = [
            mpatches.Patch(color=color, label=agent, alpha=0.7)
            for agent, color in self.agent_colors.items()
        ]
        legend_elements.extend([
            mpatches.Patch(color='none', label='○ = Text only'),
            mpatches.Patch(color='none', label='◆ = Contains code')
        ])

        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

        ax.set_xlabel('Content Length (characters)', fontsize=12)
        ax.set_ylabel('Turn Index', fontsize=12)
        ax.set_title(f"AG2 Conversation Timeline\nInstance: {trace['instance_id'][:8]}...",
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_agent_participation(self, trace: Dict[str, Any],
                                     output_path: Optional[str] = None,
                                     show: bool = True) -> None:
        """
        Visualize which agents participated and their activity levels.

        Args:
            trace: Loaded trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        flow = self.extract_conversation_flow(trace)

        agent_stats = {}
        for turn in flow:
            agent = turn['agent_name']
            if agent not in agent_stats:
                agent_stats[agent] = {
                    'turns': 0,
                    'total_chars': 0,
                    'code_turns': 0
                }
            agent_stats[agent]['turns'] += 1
            agent_stats[agent]['total_chars'] += turn['content_length']
            if turn['has_code']:
                agent_stats[agent]['code_turns'] += 1

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        agents = list(agent_stats.keys())
        turns = [agent_stats[a]['turns'] for a in agents]
        colors = [self.agent_colors.get(a, '#95A5A6') for a in agents]

        ax1.barh(agents, turns, color=colors, alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Number of Turns', fontsize=12)
        ax1.set_title('Agent Participation (Turns)', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='x')

        chars = [agent_stats[a]['total_chars'] for a in agents]
        ax2.barh(agents, chars, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Total Characters', fontsize=12)
        ax2.set_title('Agent Participation (Content Volume)', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')

        plt.suptitle(f"AG2 Agent Participation Analysis\nInstance: {trace['instance_id'][:8]}...",
                    fontsize=14, fontweight='bold')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_failure_modes(self, trace: Dict[str, Any],
                               output_path: Optional[str] = None,
                               show: bool = True) -> None:
        """
        Visualize annotated failure modes for this trace.

        Args:
            trace: Loaded trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        failure_modes = self.extract_failure_modes(trace)

        if not failure_modes:
            print("No failure mode annotations found in this trace.")
            return

        yes_modes = [mode for mode, value in failure_modes.items() if value == 'yes']
        no_modes = [mode for mode, value in failure_modes.items() if value == 'no']

        fig, ax = plt.subplots(figsize=(12, max(8, len(failure_modes) * 0.3)))

        all_modes = yes_modes + no_modes
        colors = ['#E74C3C'] * len(yes_modes) + ['#27AE60'] * len(no_modes)

        y_pos = range(len(all_modes))
        ax.barh(y_pos, [1] * len(all_modes), color=colors, alpha=0.7, edgecolor='black')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(all_modes, fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_xticks([])
        ax.set_title(f"Failure Mode Annotations\nInstance: {trace['instance_id'][:8]}...\n"
                    f"Problem: {trace['problem_statement'][0][:80]}...",
                    fontsize=12, fontweight='bold')

        legend_elements = [
            mpatches.Patch(color='#E74C3C', label=f'Present ({len(yes_modes)})', alpha=0.7),
            mpatches.Patch(color='#27AE60', label=f'Absent ({len(no_modes)})', alpha=0.7)
        ]
        ax.legend(handles=legend_elements, loc='lower right')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def generate_trace_report(self, trace_file: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete visualization report for a trace.

        Args:
            trace_file: Name of trace file
            output_dir: Optional directory to save visualizations

        Returns:
            Dictionary with trace statistics
        """
        trace = self.load_trace(trace_file)
        flow = self.extract_conversation_flow(trace)
        failure_modes = self.extract_failure_modes(trace)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base_name = Path(trace_file).stem

            self.visualize_conversation_timeline(
                trace,
                output_path=f"{output_dir}/{base_name}_timeline.png",
                show=False
            )

            self.visualize_agent_participation(
                trace,
                output_path=f"{output_dir}/{base_name}_participation.png",
                show=False
            )

            if failure_modes:
                self.visualize_failure_modes(
                    trace,
                    output_path=f"{output_dir}/{base_name}_failures.png",
                    show=False
                )

        stats = {
            'instance_id': trace['instance_id'],
            'total_turns': len(flow),
            'unique_agents': len(set(t['agent_name'] for t in flow)),
            'agents': list(set(t['agent_name'] for t in flow)),
            'total_chars': sum(t['content_length'] for t in flow),
            'code_turns': sum(1 for t in flow if t['has_code']),
            'correct': trace.get('other_data', {}).get('correct'),
            'failure_modes_present': len([v for v in failure_modes.values() if v == 'yes']),
            'failure_modes_absent': len([v for v in failure_modes.values() if v == 'no'])
        }

        return stats


def demo_ag2_visualizer():
    """Demonstrate AG2 visualizer with real trace data."""
    visualizer = AG2Visualizer()

    trace_files = list(visualizer.trace_dir.glob("*.json"))[:3]

    for trace_file in trace_files:
        print(f"\n{'='*60}")
        print(f"Processing: {trace_file.name}")
        print('='*60)

        stats = visualizer.generate_trace_report(
            trace_file.name,
            output_dir="visualizations/ag2_output"
        )

        print(f"Instance ID: {stats['instance_id']}")
        print(f"Total Turns: {stats['total_turns']}")
        print(f"Unique Agents: {stats['unique_agents']}")
        print(f"Agents: {', '.join(stats['agents'])}")
        print(f"Total Characters: {stats['total_chars']}")
        print(f"Code Turns: {stats['code_turns']}")
        print(f"Correct Answer: {stats['correct']}")
        print(f"Failure Modes Present: {stats['failure_modes_present']}")


if __name__ == "__main__":
    demo_ag2_visualizer()
