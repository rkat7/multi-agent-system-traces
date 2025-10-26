"""
HyperAgent Trajectory Visualizer

This module provides visualization tools for HyperAgent traces.
HyperAgent traces are JSON files containing hierarchical planning and execution
for software engineering tasks (SWE-bench).

Structure:
- Planner → Specialized Interns (Navigator, Editor, etc.)
- Very long traces (100s-3500+ log entries)
- Thought-action cycles
- File operations and codebase exploration
- GitHub issue context
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict, Counter


class HyperAgentVisualizer:
    """Visualizes HyperAgent trajectories and tool usage patterns."""

    def __init__(self, trace_dir: str = "traces/HyperAgent"):
        """
        Initialize HyperAgent visualizer.

        Args:
            trace_dir: Path to directory containing HyperAgent trace files
        """
        self.trace_dir = Path(trace_dir)
        self.agent_colors = {
            'Planner': '#FF6B6B',
            'Navigator': '#4ECDC4',
            'Editor': '#45B7D1',
            'Codebase Navigator': '#96CEB4',
            'Inner-Navigator-Assistant': '#5DADE2',
            'Inner-Editor-Assistant': '#58D68D'
        }
        self.tool_colors = {
            'open_file': '#3498DB',
            'get_folder_structure': '#9B59B6',
            'find_file': '#E67E22',
            'keyword_search': '#16A085',
            'editor': '#C0392B',
            'open_file_gen': '#27AE60'
        }

    def load_trace(self, trace_file: str) -> Dict[str, Any]:
        """
        Load a single HyperAgent trace file.

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

    def parse_trajectory(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse trajectory into structured events.

        Args:
            trace: Loaded trace dictionary

        Returns:
            List of parsed events
        """
        trajectory = trace.get('trajectory', [])
        events = []

        for idx, entry in enumerate(trajectory):
            if isinstance(entry, str):
                event = self._parse_log_entry(entry, idx)
                if event:
                    events.append(event)

        return events

    def _parse_log_entry(self, entry: str, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single log entry into structured format.

        Args:
            entry: Raw log entry string
            index: Index in trajectory

        Returns:
            Parsed event dictionary or None
        """
        planner_match = re.match(r".*Planner's Response: (Thought|Intern Name|Subgoal):\s*(.*)", entry)
        if planner_match:
            return {
                'index': index,
                'type': 'planner',
                'subtype': planner_match.group(1).lower(),
                'content': planner_match.group(2).strip(),
                'agent': 'Planner'
            }

        intern_match = re.match(r"Intern Name:\s*(.*)", entry)
        if intern_match:
            return {
                'index': index,
                'type': 'intern_assignment',
                'content': intern_match.group(1).strip(),
                'agent': intern_match.group(1).strip()
            }

        subgoal_match = re.match(r"Subgoal:\s*(.*)", entry)
        if subgoal_match:
            return {
                'index': index,
                'type': 'subgoal',
                'content': subgoal_match.group(1).strip(),
                'agent': 'Planner'
            }

        navigator_match = re.match(r".*Inner-Navigator-Assistant's Response: (Thought|Action):\s*(.*)", entry, re.DOTALL)
        if navigator_match:
            return {
                'index': index,
                'type': 'navigator',
                'subtype': navigator_match.group(1).lower(),
                'content': navigator_match.group(2).strip(),
                'agent': 'Inner-Navigator-Assistant'
            }

        editor_match = re.match(r".*Inner-Editor-Assistant's Response: (Thought|Action):\s*(.*)", entry, re.DOTALL)
        if editor_match:
            return {
                'index': index,
                'type': 'editor',
                'subtype': editor_match.group(1).lower(),
                'content': editor_match.group(2).strip(),
                'agent': 'Inner-Editor-Assistant'
            }

        tool_pattern = r'(open_file|get_folder_structure|find_file|keyword_search|editor|open_file_gen)\._run\('
        tool_match = re.search(tool_pattern, entry)
        if tool_match:
            return {
                'index': index,
                'type': 'tool_call',
                'tool': tool_match.group(1),
                'content': entry.strip(),
                'agent': 'Tool'
            }

        comm_match = re.match(r".*(Navigator|Editor)->Planner:\s*(.*)", entry, re.DOTALL)
        if comm_match:
            return {
                'index': index,
                'type': 'communication',
                'from': comm_match.group(1),
                'content': comm_match.group(2).strip(),
                'agent': comm_match.group(1)
            }

        if 'INFO' in entry or 'Initialized' in entry:
            return {
                'index': index,
                'type': 'system',
                'content': entry.strip(),
                'agent': 'System'
            }

        return None

    def extract_tool_usage(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Extract tool usage statistics.

        Args:
            events: List of parsed events

        Returns:
            Dictionary mapping tools to usage counts
        """
        tool_usage = Counter()

        for event in events:
            if event['type'] == 'tool_call':
                tool_usage[event['tool']] += 1

        return dict(tool_usage)

    def extract_thought_action_cycles(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract thought-action cycles from events.

        Args:
            events: List of parsed events

        Returns:
            List of thought-action pairs
        """
        cycles = []
        current_thought = None

        for event in events:
            if event.get('subtype') == 'thought':
                current_thought = event
            elif event.get('subtype') == 'action' and current_thought:
                cycles.append({
                    'thought': current_thought,
                    'action': event,
                    'agent': event['agent']
                })
                current_thought = None

        return cycles

    def extract_agent_hierarchy(self, events: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Extract agent hierarchy from events.

        Args:
            events: List of parsed events

        Returns:
            Dictionary mapping parent agents to child agents
        """
        hierarchy = defaultdict(set)

        for event in events:
            if event['type'] == 'intern_assignment':
                hierarchy['Planner'].add(event['agent'])
            elif event['type'] in ['navigator', 'editor']:
                hierarchy['Planner'].add(event['agent'])

        return {k: list(v) for k, v in hierarchy.items()}

    def visualize_tool_usage(self, trace: Dict[str, Any],
                           output_path: Optional[str] = None,
                           show: bool = True) -> None:
        """
        Visualize tool usage patterns.

        Args:
            trace: Loaded trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        events = self.parse_trajectory(trace)
        tool_usage = self.extract_tool_usage(events)

        if not tool_usage:
            print("No tool usage found in this trace.")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        tools = list(tool_usage.keys())
        counts = list(tool_usage.values())
        colors = [self.tool_colors.get(tool, '#95A5A6') for tool in tools]

        bars = ax.bar(tools, counts, color=colors, alpha=0.7, edgecolor='black')

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count)}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_xlabel('Tool', fontsize=12)
        ax.set_ylabel('Number of Calls', fontsize=12)
        ax.set_title(f"HyperAgent Tool Usage\nInstance: {trace['instance_id']}",
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_thought_action_flow(self, trace: Dict[str, Any],
                                     max_cycles: int = 20,
                                     output_path: Optional[str] = None,
                                     show: bool = True) -> None:
        """
        Visualize thought-action cycles.

        Args:
            trace: Loaded trace dictionary
            max_cycles: Maximum number of cycles to visualize
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        events = self.parse_trajectory(trace)
        cycles = self.extract_thought_action_cycles(events)[:max_cycles]

        if not cycles:
            print("No thought-action cycles found in this trace.")
            return

        fig, ax = plt.subplots(figsize=(14, max(8, len(cycles) * 0.4)))

        for idx, cycle in enumerate(cycles):
            agent = cycle['agent']
            color = self.agent_colors.get(agent, '#95A5A6')

            thought_preview = cycle['thought']['content'][:60]
            if len(cycle['thought']['content']) > 60:
                thought_preview += '...'

            action_preview = cycle['action']['content'][:60]
            if len(cycle['action']['content']) > 60:
                action_preview += '...'

            ax.barh(idx * 2, 1, left=0, color=color, alpha=0.4, edgecolor='black', label='Thought' if idx == 0 else '')
            ax.text(0.02, idx * 2, f"💭 {thought_preview}", va='center', fontsize=8)

            ax.barh(idx * 2 + 1, 1, left=0, color=color, alpha=0.8, edgecolor='black', label='Action' if idx == 0 else '')
            ax.text(0.02, idx * 2 + 1, f"⚡ {action_preview}", va='center', fontsize=8)

        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, len(cycles) * 2 - 0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"HyperAgent Thought-Action Flow (First {len(cycles)} cycles)\n"
                    f"Instance: {trace['instance_id']}",
                    fontsize=14, fontweight='bold')
        ax.invert_yaxis()

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_trajectory_overview(self, trace: Dict[str, Any],
                                     output_path: Optional[str] = None,
                                     show: bool = True) -> None:
        """
        Create an overview visualization of the entire trajectory.

        Args:
            trace: Loaded trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        events = self.parse_trajectory(trace)

        type_counts = Counter(e['type'] for e in events)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        types = list(type_counts.keys())
        counts = list(type_counts.values())

        ax1.pie(counts, labels=types, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Event Type Distribution', fontsize=12, fontweight='bold')

        agent_counts = Counter(e['agent'] for e in events if 'agent' in e)
        agents = list(agent_counts.keys())
        agent_vals = list(agent_counts.values())
        colors = [self.agent_colors.get(a, '#95A5A6') for a in agents]

        ax2.barh(agents, agent_vals, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Number of Events', fontsize=12)
        ax2.set_title('Agent Activity', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')

        plt.suptitle(f"HyperAgent Trajectory Overview\nInstance: {trace['instance_id']}\n"
                    f"Total Events: {len(events)}",
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
        failure_modes = trace.get('note', {}).get('options', {})

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
        ax.set_title(f"Failure Mode Annotations\nInstance: {trace['instance_id']}\n"
                    f"Issue: {trace['problem_statement'][0][:80]}...",
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
        events = self.parse_trajectory(trace)
        tool_usage = self.extract_tool_usage(events)
        cycles = self.extract_thought_action_cycles(events)
        failure_modes = trace.get('note', {}).get('options', {})

        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            base_name = Path(trace_file).stem

            self.visualize_trajectory_overview(
                trace,
                output_path=f"{output_dir}/{base_name}_overview.png",
                show=False
            )

            if tool_usage:
                self.visualize_tool_usage(
                    trace,
                    output_path=f"{output_dir}/{base_name}_tools.png",
                    show=False
                )

            if cycles:
                self.visualize_thought_action_flow(
                    trace,
                    output_path=f"{output_dir}/{base_name}_cycles.png",
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
            'problem_statement': trace['problem_statement'][0][:100],
            'total_events': len(events),
            'total_trajectory_entries': len(trace['trajectory']),
            'unique_agents': len(set(e['agent'] for e in events if 'agent' in e)),
            'total_tool_calls': sum(tool_usage.values()),
            'unique_tools': len(tool_usage),
            'thought_action_cycles': len(cycles),
            'failure_modes_present': len([v for v in failure_modes.values() if v == 'yes']),
            'has_patch': bool(trace.get('other_data', {}).get('patch'))
        }

        return stats


def demo_hyperagent_visualizer():
    """Demonstrate HyperAgent visualizer with real trace data."""
    visualizer = HyperAgentVisualizer()

    trace_files = [f for f in visualizer.trace_dir.glob("*.json") if '_human' in f.name][:3]

    for trace_file in trace_files:
        print(f"\n{'='*60}")
        print(f"Processing: {trace_file.name}")
        print('='*60)

        stats = visualizer.generate_trace_report(
            trace_file.name,
            output_dir="visualizations/hyperagent_output"
        )

        print(f"Instance ID: {stats['instance_id']}")
        print(f"Problem: {stats['problem_statement']}...")
        print(f"Total Events: {stats['total_events']}")
        print(f"Trajectory Entries: {stats['total_trajectory_entries']}")
        print(f"Unique Agents: {stats['unique_agents']}")
        print(f"Total Tool Calls: {stats['total_tool_calls']}")
        print(f"Unique Tools: {stats['unique_tools']}")
        print(f"Thought-Action Cycles: {stats['thought_action_cycles']}")
        print(f"Failure Modes Present: {stats['failure_modes_present']}")


if __name__ == "__main__":
    demo_hyperagent_visualizer()
