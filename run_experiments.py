"""
Comprehensive experiment suite for the Conference Paper.
Executes Scenarios 1 to 5, calculates statistical means and standard deviations over 5 repeated runs,
and generates:
- Table 1: Dataset & Experimental Configuration (CSV, MD, LaTeX)
- Table 2: Main Performance Comparison (CSV, MD, LaTeX)
- Table 3: Ablation Study (CSV, MD, LaTeX)
- Figure 1: Proposed Architecture Diagram (PNG)
- Figure 2: Timely Coverage vs. Source Budget K (PNG)
- Figure 3: Robustness Under Link Failure (PNG)
- Figure 4: Visual Case Study Network Diagram (PNG)
"""

import sys
import copy
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import (
    SOURCE_BUDGETS,
    EDGE_REMOVAL_RATES,
    NUM_REPEATED_RUNS,
    RANDOM_SEEDS,
    DEFAULT_BUDGET_K,
    DEFAULT_NUM_ROUNDS,
    ROLE_CRITICALITY,
    CRITICAL_THRESHOLD,
    FIGURES_DIR,
    TABLES_DIR
)
from src.data_loader import load_raw_contacts, build_temporal_snapshots, get_active_subsequence
from src.temporal_network import TemporalNetwork
from src.algorithms.proposed import ProposedGraphBurning
from src.algorithms.baselines import (
    RandomBurning,
    DegreeBurning,
    BetweennessBurning,
    FarthestFirstBurning,
    CriticalityOnlyBurning
)
from src.evaluation import compute_metrics
from src.visualization import (
    plot_framework_diagram,
    plot_coverage_vs_budget,
    plot_robustness_link_failure,
    plot_case_study_network,
    export_dataframe_tables
)


def run_single_method(
    method_name: str,
    network: TemporalNetwork,
    budget_k: int,
    seed: int,
    **kwargs
) -> Dict[str, Any]:
    """Instantiate and run a specific algorithm."""
    if method_name == "Proposed method":
        burner = ProposedGraphBurning(
            network=network,
            overlap_weight=kwargs.get("overlap_weight", 0.3),
            enable_criticality=kwargs.get("enable_criticality", True),
            enable_deadlines=kwargs.get("enable_deadlines", True),
            enable_overlap_penalty=kwargs.get("enable_overlap_penalty", True)
        )
        return burner.run(budget_k=budget_k)

    elif method_name == "Random burning":
        burner = RandomBurning(network)
        return burner.run(budget_k=budget_k, seed=seed)

    elif method_name == "Degree-based burning":
        burner = DegreeBurning(network)
        return burner.run(budget_k=budget_k, seed=seed)

    elif method_name == "Betweenness-based burning":
        burner = BetweennessBurning(network)
        return burner.run(budget_k=budget_k, seed=seed)

    elif method_name == "Farthest-first burning":
        burner = FarthestFirstBurning(network)
        return burner.run(budget_k=budget_k, seed=seed)

    elif method_name == "Criticality-only burning":
        burner = CriticalityOnlyBurning(network)
        return burner.run(budget_k=budget_k, seed=seed)

    else:
        raise ValueError(f"Unknown algorithm: {method_name}")


def generate_table1(nodes_meta: Dict[str, Any]) -> pd.DataFrame:
    """Generate Table 1: Dataset and Experimental Configuration."""
    med_count = sum(1 for m in nodes_meta.values() if m["role"] == "MED")
    nur_count = sum(1 for m in nodes_meta.values() if m["role"] == "NUR")
    pat_count = sum(1 for m in nodes_meta.values() if m["role"] == "PAT")
    adm_count = sum(1 for m in nodes_meta.values() if m["role"] == "ADM")

    data = [
        {"Item": "Dataset", "Setting": "SocioPatterns hospital ward"},
        {"Item": "Total participants", "Setting": f"75 ({med_count} Doctors, {nur_count} Nurses, {pat_count} Patients, {adm_count} Admin)"},
        {"Item": "Contact interval", "Setting": "20 seconds"},
        {"Item": "Graph snapshot duration", "Setting": "5 minutes (300 s)"},
        {"Item": "Experimental horizon", "Setting": f"{DEFAULT_NUM_ROUNDS} rounds (30 minutes total)"},
        {"Item": "Source budgets (K)", "Setting": "2, 3, 4, 5, and 6 sources"},
        {"Item": "Edge-removal failure rates", "Setting": "0%, 10%, 20%, 30%, and 40%"},
        {"Item": "Overlap penalty weight (Lambda)", "Setting": "0.3"},
        {"Item": "Delivery deadline rule", "Setting": "Deadline(i) = 7 - Criticality(i)"},
        {"Item": "Number of repeated runs", "Setting": f"{NUM_REPEATED_RUNS}"}
    ]
    df = pd.DataFrame(data)
    export_dataframe_tables(df, "table1_config", "Table 1: Dataset and Experimental Configuration")
    return df


