#!/usr/bin/env python3
"""
Generate workflow DAGs for HyperAgent traces.
Each node represents planning steps, intern assignments, actions, and tool calls.
Edges represent sequential workflow dependencies.
"""

import json
import re
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple

def parse_hyperagent_trajectory(trajectory: List[str]) -> List[Dict[str, Any]]:
    """
    Parse HyperAgent trajectory log entries into structured nodes.

    Args:
        trajectory: List of log entry strings

    Returns:
        List of parsed node dictionaries
    """
    nodes = []
    node_counter = 0
    current_context = None
    accumulating_action = False
    action_buffer = []

    for idx, entry in enumerate(trajectory):
        entry = entry.strip()

        if not entry:
            continue

        # INFO logs
        if ' - INFO - ' in entry:
            # Extract log message
            match = re.search(r' - INFO - (.+)', entry)
            if match:
                message = match.group(1)

                # Determine specific type
                if 'Initialized HyperAgent instance' in message:
                    node_type = 'initialization'
                elif 'Initialized tools' in message:
                    node_type = 'tool_init'
                elif "Planner's Response" in message:
                    node_type = 'planner_response'
                    current_context = 'planner'
                elif 'Navigator' in message and 'Response' in message:
                    node_type = 'navigator_response'
                    current_context = 'navigator'
                elif 'Intern' in message and 'Response' in message:
                    node_type = 'intern_response'
                else:
                    node_type = 'info_log'

                nodes.append({
                    'id': f"node_{node_counter}",
                    'type': node_type,
                    'content': entry,
                    'index': idx,
                    'context': current_context
                })
                node_counter += 1

        # Intern assignments
        elif entry.startswith('Intern Name:'):
            intern_name = entry.replace('Intern Name:', '').strip()
            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'intern_assignment',
                'intern_name': intern_name,
                'content': entry,
                'index': idx,
                'context': 'planner'
            })
            node_counter += 1
            current_context = f"intern_{intern_name}"

        # Subgoals
        elif entry.startswith('Subgoal:'):
            subgoal = entry.replace('Subgoal:', '').strip()
            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'subgoal',
                'subgoal': subgoal,
                'content': entry,
                'index': idx,
                'context': current_context
            })
            node_counter += 1

        # Thoughts
        elif entry.startswith('Thought:'):
            thought = entry.replace('Thought:', '').strip()
            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'thought',
                'thought': thought,
                'content': entry,
                'index': idx,
                'context': current_context
            })
            node_counter += 1

        # Actions (may span multiple lines with code blocks)
        elif entry.startswith('Action:'):
            accumulating_action = True
            action_buffer = [entry]

        elif accumulating_action:
            action_buffer.append(entry)

            # Check if this is the end of the action (next non-code line or specific marker)
            if idx + 1 < len(trajectory):
                next_entry = trajectory[idx + 1].strip()
                # End action accumulation when we hit a new major section
                if (next_entry.startswith(('Thought:', 'Action:', 'Intern Name:', 'Subgoal:')) or
                    ' - INFO - ' in next_entry):
                    # Save accumulated action
                    action_content = '\n'.join(action_buffer)
                    nodes.append({
                        'id': f"node_{node_counter}",
                        'type': 'action',
                        'content': action_content,
                        'index': idx - len(action_buffer) + 1,
                        'context': current_context
                    })
                    node_counter += 1
                    accumulating_action = False
                    action_buffer = []

        # Tool calls (Python code blocks)
        elif 'result = ' in entry and '._run(' in entry:
            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'tool_call',
                'content': entry,
                'index': idx,
                'context': current_context
            })
            node_counter += 1

    # Flush any remaining action buffer
    if action_buffer:
        action_content = '\n'.join(action_buffer)
        nodes.append({
            'id': f"node_{node_counter}",
            'type': 'action',
            'content': action_content,
            'index': len(trajectory) - 1,
            'context': current_context
        })

    return nodes


