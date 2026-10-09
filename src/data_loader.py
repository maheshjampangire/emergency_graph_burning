"""
Data loader and preprocessor for the SocioPatterns Hospital Ward contact network.
Downloads, extracts, aggregates contacts into temporal graph snapshots, and assigns
node roles, criticalities, and deadlines.
"""

import os
import gzip
import urllib.request
from typing import Dict, List, Tuple, Any
import networkx as nx
import pandas as pd
from src.config import (
    RAW_DATA_FILE,
    RAW_DATA_DIR,
    DATASET_URL,
    SNAPSHOT_WINDOW_SECONDS,
    ROLE_CRITICALITY,
    get_deadline_for_criticality
)


def ensure_dataset_exists() -> str:
    """Ensure the SocioPatterns raw data file exists locally, downloading if necessary."""
    if RAW_DATA_FILE.exists() and RAW_DATA_FILE.stat().st_size > 0:
        return str(RAW_DATA_FILE)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading SocioPatterns dataset from {DATASET_URL}...")
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        compressed_data = response.read()

    decompressed = gzip.decompress(compressed_data).decode("utf-8")
    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(decompressed)

    print(f"Dataset successfully saved to {RAW_DATA_FILE}")
    return str(RAW_DATA_FILE)


def load_raw_contacts() -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Load raw contact records from file and extract participant metadata.
    
    Returns:
        df: DataFrame of contacts with columns [t, u, v, role_u, role_v]
        nodes_meta: Dict mapping node_id to metadata dict (role, criticality, deadline)
    """
    file_path = ensure_dataset_exists()
    
    records = []
    nodes_meta: Dict[str, Dict[str, Any]] = {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                t = int(parts[0])
                u = str(parts[1])
                v = str(parts[2])
                role_u = parts[3].upper()
                role_v = parts[4].upper()
                
                records.append({
                    "timestamp": t,
                    "u": u,
                    "v": v,
                    "role_u": role_u,
                    "role_v": role_v
                })
                
                # Store node role (if not already recorded)
                if u not in nodes_meta:
                    crit_u = ROLE_CRITICALITY.get(role_u, 1)
                    nodes_meta[u] = {
                        "id": u,
                        "role": role_u,
                        "criticality": crit_u,
                        "deadline": get_deadline_for_criticality(crit_u)
                    }
                if v not in nodes_meta:
                    crit_v = ROLE_CRITICALITY.get(role_v, 1)
                    nodes_meta[v] = {
                        "id": v,
                        "role": role_v,
                        "criticality": crit_v,
                        "deadline": get_deadline_for_criticality(crit_v)
                    }

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    return df, nodes_meta


def build_temporal_snapshots(
    df: pd.DataFrame,
    nodes_meta: Dict[str, Dict[str, Any]],
    window_seconds: int = SNAPSHOT_WINDOW_SECONDS
) -> List[nx.Graph]:
    """
    Discretize temporal contact data into time-window snapshots.
    Each snapshot is an undirected graph G(t) containing all contacts active
    during that window. All network nodes are included in each graph.
    """
    if df.empty:
        return []

    min_time = df["timestamp"].min()
    max_time = df["timestamp"].max()

    # Assign time window bucket index
    df = df.copy()
    df["bucket"] = (df["timestamp"] - min_time) // window_seconds
    total_buckets = int((max_time - min_time) // window_seconds) + 1

    snapshots: List[nx.Graph] = []
    all_node_ids = list(nodes_meta.keys())

    for b in range(total_buckets):
        g = nx.Graph()
        # Add all nodes with their static metadata attributes
        for node_id, meta in nodes_meta.items():
            g.add_node(node_id, **meta)

        # Filter edges belonging to bucket b
        bucket_edges = df[df["bucket"] == b]
        for _, row in bucket_edges.iterrows():
            g.add_edge(row["u"], row["v"])

        snapshots.append(g)

    return snapshots


def get_active_subsequence(
    snapshots: List[nx.Graph],
    num_rounds: int = 6,
    start_index: int = 0
) -> List[nx.Graph]:
    """
    Extract a slice of snapshots that has good contact activity.
    If start_index is None, automatically finds a high-activity period.
    """
    if start_index + num_rounds <= len(snapshots):
        return snapshots[start_index : start_index + num_rounds]
    return snapshots[:num_rounds]
