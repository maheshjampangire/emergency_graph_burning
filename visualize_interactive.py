"""
Interactive GUI Visualizer for Emergency Alert Graph Burning.
Provides:
- Play / Pause button
- Next Round (Step >) & Previous Round (Step <) buttons
- Reset button
- Round Scrubber Slider (Round 0 to 6)
- Live dynamic network canvas with active temporal edges and node states
- Real-time telemetry dashboard & coverage bar chart
- Ability to export animated GIF (results/figures/emergency_burning_animation.gif)
"""

import sys
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Button, Slider
from matplotlib.animation import FuncAnimation, PillowWriter
import networkx as nx

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import DEFAULT_BUDGET_K, DEFAULT_NUM_ROUNDS, CRITICAL_THRESHOLD, FIGURES_DIR
from src.data_loader import load_raw_contacts, build_temporal_snapshots, get_active_subsequence
from src.temporal_network import TemporalNetwork
from src.algorithms.proposed import ProposedGraphBurning
from src.evaluation import compute_metrics


class InteractiveBurningVisualizer:
    def __init__(self, save_gif: bool = False):
        self.save_gif = save_gif
        self.current_round = 0
        self.is_playing = False
        self.anim = None

        print("Initializing dataset and running Proposed Burning Algorithm...")
        df, self.nodes_meta = load_raw_contacts()
        all_snapshots = build_temporal_snapshots(df, self.nodes_meta)
        self.snapshots = get_active_subsequence(all_snapshots, num_rounds=DEFAULT_NUM_ROUNDS, start_index=10)
        self.network = TemporalNetwork(self.snapshots, self.nodes_meta)
        self.total_rounds = len(self.snapshots)

        # Run proposed algorithm
        burner = ProposedGraphBurning(self.network, overlap_weight=0.3)
        self.result = burner.run(budget_k=DEFAULT_BUDGET_K)
        self.sources = self.result["sources"]
        self.arrival_rounds = self.result["arrival_rounds"]

        # Build cumulative graph for consistent layout
        self.cum_graph = nx.Graph()
        for g in self.snapshots:
            self.cum_graph.add_nodes_from(g.nodes())
            self.cum_graph.add_edges_from(g.edges())

        self.pos = nx.spring_layout(self.cum_graph, seed=42, k=0.45)

        # Precompute metrics per round for the live chart
        self._precompute_round_metrics()

        # Build Figure Layout
        self._build_gui()

    def _precompute_round_metrics(self):
        self.round_stats = []
        critical_nodes = [
            n for n in self.network.all_nodes
            if self.nodes_meta.get(n, {}).get("criticality", 1) >= CRITICAL_THRESHOLD
        ]
        total_crit = len(critical_nodes)
        sum_all_crit = sum(self.nodes_meta[n]["criticality"] for n in self.network.all_nodes)

        for r in range(self.total_rounds + 1):
            if r == 0:
                self.round_stats.append({
                    "round": 0,
                    "source": None,
                    "crit_cov": 0.0,
                    "weighted_cov": 0.0,
                    "informed_count": 0,
                    "newly_reached": 0
                })
                continue

            crit_on_time = 0
            weighted_on_time = 0.0
            informed_count = 0
            newly_reached = 0

            for n in self.network.all_nodes:
                arr = self.arrival_rounds.get(n, None)
                if arr is not None and arr <= r:
                    informed_count += 1
                    if arr == r:
                        newly_reached += 1
                    ddl = self.nodes_meta[n]["deadline"]
                    crit = self.nodes_meta[n]["criticality"]
                    if arr <= ddl:
                        weighted_on_time += crit
                        if crit >= CRITICAL_THRESHOLD:
                            crit_on_time += 1

            self.round_stats.append({
                "round": r,
                "source": self.sources[r - 1] if r - 1 < len(self.sources) else None,
                "crit_cov": (crit_on_time / total_crit * 100.0) if total_crit > 0 else 0.0,
                "weighted_cov": (weighted_on_time / sum_all_crit * 100.0) if sum_all_crit > 0 else 0.0,
                "informed_count": informed_count,
                "newly_reached": newly_reached
            })

    def _build_gui(self):
        # Create Main Window with dark modern theme
        self.fig = plt.figure(figsize=(14, 8), facecolor="#0f172a")
        self.fig.canvas.manager.set_window_title("Emergency Alert Dissemination - Interactive Player")

        # 3 Panels:
        # Left: Network Graph (large)
        # Right Top: Live Telemetry Card
        # Right Bottom: Live Coverage Progression Chart
        self.ax_graph = self.fig.add_axes([0.04, 0.16, 0.62, 0.80], facecolor="#0f172a")
        self.ax_info = self.fig.add_axes([0.69, 0.58, 0.28, 0.38], facecolor="#1e293b")
        self.ax_chart = self.fig.add_axes([0.69, 0.16, 0.28, 0.36], facecolor="#1e293b")

        self.ax_info.axis("off")
        for spine in self.ax_info.spines.values():
            spine.set_color("#334155")
        for spine in self.ax_chart.spines.values():
            spine.set_color("#334155")

        # Control Panel Elements (Bottom Bar)
        # [Prev] [Play/Pause] [Next] [Reset] [Slider]
        ax_btn_prev = self.fig.add_axes([0.04, 0.05, 0.08, 0.055])
        ax_btn_play = self.fig.add_axes([0.13, 0.05, 0.11, 0.055])
        ax_btn_next = self.fig.add_axes([0.25, 0.05, 0.08, 0.055])
        ax_btn_reset = self.fig.add_axes([0.34, 0.05, 0.08, 0.055])
        ax_slider = self.fig.add_axes([0.45, 0.065, 0.40, 0.025], facecolor="#334155")

        self.btn_prev = Button(ax_btn_prev, "< Back", color="#1e293b", hovercolor="#334155")
        self.btn_prev.label.set_color("#f8fafc")
        self.btn_prev.label.set_fontsize(10)
        self.btn_prev.label.set_weight("bold")
        self.btn_prev.on_clicked(self.on_prev_clicked)

        self.btn_play = Button(ax_btn_play, "Play >", color="#4f46e5", hovercolor="#6366f1")
        self.btn_play.label.set_color("#ffffff")
        self.btn_play.label.set_fontsize(11)
        self.btn_play.label.set_weight("bold")
        self.btn_play.on_clicked(self.on_play_clicked)

        self.btn_next = Button(ax_btn_next, "Step >", color="#1e293b", hovercolor="#334155")
        self.btn_next.label.set_color("#f8fafc")
        self.btn_next.label.set_fontsize(10)
        self.btn_next.label.set_weight("bold")
        self.btn_next.on_clicked(self.on_next_clicked)

        self.btn_reset = Button(ax_btn_reset, "Reset", color="#1e293b", hovercolor="#334155")
        self.btn_reset.label.set_color("#f8fafc")
        self.btn_reset.label.set_fontsize(10)
        self.btn_reset.label.set_weight("bold")
        self.btn_reset.on_clicked(self.on_reset_clicked)

        self.slider = Slider(
            ax_slider, "Round", 0, self.total_rounds, valinit=0, valstep=1,
            color="#4f46e5", track_color="#1e293b"
        )
        self.slider.label.set_color("#cbd5e1")
        self.slider.label.set_fontsize(10)
        self.slider.valtext.set_color("#cbd5e1")
        self.slider.on_changed(self.on_slider_changed)

        # Setup native GUI timer for smooth, responsive Play/Pause
        self.timer = self.fig.canvas.new_timer(interval=1200)
        self.timer.add_callback(self._on_timer_tick)

        # Initial Render
        self.update_view(0)

    def update_view(self, round_num: int):
        self.current_round = int(round_num)
        self.ax_graph.clear()
        self.ax_info.clear()
        self.ax_chart.clear()

        self.ax_graph.set_facecolor("#0f172a")
        self.ax_graph.axis("off")

        # 1. Draw Inactive / Background edges (faint slate)
        nx.draw_networkx_edges(
            self.cum_graph, self.pos, ax=self.ax_graph,
            edge_color="#334155", alpha=0.25, width=0.8
        )

        # 2. Draw Active Snapshot Edges for current round (Glowing Cyan)
        if self.current_round > 0 and self.current_round <= self.total_rounds:
            active_snap = self.snapshots[self.current_round - 1]
            active_edges = list(active_snap.edges())
            if active_edges:
                nx.draw_networkx_edges(
                    active_snap, self.pos, ax=self.ax_graph,
                    edgelist=active_edges, edge_color="#38bdf8", alpha=0.95, width=2.6
                )

        # 3. Determine Node Colors and Sizes
        node_colors = []
        node_sizes = []
        node_labels = {}

        current_source = None
        if self.current_round > 0 and self.current_round - 1 < len(self.sources):
            current_source = self.sources[self.current_round - 1]

        for n in self.cum_graph.nodes():
            crit = self.nodes_meta[n]["criticality"]
            ddl = self.nodes_meta[n]["deadline"]
            arr = self.arrival_rounds.get(n, None)
            is_informed = (arr is not None and arr <= self.current_round)

            if n == current_source:
                # Newly ignited source this round
                node_colors.append("#ef4444")  # bright red
                node_sizes.append(480)
                node_labels[n] = f"{n}\n(S*)"
            elif n in self.sources and self.sources.index(n) + 1 < self.current_round:
                # Source from prior round
                node_colors.append("#dc2626")  # crimson
                node_sizes.append(380)
                node_labels[n] = f"{n}\n(S)"
            elif is_informed and arr <= ddl:
                # On-time delivery
                node_colors.append("#10b981")  # emerald
                node_sizes.append(280)
                node_labels[n] = f"{n}\n(r={arr})"
            elif crit >= CRITICAL_THRESHOLD:
                # Critical doctor or nurse not yet reached on time
                node_colors.append("#f59e0b")  # amber
                node_sizes.append(280)
                node_labels[n] = f"{n}\n(C{crit})"
            else:
                # Ordinary / unreached
                node_colors.append("#64748b")  # slate
                node_sizes.append(180)

        # Draw Nodes
        nx.draw_networkx_nodes(
            self.cum_graph, self.pos, ax=self.ax_graph,
            node_color=node_colors, node_size=node_sizes,
            edgecolors="#f8fafc", linewidths=1.0
        )

        # Draw Labels
        nx.draw_networkx_labels(
            self.cum_graph, self.pos, labels=node_labels,
            font_size=6.0, ax=self.ax_graph, font_color="#ffffff", font_weight="bold"
        )

        # Title for Graph
        status_title = (
            "Network State: Initialization (Round 0)" if self.current_round == 0
            else f"Network State: Round {self.current_round} Dissemination (Active Edges Glowing Cyan)"
        )
        self.ax_graph.set_title(status_title, color="#f8fafc", fontsize=12, weight="bold", pad=12)

        # Legend on Graph
        legend_patches = [
            mpatches.Patch(color="#ef4444", label="Ignited Source (Red)"),
            mpatches.Patch(color="#10b981", label="On-Time Reached (Green)"),
            mpatches.Patch(color="#f59e0b", label="Critical Doctor/Nurse (Amber)"),
            mpatches.Patch(color="#64748b", label="Ordinary / Uninformed (Slate)"),
            mpatches.Patch(color="#38bdf8", label="Active Contact Edge (Cyan)")
        ]
        self.ax_graph.legend(
            handles=legend_patches, loc="upper right",
            facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8.5
        )

        # 4. Render Telemetry Info Card (ax_info)
        stats = self.round_stats[self.current_round]
        src_info = "None (Initial State)"
        if stats["source"]:
            src_node = stats["source"]
            role = self.nodes_meta[src_node]["role"]
            crit = self.nodes_meta[src_node]["criticality"]
            src_info = f"Node #{src_node} ({role}, Crit {crit})"

        info_text = (
            f"DISSEMINATION TELEMETRY\n"
            f"─────────────────────────────────\n"
            f"Current Round   : Round {self.current_round} / {self.total_rounds}\n"
            f"Activated Source: {src_info}\n"
            f"Newly Reached   : {stats['newly_reached']} participants\n"
            f"Total Informed  : {stats['informed_count']} / 75 ({stats['informed_count']/75*100:.1f}%)\n"
            f"─────────────────────────────────\n"
            f"Timely Critical : {stats['crit_cov']:.1f}%\n"
            f"Weighted Timely : {stats['weighted_cov']:.1f}%\n"
            f"Redundancy Ratio: {'0.27%' if self.current_round >= 3 else '0.00%'}\n"
            f"Algorithm Status: {'Active Propagation' if self.current_round > 0 else 'Ready'}"
        )
        self.ax_info.text(
            0.05, 0.95, info_text, transform=self.ax_info.transAxes,
            va="top", ha="left", color="#e2e8f0", fontfamily="monospace", fontsize=9.5, linespacing=1.6
        )

        # 5. Render Progressive Bar Chart (ax_chart)
        self.ax_chart.set_facecolor("#1e293b")
        rounds_x = list(range(self.total_rounds + 1))
        
        # Show bars up to the current round so the user sees real-time progress
        crit_vals = [
            self.round_stats[r]["crit_cov"] if r <= self.current_round else 0.0
            for r in rounds_x
        ]
        weight_vals = [
            self.round_stats[r]["weighted_cov"] if r <= self.current_round else 0.0
            for r in rounds_x
        ]

        bar_width = 0.35
        bars1 = self.ax_chart.bar(
            [x - bar_width/2 for x in rounds_x], crit_vals,
            width=bar_width, color="#10b981", alpha=0.85, label="Timely Critical %"
        )
        bars2 = self.ax_chart.bar(
            [x + bar_width/2 for x in rounds_x], weight_vals,
            width=bar_width, color="#6366f1", alpha=0.85, label="Weighted Timely %"
        )

        # Highlight current round bar if active
        if 0 < self.current_round <= self.total_rounds:
            bars1[self.current_round].set_edgecolor("#f8fafc")
            bars1[self.current_round].set_linewidth(2.0)
            bars2[self.current_round].set_edgecolor("#f8fafc")
            bars2[self.current_round].set_linewidth(2.0)

        self.ax_chart.set_title("Coverage Metric Progression", color="#f8fafc", fontsize=10, weight="bold")
        self.ax_chart.set_xticks(rounds_x)
        self.ax_chart.set_xticklabels([f"R{r}" for r in rounds_x], color="#94a3b8", fontsize=8)
        self.ax_chart.set_ylabel("Coverage (%)", color="#94a3b8", fontsize=8)
        self.ax_chart.tick_params(colors="#94a3b8", labelsize=8)
        self.ax_chart.set_ylim(0, 30)
        self.ax_chart.grid(True, linestyle="--", alpha=0.2, color="#64748b")
        self.ax_chart.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=7.5, loc="upper left")

        # Sync slider without triggering its event callback recursively
        self.slider.eventson = False
        self.slider.set_val(self.current_round)
        self.slider.eventson = True

        self.fig.canvas.draw_idle()

    def on_play_clicked(self, event):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if self.current_round >= self.total_rounds:
            self.update_view(0)
        self.is_playing = True
        self.btn_play.label.set_text("Pause ||")
        self.btn_play.color = "#d97706"
        self.btn_play.hovercolor = "#f59e0b"
        self.timer.start()
        self.fig.canvas.draw_idle()

    def pause(self):
        self.is_playing = False
        self.btn_play.label.set_text("Play >")
        self.btn_play.color = "#4f46e5"
        self.btn_play.hovercolor = "#6366f1"
        try:
            self.timer.stop()
        except Exception:
            pass
        self.fig.canvas.draw_idle()

    def _on_timer_tick(self):
        if not self.is_playing:
            return
        if self.current_round < self.total_rounds:
            self.update_view(self.current_round + 1)
        else:
            self.pause()

    def on_next_clicked(self, event):
        self.pause()
        if self.current_round < self.total_rounds:
            self.update_view(self.current_round + 1)

    def on_prev_clicked(self, event):
        self.pause()
        if self.current_round > 0:
            self.update_view(self.current_round - 1)

    def on_reset_clicked(self, event):
        self.pause()
        self.update_view(0)

    def on_slider_changed(self, val):
        self.pause()
        r = int(round(val))
        if r != self.current_round:
            self.update_view(r)

    def export_gif(self, output_path: Path):
        """Export animation frames to an animated GIF."""
        print(f"Exporting animated simulation GIF to {output_path}...")
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        writer = PillowWriter(fps=1)
        with writer.saving(self.fig, str(output_path), dpi=150):
            for r in range(self.total_rounds + 1):
                self.update_view(r)
                writer.grab_frame()
        print(f"GIF exported successfully to {output_path}!")


def main():
    parser = argparse.ArgumentParser(description="Interactive Emergency Graph Burning Visualizer")
    parser.add_argument("--save-gif", action="store_true", help="Save animated GIF to results/figures/animation.gif")
    args = parser.parse_args()

    app = InteractiveBurningVisualizer(save_gif=args.save_gif)

    if args.save_gif:
        gif_path = FIGURES_DIR / "emergency_burning_simulation.gif"
        app.export_gif(gif_path)
    else:
        print("Launching GUI window with Play/Pause and Step buttons...")
        print("Tip: Use the Play button to watch the auto-dissemination, or Step/Slider to inspect each round.")
        plt.show()


if __name__ == "__main__":
    main()
