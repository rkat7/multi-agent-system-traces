#!/usr/bin/env python3
"""
Metrics Collection and Analysis
Tracks and compares performance across different scheduling policies
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict

from scheduler import WorkflowExecutionResult, NodeExecutionResult


@dataclass
class PolicyMetrics:
    """Metrics for a single scheduling policy"""
    policy_name: str
    total_time_ms: float
    total_tokens: int
    nodes_executed: int
    total_nodes: int
    total_batches: int
    avg_latency_per_node_ms: float
    tokens_per_second: float
    parallelism_factor: float  # nodes/batches
    success: bool


class MetricsCollector:
    """Collects and analyzes metrics from workflow executions"""

    def __init__(self):
        self.execution_results: Dict[str, WorkflowExecutionResult] = {}
        self.policy_metrics: Dict[str, PolicyMetrics] = {}

    def add_execution_result(self, policy_name: str, result: WorkflowExecutionResult):
        """Add an execution result for analysis"""
        self.execution_results[policy_name] = result

        # Calculate metrics
        avg_latency = result.total_time_ms / result.nodes_executed if result.nodes_executed > 0 else 0
        tokens_per_sec = (result.total_tokens / result.total_time_ms * 1000) if result.total_time_ms > 0 else 0
        parallelism = result.nodes_executed / result.total_batches if result.total_batches > 0 else 1

        metrics = PolicyMetrics(
            policy_name=policy_name,
            total_time_ms=result.total_time_ms,
            total_tokens=result.total_tokens,
            nodes_executed=result.nodes_executed,
            total_nodes=result.total_nodes,
            total_batches=result.total_batches,
            avg_latency_per_node_ms=avg_latency,
            tokens_per_second=tokens_per_sec,
            parallelism_factor=parallelism,
            success=result.success
        )

        self.policy_metrics[policy_name] = metrics

    def generate_report(self) -> str:
        """Generate a comprehensive comparison report"""
        if not self.policy_metrics:
            return "No metrics collected"

        lines = []
        lines.append("=" * 80)
        lines.append("SCHEDULING POLICY COMPARISON REPORT")
        lines.append("=" * 80)

        # Overall comparison table
        lines.append("\n## Overall Metrics\n")
        lines.append(f"{'Policy':<20} {'Time (ms)':<12} {'Tokens':<10} {'Batches':<10} {'Parallel':<10} {'Success':<8}")
        lines.append("-" * 80)

        for policy_name, metrics in self.policy_metrics.items():
            lines.append(
                f"{policy_name:<20} "
                f"{metrics.total_time_ms:<12.0f} "
                f"{metrics.total_tokens:<10} "
                f"{metrics.total_batches:<10} "
                f"{metrics.parallelism_factor:<10.2f} "
                f"{'✓' if metrics.success else '✗':<8}"
            )

        # Performance comparison
        if len(self.policy_metrics) >= 2:
            lines.append("\n## Performance Improvements\n")

            baseline_name = "sequential"
            if baseline_name in self.policy_metrics:
                baseline = self.policy_metrics[baseline_name]

                for policy_name, metrics in self.policy_metrics.items():
                    if policy_name == baseline_name:
                        continue

                    speedup = baseline.total_time_ms / metrics.total_time_ms if metrics.total_time_ms > 0 else 0
                    time_saved = baseline.total_time_ms - metrics.total_time_ms
                    throughput_improvement = (metrics.tokens_per_second - baseline.tokens_per_second) / baseline.tokens_per_second * 100 if baseline.tokens_per_second > 0 else 0

                    lines.append(f"{policy_name} vs {baseline_name}:")
                    lines.append(f"  Speedup: {speedup:.2f}x")
                    lines.append(f"  Time saved: {time_saved:.0f}ms ({time_saved/1000:.2f}s)")
                    lines.append(f"  Throughput improvement: {throughput_improvement:+.1f}%")
                    lines.append(f"  Parallelism factor: {metrics.parallelism_factor:.2f}")
                    lines.append("")

        # Detailed metrics per policy
        lines.append("\n## Detailed Metrics by Policy\n")

        for policy_name, metrics in self.policy_metrics.items():
            lines.append(f"### {policy_name.upper()}")
            lines.append(f"  Total execution time: {metrics.total_time_ms:.0f}ms ({metrics.total_time_ms/1000:.2f}s)")
            lines.append(f"  Total tokens: {metrics.total_tokens}")
            lines.append(f"  Tokens/second: {metrics.tokens_per_second:.2f}")
            lines.append(f"  Nodes executed: {metrics.nodes_executed}/{metrics.total_nodes}")
            lines.append(f"  Total batches: {metrics.total_batches}")
            lines.append(f"  Avg parallelism: {metrics.parallelism_factor:.2f} nodes/batch")
            lines.append(f"  Avg latency per node: {metrics.avg_latency_per_node_ms:.0f}ms")
            lines.append(f"  Success: {'✓' if metrics.success else '✗'}")
            lines.append("")

        # Node-level analysis
        lines.append("\n## Node-Level Analysis\n")

        for policy_name, result in self.execution_results.items():
            lines.append(f"### {policy_name.upper()}")

            # Group by node type
            by_type = defaultdict(list)
            for node_result in result.node_results:
                by_type[node_result.node_type].append(node_result)

            for node_type, nodes in sorted(by_type.items()):
                avg_latency = sum(n.latency_ms for n in nodes) / len(nodes) if nodes else 0
                total_tokens = sum(n.tokens_used for n in nodes)
                lines.append(f"  {node_type}:")
                lines.append(f"    Count: {len(nodes)}")
                lines.append(f"    Avg latency: {avg_latency:.0f}ms")
                lines.append(f"    Total tokens: {total_tokens}")

            lines.append("")

        # Tool calls analysis
        lines.append("\n## Tool Calls Analysis\n")

        for policy_name, result in self.execution_results.items():
            tool_calls = [
                node for node in result.node_results
                if node.tool_calls and len(node.tool_calls) > 0
            ]

            if tool_calls:
                lines.append(f"### {policy_name.upper()}")
                lines.append(f"  Nodes with tool calls: {len(tool_calls)}")

                for node in tool_calls:
                    lines.append(f"    {node.node_id} ({node.agent_name}):")
                    for tool_call in node.tool_calls:
                        lines.append(f"      - {tool_call['name']}({tool_call.get('arguments', {})})")

                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def export_json(self, filepath: str):
        """Export metrics to JSON file"""
        data = {
            "policy_metrics": {
                name: {
                    "total_time_ms": m.total_time_ms,
                    "total_tokens": m.total_tokens,
                    "nodes_executed": m.nodes_executed,
                    "total_batches": m.total_batches,
                    "avg_latency_per_node_ms": m.avg_latency_per_node_ms,
                    "tokens_per_second": m.tokens_per_second,
                    "parallelism_factor": m.parallelism_factor,
                    "success": m.success
                }
                for name, m in self.policy_metrics.items()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def generate_comparison_report(results: Dict[str, WorkflowExecutionResult]) -> str:
    """Helper function to generate comparison report from results dict"""
    collector = MetricsCollector()
    for policy_name, result in results.items():
        collector.add_execution_result(policy_name, result)
    return collector.generate_report()


if __name__ == "__main__":
    # Test metrics collector
    print("Metrics collector module loaded successfully")
