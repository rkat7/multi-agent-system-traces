#!/usr/bin/env python3
"""
Main Execution Script for DAG-Aware Workflow Scheduler
Runs AppWorld traces on vLLM with dependency-aware scheduling
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

from dag_parser import DAGParser
from vllm_client import VLLMClient
from scheduler import WorkflowScheduler, SchedulerConfig
from metrics import MetricsCollector, generate_comparison_report


def main():
    parser = argparse.ArgumentParser(
        description="Execute AppWorld workflow with DAG-aware scheduling on vLLM"
    )
    parser.add_argument(
        "--dag",
        type=str,
        required=True,
        help="Path to DAG JSON file (e.g., visualizations/AppWorld/aa8502b_1_dag.json)"
    )
    parser.add_argument(
        "--vllm-url",
        type=str,
        default="http://127.0.0.1:8000/v1",
        help="vLLM server URL"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="meta-llama/Llama-3.1-8B-Instruct",
        help="Model name on vLLM server"
    )
    parser.add_argument(
        "--policy",
        type=str,
        choices=["sequential", "dependency_aware", "parallel"],
        default="dependency_aware",
        help="Scheduling policy"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=4,
        help="Maximum parallel nodes"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens per node"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--disable-tools",
        action="store_true",
        help="Disable tool calling"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="workflow_scheduler/results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run with multiple policies and compare"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load DAG
    print(f"\n{'='*70}")
    print("LOADING DAG")
    print(f"{'='*70}")
    print(f"DAG file: {args.dag}")

    dag_parser = DAGParser(args.dag)
    dag_parser.load()

    print(dag_parser.visualize_structure())

    # Print statistics
    print(f"\n{'='*70}")
    print("DAG STATISTICS")
    print(f"{'='*70}")
    stats = dag_parser.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Initialize vLLM client
    print(f"\n{'='*70}")
    print("INITIALIZING vLLM CLIENT")
    print(f"{'='*70}")
    print(f"Server URL: {args.vllm_url}")
    print(f"Model: {args.model}")

    vllm_client = VLLMClient(
        base_url=args.vllm_url,
        model_name=args.model
    )

    # Check server health
    print("\nChecking vLLM server health...")
    if not vllm_client.check_health():
        print("✗ ERROR: vLLM server is not responding!")
        print("Please ensure vLLM server is running. Start it with:")
        print("  docker run --rm -it --gpus all -p 8000:8000 --ipc=host \\")
        print("    vllm/vllm-openai:latest \\")
        print("    --model meta-llama/Llama-3.1-8B-Instruct \\")
        print("    --max-model-len 8192 \\")
        print("    --gpu-memory-utilization 0.9")
        sys.exit(1)

    print("✓ vLLM server is healthy")

    # Get available models
    models = vllm_client.get_models()
    print(f"\nAvailable models on server:")
    for model in models:
        print(f"  - {model}")

    # Execute workflow(s)
    if args.compare:
        # Run with multiple policies for comparison
        policies = ["sequential", "dependency_aware"]
        results = {}

        for policy in policies:
            print(f"\n{'='*70}")
            print(f"RUNNING WITH POLICY: {policy}")
            print(f"{'='*70}")

            config = SchedulerConfig(
                scheduling_policy=policy,
                max_parallel_nodes=args.max_parallel,
                enable_tool_calls=not args.disable_tools,
                max_tokens_per_node=args.max_tokens,
                temperature=args.temperature
            )

            # Create fresh scheduler for each run
            scheduler = WorkflowScheduler(dag_parser, vllm_client, config)
            result = scheduler.execute_workflow()

            results[policy] = result

            # Save individual result
            task_id = dag_parser.metadata.get('task_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = output_dir / f"{task_id}_{policy}_{timestamp}.json"
            scheduler.save_results(result, str(result_file))

        # Generate comparison report
        print(f"\n{'='*70}")
        print("GENERATING COMPARISON REPORT")
        print(f"{'='*70}")

        metrics_collector = MetricsCollector()
        for policy, result in results.items():
            metrics_collector.add_execution_result(policy, result)

        report = metrics_collector.generate_report()
        print(report)

        # Save comparison report
        task_id = dag_parser.metadata.get('task_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"{task_id}_comparison_{timestamp}.txt"

        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\nComparison report saved to: {report_file}")

    else:
        # Single execution with specified policy
        config = SchedulerConfig(
            scheduling_policy=args.policy,
            max_parallel_nodes=args.max_parallel,
            enable_tool_calls=not args.disable_tools,
            max_tokens_per_node=args.max_tokens,
            temperature=args.temperature
        )

        scheduler = WorkflowScheduler(dag_parser, vllm_client, config)
        result = scheduler.execute_workflow()

        # Save result
        task_id = dag_parser.metadata.get('task_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = output_dir / f"{task_id}_{args.policy}_{timestamp}.json"
        scheduler.save_results(result, str(result_file))

    # Print final vLLM client statistics
    print(f"\n{'='*70}")
    print("vLLM CLIENT STATISTICS")
    print(f"{'='*70}")
    client_stats = vllm_client.get_statistics()
    for key, value in client_stats.items():
        print(f"  {key}: {value}")

    print(f"\n{'='*70}")
    print("EXECUTION COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
