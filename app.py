"""
app.py — Streamlit web UI for the Poker Hand Probability Simulator
Project: Game Theory: Poker Hand Probability Simulator
Students: Kumar Shaiv Sah / Soutrik Ghosh (2428010002 / 2428010003)

Run with:
    streamlit run app.py
"""

import random
import os
import sys

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# ── Add project folder to path so imports work ────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card import Card, Deck
from game import play_round
from hand_eval import hand_name
from database import (
    DB_PATH, init_db, reset_db,
    get_conn,
    query_hand_frequency,
    query_win_rates,
    query_winning_hand_distribution,
    query_summary_stats,
    insert_batch,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title            = "Poker Probability Simulator",
    page_icon             = "🂡",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-base:       #080d12;
        --bg-surface:    #0d1520;
        --bg-elevated:   #111e2e;
        --bg-hover:      #162538;
        --border-subtle: #1c2e42;
        --border-mid:    #243850;
        --border-accent: #2e5080;
        --gold:          #c9a84c;
        --gold-light:    #e8c97a;
        --gold-dim:      #7a6130;
        --blue-bright:   #4fa3e8;
        --blue-mid:      #2d6fb0;
        --green-bright:  #4dba7f;
        --green-dim:     #1e4a35;
        --red-bright:    #e05c5c;
        --text-primary:  #dce8f0;
        --text-secondary:#7a9ab8;
        --text-muted:    #3a5570;
        --radius-sm:     6px;
        --radius-md:     10px;
        --radius-lg:     16px;
    }

    html, body, .stApp {
        background-color: var(--bg-base) !important;
        font-family: 'DM Sans', sans-serif;
        color: var(--text-primary);
    }

    [data-testid="stSidebar"] {
        background-color: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 2rem; }

    .sidebar-brand { text-align: center; padding: 0 1rem 1.5rem; }
    .sidebar-brand .logo {
        font-family: 'Playfair Display', serif;
        font-size: 2rem; color: var(--gold);
        letter-spacing: 0.05em; line-height: 1; display: block;
    }
    .sidebar-brand .subtitle {
        font-size: 0.65rem; letter-spacing: 0.18em;
        text-transform: uppercase; color: var(--text-muted); margin-top: 4px;
    }
    .sidebar-divider { border: none; border-top: 1px solid var(--border-subtle); margin: 0.75rem 1rem; }

    [data-testid="stSidebar"] .stRadio > div { gap: 4px !important; display: flex; flex-direction: column; }
    [data-testid="stSidebar"] .stRadio label {
        background: transparent; border-radius: var(--radius-md);
        padding: 10px 14px; cursor: pointer;
        transition: background 0.18s, color 0.18s;
        font-size: 0.88rem; font-weight: 500;
        color: var(--text-secondary); border: 1px solid transparent;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: var(--bg-hover); color: var(--text-primary); border-color: var(--border-subtle);
    }

    .sidebar-footer { padding: 0 1rem; font-size: 0.72rem; color: var(--text-muted); line-height: 1.6; }
    .sidebar-footer strong { color: var(--text-secondary); }

    h1 {
        font-family: 'Playfair Display', serif !important;
        font-size: 2rem !important; font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em; line-height: 1.2; margin-bottom: 0.25rem !important;
    }
    h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        color: var(--text-primary) !important; font-weight: 600 !important; letter-spacing: -0.01em;
    }

    .page-subtitle {
        font-size: 0.9rem; color: var(--text-secondary);
        margin-bottom: 2rem; font-weight: 300; letter-spacing: 0.01em;
    }

    hr { border: none !important; border-top: 1px solid var(--border-subtle) !important; margin: 2rem 0 !important; }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #b8861e 0%, #c9a84c 50%, #d4b96a 100%) !important;
        color: #0a0d0f !important; border: none !important;
        border-radius: var(--radius-md) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important; font-size: 0.9rem !important;
        letter-spacing: 0.04em !important; text-transform: uppercase !important;
        padding: 0.65rem 1.5rem !important; transition: all 0.2s ease !important;
        box-shadow: 0 2px 16px rgba(201,168,76,0.25), 0 1px 0 rgba(255,255,255,0.1) inset !important;
        cursor: pointer !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #c9a84c 0%, #e8c97a 60%, #c9a84c 100%) !important;
        box-shadow: 0 4px 24px rgba(201,168,76,0.4), 0 1px 0 rgba(255,255,255,0.15) inset !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(0) !important; box-shadow: 0 1px 8px rgba(201,168,76,0.3) !important;
    }

    .stButton > button:not([kind="primary"]) {
        background: var(--bg-elevated) !important; color: var(--text-secondary) !important;
        border: 1px solid var(--border-mid) !important; border-radius: var(--radius-md) !important;
        font-family: 'DM Sans', sans-serif !important; font-weight: 500 !important;
        font-size: 0.88rem !important; padding: 0.55rem 1.2rem !important;
        transition: all 0.18s ease !important; cursor: pointer !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: var(--bg-hover) !important; border-color: var(--border-accent) !important;
        color: var(--text-primary) !important; transform: translateY(-1px) !important;
    }

    .card-chip {
        display: inline-block; background: var(--bg-elevated);
        border: 1px solid var(--border-mid); border-radius: var(--radius-sm);
        padding: 5px 13px; font-size: 1.25rem;
        font-family: 'JetBrains Mono', monospace; margin: 3px;
        color: var(--text-primary); letter-spacing: 0.05em;
        box-shadow: 0 1px 4px rgba(0,0,0,0.4); transition: transform 0.12s;
    }
    .card-chip:hover { transform: translateY(-2px); }
    .card-chip.hearts, .card-chip.diamonds { color: var(--red-bright); }
    .card-chip.winner-card {
        border-color: var(--gold); background: #1a2a14;
        box-shadow: 0 0 12px rgba(201,168,76,0.3), 0 1px 4px rgba(0,0,0,0.5);
    }

    .hand-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; font-family: 'DM Sans', sans-serif;
        letter-spacing: 0.05em; text-transform: uppercase;
        background: rgba(45,111,176,0.2); color: var(--blue-bright); border: 1px solid var(--blue-mid);
    }
    .hand-badge.winner { background: rgba(77,186,127,0.15); color: var(--green-bright); border-color: #2d7a55; }

    .player-row {
        background: var(--bg-elevated); border-radius: var(--radius-md);
        padding: 12px 18px; margin: 5px 0; border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--border-mid);
        display: flex; align-items: center; gap: 12px; transition: background 0.15s;
    }
    .player-row:hover { background: var(--bg-hover); }
    .player-row.winner-row { border-left-color: var(--gold); background: rgba(26,40,18,0.7); border-color: var(--gold-dim); }

    .metric-box {
        background: var(--bg-elevated); border-radius: var(--radius-lg);
        padding: 20px 16px; text-align: center; border: 1px solid var(--border-subtle);
        position: relative; overflow: hidden;
    }
    .metric-box::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, var(--gold-dim), var(--gold), var(--gold-dim)); opacity: 0.6;
    }
    .metric-box .val {
        font-family: 'Playfair Display', serif; font-size: 2rem;
        font-weight: 700; color: var(--gold-light); line-height: 1;
    }
    .metric-box .lbl {
        font-size: 0.7rem; color: var(--text-muted); margin-top: 6px;
        letter-spacing: 0.1em; text-transform: uppercase; font-weight: 500;
    }

    .stAlert { border-radius: var(--radius-md) !important; }

    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stSelectSlider > div > div {
        background-color: var(--bg-elevated) !important; border-color: var(--border-mid) !important;
        color: var(--text-primary) !important; border-radius: var(--radius-md) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--blue-mid), var(--gold)) !important; border-radius: 4px !important;
    }
    .stProgress > div > div { background: var(--bg-elevated) !important; border-radius: 4px !important; }

    .stDataFrame { border-radius: var(--radius-md) !important; overflow: hidden; }

    .streamlit-expanderHeader {
        background-color: var(--bg-elevated) !important; border-radius: var(--radius-md) !important;
        border: 1px solid var(--border-subtle) !important; color: var(--text-secondary) !important;
        font-family: 'DM Sans', sans-serif !important; font-size: 0.88rem !important;
    }
    .streamlit-expanderContent {
        background-color: var(--bg-elevated) !important; border: 1px solid var(--border-subtle) !important;
        border-top: none !important; border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }

    [data-testid="stMetric"] {
        background: var(--bg-elevated); border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md); padding: 16px !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Playfair Display', serif !important; color: var(--gold-light) !important; font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important; font-size: 0.75rem !important;
        text-transform: uppercase !important; letter-spacing: 0.08em !important; font-family: 'DM Sans', sans-serif !important;
    }

    .section-pill {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(201,168,76,0.08); border: 1px solid var(--gold-dim);
        border-radius: 20px; padding: 4px 14px; font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold); margin-bottom: 0.75rem;
    }

    .board-area {
        background: var(--bg-elevated); border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg); padding: 20px 24px; margin-bottom: 1.5rem;
    }
    .board-title {
        font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase;
        color: var(--text-muted); margin-bottom: 12px; font-weight: 600;
    }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg-base); }
    ::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-accent); }

    .stSelectbox label, .stNumberInput label,
    .stSelectSlider label, .stCheckbox label, .stRadio label {
        font-family: 'DM Sans', sans-serif !important; font-size: 0.82rem !important;
        color: var(--text-secondary) !important; font-weight: 500 !important; letter-spacing: 0.03em !important;
    }

    .stCaption, small, caption { color: var(--text-muted) !important; font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}