def run_table2_main_comparison(base_network: TemporalNetwork) -> pd.DataFrame:
    """Run Table 2: Main Performance Comparison (5 runs, mean +/- std)."""
    print("\n--- Running Experiments for Table 2 (Main Performance Comparison) ---")
    algorithms = [
        "Random burning",
        "Degree-based burning",
        "Betweenness-based burning",
        "Farthest-first burning",
        "Criticality-only burning",
        "Proposed method"
    ]

    records = []

    for alg in algorithms:
        runs_crit = []
        runs_weighted = []
        runs_delay = []
        runs_runtime = []

        for seed in RANDOM_SEEDS[:NUM_REPEATED_RUNS]:
            net = base_network.clone()
            res = run_single_method(alg, net, budget_k=DEFAULT_BUDGET_K, seed=seed)
            m = compute_metrics(res, net)

            runs_crit.append(m["Timely Critical Coverage"])
            runs_weighted.append(m["Weighted Timely Coverage"])
            runs_delay.append(m["Average Delay"])
            runs_runtime.append(m["Runtime"])

        c_mean, c_std = np.mean(runs_crit), np.std(runs_crit)
        w_mean, w_std = np.mean(runs_weighted), np.std(runs_weighted)
        d_mean, d_std = np.mean(runs_delay), np.std(runs_delay)
        rt_mean = np.mean(runs_runtime)

        records.append({
            "Method": alg,
            "Timely Critical Coverage": f"{c_mean:5.2f} ± {c_std:4.2f}%",
            "Weighted Timely Coverage": f"{w_mean:5.2f} ± {w_std:4.2f}%",
            "Average Delay": f"{d_mean:4.2f} ± {d_std:4.2f}",
            "Runtime (s)": f"{rt_mean:6.4f}"
        })
        print(f" -> Completed {alg:<26}: Critical={c_mean:5.2f}%, Weighted={w_mean:5.2f}%, Delay={d_mean:4.2f}")

    df_t2 = pd.DataFrame(records)
    export_dataframe_tables(df_t2, "table2_main_comparison", "Table 2: Main Performance Comparison")
    return df_t2


def run_table3_ablation(base_network: TemporalNetwork) -> pd.DataFrame:
    """Run Table 3: Ablation Study."""
    print("\n--- Running Experiments for Table 3 (Ablation Study) ---")
    variations = [
        ("Complete proposed method", {"enable_criticality": True, "enable_deadlines": True, "enable_overlap_penalty": True}),
        ("Without criticality", {"enable_criticality": False, "enable_deadlines": True, "enable_overlap_penalty": True}),
        ("Without deadlines", {"enable_criticality": True, "enable_deadlines": False, "enable_overlap_penalty": True}),
        ("Without overlap penalty", {"enable_criticality": True, "enable_deadlines": True, "enable_overlap_penalty": False}),
        ("Without temporal information", {"enable_criticality": True, "enable_deadlines": True, "enable_overlap_penalty": True, "static": True})
    ]

    records = []

    for name, params in variations:
        runs_crit = []
        runs_weighted = []
        runs_overlap = []

        for seed in RANDOM_SEEDS[:NUM_REPEATED_RUNS]:
            if params.get("static", False):
                # Static ablation: collapse all snapshots into static replicated graph
                static_g = nx.Graph()
                for g in base_network.snapshots:
                    static_g.add_nodes_from(g.nodes(data=True))
                    static_g.add_edges_from(g.edges())
                net = TemporalNetwork([static_g.copy() for _ in range(base_network.num_rounds)], base_network.nodes_meta)
            else:
                net = base_network.clone()

            res = run_single_method(
                "Proposed method",
                net,
                budget_k=DEFAULT_BUDGET_K,
                seed=seed,
                **params
            )
            m = compute_metrics(res, net)
            runs_crit.append(m["Timely Critical Coverage"])
            runs_weighted.append(m["Weighted Timely Coverage"])
            runs_overlap.append(m["Source-Overlap Ratio"])

        c_mean, c_std = np.mean(runs_crit), np.std(runs_crit)
        w_mean, w_std = np.mean(runs_weighted), np.std(runs_weighted)
        o_mean, o_std = np.mean(runs_overlap), np.std(runs_overlap)

        records.append({
            "Method variation": name,
            "Timely Critical Coverage": f"{c_mean:5.2f} ± {c_std:4.2f}%",
            "Weighted Coverage": f"{w_mean:5.2f} ± {w_std:4.2f}%",
            "Overlap Ratio": f"{o_mean:5.3f} ± {o_std:4.3f}"
        })
        print(f" -> Completed {name:<30}: Critical={c_mean:5.2f}%, Overlap={o_mean:5.3f}")

    df_t3 = pd.DataFrame(records)
    export_dataframe_tables(df_t3, "table3_ablation", "Table 3: Ablation Study")
    return df_t3


