#!/usr/bin/env python3
"""
Generate workflow DAGs for AG2 traces.
Each node represents a message/turn in the agent conversation.
Edges represent sequential conversation flow.
"""

import json
import os
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Any

def create_ag2_dag(trace_data: Dict[str, Any], instance_id: str) -> nx.DiGraph:
    """
    Create a DAG from AG2 trace data.

    Args:
        trace_data: Parsed JSON trace data
        instance_id: Unique identifier for this trace

    Returns:
        NetworkX directed graph representing the conversation flow
    """
    G = nx.DiGraph()

    # Add metadata as graph attributes
    G.graph['instance_id'] = instance_id
    G.graph['problem_statement'] = trace_data.get('problem_statement', [])

    trajectory = trace_data.get('trajectory', [])

    # Create nodes for each conversation turn
    for i, step in enumerate(trajectory):
        node_id = f"step_{i}"

        # Extract full content
        content = step.get('content', [])
        if isinstance(content, list):
            content_text = '\n'.join(content)
        else:
            content_text = str(content)

        G.add_node(
            node_id,
            step_number=i,
            role=step.get('role', 'unknown'),
            agent_name=step.get('name', 'unknown'),
            content=content_text,
            label=f"Step {i}\n{step.get('name', 'unknown')}\n({step.get('role', 'unknown')})"
        )

        # Add edge from previous step
        if i > 0:
            prev_node = f"step_{i-1}"
            G.add_edge(
                prev_node,
                node_id,
                edge_type='sequential_flow',
                label=f"{i-1}→{i}"
            )

    return G


def visualize_dag(G: nx.DiGraph, output_path: Path):
    """
    Visualize and save the DAG.

    Args:
        G: NetworkX graph
        output_path: Path to save the visualization
    """
    plt.figure(figsize=(16, 12))

    # Use shell layout (doesn't require scipy)
    try:
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    except:
        # Fallback to shell layout if spring_layout fails
        pos = nx.shell_layout(G)

    # Color nodes by agent
    node_colors = []
    for node in G.nodes():
        agent = G.nodes[node].get('agent_name', 'unknown')
        if 'proxy' in agent.lower():
            node_colors.append('lightblue')
        elif 'assistant' in agent.lower():
            node_colors.append('lightgreen')
        else:
            node_colors.append('lightgray')

    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1500, alpha=0.9)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                          arrowsize=20, arrowstyle='->', width=2)

    # Draw labels
    labels = {node: G.nodes[node].get('label', node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')

    plt.title(f"AG2 Workflow DAG: {G.graph.get('instance_id', 'Unknown')}",
              fontsize=16, fontweight='bold')
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
    graphml_path = output_path.with_suffix('.graphml')
    G_copy = G.copy()
    # Convert list and None attributes to strings for GraphML compatibility
    for key in G_copy.graph:
        if isinstance(G_copy.graph[key], list):
            G_copy.graph[key] = json.dumps(G_copy.graph[key])
        elif G_copy.graph[key] is None:
            G_copy.graph[key] = ''
    for node in G_copy.nodes():
        for key in list(G_copy.nodes[node].keys()):
            if isinstance(G_copy.nodes[node][key], list):
                G_copy.nodes[node][key] = json.dumps(G_copy.nodes[node][key])
            elif G_copy.nodes[node][key] is None:
                G_copy.nodes[node][key] = ''
    for u, v in G_copy.edges():
        for key in list(G_copy.edges[u, v].keys()):
            if isinstance(G_copy.edges[u, v][key], list):
                G_copy.edges[u, v][key] = json.dumps(G_copy.edges[u, v][key])
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
                **G.nodes[node]
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


def process_all_ag2_traces(traces_dir: Path, output_dir: Path):
    """
    Process all AG2 traces and generate DAGs.

    Args:
        traces_dir: Directory containing AG2 trace files
        output_dir: Directory to save generated DAGs
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON trace files
    trace_files = list(traces_dir.glob('*.json'))

    print(f"Found {len(trace_files)} AG2 trace files")

    for i, trace_file in enumerate(trace_files, 1):
        print(f"Processing {i}/{len(trace_files)}: {trace_file.name}")

        try:
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace_data = json.load(f)

            instance_id = trace_data.get('instance_id', trace_file.stem)

            # Create DAG
            G = create_ag2_dag(trace_data, instance_id)

            # Save outputs
            base_output_path = output_dir / f"{instance_id}_dag"

            # Save visualization
            visualize_dag(G, base_output_path.with_suffix('.png'))

            # Save data files
            save_dag_data(G, base_output_path)

            print(f"  ✓ Generated DAG with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        except Exception as e:
            print(f"  ✗ Error processing {trace_file.name}: {e}")
            continue

    print(f"\n✓ Completed processing all AG2 traces")
    print(f"  Output directory: {output_dir}")


def main():
    # Set up paths
    project_root = Path(__file__).parent
    traces_dir = project_root / 'traces' / 'AG2'
    output_dir = project_root / 'visualizations' / 'AG2'

    # Process all traces
    process_all_ag2_traces(traces_dir, output_dir)


if __name__ == '__main__':
    main()