RED_SUITS    = {"Hearts", "Diamonds"}

HAND_ORDER = [
    "High Card", "One Pair", "Two Pair", "Three of a Kind",
    "Straight", "Flush", "Full House", "Four of a Kind",
    "Straight Flush", "Royal Flush",
]

HAND_COLOURS = [
    "#4a90d9", "#5ba3e8", "#6db5f0", "#7fc6f8",
    "#52b788", "#40916c", "#2d6a4f", "#f4a261",
    "#e76f51", "#e63946",
]

THEORETICAL_PCT = {
    "High Card":       50.12,
    "One Pair":        42.26,
    "Two Pair":         4.75,
    "Three of a Kind":  2.11,
    "Straight":         0.39,
    "Flush":            0.20,
    "Full House":       0.14,
    "Four of a Kind":   0.02,
    "Straight Flush":   0.0014,
    "Royal Flush":      0.00015,
}

CHART_BG   = "#080d12"
CHART_SURF = "#0d1520"
CHART_GRID = "#1a2738"
CHART_TEXT = "#7a9ab8"
CHART_TICK = "#4a6a88"


# ── Helpers ───────────────────────────────────────────────────────────────────

def card_html(card: Card, highlight: bool = False) -> str:
    suit_cls = card.suit.lower()
    win_cls  = "winner-card" if highlight else ""
    sym      = SUIT_SYMBOLS[card.suit]
    return f'<span class="card-chip {suit_cls} {win_cls}">{card.rank}{sym}</span>'


