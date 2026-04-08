# app.py — Production Ready Streamlit Poker Simulator

import os
import sys
import time
import random
from pathlib import Path

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

# ─────────────────────────────────────────────
# PATH FIX (DEPLOY SAFE)
# ─────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# ─────────────────────────────────────────────
# IMPORTS (PROJECT FILES)
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Poker Probability Simulator",
    page_icon="🂡",
    layout="wide"
)

# ─────────────────────────────────────────────
# INIT DB ONCE
# ─────────────────────────────────────────────
@st.cache_resource
def init_database():
    init_db(DB_PATH)

init_database()

# ─────────────────────────────────────────────
# CACHE QUERIES (IMPORTANT)
# ─────────────────────────────────────────────
@st.cache_data
def get_summary():
    return query_summary_stats(DB_PATH)

@st.cache_data
def get_freq():
    return query_hand_frequency(DB_PATH)

@st.cache_data
def get_win_rates():
    return query_win_rates(DB_PATH)

@st.cache_data
def get_win_dist():
    return query_winning_hand_distribution(DB_PATH)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["Demo", "Simulation", "Analytics"]
)

# ─────────────────────────────────────────────
# PAGE 1: DEMO
# ─────────────────────────────────────────────
if page == "Demo":
    st.title("🎲 Poker Demo Round")

    players = st.slider("Players", 2, 6, 4)

    if st.button("Deal Cards"):
        try:
            result = play_round(num_players=players)

            st.subheader("Community Cards")
            st.write([str(c) for c in result.community_cards])

            for p in result.players:
                st.write(f"Player {p.player_id}: {[str(c) for c in p.hole_cards]}")

            st.success(f"Winner: {result.winner_ids}")

        except Exception as e:
            st.error(f"Error: {e}")

# ─────────────────────────────────────────────
# PAGE 2: SIMULATION
# ─────────────────────────────────────────────
elif page == "Simulation":
    st.title("📊 Run Simulation")

    rounds = st.selectbox("Rounds", [1000, 5000, 10000])
    players = st.slider("Players", 2, 6, 4)

    seed_mode = st.checkbox("Use Seed")
    seed_val = st.number_input("Seed", value=42)

    if st.button("Start Simulation"):

        try:
            if seed_mode:
                random.seed(seed_val)
                np.random.seed(seed_val)

            progress = st.progress(0)
            status = st.empty()

            BATCH = 500
            done = 0

            while done < rounds:
                batch_size = min(BATCH, rounds - done)

                batch = [play_round(num_players=players) for _ in range(batch_size)]
                insert_batch(batch, DB_PATH)

                done += batch_size
                progress.progress(done / rounds)

                status.text(f"{done}/{rounds} completed")

                time.sleep(0.01)  # prevent UI freeze

            st.success("Simulation Complete ✅")

            # Clear cache after update
            st.cache_data.clear()

        except Exception as e:
            st.error(f"Simulation failed: {e}")

# ─────────────────────────────────────────────
# PAGE 3: ANALYTICS
# ─────────────────────────────────────────────
elif page == "Analytics":
    st.title("📈 Statistics")

    stats = get_summary()

    if stats["total_rounds"] == 0:
        st.warning("Run simulation first")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Rounds", stats["total_rounds"])
    col2.metric("Hands", stats["total_hands"])
    col3.metric("Tie %", f"{stats['tie_rate_pct']:.2f}%")

    # ─────────────────────────────
    # HAND FREQUENCY
    # ─────────────────────────────
    st.subheader("Hand Frequency")

    freq = get_freq()

    names = [r["hand_name"] for r in freq]
    values = [r["pct"] for r in freq]

    fig, ax = plt.subplots()
    ax.bar(names, values)
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # ─────────────────────────────
    # WIN RATES
    # ─────────────────────────────
    st.subheader("Win Rates")

    rates = get_win_rates()

    df = pd.DataFrame(rates)
    st.dataframe(df)

    # ─────────────────────────────
    # PIE CHART
    # ─────────────────────────────
    st.subheader("Winning Distribution")

    dist = get_win_dist()

    labels = [r["winning_hand"] for r in dist]
    sizes = [r["rounds_won"] for r in dist]

    fig2, ax2 = plt.subplots()
    ax2.pie(sizes, labels=labels, autopct='%1.1f%%')
    st.pyplot(fig2)

    # ─────────────────────────────
    # DOWNLOAD BUTTON
    # ─────────────────────────────
    st.download_button(
        "Download Data",
        df.to_csv(index=False),
        "poker_stats.csv",
        "text/csv"
    )