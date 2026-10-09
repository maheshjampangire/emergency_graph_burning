"""
Quick demonstration and interactive execution of Criticality- and Deadline-Aware Graph Burning.
Shows step-by-step burning rounds, source selections, and outputs Figure 1 & Figure 4.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import DEFAULT_BUDGET_K, DEFAULT_NUM_ROUNDS, CRITICAL_THRESHOLD
from src.data_loader import load_raw_contacts, build_temporal_snapshots, get_active_subsequence
from src.temporal_network import TemporalNetwork
from src.algorithms.proposed import ProposedGraphBurning
from src.evaluation import compute_metrics
from src.visualization import plot_framework_diagram, plot_case_study_network


def run_quick_demo():
    print("=" * 70)
    print(" CRITICALITY- AND DEADLINE-AWARE GRAPH BURNING FOR EMERGENCY ALERTS ")
    print("=" * 70)

    # 1. Load data
    print("\n[Step 1] Loading SocioPatterns Hospital Ward Contact Network...")
    df, nodes_meta = load_raw_contacts()
    print(f" -> Total raw contact records: {len(df)}")
    print(f" -> Total network participants: {len(nodes_meta)}")

    role_counts = {}
    for meta in nodes_meta.values():
        role = meta["role"]
        role_counts[role] = role_counts.get(role, 0) + 1
    print(f" -> Participant roles: {role_counts}")

    # 2. Build 5-minute temporal snapshots
    print("\n[Step 2] Building 5-minute discretized temporal snapshots...")
    all_snapshots = build_temporal_snapshots(df, nodes_meta)
    active_snapshots = get_active_subsequence(all_snapshots, num_rounds=DEFAULT_NUM_ROUNDS, start_index=10)
    network = TemporalNetwork(active_snapshots, nodes_meta)
    print(f" -> Total snapshots created: {len(all_snapshots)}")
    print(f" -> Active experimental window: {len(network.snapshots)} rounds")

    # 3. Initialize and execute Proposed Algorithm
    print(f"\n[Step 3] Executing Proposed Algorithm (Budget K = {DEFAULT_BUDGET_K})...")
    burner = ProposedGraphBurning(network, overlap_weight=0.3)
    result = burner.run(budget_k=DEFAULT_BUDGET_K)

    print("\n" + "-" * 70)
    print(f"{'Round':<8} {'Selected Source':<18} {'Role':<8} {'Crit':<6} {'Newly Reached':<15} {'Total Informed':<15}")
    print("-" * 70)
    for log in result["rounds_log"]:
        src = log["selected_source"]
        if src:
            meta = nodes_meta.get(src, {})
            role = meta.get("role", "N/A")
            crit = meta.get("criticality", 1)
        else:
            role, crit = "-", "-"

        print(f"{log['round']:<8} {str(src):<18} {role:<8} {str(crit):<6} {log['newly_reached_count']:<15} {log['total_informed']:<15}")
    print("-" * 70)

    # 4. Compute Metrics
    print("\n[Step 4] Computing Dissemination Metrics...")
    metrics = compute_metrics(result, network, critical_threshold=CRITICAL_THRESHOLD)
    for metric_name, val in metrics.items():
        if "Coverage" in metric_name or "Ratio" in metric_name:
            print(f" -> {metric_name:<30}: {val:6.2f}%")
        elif "Delay" in metric_name:
            print(f" -> {metric_name:<30}: {val:6.2f} rounds")
        elif "Runtime" in metric_name:
            print(f" -> {metric_name:<30}: {val:6.4f} seconds")

    # 5. Generate Figures
    print("\n[Step 5] Generating Publication Diagrams...")
    fig1 = plot_framework_diagram()
    print(f" -> Saved Figure 1: {fig1}")
    fig4 = plot_case_study_network(network, result)
    print(f" -> Saved Case Study Network Plot: {fig4}")

    print("\n[SUCCESS] Quick demonstration completed successfully!")
    print("Commands:")
    print("  • Run Interactive GUI Player (Play/Pause/Scrubber) : python visualize_interactive.py")
    print("  • Run Full Conference Benchmark Experiments        : python run_experiments.py")
    print("=" * 70)


if __name__ == "__main__":
    if "--gui" in sys.argv:
        from visualize_interactive import InteractiveBurningVisualizer
        import matplotlib.pyplot as plt
        app = InteractiveBurningVisualizer()
        plt.show()
    else:
        run_quick_demo()