def init_db_once() -> None:
    if "db_ready" not in st.session_state:
        init_db(DB_PATH)
        st.session_state.db_ready = True


def styled_chart_axes(ax, fig) -> None:
    """Apply consistent dark-theme styling to a matplotlib axes."""
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_SURF)
    ax.tick_params(colors=CHART_TICK, labelsize=8)
    ax.xaxis.label.set_color(CHART_TEXT)
    ax.yaxis.label.set_color(CHART_TEXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, color=CHART_GRID, linewidth=0.6, zorder=0, linestyle='--')
    ax.set_axisbelow(True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand">
            <span class="logo">♠ Poker</span>
            <div class="subtitle">Probability Simulator</div>
        </div>
        <hr class="sidebar-divider">
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🃏  Demo Round", "📊  Run Simulation", "📈  Statistics & Charts"],
        label_visibility="collapsed",
    )

    st.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
    st.markdown("""
        <div class="sidebar-footer">
            <strong>Kumar Shaiv Sah</strong> · 2428010002<br>
            <strong>Soutrik Ghosh</strong> · 2428010003<br>
            Computer &amp; Communication Eng.
        </div>
    """, unsafe_allow_html=True)

init_db_once()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DEMO ROUND
# ══════════════════════════════════════════════════════════════════════════════

