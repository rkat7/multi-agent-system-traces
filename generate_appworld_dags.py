#!/usr/bin/env python3
"""
Generate workflow DAGs for AppWorld traces.
Each node represents agent interactions, API calls, and code executions.
Edges represent message flow and control flow between components.
"""

import re
import os
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Any

def parse_appworld_trace(trace_content: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse AppWorld trace text into structured nodes and metadata.

    Args:
        trace_content: Raw trace file content

    Returns:
        Tuple of (nodes list, metadata dict)
    """
    lines = trace_content.split('\n')
    nodes = []
    current_agent_context = None
    node_counter = 0

    # Extract task info from header
    task_match = re.search(r'\*+ Task (\d+/\d+) \(([^)]+)\)', trace_content)
    task_info = task_match.groups() if task_match else ('Unknown', 'Unknown')

    # Extract task description
    task_desc_match = re.search(r'\) \s+\*+\s*\n(.+?)(?:\n[A-Z]|\nResponse from)', trace_content, re.DOTALL)
    task_description = task_desc_match.group(1).strip() if task_desc_match else ''

    metadata = {
        'task_id': task_info[1] if len(task_info) > 1 else task_info[0],
        'task_number': task_info[0],
        'task_description': task_description
    }

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Agent message loop entry/exit
        if re.match(r'Entering (\w+) Agent message loop', line):
            match = re.match(r'Entering (\w+) Agent message loop', line)
            agent_name = match.group(1)
            current_agent_context = agent_name

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'agent_entry',
                'agent': agent_name,
                'content': line,
                'line_number': i
            })
            node_counter += 1

        elif re.match(r'Exiting (\w+) Agent message loop', line):
            match = re.match(r'Exiting (\w+) Agent message loop', line)
            agent_name = match.group(1)

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'agent_exit',
                'agent': agent_name,
                'content': line,
                'line_number': i
            })
            node_counter += 1
            current_agent_context = None

        # Response from agents
        elif re.match(r'Response from (\w+) Agent', line):
            match = re.match(r'Response from (\w+) Agent', line)
            agent_name = match.group(1)

            # Collect content until next major section
            content_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'(Response from|Message to|Code Execution|Entering|Exiting|Reply from)', next_line):
                    break
                content_lines.append(lines[j])
                j += 1

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'agent_response',
                'agent': agent_name,
                'content': '\n'.join(content_lines),
                'line_number': i,
                'context': current_agent_context
            })
            node_counter += 1
            i = j - 1

        # Message to agents
        elif re.match(r'Message to (\w+) Agent', line):
            match = re.match(r'Message to (\w+) Agent', line)
            agent_name = match.group(1)

            # Collect message content
            content_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'(Response from|Message to|Code Execution|Entering|Exiting)', next_line):
                    break
                content_lines.append(lines[j])
                j += 1

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'agent_message',
                'agent': agent_name,
                'content': '\n'.join(content_lines),
                'line_number': i,
                'context': current_agent_context
            })
            node_counter += 1
            i = j - 1

        # Code execution
        elif line.startswith('Code Execution Output'):
            # Collect execution content
            content_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'(Response from|Message to|Code Execution|Entering|Exiting)', next_line):
                    break
                content_lines.append(lines[j])
                j += 1

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'code_execution',
                'content': '\n'.join(content_lines),
                'line_number': i,
                'context': current_agent_context or 'Supervisor'
            })
            node_counter += 1
            i = j - 1

        # Reply from sub-agent to supervisor
        elif re.match(r'Reply from (\w+) Agent to (\w+)', line):
            match = re.match(r'Reply from (\w+) Agent to (\w+)', line)
            from_agent = match.group(1)
            to_agent = match.group(2)

            # Collect reply content
            content_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'(Response from|Message to|Code Execution|Entering|Exiting|Reply from)', next_line):
                    break
                content_lines.append(lines[j])
                j += 1

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'agent_reply',
                'from_agent': from_agent,
                'to_agent': to_agent,
                'content': '\n'.join(content_lines),
                'line_number': i,
                'context': current_agent_context
            })
            node_counter += 1
            i = j - 1

        # send_message API response
        elif line.startswith('Response from send_message API'):
            # Collect response content
            content_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'(Response from|Message to|Code Execution|Entering|Exiting)', next_line):
                    break
                content_lines.append(lines[j])
                j += 1

            nodes.append({
                'id': f"node_{node_counter}",
                'type': 'api_response',
                'api': 'send_message',
                'content': '\n'.join(content_lines),
                'line_number': i
            })
            node_counter += 1
            i = j - 1

        i += 1

    return nodes, metadata


def create_appworld_dag(nodes: List[Dict[str, Any]], metadata: Dict[str, Any]) -> nx.DiGraph:
    """
    Create a DAG from parsed AppWorld trace nodes.

    Args:
        nodes: List of parsed node dictionaries
        metadata: Trace metadata

    Returns:
        NetworkX directed graph representing the workflow
    """
    G = nx.DiGraph()

    # Add metadata as graph attributes
    G.graph.update(metadata)

    # Add nodes to graph
    for node in nodes:
        node_id = node['id']
        node_type = node['type']

        # Create label based on type
        if node_type == 'agent_response':
            label = f"{node['agent']} Response"
        elif node_type == 'agent_message':
            label = f"→ {node['agent']}"
        elif node_type == 'agent_entry':
            label = f"Enter {node['agent']}"
        elif node_type == 'agent_exit':
            label = f"Exit {node['agent']}"
        elif node_type == 'code_execution':
            label = "Code Exec"
        elif node_type == 'agent_reply':
            label = f"{node['from_agent']} → {node['to_agent']}"
        elif node_type == 'api_response':
            label = f"API: {node['api']}"
        else:
            label = node_type

        G.add_node(
            node_id,
            label=label,
            **node
        )

    # Add edges based on sequential flow and agent context
    for i in range(len(nodes) - 1):
        current_node = nodes[i]
        next_node = nodes[i + 1]

        current_id = current_node['id']
        next_id = next_node['id']

        # Determine edge type
        edge_type = 'sequential'

        # Special edge types
        if current_node['type'] == 'agent_message' and next_node['type'] == 'agent_response':
            edge_type = 'request_response'
        elif current_node['type'] == 'agent_entry':
            edge_type = 'context_entry'
        elif current_node['type'] == 'agent_exit':
            edge_type = 'context_exit'
        elif current_node['type'] == 'code_execution':
            edge_type = 'execution_result'

        G.add_edge(current_id, next_id, edge_type=edge_type)

    return G


def visualize_dag(G: nx.DiGraph, output_path: Path):
    """
    Visualize and save the AppWorld DAG.

    Args:
        G: NetworkX graph
        output_path: Path to save the visualization
    """
    plt.figure(figsize=(20, 14))

    # Use shell layout (doesn't require scipy)
    try:
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    except:
        # Fallback to shell layout if spring_layout fails
        pos = nx.shell_layout(G)

    # Color nodes by type
    color_map = {
        'agent_response': 'lightblue',
        'agent_message': 'lightgreen',
        'agent_entry': 'lightcoral',
        'agent_exit': 'lightyellow',
        'code_execution': 'plum',
        'agent_reply': 'lightcyan',
        'api_response': 'peachpuff'
    }

    node_colors = [color_map.get(G.nodes[node].get('type', ''), 'lightgray') for node in G.nodes()]

    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000, alpha=0.9)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                          arrowsize=15, arrowstyle='->', width=1.5)

    # Draw labels
    labels = {node: G.nodes[node].get('label', node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_weight='bold')

    plt.title(f"AppWorld Workflow DAG: {G.graph.get('task_id', 'Unknown')}\n{G.graph.get('task_description', '')[:100]}",
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
    import json
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


def process_all_appworld_traces(traces_dir: Path, output_dir: Path):
    """
    Process all AppWorld traces and generate DAGs.

    Args:
        traces_dir: Directory containing AppWorld trace files
        output_dir: Directory to save generated DAGs
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all .txt trace files
    trace_files = list(traces_dir.glob('*.txt'))

    print(f"Found {len(trace_files)} AppWorld trace files")

    for i, trace_file in enumerate(trace_files, 1):
        print(f"Processing {i}/{len(trace_files)}: {trace_file.name}")

        try:
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace_content = f.read()

            # Parse trace
            nodes, metadata = parse_appworld_trace(trace_content)

            # Create DAG
            G = create_appworld_dag(nodes, metadata)

            # Save outputs
            base_output_path = output_dir / f"{trace_file.stem}_dag"

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

    print(f"\n✓ Completed processing all AppWorld traces")
    print(f"  Output directory: {output_dir}")


def main():
    # Set up paths
    project_root = Path(__file__).parent
    traces_dir = project_root / 'traces' / 'AppWorld'
    output_dir = project_root / 'visualizations' / 'AppWorld'

    # Process all traces
    process_all_appworld_traces(traces_dir, output_dir)


if __name__ == '__main__':
    main()