def create_hyperagent_dag(trace_data: Dict[str, Any], instance_id: str) -> nx.DiGraph:
    """
    Create a DAG from HyperAgent trace data.

    Args:
        trace_data: Parsed JSON trace data
        instance_id: Unique identifier for this trace

    Returns:
        NetworkX directed graph representing the workflow
    """
    G = nx.DiGraph()

    # Add metadata as graph attributes
    G.graph['instance_id'] = instance_id
    G.graph['problem_statement'] = trace_data.get('problem_statement', [])

    trajectory = trace_data.get('trajectory', [])

    # Parse trajectory into nodes
    nodes = parse_hyperagent_trajectory(trajectory)

    # Add nodes to graph
    for node in nodes:
        node_id = node['id']
        node_type = node['type']

        # Create label based on type
        if node_type == 'initialization':
            label = 'Init'
        elif node_type == 'tool_init':
            label = 'Tools Init'
        elif node_type == 'planner_response':
            label = 'Planner'
        elif node_type == 'navigator_response':
            label = 'Navigator'
        elif node_type == 'intern_response':
            label = 'Intern Reply'
        elif node_type == 'intern_assignment':
            label = f"Intern: {node.get('intern_name', 'Unknown')}"
        elif node_type == 'subgoal':
            subgoal = node.get('subgoal', '')[:40]
            label = f"Subgoal: {subgoal}..."
        elif node_type == 'thought':
            thought = node.get('thought', '')[:40]
            label = f"Think: {thought}..."
        elif node_type == 'action':
            label = 'Action'
        elif node_type == 'tool_call':
            # Extract tool name
            match = re.search(r'(\w+)\._run\(', node['content'])
            tool_name = match.group(1) if match else 'Tool'
            label = f"Tool: {tool_name}"
        else:
            label = node_type

        G.add_node(
            node_id,
            label=label,
            **node
        )

    # Add edges based on sequential flow and context dependencies
    for i in range(len(nodes) - 1):
        current_node = nodes[i]
        next_node = nodes[i + 1]

        current_id = current_node['id']
        next_id = next_node['id']

        # Determine edge type
        edge_type = 'sequential'

        # Special edge types based on workflow patterns
        if current_node['type'] == 'planner_response' and next_node['type'] == 'intern_assignment':
            edge_type = 'delegation'
        elif current_node['type'] == 'intern_assignment' and next_node['type'] == 'subgoal':
            edge_type = 'task_assignment'
        elif current_node['type'] == 'subgoal' and next_node['type'] in ['navigator_response', 'intern_response']:
            edge_type = 'execution'
        elif current_node['type'] == 'thought' and next_node['type'] == 'action':
            edge_type = 'reasoning_to_action'
        elif current_node['type'] == 'action' and next_node['type'] == 'tool_call':
            edge_type = 'action_execution'

        G.add_edge(current_id, next_id, edge_type=edge_type)

    return G


