#!/usr/bin/env python3
"""
DAG Parser for AppWorld Traces
Parses workflow DAGs and extracts nodes, edges, and dependencies
"""

import json
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque


@dataclass
class WorkflowNode:
    """Represents a single node in the workflow DAG"""
    id: str
    label: str
    type: str
    agent: str
    content: str
    line_number: int
    context: str = None

    # Node type classifications
    is_agent_response: bool = False
    is_code_execution: bool = False
    is_tool_call: bool = False
    is_api_call: bool = False

    def __post_init__(self):
        """Classify node based on type"""
        self.is_agent_response = self.type == "agent_response"
        self.is_code_execution = self.type == "code_execution"
        self.is_tool_call = "api_docs" in self.content or "show_" in self.content
        self.is_api_call = self.type == "api_response"


@dataclass
class WorkflowEdge:
    """Represents an edge (dependency) between nodes"""
    source: str
    target: str
    edge_type: str


class DAGParser:
    """Parses AppWorld DAG JSON files into executable workflow structures"""

    def __init__(self, dag_path: str):
        self.dag_path = dag_path
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self.metadata: Dict[str, Any] = {}

    def load(self) -> None:
        """Load and parse the DAG JSON file"""
        with open(self.dag_path, 'r') as f:
            data = json.load(f)

        self.metadata = data.get('metadata', {})

        # Parse nodes
        for node_data in data.get('nodes', []):
            node = WorkflowNode(
                id=node_data['id'],
                label=node_data['label'],
                type=node_data['type'],
                agent=node_data.get('agent', ''),
                content=node_data['content'],
                line_number=node_data['line_number'],
                context=node_data.get('context')
            )
            self.nodes[node.id] = node

        # Parse edges and build adjacency lists
        for edge_data in data.get('edges', []):
            edge = WorkflowEdge(
                source=edge_data['source'],
                target=edge_data['target'],
                edge_type=edge_data['edge_type']
            )
            self.edges.append(edge)
            self.adjacency_list[edge.source].append(edge.target)
            self.reverse_adjacency[edge.target].append(edge.source)

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm
        Returns list of node IDs in execution order
        """
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node_id in self.nodes:
            in_degree[node_id] = len(self.reverse_adjacency[node_id])

        # Initialize queue with nodes that have no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)

            # Reduce in-degree for dependent nodes
            for neighbor in self.adjacency_list[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(sorted_nodes) != len(self.nodes):
            raise ValueError("DAG contains cycles - cannot perform topological sort")

        return sorted_nodes

    def get_execution_batches(self) -> List[List[str]]:
        """
        Group nodes into batches that can be executed in parallel
        Returns list of batches, where each batch contains node IDs that can run concurrently
        """
        # Calculate in-degrees
        in_degree = {node_id: len(self.reverse_adjacency[node_id]) for node_id in self.nodes}

        batches = []
        processed = set()

        while len(processed) < len(self.nodes):
            # Find all nodes with satisfied dependencies
            current_batch = []
            for node_id in self.nodes:
                if node_id not in processed:
                    # Check if all dependencies are satisfied
                    dependencies_met = all(
                        dep in processed
                        for dep in self.reverse_adjacency[node_id]
                    )
                    if dependencies_met:
                        current_batch.append(node_id)

            if not current_batch:
                raise ValueError("Unable to create execution batches - possible cycle in DAG")

            batches.append(current_batch)
            processed.update(current_batch)

        return batches

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all dependencies (predecessors) for a given node"""
        return self.reverse_adjacency[node_id]

    def get_dependents(self, node_id: str) -> List[str]:
        """Get all dependents (successors) for a given node"""
        return self.adjacency_list[node_id]

    def get_agent_nodes(self, agent_name: str) -> List[WorkflowNode]:
        """Get all nodes belonging to a specific agent"""
        return [node for node in self.nodes.values() if node.agent == agent_name]

    def get_nodes_by_type(self, node_type: str) -> List[WorkflowNode]:
        """Get all nodes of a specific type"""
        return [node for node in self.nodes.values() if node.type == node_type]

    def get_critical_path(self) -> List[str]:
        """
        Find the critical path (longest path) through the DAG
        Returns list of node IDs representing the critical path
        """
        # Initialize distances
        distances = {node_id: 0 for node_id in self.nodes}
        predecessors = {node_id: None for node_id in self.nodes}

        # Process nodes in topological order
        topo_order = self.topological_sort()

        for node_id in topo_order:
            for dependent in self.adjacency_list[node_id]:
                new_distance = distances[node_id] + 1
                if new_distance > distances[dependent]:
                    distances[dependent] = new_distance
                    predecessors[dependent] = node_id

        # Find the node with maximum distance
        end_node = max(distances, key=distances.get)

        # Reconstruct path
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = predecessors[current]

        return list(reversed(path))

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the DAG"""
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'num_agents': len(set(node.agent for node in self.nodes.values() if node.agent)),
            'node_type_counts': self._count_node_types(),
            'edge_type_counts': self._count_edge_types(),
            'max_depth': max(self._calculate_depths().values()) if self.nodes else 0,
            'critical_path_length': len(self.get_critical_path())
        }

    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = defaultdict(int)
        for node in self.nodes.values():
            counts[node.type] += 1
        return dict(counts)

    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type"""
        counts = defaultdict(int)
        for edge in self.edges:
            counts[edge.edge_type] += 1
        return dict(counts)

    def _calculate_depths(self) -> Dict[str, int]:
        """Calculate depth of each node from root"""
        depths = {}
        visited = set()

        # Find root nodes (no incoming edges)
        roots = [node_id for node_id in self.nodes if not self.reverse_adjacency[node_id]]

        # BFS to calculate depths
        queue = deque([(root, 0) for root in roots])

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue

            visited.add(node_id)
            depths[node_id] = depth

            for dependent in self.adjacency_list[node_id]:
                queue.append((dependent, depth + 1))

        return depths

    def visualize_structure(self) -> str:
        """Generate a text-based visualization of the DAG structure"""
        lines = []
        lines.append(f"=== DAG Structure: {self.metadata.get('task_id', 'Unknown')} ===")
        lines.append(f"Task: {self.metadata.get('task_description', 'N/A')}")
        lines.append(f"\nTotal Nodes: {len(self.nodes)}")
        lines.append(f"Total Edges: {len(self.edges)}")
        lines.append(f"\nExecution Batches:")

        batches = self.get_execution_batches()
        for i, batch in enumerate(batches):
            lines.append(f"\n  Batch {i+1} ({len(batch)} nodes - can run in parallel):")
            for node_id in batch:
                node = self.nodes[node_id]
                lines.append(f"    - {node_id}: {node.label} ({node.type}) [Agent: {node.agent or 'N/A'}]")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the parser
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dag_parser.py <path_to_dag.json>")
        sys.exit(1)

    parser = DAGParser(sys.argv[1])
    parser.load()

    print(parser.visualize_structure())
    print("\n" + "="*60)
    print("Statistics:")
    stats = parser.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
