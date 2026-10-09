"""
Baseline algorithms for Graph Burning comparison:
1. Random Burning
2. Degree-based Burning
3. Betweenness-based Burning
4. Farthest-First Burning
5. Criticality-only Burning
6. Static-network Burning (Temporal ablation)
"""

import time
import random
from typing import Dict, List, Set, Any, Optional
import networkx as nx
from src.temporal_network import TemporalNetwork
from src.config import CRITICAL_THRESHOLD


class BaseBurner:
    """Base class for running baseline burning strategies on a TemporalNetwork."""

    def __init__(self, network: TemporalNetwork, name: str):
        self.network = network
        self.name = name

    def _select_source(
        self,
        round_idx: int,
        selected_sources: List[str],
        real_informed: Set[str],
        current_snapshot: nx.Graph,
        rng: random.Random
    ) -> str:
        raise NotImplementedError

    def run(self, budget_k: int, seed: Optional[int] = None) -> Dict[str, Any]:
        rng = random.Random(seed)
        start_time = time.perf_counter()

        selected_sources: List[str] = []
        real_informed: Set[str] = set()
        arrival_rounds: Dict[str, int] = {}
        rounds_log: List[Dict[str, Any]] = []

        total_rounds = self.network.num_rounds

        for round_idx in range(1, total_rounds + 1):
            snap_idx = round_idx - 1
            current_snapshot = self.network.snapshots[snap_idx]

            # 1. Source selection round (up to budget K)
            if len(selected_sources) < budget_k:
                source = self._select_source(
                    round_idx=round_idx,
                    selected_sources=selected_sources,
                    real_informed=real_informed,
                    current_snapshot=current_snapshot,
                    rng=rng
                )
                selected_sources.append(source)
                if source not in real_informed:
                    real_informed.add(source)
                    arrival_rounds[source] = round_idx

            # 2. Propagation along current active edges
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
            "algorithm": self.name,
            "sources": selected_sources,
            "arrival_rounds": arrival_rounds,
            "informed_nodes": real_informed,
            "rounds_log": rounds_log,
            "runtime": runtime
        }


class RandomBurning(BaseBurner):
    """Baseline 1: Randomly select an uninformed node in each round."""

    def __init__(self, network: TemporalNetwork):
        super().__init__(network, "Random Burning")

    def _select_source(self, round_idx, selected_sources, real_informed, current_snapshot, rng):
        candidate_pool = [n for n in self.network.all_nodes if n not in real_informed]
        if not candidate_pool:
            candidate_pool = [n for n in self.network.all_nodes if n not in selected_sources]
        if not candidate_pool:
            candidate_pool = list(self.network.all_nodes)
        return rng.choice(candidate_pool)


class DegreeBurning(BaseBurner):
    """Baseline 2: Select the node with the highest degree in the current snapshot."""

    def __init__(self, network: TemporalNetwork):
        super().__init__(network, "Degree-based Burning")

    def _select_source(self, round_idx, selected_sources, real_informed, current_snapshot, rng):
        candidate_pool = [n for n in self.network.all_nodes if n not in selected_sources]
        if not candidate_pool:
            candidate_pool = list(self.network.all_nodes)

        # Degree in current snapshot; if 0, fallback to degree across all snapshots
        degrees = dict(current_snapshot.degree())
        best_candidate = max(
            candidate_pool,
            key=lambda n: (degrees.get(n, 0), n not in real_informed)
        )
        return best_candidate


class BetweennessBurning(BaseBurner):
    """Baseline 3: Select the unselected node with the highest betweenness centrality."""

    def __init__(self, network: TemporalNetwork):
        super().__init__(network, "Betweenness-based Burning")
        # Precompute cumulative betweenness across the active window to handle sparse individual snapshots
        cumulative_g = nx.Graph()
        for g in network.snapshots:
            cumulative_g.add_nodes_from(g.nodes(data=True))
            cumulative_g.add_edges_from(g.edges())
        self.centrality = nx.betweenness_centrality(cumulative_g)

    def _select_source(self, round_idx, selected_sources, real_informed, current_snapshot, rng):
        candidate_pool = [n for n in self.network.all_nodes if n not in selected_sources]
        if not candidate_pool:
            candidate_pool = list(self.network.all_nodes)

        # Prioritize uninformed nodes, then highest betweenness
        best_candidate = max(
            candidate_pool,
            key=lambda n: (n not in real_informed, self.centrality.get(n, 0.0))
        )
        return best_candidate


class FarthestFirstBurning(BaseBurner):
    """
    Baseline 4: Farthest-first burning.
    Selects the candidate furthest from currently selected sources.
    """

    def __init__(self, network: TemporalNetwork):
        super().__init__(network, "Farthest-first Burning")
        self.cumulative_g = nx.Graph()
        for g in network.snapshots:
            self.cumulative_g.add_nodes_from(g.nodes(data=True))
            self.cumulative_g.add_edges_from(g.edges())

    def _select_source(self, round_idx, selected_sources, real_informed, current_snapshot, rng):
        candidate_pool = [n for n in self.network.all_nodes if n not in selected_sources]
        if not candidate_pool:
            candidate_pool = list(self.network.all_nodes)

        if not selected_sources:
            # First round: choose random or center
            return rng.choice(candidate_pool)

        # Calculate minimum distance from candidate to any already selected source
        def min_dist_to_sources(cand: str) -> float:
            dists = []
            for src in selected_sources:
                try:
                    d = nx.shortest_path_length(self.cumulative_g, source=cand, target=src)
                    dists.append(d)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    dists.append(9999)  # Disconnected / infinite distance
            return min(dists) if dists else 9999

        best_candidate = max(
            candidate_pool,
            key=lambda n: (min_dist_to_sources(n), n not in real_informed)
        )
        return best_candidate


class CriticalityOnlyBurning(BaseBurner):
    """
    Baseline 5: Criticality-only burning.
    Greedily selects the uninformed node with the highest criticality,
    blind to network structure or future spread.
    """

    def __init__(self, network: TemporalNetwork):
        super().__init__(network, "Criticality-only Burning")

    def _select_source(self, round_idx, selected_sources, real_informed, current_snapshot, rng):
        candidate_pool = [n for n in self.network.all_nodes if n not in real_informed]
        if not candidate_pool:
            candidate_pool = [n for n in self.network.all_nodes if n not in selected_sources]
        if not candidate_pool:
            candidate_pool = list(self.network.all_nodes)

        best_candidate = max(
            candidate_pool,
            key=lambda n: (
                self.network.nodes_meta.get(n, {}).get("criticality", 1),
                current_snapshot.degree(n)
            )
        )
        return best_candidate