def visualize_dag(G: nx.DiGraph, output_path: Path):
    """
    Visualize and save the HyperAgent DAG.

    Args:
        G: NetworkX graph
        output_path: Path to save the visualization
    """
    # Determine figure size based on number of nodes
    n_nodes = G.number_of_nodes()
    fig_width = max(20, n_nodes * 0.3)
    fig_height = max(14, n_nodes * 0.2)

    plt.figure(figsize=(fig_width, fig_height))

    # Use shell layout (doesn't require scipy)
    try:
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    except:
        # Fallback to shell layout if spring_layout fails
        pos = nx.shell_layout(G)

    # Color nodes by type
    color_map = {
        'initialization': 'lightgray',
        'tool_init': 'lightgray',
        'planner_response': 'lightblue',
        'navigator_response': 'lightgreen',
        'intern_response': 'lightcyan',
        'intern_assignment': 'lightyellow',
        'subgoal': 'peachpuff',
        'thought': 'plum',
        'action': 'lightcoral',
        'tool_call': 'lightsteelblue',
        'info_log': 'whitesmoke'
    }

    node_colors = [color_map.get(G.nodes[node].get('type', ''), 'white') for node in G.nodes()]

    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1500, alpha=0.9,
                          edgecolors='black', linewidths=1)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                          arrowsize=12, arrowstyle='->', width=1.5, alpha=0.6)

    # Draw labels
    labels = {node: G.nodes[node].get('label', node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=6, font_weight='bold')

    problem_preview = ' '.join(G.graph.get('problem_statement', [''])[:1])[:80]
    plt.title(f"HyperAgent Workflow DAG: {G.graph.get('instance_id', 'Unknown')}\n{problem_preview}...",
              fontsize=14, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def save_dag_data(G: nx.DiGraph, output_path: Path):
    """
    Save DAG structure and full data to JSON and GraphML formats.

    Args:
        G: NetworkX graph
        output_path: Base path for output files
    """
    # Save as GraphML (convert lists to strings for compatibility)
    import json as json_module
    graphml_path = output_path.with_suffix('.graphml')
    G_copy = G.copy()
    # Convert list and None attributes to strings for GraphML compatibility
    for key in G_copy.graph:
        if isinstance(G_copy.graph[key], list):
            G_copy.graph[key] = json_module.dumps(G_copy.graph[key])
        elif G_copy.graph[key] is None:
            G_copy.graph[key] = ''
    for node in G_copy.nodes():
        for key in list(G_copy.nodes[node].keys()):
            if isinstance(G_copy.nodes[node][key], list):
                G_copy.nodes[node][key] = json_module.dumps(G_copy.nodes[node][key])
            elif G_copy.nodes[node][key] is None:
                G_copy.nodes[node][key] = ''
    for u, v in G_copy.edges():
        for key in list(G_copy.edges[u, v].keys()):
            if isinstance(G_copy.edges[u, v][key], list):
                G_copy.edges[u, v][key] = json_module.dumps(G_copy.edges[u, v][key])
            elif G_copy.edges[u, v][key] is None:
                G_copy.edges[u, v][key] = ''
    nx.write_graphml(G_copy, graphml_path)

    # Save as JSON with full details
    json_path = output_path.with_suffix('.json')
    data = {
        'metadata': G.graph,
        'nodes': [
            {
                'id': node,
                **{k: v for k, v in G.nodes[node].items()}
            }
            for node in G.nodes()
        ],
        'edges': [
            {
                'source': u,
                'target': v,
                **G.edges[u, v]
            }
            for u, v in G.edges()
        ]
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_all_hyperagent_traces(traces_dir: Path, output_dir: Path):
    """
    Process all HyperAgent traces and generate DAGs.

    Args:
        traces_dir: Directory containing HyperAgent trace files
        output_dir: Directory to save generated DAGs
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON trace files
    trace_files = list(traces_dir.glob('*.json'))

    print(f"Found {len(trace_files)} HyperAgent trace files")

    for i, trace_file in enumerate(trace_files, 1):
        print(f"Processing {i}/{len(trace_files)}: {trace_file.name}")

        try:
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace_data = json.load(f)

            instance_id = trace_data.get('instance_id', trace_file.stem)

            # Create DAG
            G = create_hyperagent_dag(trace_data, instance_id)

            # Save outputs
            base_output_path = output_dir / f"{instance_id}_dag"

            # Save visualization
            visualize_dag(G, base_output_path.with_suffix('.png'))

            # Save data files
            save_dag_data(G, base_output_path)

            print(f"  ✓ Generated DAG with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        except Exception as e:
            print(f"  ✗ Error processing {trace_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n✓ Completed processing all HyperAgent traces")
    print(f"  Output directory: {output_dir}")


def main():
    # Set up paths
    project_root = Path(__file__).parent
    traces_dir = project_root / 'traces' / 'HyperAgent'
    output_dir = project_root / 'visualizations' / 'HyperAgent'

    # Process all traces
    process_all_hyperagent_traces(traces_dir, output_dir)


if __name__ == '__main__':
    main()
