"""
app.py — Streamlit web UI for the Poker Hand Probability Simulator
Project: Game Theory: Poker Hand Probability Simulator
Students: Kumar Shaiv Sah / Soutrik Ghosh (2428010002 / 2428010003)

Run with:
    streamlit run app.py
"""

import random
import os
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# ── Add project folder to path so imports work ────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(__file__))

from card import Card, Deck
from game import play_round
from database import (
    DB_PATH, init_db, reset_db,
    query_hand_frequency,
    query_win_rates,
    query_winning_hand_distribution,
    query_summary_stats,
    insert_batch,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title  = "Poker Probability Simulator",
    page_icon   = "🂡",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS — clean, beginner-friendly look ────────────────────────────────

st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1923; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #162030;
        border-right: 1px solid #2a3a50;
    }

    /* Cards in demo section */
    .card-chip {
        display: inline-block;
        background: #1e2f42;
        border: 1px solid #2e4560;
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 22px;
        margin: 3px;
        color: #e8e8e8;
    }
    .card-chip.hearts, .card-chip.diamonds { color: #e05c5c; }
    .card-chip.winner-card {
        border-color: #f0c040;
        background: #2a3d20;
        box-shadow: 0 0 8px #f0c04055;
    }

    /* Hand badge */
    .hand-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        background: #1e3a5f;
        color: #90c8ff;
        border: 1px solid #2d5080;
    }
    .hand-badge.winner { background: #2a3d20; color: #7ecf7e; border-color: #4a7a4a; }

    /* Player row */
    .player-row {
        background: #1a2a3a;
        border-radius: 10px;
        padding: 10px 16px;
        margin: 6px 0;
        border-left: 3px solid #2e4560;
    }
    .player-row.winner-row { border-left-color: #f0c040; background: #1e2e1e; }

    /* Metric boxes */
    .metric-box {
        background: #1a2a3a;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2e4560;
    }
    .metric-box .val { font-size: 28px; font-weight: 700; color: #90c8ff; }
    .metric-box .lbl { font-size: 12px; color: #607080; margin-top: 2px; }

    /* Section headers */
    h1, h2, h3 { color: #c8d8e8 !important; }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

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
    "High Card": 50.12, "One Pair": 42.26, "Two Pair": 4.75,
    "Three of a Kind": 2.11, "Straight": 0.39, "Flush": 0.20,
    "Full House": 0.14, "Four of a Kind": 0.02,
    "Straight Flush": 0.0014, "Royal Flush": 0.00015,
}


def card_html(card: Card, highlight: bool = False) -> str:
    suit_cls = card.suit.lower()
    win_cls  = "winner-card" if highlight else ""
    sym      = SUIT_SYMBOLS[card.suit]
    return f'<span class="card-chip {suit_cls} {win_cls}">{card.rank}{sym}</span>'


def init_db_once():
    if "db_ready" not in st.session_state:
        init_db(DB_PATH)
        st.session_state.db_ready = True


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🂡 Poker Simulator")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🃏  Demo Round", "📊  Run Simulation", "📈  Statistics & Charts"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#607080'>Kumar Shaiv Sah · Soutrik Ghosh<br>"
        "2428010002 · 2428010003<br>"
        "Computer & Communication Eng.</small>",
        unsafe_allow_html=True,
    )

init_db_once()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DEMO ROUND
# ══════════════════════════════════════════════════════════════════════════════

if page == "🃏  Demo Round":
    st.title("🃏 Live Demo Round")
    st.markdown("Deal a Texas Hold'em hand and watch the evaluator work in real time.")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        num_players = st.selectbox("Players", [2, 3, 4, 5, 6], index=2)
    with col2:
        use_seed = st.checkbox("Fixed seed")
        seed_val = st.number_input("Seed", value=42, disabled=not use_seed)

    if st.button("🎲  Deal New Hand", type="primary", use_container_width=True):
        if use_seed:
            random.seed(int(seed_val))

        result = play_round(num_players=num_players)

        # ── Community cards ───────────────────────────────────────────────────
        st.markdown("### 🂠 Community Cards (Board)")
        board_html = " ".join(card_html(c) for c in result.community_cards)
        st.markdown(board_html, unsafe_allow_html=True)
        st.markdown("")

        # ── Players ───────────────────────────────────────────────────────────
        st.markdown("### 👥 Players")
        for player in result.players:
            is_winner = player.player_id in result.winner_ids
            rank_tuple, best_five = result.player_hands[player.player_id]

            best_set  = set(id(c) for c in best_five)
            hole_html = " ".join(
                card_html(c, highlight=(id(c) in best_set and is_winner))
                for c in player.hole_cards
            )

            from hand_eval import hand_name
            h_name    = hand_name(rank_tuple)
            badge_cls = "hand-badge winner" if is_winner else "hand-badge"
            row_cls   = "player-row winner-row" if is_winner else "player-row"
            crown     = " 👑" if is_winner else ""

            st.markdown(f"""
            <div class="{row_cls}">
                <strong style="color:#c8d8e8">Player {player.player_id}{crown}</strong>
                &nbsp;&nbsp;{hole_html}&nbsp;&nbsp;
                <span class="{badge_cls}">{h_name}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # ── Result banner ─────────────────────────────────────────────────────
        if len(result.winner_ids) == 1:
            st.success(f"🏆 Player {result.winner_ids[0]} wins with **{result.winner_hand_name()}**!")
        else:
            ids = ", ".join(str(i) for i in result.winner_ids)
            st.info(f"🤝 Split pot — Players {ids} tie with **{result.winner_hand_name()}**!")

        # ── Best hand breakdown ───────────────────────────────────────────────
        with st.expander("🔍 Best hand breakdown"):
            for player in result.players:
                rank_tuple, best_five = result.player_hands[player.player_id]
                from hand_eval import hand_name
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
    st.title("📊 Monte Carlo Simulation")
    st.markdown("Run thousands of rounds and store the results for analysis.")

    col1, col2 = st.columns(2)
    with col1:
        num_rounds  = st.select_slider(
            "Number of rounds",
            options=[500, 1_000, 2_000, 5_000, 10_000, 25_000, 50_000],
            value=10_000,
        )
        num_players = st.selectbox("Players per round", [2, 3, 4, 5, 6], index=2)
    with col2:
        use_seed2 = st.checkbox("Use fixed seed (reproducible)")
        seed2     = st.number_input("Seed value", value=42, disabled=not use_seed2)
        reset_db_ = st.checkbox("Reset database before running", value=False)

    st.info(
        f"📌 This will simulate **{num_rounds:,} rounds** with "
        f"**{num_players} players** each — "
        f"evaluating **{num_rounds * num_players:,} hands** total."
    )

    if st.button("▶️  Start Simulation", type="primary", use_container_width=True):
        if reset_db_:
            reset_db(DB_PATH)
            init_db(DB_PATH)

        seed_val2 = int(seed2) if use_seed2 else None
        if seed_val2 is not None:
            random.seed(seed_val2)

        progress = st.progress(0, text="Starting simulation...")
        status   = st.empty()

        BATCH = 500
        done  = 0

        while done < num_rounds:
            this_batch = min(BATCH, num_rounds - done)
            batch      = [play_round(num_players=num_players) for _ in range(this_batch)]
            insert_batch(batch, DB_PATH)
            done += this_batch
            pct   = done / num_rounds
            progress.progress(pct, text=f"Simulating... {done:,} / {num_rounds:,} rounds")

        progress.progress(1.0, text="Done!")
        status.empty()

        stats = query_summary_stats(DB_PATH)
        st.success(f"✅ Simulation complete! {stats['total_rounds']:,} total rounds in database.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total rounds",  f"{stats['total_rounds']:,}")
        m2.metric("Total hands",   f"{stats['total_hands']:,}")
        m3.metric("Split pots",    f"{stats['total_ties']:,}")
        m4.metric("Tie rate",      f"{stats['tie_rate_pct']:.2f}%")

        st.markdown("➡️ Go to **Statistics & Charts** to see the results.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — STATISTICS & CHARTS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈  Statistics & Charts":
    st.title("📈 Statistics & Charts")

    stats = query_summary_stats(DB_PATH)

    if stats["total_rounds"] == 0:
        st.warning("⚠️ No simulation data yet. Go to **Run Simulation** first.")
        st.stop()

    # ── Summary metrics ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rounds simulated", f"{stats['total_rounds']:,}")
    m2.metric("Hands evaluated",  f"{stats['total_hands']:,}")
    m3.metric("Split pots",       f"{stats['total_ties']:,}")
    m4.metric("Tie rate",         f"{stats['tie_rate_pct']:.2f}%")

    st.markdown("---")

    # ── Chart 1: Hand Frequency ───────────────────────────────────────────────
    st.subheader("📊 Hand Frequency Distribution")
    st.caption("How often each hand type appeared across all simulated player hands.")

    freqs     = query_hand_frequency(DB_PATH)
    freq_map  = {r["hand_name"]: r for r in freqs}
    names_ord = [h for h in HAND_ORDER if h in freq_map]
    pcts      = [freq_map[h]["pct"]  for h in names_ord]
    colours   = [HAND_COLOURS[HAND_ORDER.index(h)] for h in names_ord]

    fig1, ax1 = plt.subplots(figsize=(10, 4), facecolor="#0f1923")
    ax1.set_facecolor("#0f1923")
    bars = ax1.bar(names_ord, pcts, color=colours, edgecolor="#0f1923", linewidth=0.8, zorder=3)

    for bar, pct in zip(bars, pcts):
        if pct >= 0.3:
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{pct:.1f}%",
                ha="center", va="bottom", fontsize=8, color="#a0b8c8"
            )

    ax1.set_ylabel("Frequency (%)", color="#607080")
    ax1.tick_params(colors="#607080")
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
    ax1.spines[:].set_visible(False)
    ax1.yaxis.grid(True, color="#1e2f42", linewidth=0.5, zorder=0)
    plt.xticks(rotation=30, ha="right", color="#a0b8c8", fontsize=9)
    plt.tight_layout()
    st.pyplot(fig1)
    plt.close(fig1)

    st.markdown("---")

    # ── Chart 2 + Table: Win Rates ────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("🏆 Win Rate per Hand Type")
        st.caption("How often each hand won when it appeared.")

        rates     = query_win_rates(DB_PATH)
        rates_s   = sorted(rates, key=lambda r: r["win_rate_pct"])
        rnames    = [r["hand_name"]    for r in rates_s]
        rwinpcts  = [r["win_rate_pct"] for r in rates_s]
        rcolours  = [HAND_COLOURS[HAND_ORDER.index(h)] for h in rnames]

        fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor="#0f1923")
        ax2.set_facecolor("#0f1923")
        hbars = ax2.barh(rnames, rwinpcts, color=rcolours,
                         edgecolor="#0f1923", linewidth=0.8)

        for bar, pct in zip(hbars, rwinpcts):
            ax2.text(
                bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=8, color="#a0b8c8"
            )

        ax2.set_xlim(0, 115)
        ax2.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
        ax2.tick_params(colors="#607080")
        ax2.spines[:].set_visible(False)
        ax2.xaxis.grid(True, color="#1e2f42", linewidth=0.5)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

    with col_b:
        st.subheader("📋 Hand Stats Table")
        import pandas as pd
        table_rows = []
        for r in query_win_rates(DB_PATH):
            table_rows.append({
                "Hand":     r["hand_name"],
                "Seen":     f"{r['seen']:,}",
                "Wins":     f"{r['wins']:,}",
                "Win %":    f"{r['win_rate_pct']:.1f}%",
            })
        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Chart 3: Simulated vs Theoretical ────────────────────────────────────
    st.subheader("🔬 Simulated vs Theoretical Frequency")
    st.caption(
        "Comparing your Monte Carlo results to the known 5-card draw probabilities. "
        "Hold'em best-of-7 inflates stronger hands — this chart shows the difference."
    )

    sim_map  = {r["hand_name"]: r["pct"] for r in freqs}
    sim_vals = np.array([sim_map.get(h, 0)       for h in HAND_ORDER])
    th_vals  = np.array([THEORETICAL_PCT[h]       for h in HAND_ORDER])
    x        = np.arange(len(HAND_ORDER))
    w        = 0.38

    fig3, ax3 = plt.subplots(figsize=(11, 4), facecolor="#0f1923")
    ax3.set_facecolor("#0f1923")
    ax3.bar(x - w/2, sim_vals, w, label="Simulated (Hold'em)",
            color="#4a90d9", edgecolor="#0f1923")
    ax3.bar(x + w/2, th_vals,  w, label="Theoretical (5-card)",
            color="#52b788", edgecolor="#0f1923", alpha=0.85)
    ax3.set_yscale("log")
    ax3.set_xticks(x)
    ax3.set_xticklabels(HAND_ORDER, rotation=30, ha="right",
                        color="#a0b8c8", fontsize=9)
    ax3.set_ylabel("Frequency (%, log scale)", color="#607080")
    ax3.tick_params(colors="#607080")
    ax3.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=3))
    ax3.spines[:].set_visible(False)
    ax3.yaxis.grid(True, color="#1e2f42", linewidth=0.5)
    ax3.legend(frameon=False, labelcolor="#a0b8c8")
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close(fig3)

    st.markdown("---")

    # ── Chart 4: Convergence ──────────────────────────────────────────────────
    st.subheader("📉 Monte Carlo Convergence")
    st.caption(
        "Running frequency of the selected hand stabilises as more rounds accumulate — "
        "proof that Monte Carlo simulation converges to the true probability."
    )

    conv_hand = st.selectbox("Select hand to track", HAND_ORDER, index=1)

    from database import get_conn
    with get_conn(DB_PATH) as conn:
        raw = conn.execute(
            "SELECT best_hand FROM player_hands ORDER BY id"
        ).fetchall()

    total_h  = len(raw)
    running  = 0
    xs, ys   = [], []
    gap      = max(1, total_h // 400)

    for i, row in enumerate(raw, 1):
        if row["best_hand"] == conv_hand:
            running += 1
        if i % gap == 0 or i == total_h:
            xs.append(i)
            ys.append(100.0 * running / i)

    theory_line = THEORETICAL_PCT.get(conv_hand)

    fig4, ax4 = plt.subplots(figsize=(10, 3.5), facecolor="#0f1923")
    ax4.set_facecolor("#0f1923")
    ax4.plot(xs, ys, color="#4a90d9", linewidth=1.6,
             label=f"Running frequency of '{conv_hand}'")
    if theory_line:
        ax4.axhline(theory_line, color="#e76f51", linewidth=1.2,
                    linestyle="--", label=f"5-card theory: {theory_line:.3f}%")
    ax4.set_xlabel("Hands simulated", color="#607080")
    ax4.set_ylabel("Running frequency (%)", color="#607080")
    ax4.tick_params(colors="#607080")
    ax4.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=2))
    ax4.spines[:].set_visible(False)
    ax4.yaxis.grid(True, color="#1e2f42", linewidth=0.5)
    ax4.legend(frameon=False, labelcolor="#a0b8c8")
    plt.tight_layout()
    st.pyplot(fig4)
    plt.close(fig4)

    # ── Winning hand pie ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🥧 Winning Hand Share")
    st.caption("Which hands win the most rounds.")

    dist      = query_winning_hand_distribution(DB_PATH)
    pie_names = [r["winning_hand"] for r in dist]
    pie_vals  = [r["rounds_won"]   for r in dist]
    pie_cols  = [HAND_COLOURS[HAND_ORDER.index(h)] for h in pie_names]

    fig5, ax5 = plt.subplots(figsize=(7, 5), facecolor="#0f1923")
    ax5.set_facecolor("#0f1923")
    wedges, texts, autotexts = ax5.pie(
        pie_vals, labels=pie_names, colors=pie_cols,
        autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
        startangle=140,
        wedgeprops=dict(edgecolor="#0f1923", linewidth=1.2),
        textprops=dict(color="#a0b8c8", fontsize=9),
    )
    for at in autotexts:
        at.set_color("#0f1923")
        at.set_fontsize(8)
    plt.tight_layout()
    st.pyplot(fig5)
    plt.close(fig5)
