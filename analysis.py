import os
import sqlite3
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

from database import (
    DB_PATH,
    query_hand_frequency,
    query_win_rates,
    query_winning_hand_distribution,
    query_summary_stats,
    get_conn,
)

# ── Style ─────────────────────────────────────────────────────────────────────

matplotlib.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "figure.dpi":        130,
})

# Colour palette (one per hand rank, worst → best)
HAND_ORDER = [
    "High Card", "One Pair", "Two Pair", "Three of a Kind",
    "Straight", "Flush", "Full House", "Four of a Kind",
    "Straight Flush", "Royal Flush",
]

COLOURS = [
    "#9ecae1", "#6baed6", "#4292c6", "#2171b5",
    "#08519c", "#74c476", "#41ab5d", "#238b45",
    "#fc8d59", "#d73027",
]

HAND_COLOUR = dict(zip(HAND_ORDER, COLOURS))

# Theoretical probabilities for a single 5-card hand from a 52-card deck
# (used in chart 3 for comparison)
THEORETICAL_PCT = {
    "High Card":       50.1177,
    "One Pair":        42.2569,
    "Two Pair":         4.7539,
    "Three of a Kind":  2.1128,
    "Straight":         0.3925,
    "Flush":            0.1965,
    "Full House":       0.1441,
    "Four of a Kind":   0.0240,
    "Straight Flush":   0.00139,
    "Royal Flush":      0.000154,
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "charts")


# ── Helper ────────────────────────────────────────────────────────────────────

def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save(fig: plt.Figure, filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, bbox_inches="tight")
    print(f"  Saved → {path}")
    return path


# ── Chart 1 — Hand frequency distribution ────────────────────────────────────

def chart_hand_frequency(db_path: str = DB_PATH) -> str:
    """
    Bar chart: how often each hand type appeared across all simulated rounds.
    Both raw count and percentage are shown.
    """
    rows  = query_hand_frequency(db_path)
    if not rows:
        print("  No data yet — run simulation.py first.")
        return ""

    # Sort worst → best for a clean left-to-right gradient
    order_map = {h: i for i, h in enumerate(HAND_ORDER)}
    rows = sorted(rows, key=lambda r: order_map.get(r["hand_name"], 99))

    names  = [r["hand_name"] for r in rows]
    pcts   = [r["pct"]       for r in rows]
    colours = [HAND_COLOUR.get(n, "#999") for n in names]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(names, pcts, color=colours, edgecolor="white", linewidth=0.6)

    # Value labels on top of each bar
    for bar, pct in zip(bars, pcts):
        if pct >= 0.5:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{pct:.2f}%",
                ha="center", va="bottom", fontsize=8, color="#333"
            )

    ax.set_title("Hand Frequency Distribution")
    ax.set_ylabel("Frequency (%)")
    ax.set_xlabel("Hand Type")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    _ensure_output_dir()
    return _save(fig, "1_hand_frequency.png")


# ── Chart 2 — Win rate per hand type ─────────────────────────────────────────

def chart_win_rates(db_path: str = DB_PATH) -> str:
    """
    Horizontal bar chart: what percentage of the time each hand type won,
    given that it appeared.
    """
    rows = query_win_rates(db_path)
    if not rows:
        print("  No data yet — run simulation.py first.")
        return ""

    # Sort by win rate ascending (best at top in horizontal bar)
    rows = sorted(rows, key=lambda r: r["win_rate_pct"])

    names    = [r["hand_name"]    for r in rows]
    win_pcts = [r["win_rate_pct"] for r in rows]
    colours  = [HAND_COLOUR.get(n, "#999") for n in names]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(names, win_pcts, color=colours, edgecolor="white", linewidth=0.6)

    for bar, pct in zip(bars, win_pcts):
        ax.text(
            bar.get_width() + 0.8,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%",
            va="center", fontsize=8.5, color="#333"
        )

    ax.set_title("Win Rate per Hand Type\n(% of times it won when it appeared)")
    ax.set_xlabel("Win Rate (%)")
    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    plt.tight_layout()

    _ensure_output_dir()
    return _save(fig, "2_win_rates.png")


# ── Chart 3 — Simulated vs theoretical frequency ─────────────────────────────