def run_figure2_budget_study(base_network: TemporalNetwork) -> pd.DataFrame:
    """Evaluate Timely Critical Coverage across different source budgets K (2 to 6)."""
    print("\n--- Running Experiments for Figure 2 (Timely Coverage vs. Budget K) ---")
    algorithms = [
        "Random burning",
        "Degree-based burning",
        "Betweenness-based burning",
        "Farthest-first burning",
        "Criticality-only burning",
        "Proposed method"
    ]

    records = []
    for k in SOURCE_BUDGETS:
        for alg in algorithms:
            runs_crit = []
            for seed in RANDOM_SEEDS[:NUM_REPEATED_RUNS]:
                net = base_network.clone()
                res = run_single_method(alg, net, budget_k=k, seed=seed)
                m = compute_metrics(res, net)
                runs_crit.append(m["Timely Critical Coverage"])

            records.append({
                "Source Budget": k,
                "Algorithm": alg,
                "Timely Critical Coverage Mean": np.mean(runs_crit),
                "Timely Critical Coverage Std": np.std(runs_crit)
            })

    df = pd.DataFrame(records)
    plot_coverage_vs_budget(df)
    return df


def run_figure3_link_failure_study(base_network: TemporalNetwork) -> pd.DataFrame:
    """Evaluate Weighted Timely Coverage across edge failure rates (0% to 40%)."""
    print("\n--- Running Experiments for Figure 3 (Robustness Under Link Failure) ---")
    algorithms = [
        "Random burning",
        "Degree-based burning",
        "Betweenness-based burning",
        "Farthest-first burning",
        "Criticality-only burning",
        "Proposed method"
    ]

    records = []
    for rate in EDGE_REMOVAL_RATES:
        for alg in algorithms:
            runs_weighted = []
            for seed in RANDOM_SEEDS[:NUM_REPEATED_RUNS]:
                net = base_network.apply_random_edge_removal(removal_rate=rate, seed=seed)
                res = run_single_method(alg, net, budget_k=DEFAULT_BUDGET_K, seed=seed)
                m = compute_metrics(res, net)
                runs_weighted.append(m["Weighted Timely Coverage"])

            records.append({
                "Edge Removal Rate": rate,
                "Algorithm": alg,
                "Weighted Timely Coverage Mean": np.mean(runs_weighted),
                "Weighted Timely Coverage Std": np.std(runs_weighted)
            })

    df = pd.DataFrame(records)
    plot_robustness_link_failure(df)
    return df


def main():
    print("======================================================================")
    print(" STARTING FULL EXPERIMENTAL BENCHMARK SUITE FOR CONFERENCE PAPER ")
    print("======================================================================")

    # 1. Prepare data
    print("\n[Stage 1] Loading Contact Data & Snapshots...")
    df, nodes_meta = load_raw_contacts()
    all_snapshots = build_temporal_snapshots(df, nodes_meta)
    active_snapshots = get_active_subsequence(all_snapshots, num_rounds=DEFAULT_NUM_ROUNDS, start_index=10)
    base_network = TemporalNetwork(active_snapshots, nodes_meta)

    # 2. Table 1
    print("\n[Stage 2] Generating Table 1 (Configuration)...")
    generate_table1(nodes_meta)

    # 3. Figure 1
    print("\n[Stage 3] Generating Figure 1 (Framework Diagram)...")
    plot_framework_diagram()

    # 4. Table 2
    print("\n[Stage 4] Generating Table 2 (Main Performance Comparison)...")
    run_table2_main_comparison(base_network)

    # 5. Table 3
    print("\n[Stage 5] Generating Table 3 (Ablation Study)...")
    run_table3_ablation(base_network)

    # 6. Figure 2
    print("\n[Stage 6] Generating Figure 2 (Timely Coverage vs. Budget K)...")
    run_figure2_budget_study(base_network)

    # 7. Figure 3
    print("\n[Stage 7] Generating Figure 3 (Link Disruption Robustness)...")
    run_figure3_link_failure_study(base_network)

    # 8. Figure 4: Visual Case Study
    print("\n[Stage 8] Generating Figure 4 (Case Study Snapshot)...")
    sample_result = run_single_method("Proposed method", base_network.clone(), budget_k=DEFAULT_BUDGET_K, seed=42)
    plot_case_study_network(base_network, sample_result)

    print("\n======================================================================")
    print(" ALL EXPERIMENTS COMPLETE!")
    print(f" -> Tables exported to:  {TABLES_DIR}")
    print(f" -> Figures exported to: {FIGURES_DIR}")
    print("======================================================================")


if __name__ == "__main__":
    main()
