"""
Temporal network representation and alert propagation simulation.
Models dynamic network snapshots G(1), G(2), ..., G(T) and handles edge disruption scenarios.
"""

import copy
import random
from typing import Dict, List, Set, Tuple, Any, Optional
import networkx as nx


class TemporalNetwork:
    """
    Manages a sequence of static graph snapshots representing a time-varying network.
    Each snapshot G(t) contains the edges active during time interval t.
    """

    def __init__(self, snapshots: List[nx.Graph], nodes_meta: Dict[str, Dict[str, Any]]):
        self.snapshots = snapshots
        self.nodes_meta = nodes_meta
        self.all_nodes = list(nodes_meta.keys())
        self.num_rounds = len(snapshots)

    def clone(self) -> "TemporalNetwork":
        """Create a deep copy of the temporal network."""
        new_snapshots = [g.copy() for g in self.snapshots]
        return TemporalNetwork(new_snapshots, copy.deepcopy(self.nodes_meta))

    def apply_random_edge_removal(self, removal_rate: float, seed: Optional[int] = None) -> "TemporalNetwork":
        """
        Simulate moderate to severe communication failure by randomly removing
        a specified fraction of temporal edges across all snapshots.
        """
        if removal_rate <= 0.0:
            return self.clone()

        rng = random.Random(seed)
        new_snapshots = []
        for g in self.snapshots:
            g_copy = g.copy()
            edges = list(g_copy.edges())
            num_to_remove = int(len(edges) * removal_rate)
            if num_to_remove > 0:
                edges_to_remove = rng.sample(edges, num_to_remove)
                g_copy.remove_edges_from(edges_to_remove)
            new_snapshots.append(g_copy)

        return TemporalNetwork(new_snapshots, copy.deepcopy(self.nodes_meta))

    def apply_critical_link_failure(self, top_k_relays: int = 3, fail_rounds: Optional[List[int]] = None) -> "TemporalNetwork":
        """
        Simulate targeted critical failure by removing contacts involving
        the most connected relay nodes during specific rounds.
        """
        # Find high-degree relay nodes across all snapshots
        total_degree: Dict[str, int] = {node: 0 for node in self.all_nodes}
        for g in self.snapshots:
            for node, deg in g.degree():
                total_degree[node] += deg

        sorted_nodes = sorted(total_degree.keys(), key=lambda n: total_degree[n], reverse=True)
        critical_relays = set(sorted_nodes[:top_k_relays])

        if fail_rounds is None:
            # By default fail during intermediate propagation rounds
            fail_rounds = list(range(1, min(4, self.num_rounds)))

        new_snapshots = []
        for r_idx, g in enumerate(self.snapshots):
            g_copy = g.copy()
            if r_idx in fail_rounds:
                edges_to_remove = [
                    (u, v) for u, v in g_copy.edges()
                    if u in critical_relays or v in critical_relays
                ]
                g_copy.remove_edges_from(edges_to_remove)
            new_snapshots.append(g_copy)

        return TemporalNetwork(new_snapshots, copy.deepcopy(self.nodes_meta))

    def simulate_candidate_reachability(
        self,
        current_round: int,
        candidate_node: str,
        already_informed: Set[str],
        arrival_times: Dict[str, int]
    ) -> Tuple[Dict[str, int], Set[str]]:
        """
        Temporarily simulate alert propagation forward in time starting from current_round
        if candidate_node is selected as the new source.
        
        Args:
            current_round: 1-indexed round number where candidate is ignited.
            candidate_node: The candidate node to evaluate.
            already_informed: Nodes already informed prior to this round.
            arrival_times: Existing arrival round mapping for already informed nodes.
            
        Returns:
            sim_arrival: Dict of arrival round for all reachable nodes in simulation.
            candidate_reachable: Set of all nodes reached through candidate's propagation.
        """
        # We start with existing informed nodes plus the candidate
        sim_informed: Set[str] = set(already_informed)
        sim_arrival: Dict[str, int] = dict(arrival_times)

        # Candidate is informed at current_round
        if candidate_node not in sim_informed:
            sim_informed.add(candidate_node)
            sim_arrival[candidate_node] = current_round

        candidate_reachable: Set[str] = {candidate_node}

        # Propagate from current_round to the final snapshot (round indices 1-indexed)
        # current_round is 1-indexed, snapshots are 0-indexed: snapshot index = r - 1
        active_spreaders = set(sim_informed)

        for r in range(current_round, self.num_rounds + 1):
            snap_idx = r - 1
            if snap_idx >= len(self.snapshots):
                break
            g = self.snapshots[snap_idx]

            newly_reached = set()
            for spreader in active_spreaders:
                if spreader in g:
                    for neighbor in g.neighbors(spreader):
                        if neighbor not in sim_informed:
                            newly_reached.add(neighbor)
                            sim_informed.add(neighbor)
                            sim_arrival[neighbor] = r
                            candidate_reachable.add(neighbor)

            active_spreaders.update(newly_reached)

        return sim_arrival, candidate_reachable