def chart_simulated_vs_theoretical(db_path: str = DB_PATH) -> str:
    """
    Grouped bar chart comparing simulated hand frequency (from Monte Carlo)
    against the known theoretical probability for a single 5-card deal.

    Note: Texas Hold'em best-hand frequencies differ slightly from pure
    5-card-draw theory because players pick the best 5 from 7 cards,
    inflating stronger hands. This chart makes that bias visible.
    """
    rows = query_hand_frequency(db_path)
    if not rows:
        print("  No data yet — run simulation.py first.")
        return ""

    sim_map = {r["hand_name"]: r["pct"] for r in rows}

    # Use log scale — frequencies span 5 orders of magnitude
    hands  = HAND_ORDER
    sim    = np.array([sim_map.get(h, 0) for h in hands])
    theory = np.array([THEORETICAL_PCT[h] for h in hands])

    x     = np.arange(len(hands))
    width = 0.38

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width / 2, sim,    width, label="Simulated (Hold'em best-of-7)",
           color="#4292c6", edgecolor="white")
    ax.bar(x + width / 2, theory, width, label="Theoretical (5-card draw)",
           color="#74c476", edgecolor="white", alpha=0.85)

    ax.set_yscale("log")
    ax.set_title("Simulated vs Theoretical Hand Frequency (log scale)")
    ax.set_ylabel("Frequency (%, log scale)")
    ax.set_xlabel("Hand Type")
    ax.set_xticks(x)
    ax.set_xticklabels(hands, rotation=30, ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=3))
    ax.legend(frameon=False)
    plt.tight_layout()

    _ensure_output_dir()
    return _save(fig, "3_simulated_vs_theoretical.png")


# ── Chart 4 — Convergence of One Pair frequency ───────────────────────────────

def chart_convergence(db_path: str = DB_PATH, hand: str = "One Pair") -> str:
    """
    Line chart showing how the running frequency of `hand` stabilises
    as more rounds are simulated — classic Monte Carlo convergence proof.
    """
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT best_hand
            FROM   player_hands
            ORDER  BY id
            """,
        ).fetchall()

    if not rows:
        print("  No data yet — run simulation.py first.")
        return ""

    total      = len(rows)
    running    = 0
    xs, ys     = [], []
    sample_gap = max(1, total // 500)   # at most 500 points on the chart

    for i, row in enumerate(rows, 1):
        if row["best_hand"] == hand:
            running += 1
        if i % sample_gap == 0 or i == total:
            xs.append(i)
            ys.append(100.0 * running / i)

    # Theoretical reference line (5-card draw)
    theory_pct = THEORETICAL_PCT.get(hand, None)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, ys, color="#4292c6", linewidth=1.4, label=f"Running frequency of '{hand}'")

    if theory_pct is not None:
        ax.axhline(theory_pct, color="#d73027", linewidth=1,
                   linestyle="--", label=f"5-card theory: {theory_pct:.2f}%")

    ax.set_title(f"Monte Carlo Convergence — '{hand}' Frequency")
    ax.set_xlabel("Hands simulated")
    ax.set_ylabel("Running frequency (%)")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
    ax.legend(frameon=False)
    plt.tight_layout()

    _ensure_output_dir()
    return _save(fig, f"4_convergence_{hand.replace(' ', '_').lower()}.png")


# ── Master function: generate all charts ─────────────────────────────────────

def generate_all_charts(db_path: str = DB_PATH) -> list[str]:
    """
    Generate all 4 charts and return a list of saved file paths.
    """
    stats = query_summary_stats(db_path)
    if stats["total_rounds"] == 0:
        print("Database is empty. Run simulation.py first.")
        return []

    print(f"\nGenerating charts from {stats['total_rounds']:,} simulated rounds ...\n")

    paths = []
    paths.append(chart_hand_frequency(db_path))
    paths.append(chart_win_rates(db_path))
    paths.append(chart_simulated_vs_theoretical(db_path))
    paths.append(chart_convergence(db_path))

    print(f"\nAll charts saved to: {OUTPUT_DIR}/")
    return [p for p in paths if p]


# ── CLI / self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from simulation import run_simulation

    parser = argparse.ArgumentParser(
        description="Generate analysis charts for the Poker Simulator"
    )
    parser.add_argument("-d", "--db",  default=DB_PATH,
                        help="SQLite database path")
    parser.add_argument("--run-sim",   action="store_true",
                        help="Run a fresh 10,000-round simulation before charting")
    parser.add_argument("-n", "--rounds", type=int, default=10_000)
    parser.add_argument("-p", "--players", type=int, default=4)
    parser.add_argument("-s", "--seed",    type=int, default=42)
    args = parser.parse_args()

    if args.run_sim:
        run_simulation(
            num_rounds=args.rounds,
            num_players=args.players,
            seed=args.seed,
            db_path=args.db,
        )

    generate_all_charts(args.db)