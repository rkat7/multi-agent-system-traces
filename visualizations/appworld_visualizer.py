"""
AppWorld Trajectory Visualizer

This module provides visualization tools for AppWorld agent traces.
AppWorld traces are text files containing hierarchical agent communications
for multi-app task completion (Spotify, Email, etc.).

Structure:
- Supervisor Agent → App-specific agents (hierarchical)
- Text-based format with delimiters
- API exploration and execution patterns
- Code execution outputs
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict


class AppWorldVisualizer:
    """Visualizes AppWorld agent trajectories and tool usage patterns."""

    def __init__(self, trace_dir: str = "traces/AppWorld"):
        """
        Initialize AppWorld visualizer.

        Args:
            trace_dir: Path to directory containing AppWorld trace files
        """
        self.trace_dir = Path(trace_dir)
        self.agent_colors = {
            'Supervisor': '#FF6B6B',
            'Spotify': '#1DB954',
            'Email': '#4285F4',
            'Gmail': '#EA4335',
            'Amazon': '#FF9900',
            'Todoist': '#E44332',
            'Venmo': '#3D95CE',
            'Phone': '#34A853',
            'SimpleNote': '#3B88C3',
            'FileSystem': '#FFA000'
        }

    def load_trace(self, trace_file: str) -> str:
        """
        Load a single AppWorld trace file.

        Args:
            trace_file: Name of trace file (with or without .txt extension)

        Returns:
            Raw trace content as string
        """
        if not trace_file.endswith('.txt'):
            trace_file += '.txt'

        trace_path = self.trace_dir / trace_file

        with open(trace_path, 'r') as f:
            return f.read()

    def parse_trace(self, trace_content: str) -> Dict[str, Any]:
        """
        Parse AppWorld trace into structured format.

        Args:
            trace_content: Raw trace content

        Returns:
            Structured trace dictionary
        """
        task_match = re.search(r'\*+ Task (\d+)/(\d+) \(([^)]+)\)\s+\*+\n(.*?)\n(?=Response from Supervisor)',
                              trace_content, re.DOTALL)

        if task_match:
            task_num, total_tasks, task_id, task_description = task_match.groups()
        else:
            task_num, total_tasks, task_id, task_description = "?", "?", "unknown", "No description"

        events = []

        supervisor_pattern = r'Response from Supervisor Agent\n(.*?)(?=\n(?:Code Execution Output|Message to Supervisor|Entering|Exiting|Response from send_message|$))'
        for match in re.finditer(supervisor_pattern, trace_content, re.DOTALL):
            events.append({
                'type': 'supervisor_response',
                'agent': 'Supervisor',
                'content': match.group(1).strip(),
                'position': match.start()
            })

        entering_pattern = r'Entering ([A-Za-z_]+) Agent message loop'
        for match in re.finditer(entering_pattern, trace_content):
            events.append({
                'type': 'enter_agent',
                'agent': match.group(1),
                'content': f"Entering {match.group(1)} Agent",
                'position': match.start()
            })

        exiting_pattern = r'Exiting ([A-Za-z_]+) Agent message loop'
        for match in re.finditer(exiting_pattern, trace_content):
            events.append({
                'type': 'exit_agent',
                'agent': match.group(1),
                'content': f"Exiting {match.group(1)} Agent",
                'position': match.start()
            })

        agent_response_pattern = r'Response from ([A-Za-z_]+) Agent\n(.*?)(?=\n(?:Message to|Response from|Entering|Exiting|Code Execution|Reply from|$))'
        for match in re.finditer(agent_response_pattern, trace_content, re.DOTALL):
            agent_name = match.group(1)
            if agent_name != 'Supervisor':
                events.append({
                    'type': 'agent_response',
                    'agent': agent_name,
                    'content': match.group(2).strip(),
                    'position': match.start()
                })

        api_call_pattern = r'apis\.([a-z_]+)\.([a-z_]+)\('
        for match in re.finditer(api_call_pattern, trace_content):
            events.append({
                'type': 'api_call',
                'agent': 'API',
                'content': f"{match.group(1)}.{match.group(2)}()",
                'app': match.group(1),
                'api_name': match.group(2),
                'position': match.start()
            })

        events.sort(key=lambda x: x['position'])

        return {
            'task_id': task_id,
            'task_num': task_num,
            'total_tasks': total_tasks,
            'task_description': task_description.strip(),
            'events': events,
            'raw_content': trace_content
        }

    def extract_agent_hierarchy(self, trace: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract agent communication hierarchy.

        Args:
            trace: Parsed trace dictionary

        Returns:
            Dictionary mapping parent agents to child agents
        """
        hierarchy = defaultdict(list)
        current_agent_stack = ['Supervisor']

        for event in trace['events']:
            if event['type'] == 'enter_agent':
                parent = current_agent_stack[-1] if current_agent_stack else 'Supervisor'
                child = event['agent']
                if child not in hierarchy[parent]:
                    hierarchy[parent].append(child)
                current_agent_stack.append(child)
            elif event['type'] == 'exit_agent':
                if current_agent_stack and current_agent_stack[-1] == event['agent']:
                    current_agent_stack.pop()

        return dict(hierarchy)

    def extract_api_usage(self, trace: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract API usage patterns by app.

        Args:
            trace: Parsed trace dictionary

        Returns:
            Dictionary mapping apps to API calls
        """
        api_usage = defaultdict(list)

        for event in trace['events']:
            if event['type'] == 'api_call':
                app = event['app']
                api_name = event['api_name']
                api_usage[app].append(api_name)

        return dict(api_usage)

    def visualize_agent_hierarchy(self, trace: Dict[str, Any],
                                  output_path: Optional[str] = None,
                                  show: bool = True) -> None:
        """
        Visualize the hierarchical agent communication structure.

        Args:
            trace: Parsed trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        hierarchy = self.extract_agent_hierarchy(trace)

        G = nx.DiGraph()

        for parent, children in hierarchy.items():
            for child in children:
                G.add_edge(parent, child)

        fig, ax = plt.subplots(figsize=(12, 8))

        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

        node_colors = []
        for node in G.nodes():
            node_colors.append(self.agent_colors.get(node, '#95A5A6'))

        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000,
                              alpha=0.9, ax=ax, edgecolors='black', linewidths=2)

        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)

        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                              arrowsize=20, width=2, alpha=0.6,
                              connectionstyle='arc3,rad=0.1', ax=ax)

        ax.set_title(f"AppWorld Agent Hierarchy\nTask: {trace['task_id']}\n"
                    f"{trace['task_description'][:80]}...",
                    fontsize=13, fontweight='bold')
        ax.axis('off')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_event_timeline(self, trace: Dict[str, Any],
                                output_path: Optional[str] = None,
                                show: bool = True) -> None:
        """
        Visualize the timeline of events in the trace.

        Args:
            trace: Parsed trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        events = trace['events']

        fig, ax = plt.subplots(figsize=(14, max(8, len(events) * 0.15)))

        type_colors = {
            'supervisor_response': '#FF6B6B',
            'enter_agent': '#4ECDC4',
            'exit_agent': '#95A5A6',
            'agent_response': '#45B7D1',
            'api_call': '#96CEB4'
        }

        for idx, event in enumerate(events):
            event_type = event['type']
            color = type_colors.get(event_type, '#BDC3C7')

            content_preview = event['content'][:50]
            if len(event['content']) > 50:
                content_preview += '...'

            ax.barh(idx, 1, left=0, color=color, alpha=0.7, edgecolor='black')
            ax.text(0.02, idx, f"{event['agent']}: {content_preview}",
                   va='center', fontsize=8)

        legend_elements = [
            mpatches.Patch(color=color, label=label.replace('_', ' ').title(), alpha=0.7)
            for label, color in type_colors.items()
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, len(events) - 0.5)
        ax.set_xticks([])
        ax.set_ylabel('Event Index', fontsize=12)
        ax.set_title(f"AppWorld Event Timeline\nTask: {trace['task_id']}",
                    fontsize=14, fontweight='bold')
        ax.invert_yaxis()

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

    def visualize_api_usage(self, trace: Dict[str, Any],
                          output_path: Optional[str] = None,
                          show: bool = True) -> None:
        """
        Visualize API usage patterns by application.

        Args:
            trace: Parsed trace dictionary
            output_path: Optional path to save the visualization
            show: Whether to display the visualization
        """
        api_usage = self.extract_api_usage(trace)

        if not api_usage:
            print("No API calls found in this trace.")
            return

        fig, ax = plt.subplots(figsize=(12, max(6, len(api_usage) * 1.5)))

        apps = list(api_usage.keys())
        y_pos = 0
        bar_positions = []
        bar_labels = []

        for app in apps:
            apis = api_usage[app]
            api_counts = defaultdict(int)
            for api in apis:
                api_counts[api] += 1

            for api, count in api_counts.items():
                color = self.agent_colors.get(app.title(), '#95A5A6')
                ax.barh(y_pos, count, color=color, alpha=0.7, edgecolor='black')
                bar_positions.append(y_pos)
                bar_labels.append(f"{app}.{api}")
                y_pos += 1

        ax.set_yticks(bar_positions)
        ax.set_yticklabels(bar_labels, fontsize=9)
        ax.set_xlabel('Number of Calls', fontsize=12)
        ax.set_title(f"AppWorld API Usage\nTask: {trace['task_id']}",
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

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
        trace_content = self.load_trace(trace_file)
        trace = self.parse_trace(trace_content)
        hierarchy = self.extract_agent_hierarchy(trace)
        api_usage = self.extract_api_usage(trace)

        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            base_name = Path(trace_file).stem

            self.visualize_agent_hierarchy(
                trace,
                output_path=f"{output_dir}/{base_name}_hierarchy.png",
                show=False
            )

            self.visualize_event_timeline(
                trace,
                output_path=f"{output_dir}/{base_name}_timeline.png",
                show=False
            )

            if api_usage:
                self.visualize_api_usage(
                    trace,
                    output_path=f"{output_dir}/{base_name}_api_usage.png",
                    show=False
                )

        stats = {
            'task_id': trace['task_id'],
            'task_description': trace['task_description'],
            'total_events': len(trace['events']),
            'unique_agents': len(set(e['agent'] for e in trace['events'])),
            'agents': list(set(e['agent'] for e in trace['events'])),
            'total_api_calls': sum(len(apis) for apis in api_usage.values()),
            'apps_used': list(api_usage.keys()),
            'hierarchy_depth': max(len(children) for children in hierarchy.values()) if hierarchy else 0
        }

        return stats


def demo_appworld_visualizer():
    """Demonstrate AppWorld visualizer with real trace data."""
    visualizer = AppWorldVisualizer()

    trace_files = list(visualizer.trace_dir.glob("*.txt"))[:3]

    for trace_file in trace_files:
        print(f"\n{'='*60}")
        print(f"Processing: {trace_file.name}")
        print('='*60)

        stats = visualizer.generate_trace_report(
            trace_file.name,
            output_dir="visualizations/appworld_output"
        )

        print(f"Task ID: {stats['task_id']}")
        print(f"Description: {stats['task_description'][:100]}...")
        print(f"Total Events: {stats['total_events']}")
        print(f"Unique Agents: {stats['unique_agents']}")
        print(f"Agents: {', '.join(stats['agents'])}")
        print(f"Total API Calls: {stats['total_api_calls']}")
        print(f"Apps Used: {', '.join(stats['apps_used'])}")


if __name__ == "__main__":
    demo_appworld_visualizer()
