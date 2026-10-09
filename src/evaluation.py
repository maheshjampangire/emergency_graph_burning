"""
Evaluation metrics for emergency alert dissemination:
- Timely Critical-Node Coverage
- Weighted Timely Coverage
- Total Coverage
- Average Alert Delay
- Deadline-Miss Ratio
- Source-Overlap Ratio
- Runtime
"""

import numpy as np
from typing import Dict, List, Set, Any
from src.temporal_network import TemporalNetwork
from src.config import CRITICAL_THRESHOLD


def compute_metrics(
    result: Dict[str, Any],
    network: TemporalNetwork,
    critical_threshold: int = CRITICAL_THRESHOLD
) -> Dict[str, float]:
    """
    Compute all standard conference metrics for a burning run.

    Args:
        result: Output dict from an algorithm run containing sources, arrival_rounds, informed_nodes, runtime.
        network: The TemporalNetwork instance.
        critical_threshold: Minimum criticality considered a 'critical' recipient.

    Returns:
        Dictionary of metric values.
    """
    nodes_meta = network.nodes_meta
    all_nodes = network.all_nodes
    total_nodes = len(all_nodes)
    arrival_rounds = result.get("arrival_rounds", {})
    sources = result.get("sources", [])
    runtime = result.get("runtime", 0.0)

    # 1. Critical nodes definition
    critical_nodes = [
        n for n in all_nodes
        if nodes_meta.get(n, {}).get("criticality", 1) >= critical_threshold
    ]
    total_critical = len(critical_nodes)

    # 2. Check timely arrivals
    timely_reached_critical = 0
    sum_timely_criticality = 0.0
    sum_all_criticality = 0.0
    informed_delays = []
    deadline_misses = 0

    for n in all_nodes:
        meta = nodes_meta.get(n, {})
        crit = meta.get("criticality", 1)
        ddl = meta.get("deadline", 999)
        sum_all_criticality += crit

        arr = arrival_rounds.get(n, None)

        if arr is not None:
            delay = arr - 1  # 0 delay if reached in round 1
            informed_delays.append(delay)

            if arr <= ddl:
                sum_timely_criticality += crit
                if crit >= critical_threshold:
                    timely_reached_critical += 1
            else:
                deadline_misses += 1
        else:
            # Unreached counts as deadline miss
            deadline_misses += 1

    # 16.1 Timely Critical-Node Coverage (%)
    timely_crit_cov = (timely_reached_critical / total_critical * 100.0) if total_critical > 0 else 0.0

    # 16.2 Weighted Timely Coverage (%)
    weighted_timely_cov = (sum_timely_criticality / sum_all_criticality * 100.0) if sum_all_criticality > 0 else 0.0

    # 16.3 Total Coverage (%)
    total_cov = (len(arrival_rounds) / total_nodes * 100.0) if total_nodes > 0 else 0.0

    # 16.4 Average Alert Delay
    avg_delay = float(np.mean(informed_delays)) if informed_delays else 0.0

    # 16.5 Deadline-Miss Ratio (%)
    miss_ratio = (deadline_misses / total_nodes * 100.0) if total_nodes > 0 else 0.0

    # 16.6 Source-Overlap Ratio
    overlap_ratio = compute_source_overlap_ratio(sources, network)

    return {
        "Timely Critical Coverage": timely_crit_cov,
        "Weighted Timely Coverage": weighted_timely_cov,
        "Total Coverage": total_cov,
        "Average Delay": avg_delay,
        "Deadline-Miss Ratio": miss_ratio,
        "Source-Overlap Ratio": overlap_ratio,
        "Runtime": runtime
    }


def compute_source_overlap_ratio(sources: List[str], network: TemporalNetwork) -> float:
    """
    Calculate the average pairwise Jaccard overlap between the reachable regions
    of selected sources when propagating individually.
    """
    if len(sources) <= 1:
        return 0.0

    # Simulate individual forward reach of each source from its activation round
    reach_sets = []
    for r_idx, src in enumerate(sources):
        current_round = r_idx + 1
        # Reach from candidate alone
        _, reached = network.simulate_candidate_reachability(
            current_round=current_round,
            candidate_node=src,
            already_informed=set(),
            arrival_times={}
        )
        reach_sets.append(reached)

    overlaps = []
    for i in range(len(reach_sets)):
        for j in range(i + 1, len(reach_sets)):
            s1 = reach_sets[i]
            s2 = reach_sets[j]
            union_len = len(s1.union(s2))
            if union_len > 0:
                inter_len = len(s1.intersection(s2))
                overlaps.append(inter_len / union_len)
            else:
                overlaps.append(0.0)

    return float(np.mean(overlaps)) if overlaps else 0.0
