"""
Proposed Criticality- and Deadline-Aware Graph Burning Algorithm.
Greedily selects an ordered sequence of alert sources based on temporal reachability,
timely criticality gain, and redundancy/overlap penalty.
"""

import time
from typing import Dict, List, Set, Tuple, Any, Optional
import networkx as nx
from src.temporal_network import TemporalNetwork
from src.config import DEFAULT_OVERLAP_WEIGHT, CRITICAL_THRESHOLD


class ProposedGraphBurning:
    """
    Implements the criticality- and deadline-aware graph burning algorithm.
    """

    def __init__(
        self,
        network: TemporalNetwork,
        overlap_weight: float = DEFAULT_OVERLAP_WEIGHT,
        enable_criticality: bool = True,
        enable_deadlines: bool = True,
        enable_overlap_penalty: bool = True
    ):
        self.network = network
        self.overlap_weight = overlap_weight if enable_overlap_penalty else 0.0
        self.enable_criticality = enable_criticality
        self.enable_deadlines = enable_deadlines
        self.enable_overlap_penalty = enable_overlap_penalty

    def _get_criticality(self, node: str) -> int:
        if not self.enable_criticality:
            return 1
        return self.network.nodes_meta.get(node, {}).get("criticality", 1)

    def _get_deadline(self, node: str) -> int:
        if not self.enable_deadlines:
            return 999999  # Effectively infinite deadline
        return self.network.nodes_meta.get(node, {}).get("deadline", 999999)

    def run(self, budget_k: int) -> Dict[str, Any]:
        """
        Execute the greedy graph-burning source selection process.

        Args:
            budget_k: Total number of source selection rounds K.

        Returns:
            Dictionary containing sources, arrival rounds, informed set, and runtime.
        """
        start_time = time.perf_counter()

        selected_sources: List[str] = []
        real_informed: Set[str] = set()
        arrival_rounds: Dict[str, int] = {}
        rounds_log: List[Dict[str, Any]] = []

        total_rounds = self.network.num_rounds
        all_nodes = self.network.all_nodes
        critical_nodes = [
            n for n in all_nodes
            if self.network.nodes_meta.get(n, {}).get("criticality", 1) >= CRITICAL_THRESHOLD
        ]

        for round_idx in range(1, total_rounds + 1):
            snap_idx = round_idx - 1
            current_snapshot = self.network.snapshots[snap_idx]

            # Source selection only occurs if we haven't exhausted budget K
            if len(selected_sources) < budget_k:
                # Early stop check: If all critical nodes are already informed, we may stop
                uninformed_critical = [c for c in critical_nodes if c not in real_informed]
                if critical_nodes and len(uninformed_critical) == 0 and len(selected_sources) > 0:
                    # All critical nodes covered!
                    pass

                # Candidate pool: unselected nodes
                candidate_pool = [n for n in all_nodes if n not in selected_sources]
                if not candidate_pool:
                    candidate_pool = list(all_nodes)

                best_candidate: Optional[str] = None
                best_score: float = -1.0
                best_gain: float = 0.0
                best_overlap: float = 0.0

                for candidate in candidate_pool:
                    # 1. Simulate forward reachability without modifying real state
                    sim_arrival, candidate_reachable = self.network.simulate_candidate_reachability(
                        current_round=round_idx,
                        candidate_node=candidate,
                        already_informed=real_informed,
                        arrival_times=arrival_rounds
                    )

                    # 2. Calculate timely criticality gain for newly reached nodes
                    timely_gain = 0.0
                    newly_reached = candidate_reachable - real_informed

                    for v in newly_reached:
                        arr_round = sim_arrival.get(v, round_idx)
                        deadline_v = self._get_deadline(v)

                        # Only counts if reached before or on its deadline
                        if arr_round <= deadline_v:
                            crit_v = self._get_criticality(v)
                            # Delay relative to round 1 start (round 1 arrival has 0 delay)
                            delay = arr_round - 1
                            timely_gain += crit_v / (1.0 + delay)

                    # 3. Calculate overlap ratio
                    if len(candidate_reachable) > 0:
                        overlap_count = len(candidate_reachable.intersection(real_informed))
                        overlap_ratio = overlap_count / len(candidate_reachable)
                    else:
                        overlap_ratio = 0.0

                    # 4. Source Score
                    score = timely_gain * (1.0 - self.overlap_weight * overlap_ratio)

                    if score > best_score:
                        best_score = score
                        best_candidate = candidate
                        best_gain = timely_gain
                        best_overlap = overlap_ratio

                # If all scores are 0 (e.g. no new reachable nodes in time), pick highest criticality/degree unselected node
                if best_candidate is None or best_score <= 0.0:
                    unselected_uninformed = [n for n in candidate_pool if n not in real_informed]
                    pool = unselected_uninformed if unselected_uninformed else candidate_pool
                    best_candidate = max(
                        pool,
                        key=lambda n: (self._get_criticality(n), current_snapshot.degree(n))
                    )
                    best_score = 0.0
                    best_gain = 0.0
                    best_overlap = 0.0

                # Commit selected source
                selected_sources.append(best_candidate)
                if best_candidate not in real_informed:
                    real_informed.add(best_candidate)
                    arrival_rounds[best_candidate] = round_idx

            # Propagate alert along active edges of current snapshot
            # Nodes that were informed up to this round propagate to neighbors in G(snap_idx)
            current_spreaders = list(real_informed)
            new_spread = set()
            for spreader in current_spreaders:
                if spreader in current_snapshot:
                    for nbr in current_snapshot.neighbors(spreader):
                        if nbr not in real_informed:
                            new_spread.add(nbr)
                            arrival_rounds[nbr] = round_idx

            real_informed.update(new_spread)

            rounds_log.append({
                "round": round_idx,
                "selected_source": selected_sources[-1] if round_idx <= len(selected_sources) else None,
                "newly_reached_count": len(new_spread),
                "total_informed": len(real_informed)
            })

        runtime = time.perf_counter() - start_time

        return {
            "algorithm": "Proposed Method",
            "sources": selected_sources,
            "arrival_rounds": arrival_rounds,
            "informed_nodes": real_informed,
            "rounds_log": rounds_log,
            "runtime": runtime
        }
