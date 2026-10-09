"""
Visualization and reporting module.
Generates:
- Figure 1: Proposed framework architecture diagram
- Figure 2: Timely coverage vs. number of sources (K = 2..6)
- Figure 3: Robustness under link failure (0%..40%)
- Figure 4: Visual case study of temporal network alert dissemination
- Table 1, Table 2, Table 3 in CSV, Markdown, and publication-ready LaTeX formats
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import pandas as pd
from src.temporal_network import TemporalNetwork
from src.config import FIGURES_DIR, TABLES_DIR, CRITICAL_THRESHOLD

# Set clean aesthetic plot style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10


def plot_framework_diagram(output_path: Optional[Path] = None) -> Path:
    """Figure 1: Proposed Emergency Alert Graph Burning Architecture."""
    if output_path is None:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = FIGURES_DIR / "figure1_framework.png"

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    ax.axis("off")

    stages = [
        ("1. Temporal Contact Data", "SocioPatterns Hospital Ward (t, u, v, role)\n5-minute discretized snapshots G(1)...G(T)"),
        ("2. Role Criticality & Deadline Assignment", "Roles: MED(5), NUR(4), PAT(3), ADM(2)\nDeadlines: Deadline(i) = 7 - Criticality(i)"),
        ("3. Temporal Reachability Simulation", "Simulate forward reachability from current round\nwithout modifying real graph state"),
        ("4. Candidate Source Scoring", "TimelyCriticalityGain = Sum[Crit / (1 + Delay)]\nScore = TimelyGain * (1 - Lambda * OverlapRatio)"),
        ("5. Ordered Burning Sequence", "Select candidate with maximum SourceScore\nS = [source1, source2, ..., sourceK]"),
        ("6. Emergency Alert Propagation", "Propagate across active dynamic edges G(t)\nRecord arrival times & evaluate timely delivery")
    ]

    colors = ["#2b5c8f", "#1f77b4", "#17becf", "#ff7f0e", "#2ca02c", "#d62728"]

    y_pos = 0.90
    box_height = 0.10
    spacing = 0.04

    for i, (title, desc) in enumerate(stages):
        # Draw rounded box using FancyBboxPatch
        box = mpatches.FancyBboxPatch(
            (0.12, y_pos - box_height), 0.76, box_height,
            boxstyle="round,pad=0.02,rounding_size=0.02",
            facecolor="#f8f9fa", edgecolor=colors[i], linewidth=2.0,
            transform=ax.transAxes, zorder=2
        )
        ax.add_patch(box)

        # Text inside box
        ax.text(
            0.50, y_pos - 0.03, title,
            ha="center", va="center", weight="bold", fontsize=11, color=colors[i],
            transform=ax.transAxes, zorder=3
        )
        ax.text(
            0.50, y_pos - 0.075, desc,
            ha="center", va="center", fontsize=8.5, color="#333333",
            transform=ax.transAxes, zorder=3
        )

        # Draw connecting arrow
        if i < len(stages) - 1:
            arrow_start_y = y_pos - box_height
            arrow_end_y = y_pos - box_height - spacing
            ax.annotate(
                "",
                xy=(0.50, arrow_end_y),
                xytext=(0.50, arrow_start_y),
                arrowprops=dict(facecolor="#555555", edgecolor="#555555", width=1.5, headwidth=6, shrink=0.1),
                xycoords="axes fraction",
                zorder=1
            )

        y_pos -= (box_height + spacing)

    plt.title("Figure 1: Proposed Criticality- and Deadline-Aware Graph Burning Framework", pad=20, weight="bold", fontsize=12)
    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_coverage_vs_budget(df_budget: pd.DataFrame, output_path: Optional[Path] = None) -> Path:
    """Figure 2: Timely Critical Coverage (%) versus Source Budget K (2 to 6)."""
    if output_path is None:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = FIGURES_DIR / "figure2_coverage_vs_budget.png"

    fig, ax = plt.subplots(figsize=(7, 4.8), dpi=300)

    markers = ["o", "s", "^", "D", "v", "P"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    for idx, (method, group) in enumerate(df_budget.groupby("Algorithm")):
        group = group.sort_values("Source Budget")
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        is_proposed = "Proposed" in method and "without" not in method

        linewidth = 2.8 if is_proposed else 1.8
        ax.plot(
            group["Source Budget"],
            group["Timely Critical Coverage Mean"],
            label=method,
            marker=marker,
            markersize=7 if is_proposed else 5,
            linewidth=linewidth,
            color=color
        )
        if "Timely Critical Coverage Std" in group.columns:
            ax.fill_between(
                group["Source Budget"],
                group["Timely Critical Coverage Mean"] - group["Timely Critical Coverage Std"],
                group["Timely Critical Coverage Mean"] + group["Timely Critical Coverage Std"],
                alpha=0.15,
                color=color
            )

    ax.set_xlabel("Number of Selected Sources (Source Budget K)", fontsize=11, weight="bold")
    ax.set_ylabel("Timely Critical-Node Coverage (%)", fontsize=11, weight="bold")
    ax.set_title("Figure 2: Timely Critical Coverage vs. Number of Sources", fontsize=12, weight="bold", pad=12)
    ax.set_xticks([2, 3, 4, 5, 6])
    ax.set_ylim(-2, 105)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True, fontsize=9, loc="lower right")

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_robustness_link_failure(df_failure: pd.DataFrame, output_path: Optional[Path] = None) -> Path:
    """Figure 3: Weighted Timely Coverage (%) under varying edge failure rates (0% to 40%)."""
    if output_path is None:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = FIGURES_DIR / "figure3_robustness_link_failure.png"

    fig, ax = plt.subplots(figsize=(7, 4.8), dpi=300)

    markers = ["o", "s", "^", "D", "v", "P"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    for idx, (method, group) in enumerate(df_failure.groupby("Algorithm")):
        group = group.sort_values("Edge Removal Rate")
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        is_proposed = "Proposed" in method and "without" not in method

        linewidth = 2.8 if is_proposed else 1.8
        x_pct = [r * 100 for r in group["Edge Removal Rate"]]

        ax.plot(
            x_pct,
            group["Weighted Timely Coverage Mean"],
            label=method,
            marker=marker,
            markersize=7 if is_proposed else 5,
            linewidth=linewidth,
            color=color
        )
        if "Weighted Timely Coverage Std" in group.columns:
            ax.fill_between(
                x_pct,
                group["Weighted Timely Coverage Mean"] - group["Weighted Timely Coverage Std"],
                group["Weighted Timely Coverage Mean"] + group["Weighted Timely Coverage Std"],
                alpha=0.15,
                color=color
            )

    ax.set_xlabel("Percentage of Removed Communication Links (%)", fontsize=11, weight="bold")
    ax.set_ylabel("Weighted Timely Coverage (%)", fontsize=11, weight="bold")
    ax.set_title("Figure 3: Robustness Under Communication Link Failure", fontsize=12, weight="bold", pad=12)
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.set_ylim(-2, 105)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True, fontsize=9, loc="lower left")

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_case_study_network(
    network: TemporalNetwork,
    result: Dict[str, Any],
    output_path: Optional[Path] = None
) -> Path:
    """
    Visual Case Study:
    - Red nodes: Selected sources
    - Orange nodes: Critical recipients not yet reached on time
    - Green nodes: Recipients reached before deadline
    - Grey nodes: Recipients not reached
    - Labels: Node ID and arrival round
    """
    if output_path is None:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = FIGURES_DIR / "figure4_case_study_network.png"

    # Cumulative graph for layout
    cumulative_g = nx.Graph()
    for g in network.snapshots:
        cumulative_g.add_nodes_from(g.nodes())
        cumulative_g.add_edges_from(g.edges())

    pos = nx.spring_layout(cumulative_g, seed=42, k=0.35)

    fig, ax = plt.subplots(figsize=(10, 7.5), dpi=300)

    sources = set(result.get("sources", []))
    arrival_rounds = result.get("arrival_rounds", {})

    node_colors = []
    node_labels = {}

    for node in cumulative_g.nodes():
        crit = network.nodes_meta.get(node, {}).get("criticality", 1)
        ddl = network.nodes_meta.get(node, {}).get("deadline", 999)
        arr = arrival_rounds.get(node, None)

        if node in sources:
            node_colors.append("#d62728")  # Red for selected sources
            node_labels[node] = f"{node}\n(S,r={arr})"
        elif arr is not None and arr <= ddl:
            node_colors.append("#2ca02c")  # Green for reached before deadline
            node_labels[node] = f"{node}\n(r={arr})"
        elif crit >= CRITICAL_THRESHOLD:
            node_colors.append("#ff7f0e")  # Orange for critical recipients missed/delayed
            node_labels[node] = f"{node}\n(C{crit})"
        else:
            node_colors.append("#aaaaaa")  # Grey for unreached or low priority
            node_labels[node] = f"{node}"

    # Draw edges
    nx.draw_networkx_edges(cumulative_g, pos, ax=ax, alpha=0.25, edge_color="#7f7f7f", width=0.8)

    # Draw nodes
    nx.draw_networkx_nodes(cumulative_g, pos, ax=ax, node_color=node_colors, node_size=320, edgecolors="black", linewidths=0.6)

    # Draw labels
    nx.draw_networkx_labels(cumulative_g, pos, labels=node_labels, font_size=5.5, ax=ax, font_color="black")

    legend_patches = [
        mpatches.Patch(color="#d62728", label="Selected Sources (Red)"),
        mpatches.Patch(color="#2ca02c", label="Reached Before Deadline (Green)"),
        mpatches.Patch(color="#ff7f0e", label="Critical Nodes Missed/Delayed (Orange)"),
        mpatches.Patch(color="#aaaaaa", label="Ordinary / Unreached (Grey)")
    ]
    ax.legend(handles=legend_patches, loc="upper right", frameon=True, fontsize=9)
    ax.set_title("Figure 4: Emergency Alert Dissemination Case Study Snapshot", fontsize=12, weight="bold", pad=12)
    ax.axis("off")

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def export_dataframe_tables(df: pd.DataFrame, base_name: str, caption: str) -> None:
    """Exports a dataframe to CSV, Markdown, and LaTeX."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    
    csv_path = TABLES_DIR / f"{base_name}.csv"
    md_path = TABLES_DIR / f"{base_name}.md"
    tex_path = TABLES_DIR / f"{base_name}.tex"

    df.to_csv(csv_path, index=False)
    
    # Generate Markdown table safely without external dependency
    try:
        md_table = df.to_markdown(index=False)
    except Exception:
        headers = list(df.columns)
        header_row = "| " + " | ".join(headers) + " |"
        sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        body_rows = [
            "| " + " | ".join(str(val) for val in row) + " |"
            for row in df.values
        ]
        md_table = "\n".join([header_row, sep_row] + body_rows)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"### {caption}\n\n")
        f.write(md_table)
        f.write("\n")

    # Generate LaTeX table safely
    try:
        tex_table = df.to_latex(index=False, escape=True)
    except Exception:
        tex_table = df.to_string(index=False)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(f"% {caption}\n")
        f.write(tex_table)
        f.write("\n")
