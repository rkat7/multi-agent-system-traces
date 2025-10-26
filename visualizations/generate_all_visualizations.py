"""
Generate comprehensive visualizations for AG2, AppWorld, and HyperAgent traces.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ag2_visualizer import AG2Visualizer
from appworld_visualizer import AppWorldVisualizer
from hyperagent_visualizer import HyperAgentVisualizer
from unified_visualizer import UnifiedVisualizer


def generate_ag2_visualizations(num_traces=5):
    """Generate AG2 visualizations."""
    print("="*80)
    print("GENERATING AG2 VISUALIZATIONS")
    print("="*80)

    visualizer = AG2Visualizer(trace_dir="../traces/AG2")
    output_dir = "ag2_output"
    os.makedirs(output_dir, exist_ok=True)

    trace_files = list(visualizer.trace_dir.glob("*_human.json"))[:num_traces]

    all_stats = []
    for i, trace_file in enumerate(trace_files, 1):
        print(f"\n[{i}/{len(trace_files)}] Processing: {trace_file.name}")

        try:
            stats = visualizer.generate_trace_report(
                trace_file.name,
                output_dir=output_dir
            )
            all_stats.append(stats)

            print(f"  ✓ Instance: {stats['instance_id'][:20]}...")
            print(f"  ✓ Turns: {stats['total_turns']}")
            print(f"  ✓ Agents: {stats['unique_agents']}")
            print(f"  ✓ Correct: {stats['correct']}")
            print(f"  ✓ Failure modes: {stats['failure_modes_present']}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Generated {len(all_stats)} AG2 visualization sets in {output_dir}/")
    return all_stats


def generate_appworld_visualizations(num_traces=5):
    """Generate AppWorld visualizations."""
    print("\n" + "="*80)
    print("GENERATING APPWORLD VISUALIZATIONS")
    print("="*80)

    visualizer = AppWorldVisualizer(trace_dir="../traces/AppWorld")
    output_dir = "appworld_output"
    os.makedirs(output_dir, exist_ok=True)

    trace_files = list(visualizer.trace_dir.glob("*.txt"))[:num_traces]

    all_stats = []
    for i, trace_file in enumerate(trace_files, 1):
        print(f"\n[{i}/{len(trace_files)}] Processing: {trace_file.name}")

        try:
            stats = visualizer.generate_trace_report(
                trace_file.name,
                output_dir=output_dir
            )
            all_stats.append(stats)

            print(f"  ✓ Task: {stats['task_id']}")
            print(f"  ✓ Events: {stats['total_events']}")
            print(f"  ✓ Agents: {stats['unique_agents']}")
            print(f"  ✓ API calls: {stats['total_api_calls']}")
            print(f"  ✓ Apps: {', '.join(stats['apps_used'][:3])}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Generated {len(all_stats)} AppWorld visualization sets in {output_dir}/")
    return all_stats


def generate_hyperagent_visualizations(num_traces=5):
    """Generate HyperAgent visualizations."""
    print("\n" + "="*80)
    print("GENERATING HYPERAGENT VISUALIZATIONS")
    print("="*80)

    visualizer = HyperAgentVisualizer(trace_dir="../traces/HyperAgent")
    output_dir = "hyperagent_output"
    os.makedirs(output_dir, exist_ok=True)

    trace_files = [f for f in visualizer.trace_dir.glob("*_human.json")][:num_traces]

    all_stats = []
    for i, trace_file in enumerate(trace_files, 1):
        print(f"\n[{i}/{len(trace_files)}] Processing: {trace_file.name}")

        try:
            stats = visualizer.generate_trace_report(
                trace_file.name,
                output_dir=output_dir
            )
            all_stats.append(stats)

            print(f"  ✓ Instance: {stats['instance_id']}")
            print(f"  ✓ Events: {stats['total_events']}")
            print(f"  ✓ Tool calls: {stats['total_tool_calls']}")
            print(f"  ✓ Thought-action cycles: {stats['thought_action_cycles']}")
            print(f"  ✓ Failure modes: {stats['failure_modes_present']}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Generated {len(all_stats)} HyperAgent visualization sets in {output_dir}/")
    return all_stats


def generate_unified_visualizations(ag2_stats, appworld_stats, hyperagent_stats):
    """Generate unified cross-system visualizations."""
    print("\n" + "="*80)
    print("GENERATING UNIFIED CROSS-SYSTEM VISUALIZATIONS")
    print("="*80)

    visualizer = UnifiedVisualizer(base_trace_dir="../traces")
    output_dir = "unified_output"
    os.makedirs(output_dir, exist_ok=True)

    # Add agent type to stats
    for stat in ag2_stats:
        stat['agent_type'] = 'ag2'
    for stat in appworld_stats:
        stat['agent_type'] = 'appworld'
    for stat in hyperagent_stats:
        stat['agent_type'] = 'hyperagent'

    all_stats = ag2_stats + appworld_stats + hyperagent_stats

    print("\n1. Creating comparative analysis...")
    visualizer.compare_agents(
        all_stats,
        output_path=f"{output_dir}/comparison.png",
        show=False
    )
    print("  ✓ Saved: comparison.png")

    print("\n2. Analyzing AG2 failure patterns...")
    visualizer.analyze_failure_patterns(
        'ag2',
        max_traces=20,
        output_path=f"{output_dir}/ag2_failure_patterns.png",
        show=False
    )
    print("  ✓ Saved: ag2_failure_patterns.png")

    print("\n3. Analyzing HyperAgent failure patterns...")
    visualizer.analyze_failure_patterns(
        'hyperagent',
        max_traces=20,
        output_path=f"{output_dir}/hyperagent_failure_patterns.png",
        show=False
    )
    print("  ✓ Saved: hyperagent_failure_patterns.png")

    print(f"\n✓ Generated unified visualizations in {output_dir}/")


def print_summary(ag2_stats, appworld_stats, hyperagent_stats):
    """Print comprehensive summary."""
    print("\n" + "="*80)
    print("VISUALIZATION SUMMARY")
    print("="*80)

    print(f"\n📊 AG2 Statistics:")
    print(f"  • Traces processed: {len(ag2_stats)}")
    if ag2_stats:
        avg_turns = sum(s['total_turns'] for s in ag2_stats) / len(ag2_stats)
        avg_failures = sum(s['failure_modes_present'] for s in ag2_stats) / len(ag2_stats)
        correct_count = sum(1 for s in ag2_stats if s.get('correct'))
        print(f"  • Avg turns per trace: {avg_turns:.1f}")
        print(f"  • Avg failure modes: {avg_failures:.1f}")
        print(f"  • Correct answers: {correct_count}/{len(ag2_stats)}")

    print(f"\n📊 AppWorld Statistics:")
    print(f"  • Traces processed: {len(appworld_stats)}")
    if appworld_stats:
        avg_events = sum(s['total_events'] for s in appworld_stats) / len(appworld_stats)
        avg_api_calls = sum(s['total_api_calls'] for s in appworld_stats) / len(appworld_stats)
        all_apps = set()
        for s in appworld_stats:
            all_apps.update(s['apps_used'])
        print(f"  • Avg events per trace: {avg_events:.1f}")
        print(f"  • Avg API calls: {avg_api_calls:.1f}")
        print(f"  • Unique apps used: {len(all_apps)}")

    print(f"\n📊 HyperAgent Statistics:")
    print(f"  • Traces processed: {len(hyperagent_stats)}")
    if hyperagent_stats:
        avg_events = sum(s['total_events'] for s in hyperagent_stats) / len(hyperagent_stats)
        avg_tools = sum(s['total_tool_calls'] for s in hyperagent_stats) / len(hyperagent_stats)
        avg_cycles = sum(s['thought_action_cycles'] for s in hyperagent_stats) / len(hyperagent_stats)
        avg_failures = sum(s['failure_modes_present'] for s in hyperagent_stats) / len(hyperagent_stats)
        print(f"  • Avg events per trace: {avg_events:.1f}")
        print(f"  • Avg tool calls: {avg_tools:.1f}")
        print(f"  • Avg thought-action cycles: {avg_cycles:.1f}")
        print(f"  • Avg failure modes: {avg_failures:.1f}")

    total_traces = len(ag2_stats) + len(appworld_stats) + len(hyperagent_stats)
    print(f"\n📈 Total Traces Visualized: {total_traces}")

    print("\n" + "="*80)
    print("OUTPUT DIRECTORIES:")
    print("="*80)
    print("  • ag2_output/          - AG2 visualizations")
    print("  • appworld_output/     - AppWorld visualizations")
    print("  • hyperagent_output/   - HyperAgent visualizations")
    print("  • unified_output/      - Cross-system comparisons")
    print("="*80)


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("COMPREHENSIVE AGENT TRAJECTORY VISUALIZATION GENERATOR")
    print("="*80)
    print("\nGenerating visualizations for:")
    print("  1. AG2 (Mathematical Problem Solving)")
    print("  2. AppWorld (Multi-App Task Automation)")
    print("  3. HyperAgent (Software Engineering)")
    print("  4. Unified Cross-System Analysis")

    # Generate individual visualizations
    ag2_stats = generate_ag2_visualizations(num_traces=5)
    appworld_stats = generate_appworld_visualizations(num_traces=5)
    hyperagent_stats = generate_hyperagent_visualizations(num_traces=5)

    # Generate unified visualizations
    generate_unified_visualizations(ag2_stats, appworld_stats, hyperagent_stats)

    # Print summary
    print_summary(ag2_stats, appworld_stats, hyperagent_stats)

    print("\n✅ All visualizations generated successfully!\n")


if __name__ == "__main__":
    main()
