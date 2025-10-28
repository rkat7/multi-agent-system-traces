#!/usr/bin/env python3
"""
DAG-Aware Workflow Scheduler
Schedules and executes multi-agent workflows with dependency tracking
"""

import time
import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

from dag_parser import DAGParser, WorkflowNode
from vllm_client import VLLMClient, InferenceRequest, InferenceResponse, ToolRegistry


@dataclass
class SchedulerConfig:
    """Configuration for the workflow scheduler"""
    scheduling_policy: str = "dependency_aware"  # Options: sequential, dependency_aware, parallel
    max_parallel_nodes: int = 4
    enable_tool_calls: bool = True
    max_tokens_per_node: int = 512
    temperature: float = 0.7
    retry_failed_nodes: bool = False
    max_retries: int = 2


@dataclass
class NodeExecutionResult:
    """Result of executing a single node"""
    node_id: str
    node_type: str
    agent_name: str
    start_time: float
    end_time: float
    latency_ms: float
    original_content: str
    generated_content: str
    tokens_used: int
    tool_calls: Optional[List[Dict]] = None
    error: Optional[str] = None
    dependencies_met: bool = True


@dataclass
class WorkflowExecutionResult:
    """Complete workflow execution result"""
    task_id: str
    task_description: str
    total_nodes: int
    nodes_executed: int
    total_batches: int
    total_time_ms: float
    total_tokens: int
    scheduling_policy: str
    node_results: List[NodeExecutionResult]
    success: bool
    error: Optional[str] = None


