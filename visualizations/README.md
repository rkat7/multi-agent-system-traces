# Agent Workflow DAG Visualizations

This directory contains workflow DAGs (Directed Acyclic Graphs) generated from agent traces for AG2, AppWorld, and HyperAgent systems.

## Overview

Each subdirectory contains DAG visualizations and data for all traces from the respective agent system:

- **AG2/**: 38 conversation workflow DAGs
- **AppWorld/**: 16 multi-agent interaction DAGs
- **HyperAgent/**: 206 planning-execution workflow DAGs

## File Formats

For each trace, three files are generated:

1. **`.png`** - Visual graph representation (NetworkX matplotlib visualization)
2. **`.json`** - Complete DAG data with full node/edge attributes including all trace content
3. **`.graphml`** - GraphML format for import into other graph tools

## DAG Semantics

### AG2 DAGs
- **Nodes**: Conversation turns between agents
  - Attributes: `role`, `agent_name`, `content`, `step_number`
  - Colors: Blue (proxy agents), Green (assistant agents)
- **Edges**: Sequential message flow
  - Type: `sequential_flow`

### AppWorld DAGs
- **Nodes**: Agent interactions, API calls, code executions
  - Types: `agent_response`, `agent_message`, `agent_entry`, `agent_exit`, `code_execution`, `agent_reply`, `api_response`
  - Attributes: Full message content, agent names, line numbers
  - Colors: Different color per node type
- **Edges**: Message passing and control flow
  - Types: `sequential`, `request_response`, `context_entry`, `context_exit`, `execution_result`

### HyperAgent DAGs
- **Nodes**: Planning steps, intern assignments, actions, tool calls
  - Types: `initialization`, `planner_response`, `navigator_response`, `intern_assignment`, `subgoal`, `thought`, `action`, `tool_call`
  - Attributes: Full log content, context information, indices
  - Colors: Different color per step type
- **Edges**: Workflow dependencies
  - Types: `sequential`, `delegation`, `task_assignment`, `execution`, `reasoning_to_action`, `action_execution`

## Usage

### Python (NetworkX)

```python
import networkx as nx
import json

# Load GraphML format
G = nx.read_graphml('AG2/instance_id_dag.graphml')

# Load JSON format with full data
with open('AG2/instance_id_dag.json', 'r') as f:
    dag_data = json.load(f)

# Access node attributes
for node in G.nodes():
    print(G.nodes[node]['label'])
    print(G.nodes[node]['content'])  # Full trace content
```

### Analyzing Workflows

```python
# Count node types
from collections import Counter

node_types = [G.nodes[n]['type'] for n in G.nodes()]
print(Counter(node_types))

# Find longest path (critical path)
longest_path = nx.dag_longest_path(G)
print(f"Critical path length: {len(longest_path)}")

# Analyze branching
out_degrees = dict(G.out_degree())
max_branching = max(out_degrees.values())
print(f"Maximum branching factor: {max_branching}")
```

### Gephi / Cytoscape

Import the `.graphml` files directly into graph visualization tools like Gephi or Cytoscape for interactive exploration and advanced layout algorithms.

## Generation Scripts

The DAGs were generated using:
- `generate_ag2_dags.py` - AG2 trace processor
- `generate_appworld_dags.py` - AppWorld trace processor
- `generate_hyperagent_dags.py` - HyperAgent trace processor

To regenerate all DAGs:
```bash
python3 generate_ag2_dags.py
python3 generate_appworld_dags.py
python3 generate_hyperagent_dags.py
```

## Notes

- All node and edge attributes contain the **full content** from the original traces (not summaries)
- Visualization layouts use NetworkX shell layout (fallback from spring layout for compatibility)
- Large graphs (>100 nodes) may have dense visualizations - use GraphML with external tools for better exploration
- HyperAgent traces with very large workflows (>500 nodes) took longer to process but completed successfully