if page == "🃏  Demo Round":
    st.markdown('<div class="section-pill">Live Play</div>', unsafe_allow_html=True)
    st.title("Deal a Hand")
    st.markdown(
        "<p class='page-subtitle'>Texas Hold'em evaluation — see how the hand classifier works in real time.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        num_players = st.selectbox("Players at table", [2, 3, 4, 5, 6], index=2)
    with col2:
        use_seed = st.checkbox("Fixed seed")
        seed_val = st.number_input("Seed", value=42, disabled=not use_seed)

    st.markdown("")
    if st.button("🎲  Deal New Hand", type="primary", use_container_width=True):
        if use_seed:
            random.seed(int(seed_val))

        result = play_round(num_players=num_players)

        # ── Community cards ───────────────────────────────────────────────────
        board_html = " ".join(card_html(c) for c in result.community_cards)
        st.markdown(f"""
            <div class="board-area">
                <div class="board-title">Community Cards — The Board</div>
                {board_html}
            </div>
        """, unsafe_allow_html=True)

        # ── Players ───────────────────────────────────────────────────────────
        st.markdown("##### Players")
        for player in result.players:
            is_winner  = player.player_id in result.winner_ids
            rank_tuple, best_five = result.player_hands[player.player_id]

            best_set  = {id(c) for c in best_five}
            hole_html = " ".join(
                card_html(c, highlight=(id(c) in best_set and is_winner))
                for c in player.hole_cards
            )

            h_name    = hand_name(rank_tuple)
            badge_cls = "hand-badge winner" if is_winner else "hand-badge"
            row_cls   = "player-row winner-row" if is_winner else "player-row"
            crown     = " 👑" if is_winner else ""

            st.markdown(f"""
            <div class="{row_cls}">
                <strong style="color:#dce8f0;font-family:'DM Sans',sans-serif;font-size:0.9rem">
                    Player {player.player_id}{crown}
                </strong>
                <span style="flex:1">{hole_html}</span>
                <span class="{badge_cls}">{h_name}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # ── Result banner ─────────────────────────────────────────────────────
        if len(result.winner_ids) == 1:
            st.success(f"🏆  Player {result.winner_ids[0]} wins with **{result.winner_hand_name()}**")
        else:
            ids = ", ".join(str(i) for i in result.winner_ids)
            st.info(f"🤝  Split pot — Players {ids} tie with **{result.winner_hand_name()}**")

        # ── Best hand breakdown ───────────────────────────────────────────────
        with st.expander("🔍  Full hand breakdown"):
            for player in result.players:
                rank_tuple, best_five = result.player_hands[player.player_id]
                cards_str = "  ".join(
                    f"{c.rank}{SUIT_SYMBOLS[c.suit]}" for c in best_five
                )
                st.markdown(
                    f"**Player {player.player_id}** → "
                    f"`{hand_name(rank_tuple)}` — {cards_str}"
                )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — RUN SIMULATION
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊  Run Simulation":
    st.markdown('<div class="section-pill">Monte Carlo</div>', unsafe_allow_html=True)
    st.title("Run Simulation")
    st.markdown(
        "<p class='page-subtitle'>Configure and launch a batch simulation to populate the statistics database.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        num_rounds  = st.select_slider(
            "Number of rounds",
            options=[500, 1_000, 2_000, 5_000, 10_000, 25_000, 50_000],
            value=10_000,
        )
        num_players = st.selectbox("Players per round", [2, 3, 4, 5, 6], index=2)
    with col2:
        use_seed2 = st.checkbox("Reproducible (fixed seed)")
        seed2     = st.number_input("Seed value", value=42, disabled=not use_seed2)
        reset_db_ = st.checkbox("Reset database before running", value=False)

    st.markdown("")
    st.info(
        f"**{num_rounds:,} rounds** · **{num_players} players** · "
        f"**{num_rounds * num_players:,} hands** evaluated"
    )

    st.markdown("")
    if st.button("▶  Start Simulation", type="primary", use_container_width=True):
        if reset_db_:
            reset_db(DB_PATH)
            init_db(DB_PATH)

        seed_val2 = int(seed2) if use_seed2 else None
        if seed_val2 is not None:
            random.seed(seed_val2)

        progress = st.progress(0, text="Initialising…")
        status   = st.empty()

        BATCH = 500
        done  = 0

        while done < num_rounds:
            this_batch = min(BATCH, num_rounds - done)
            batch      = [play_round(num_players=num_players) for _ in range(this_batch)]
            insert_batch(batch, DB_PATH)
            done += this_batch
            pct   = done / num_rounds
            progress.progress(pct, text=f"Simulating… {done:,} / {num_rounds:,} rounds")

        progress.progress(1.0, text="Complete")
        status.empty()

        stats = query_summary_stats(DB_PATH)
        st.success(f"✅  Simulation complete — **{stats['total_rounds']:,}** total rounds in database.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total rounds",  f"{stats['total_rounds']:,}")
        m2.metric("Total hands",   f"{stats['total_hands']:,}")
        m3.metric("Split pots",    f"{stats['total_ties']:,}")
        m4.metric("Tie rate",      f"{stats['tie_rate_pct']:.2f}%")

        st.markdown("➡️  Navigate to **Statistics & Charts** to explore the results.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — STATISTICS & CHARTS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈  Statistics & Charts":
    st.markdown('<div class="section-pill">Analysis</div>', unsafe_allow_html=True)
    st.title("Statistics & Charts")
    st.markdown(
        "<p class='page-subtitle'>Aggregated results from all simulated rounds in the database.</p>",
        unsafe_allow_html=True,
    )

    stats = query_summary_stats(DB_PATH)

    if stats["total_rounds"] == 0:
        st.warning("⚠️  No data yet — run a simulation first.")
        st.stop()

    # ── Summary metrics ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rounds simulated", f"{stats['total_rounds']:,}")
    m2.metric("Hands evaluated",  f"{stats['total_hands']:,}")
    m3.metric("Split pots",       f"{stats['total_ties']:,}")
    m4.metric("Tie rate",         f"{stats['tie_rate_pct']:.2f}%")

    st.markdown("---")

    # ── Chart 1: Hand Frequency ───────────────────────────────────────────────
    st.subheader("Hand Frequency Distribution")
    st.caption("How often each hand type appeared across all simulated player hands.")

    freqs     = query_hand_frequency(DB_PATH)
    freq_map  = {r["hand_name"]: r for r in freqs}
    names_ord = [h for h in HAND_ORDER if h in freq_map]
    pcts      = [freq_map[h]["pct"]  for h in names_ord]
    colours   = [HAND_COLOURS[HAND_ORDER.index(h)] for h in names_ord]

    fig1, ax1 = plt.subplots(figsize=(10, 4), facecolor=CHART_BG)
    styled_chart_axes(ax1, fig1)
    bars = ax1.bar(names_ord, pcts, color=colours,
                   edgecolor=CHART_BG, linewidth=0.6, zorder=3, width=0.6)

    for bar, pct in zip(bars, pcts):
        if pct >= 0.3:
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{pct:.1f}%",
                ha="center", va="bottom", fontsize=7.5,
                color=CHART_TEXT, fontfamily="DM Sans",
            )

    ax1.set_ylabel("Frequency (%)", color=CHART_TEXT, fontsize=9)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
    plt.xticks(rotation=30, ha="right", color=CHART_TICK, fontsize=8.5)
    plt.tight_layout(pad=1.2)
    st.pyplot(fig1)
    plt.close(fig1)

    st.markdown("---")

    # ── Chart 2 + Table: Win Rates ────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Win Rate by Hand Type")
        st.caption("How often each hand won when it was the best at showdown.")

        rates    = query_win_rates(DB_PATH)
        rates_s  = sorted(rates, key=lambda r: r["win_rate_pct"])
        rnames   = [r["hand_name"]    for r in rates_s]
        rwinpcts = [r["win_rate_pct"] for r in rates_s]
        rcolours = [HAND_COLOURS[HAND_ORDER.index(h)] for h in rnames]

        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor=CHART_BG)
        styled_chart_axes(ax2, fig2)
        ax2.xaxis.grid(True, color=CHART_GRID, linewidth=0.6, zorder=0, linestyle='--')
        ax2.yaxis.grid(False)
        hbars = ax2.barh(rnames, rwinpcts, color=rcolours,
                         edgecolor=CHART_BG, linewidth=0.6, height=0.55)

        for bar, pct in zip(hbars, rwinpcts):
            ax2.text(
                bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=8,
                color=CHART_TEXT,
            )

        ax2.set_xlim(0, 115)
        ax2.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
        plt.tight_layout(pad=1.2)
        st.pyplot(fig2)
        plt.close(fig2)

    with col_b:
        st.subheader("Hand Stats Table")
        table_rows = []
        for r in query_win_rates(DB_PATH):
            table_rows.append({
                "Hand":  r["hand_name"],
                "Seen":  f"{r['seen']:,}",
                "Wins":  f"{r['wins']:,}",
                "Win %": f"{r['win_rate_pct']:.1f}%",
            })
        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Chart 3: Simulated vs Theoretical ────────────────────────────────────
    st.subheader("Simulated vs Theoretical Frequency")
    st.caption(
        "Monte Carlo results vs known 5-card draw probabilities. "
        "Hold'em best-of-7 inflates stronger hands — the gap reflects that."
    )

    sim_map  = {r["hand_name"]: r["pct"] for r in freqs}
    sim_vals = np.array([sim_map.get(h, 0)  for h in HAND_ORDER])
    th_vals  = np.array([THEORETICAL_PCT[h] for h in HAND_ORDER])
    x        = np.arange(len(HAND_ORDER))
    w        = 0.38

    fig3, ax3 = plt.subplots(figsize=(11, 4), facecolor=CHART_BG)
    styled_chart_axes(ax3, fig3)
    ax3.bar(x - w / 2, sim_vals, w, label="Simulated (Hold'em)",
            color="#4a90d9", edgecolor=CHART_BG, linewidth=0.6)
    ax3.bar(x + w / 2, th_vals,  w, label="Theoretical (5-card)",
            color="#52b788", edgecolor=CHART_BG, linewidth=0.6, alpha=0.85)
    ax3.set_yscale("log")
    ax3.set_xticks(x)
    ax3.set_xticklabels(HAND_ORDER, rotation=30, ha="right",
                        color=CHART_TICK, fontsize=8.5)
    ax3.set_ylabel("Frequency (%, log scale)", color=CHART_TEXT, fontsize=9)
    ax3.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=3))
    legend = ax3.legend(frameon=True, labelcolor=CHART_TEXT, fontsize=8)
    legend.get_frame().set_facecolor(CHART_SURF)
    legend.get_frame().set_edgecolor(CHART_GRID)
    plt.tight_layout(pad=1.2)
    st.pyplot(fig3)
    plt.close(fig3)

    st.markdown("---")

    # ── Chart 4: Convergence ──────────────────────────────────────────────────
    st.subheader("Monte Carlo Convergence")
    st.caption(
        "Running frequency of the selected hand stabilises as rounds accumulate — "
        "demonstrating convergence to the true probability."
    )

    conv_hand = st.selectbox("Hand to track", HAND_ORDER, index=1)

    with get_conn(DB_PATH) as conn:
        raw = conn.execute(
            "SELECT best_hand FROM player_hands ORDER BY id"
        ).fetchall()

    total_h = len(raw)
    running = 0
    xs, ys  = [], []
    gap     = max(1, total_h // 400)

    for i, row in enumerate(raw, 1):
        if row["best_hand"] == conv_hand:
            running += 1
        if i % gap == 0 or i == total_h:
            xs.append(i)
            ys.append(100.0 * running / i)

    theory_line = THEORETICAL_PCT.get(conv_hand)

    fig4, ax4 = plt.subplots(figsize=(10, 3.5), facecolor=CHART_BG)
    styled_chart_axes(ax4, fig4)
    ax4.plot(xs, ys, color="#4a90d9", linewidth=1.8,
             label=f"Running — '{conv_hand}'", zorder=3)
    if theory_line:
        ax4.axhline(theory_line, color="#c9a84c", linewidth=1.2,
                    linestyle="--", label=f"5-card theory: {theory_line:.4f}%",
                    alpha=0.8)
    ax4.set_xlabel("Hands simulated", color=CHART_TEXT, fontsize=9)
    ax4.set_ylabel("Running frequency (%)", color=CHART_TEXT, fontsize=9)
    ax4.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=2))
    legend4 = ax4.legend(frameon=True, labelcolor=CHART_TEXT, fontsize=8)
    legend4.get_frame().set_facecolor(CHART_SURF)
    legend4.get_frame().set_edgecolor(CHART_GRID)
    plt.tight_layout(pad=1.2)
    st.pyplot(fig4)
    plt.close(fig4)

    # ── Winning hand pie ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Winning Hand Share")
    st.caption("Distribution of which hand type won each round.")

    dist      = query_winning_hand_distribution(DB_PATH)
    pie_names = [r["winning_hand"] for r in dist]
    pie_vals  = [r["rounds_won"]   for r in dist]
    pie_cols  = [HAND_COLOURS[HAND_ORDER.index(h)] for h in pie_names if h in HAND_ORDER]

    # Guard: only include hands that exist in HAND_ORDER
    filtered = [(n, v) for n, v in zip(pie_names, pie_vals) if n in HAND_ORDER]
    if filtered:
        pie_names_f, pie_vals_f = zip(*filtered)
        pie_cols_f = [HAND_COLOURS[HAND_ORDER.index(h)] for h in pie_names_f]

        fig5, ax5 = plt.subplots(figsize=(7, 5), facecolor=CHART_BG)
        ax5.set_facecolor(CHART_BG)
        wedges, texts, autotexts = ax5.pie(
            pie_vals_f, labels=pie_names_f, colors=pie_cols_f,
            autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
            startangle=140,
            wedgeprops=dict(edgecolor=CHART_BG, linewidth=1.5),
            textprops=dict(color=CHART_TEXT, fontsize=8.5),
            pctdistance=0.78,
        )
        for at in autotexts:
            at.set_color("#0a0d0f")
            at.set_fontsize(7.5)
            at.set_fontweight("bold")
        plt.tight_layout()
        st.pyplot(fig5)
        plt.close(fig5)