class WorkflowScheduler:
    """
    DAG-aware scheduler for multi-agent workflows
    Implements dependency-aware batching and parallel execution
    """

    def __init__(
        self,
        dag_parser: DAGParser,
        vllm_client: VLLMClient,
        config: SchedulerConfig
    ):
        self.dag_parser = dag_parser
        self.vllm_client = vllm_client
        self.config = config

        # Execution state
        self.completed_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        self.node_results: Dict[str, NodeExecutionResult] = {}
        self.execution_start_time: Optional[float] = None

    def create_prompt_for_node(self, node: WorkflowNode) -> str:
        """
        Create an appropriate prompt for a node based on its type and context
        """
        # Get previous context from dependencies
        dependencies = self.dag_parser.get_dependencies(node.id)
        context_parts = []

        if dependencies:
            context_parts.append("=== Previous Context ===")
            for dep_id in dependencies[-3:]:  # Last 3 dependencies for context
                if dep_id in self.node_results:
                    dep_result = self.node_results[dep_id]
                    context_parts.append(
                        f"[{dep_result.agent_name}]: {dep_result.generated_content[:200]}"
                    )

        # Build system prompt based on agent role
        system_prompt = self._get_system_prompt_for_agent(node.agent)

        # Build the actual task prompt
        task_description = self.dag_parser.metadata.get('task_description', '')

        prompt_parts = [system_prompt]

        if context_parts:
            prompt_parts.append("\n".join(context_parts))

        # Add specific instructions based on node type
        if node.is_agent_response:
            prompt_parts.append(f"\n=== Current Task ===\n{task_description}")
            prompt_parts.append(f"\n=== Your Response ===")
            prompt_parts.append("Generate the next action or response as the agent.")
        elif node.is_code_execution:
            prompt_parts.append("\nExecute the code and provide the output.")

        # Add original trace content as reference (for comparison)
        prompt_parts.append(f"\n=== Reference (Original Trace) ===\n{node.content[:300]}...")

        return "\n\n".join(prompt_parts)

    def _get_system_prompt_for_agent(self, agent_name: str) -> str:
        """Get system prompt based on agent role"""
        agent_lower = agent_name.lower() if agent_name else ""

        if "supervisor" in agent_lower:
            return """You are a Supervisor Agent in a multi-agent system. Your role is to:
- Coordinate tasks between different app-specific agents
- Manage workflow and delegate subtasks
- Retrieve necessary information from system APIs
- Make decisions about next steps
You have access to supervisor APIs and can send messages to other agents."""

        elif "spotify" in agent_lower:
            return """You are a Spotify Agent. Your role is to:
- Handle Spotify-related tasks and API calls
- Retrieve liked songs, playlists, and artist information
- Follow/unfollow artists
- Manage Spotify authentication
You have access to Spotify APIs."""

        else:
            return f"""You are an agent in a multi-agent system. Your role: {agent_name}.
Assist with your specific responsibilities and communicate with other agents as needed."""

    def execute_node(self, node: WorkflowNode) -> NodeExecutionResult:
        """Execute a single node"""
        start_time = time.time()

        try:
            # Check if this is an agent response node that needs LLM generation
            if node.is_agent_response:
                # Create prompt
                prompt = self.create_prompt_for_node(node)

                # Get tools for this agent
                tools = None
                if self.config.enable_tool_calls:
                    tools = ToolRegistry.get_tools_for_agent(node.agent)

                # Create inference request
                request = InferenceRequest(
                    node_id=node.id,
                    prompt=prompt,
                    agent_name=node.agent,
                    node_type=node.type,
                    max_tokens=self.config.max_tokens_per_node,
                    temperature=self.config.temperature,
                    tools=tools
                )

                # Generate response via vLLM
                response = self.vllm_client.generate(request)

                end_time = time.time()

                return NodeExecutionResult(
                    node_id=node.id,
                    node_type=node.type,
                    agent_name=node.agent,
                    start_time=start_time,
                    end_time=end_time,
                    latency_ms=(end_time - start_time) * 1000,
                    original_content=node.content,
                    generated_content=response.content,
                    tokens_used=response.tokens_used,
                    tool_calls=response.tool_calls,
                    error=None if response.finish_reason != "error" else response.content
                )

            else:
                # Non-LLM nodes (code execution, messages, etc.) - just record
                end_time = time.time()

                return NodeExecutionResult(
                    node_id=node.id,
                    node_type=node.type,
                    agent_name=node.agent or "system",
                    start_time=start_time,
                    end_time=end_time,
                    latency_ms=(end_time - start_time) * 1000,
                    original_content=node.content,
                    generated_content=f"[Simulated: {node.type}]",
                    tokens_used=0,
                    tool_calls=None
                )

        except Exception as e:
            end_time = time.time()
            return NodeExecutionResult(
                node_id=node.id,
                node_type=node.type,
                agent_name=node.agent or "unknown",
                start_time=start_time,
                end_time=end_time,
                latency_ms=(end_time - start_time) * 1000,
                original_content=node.content,
                generated_content="",
                tokens_used=0,
                error=str(e),
                dependencies_met=False
            )

    def execute_batch(self, batch_node_ids: List[str]) -> List[NodeExecutionResult]:
        """Execute a batch of nodes that can run in parallel"""
        results = []

        print(f"\n  Executing batch of {len(batch_node_ids)} nodes...")

        for node_id in batch_node_ids:
            node = self.dag_parser.nodes[node_id]
            print(f"    - {node_id}: {node.label} ({node.agent})")

            result = self.execute_node(node)
            results.append(result)

            # Track completion
            if result.error:
                self.failed_nodes.add(node_id)
                print(f"      ✗ FAILED: {result.error}")
            else:
                self.completed_nodes.add(node_id)
                print(f"      ✓ Completed in {result.latency_ms:.0f}ms, {result.tokens_used} tokens")

            # Store result
            self.node_results[node_id] = result

        return results

    def execute_workflow(self) -> WorkflowExecutionResult:
        """Execute the entire workflow using the configured scheduling policy"""
        self.execution_start_time = time.time()
        all_results = []

        print(f"\n{'='*70}")
        print(f"EXECUTING WORKFLOW: {self.dag_parser.metadata.get('task_id', 'Unknown')}")
        print(f"Task: {self.dag_parser.metadata.get('task_description', 'N/A')}")
        print(f"Scheduling Policy: {self.config.scheduling_policy}")
        print(f"{'='*70}")

        try:
            if self.config.scheduling_policy == "sequential":
                all_results = self._execute_sequential()
            elif self.config.scheduling_policy == "dependency_aware":
                all_results = self._execute_dependency_aware()
            elif self.config.scheduling_policy == "parallel":
                all_results = self._execute_parallel()
            else:
                raise ValueError(f"Unknown scheduling policy: {self.config.scheduling_policy}")

            execution_end_time = time.time()
            total_time_ms = (execution_end_time - self.execution_start_time) * 1000

            # Calculate totals
            total_tokens = sum(r.tokens_used for r in all_results)
            success = len(self.failed_nodes) == 0

            print(f"\n{'='*70}")
            print(f"WORKFLOW EXECUTION COMPLETED")
            print(f"  Total Time: {total_time_ms:.0f}ms ({total_time_ms/1000:.2f}s)")
            print(f"  Nodes Executed: {len(self.completed_nodes)}/{len(self.dag_parser.nodes)}")
            print(f"  Failed Nodes: {len(self.failed_nodes)}")
            print(f"  Total Tokens: {total_tokens}")
            print(f"  Success: {success}")
            print(f"{'='*70}\n")

            return WorkflowExecutionResult(
                task_id=self.dag_parser.metadata.get('task_id', 'unknown'),
                task_description=self.dag_parser.metadata.get('task_description', ''),
                total_nodes=len(self.dag_parser.nodes),
                nodes_executed=len(self.completed_nodes),
                total_batches=len(self._get_batches()),
                total_time_ms=total_time_ms,
                total_tokens=total_tokens,
                scheduling_policy=self.config.scheduling_policy,
                node_results=all_results,
                success=success
            )

        except Exception as e:
            execution_end_time = time.time()
            total_time_ms = (execution_end_time - self.execution_start_time) * 1000

            print(f"\n{'='*70}")
            print(f"WORKFLOW EXECUTION FAILED: {str(e)}")
            print(f"{'='*70}\n")

            return WorkflowExecutionResult(
                task_id=self.dag_parser.metadata.get('task_id', 'unknown'),
                task_description=self.dag_parser.metadata.get('task_description', ''),
                total_nodes=len(self.dag_parser.nodes),
                nodes_executed=len(self.completed_nodes),
                total_batches=0,
                total_time_ms=total_time_ms,
                total_tokens=sum(r.tokens_used for r in all_results),
                scheduling_policy=self.config.scheduling_policy,
                node_results=all_results,
                success=False,
                error=str(e)
            )

    def _execute_sequential(self) -> List[NodeExecutionResult]:
        """Execute nodes sequentially in topological order"""
        all_results = []
        topo_order = self.dag_parser.topological_sort()

        print(f"\nExecuting {len(topo_order)} nodes sequentially...\n")

        for i, node_id in enumerate(topo_order):
            print(f"[{i+1}/{len(topo_order)}] Processing {node_id}...")
            batch_results = self.execute_batch([node_id])
            all_results.extend(batch_results)

        return all_results

    def _execute_dependency_aware(self) -> List[NodeExecutionResult]:
        """Execute nodes in batches based on dependency satisfaction"""
        all_results = []
        batches = self._get_batches()

        print(f"\nExecuting {len(batches)} dependency-aware batches...\n")

        for i, batch in enumerate(batches):
            print(f"Batch {i+1}/{len(batches)}: {len(batch)} nodes")
            batch_results = self.execute_batch(batch)
            all_results.extend(batch_results)

        return all_results

    def _execute_parallel(self) -> List[NodeExecutionResult]:
        """Execute as many nodes in parallel as possible (aggressive batching)"""
        # Similar to dependency_aware but with higher parallelism
        return self._execute_dependency_aware()

    def _get_batches(self) -> List[List[str]]:
        """Get execution batches based on dependencies"""
        return self.dag_parser.get_execution_batches()

    def save_results(self, result: WorkflowExecutionResult, output_path: str):
        """Save execution results to JSON file"""
        result_dict = asdict(result)

        # Add timestamp
        result_dict['execution_timestamp'] = datetime.now().isoformat()

        with open(output_path, 'w') as f:
            json.dump(result_dict, f, indent=2)

        print(f"Results saved to: {output_path}")
