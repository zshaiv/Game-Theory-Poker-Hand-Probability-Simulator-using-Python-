import sqlite3
import os
from contextlib import contextmanager
from game import RoundResult, round_to_record

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "poker_sim.db")


# ── Schema ────────────────────────────────────────────────────────────────────

# One row per simulated round
CREATE_ROUNDS = """
CREATE TABLE IF NOT EXISTS rounds (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    num_players      INTEGER NOT NULL,
    community_cards  TEXT    NOT NULL,
    winner_ids       TEXT    NOT NULL,   -- comma-separated for split pots
    winning_hand     TEXT    NOT NULL,
    is_tie           INTEGER NOT NULL DEFAULT 0,
    simulated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# One row per player per round
CREATE_PLAYER_HANDS = """
CREATE TABLE IF NOT EXISTS player_hands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id    INTEGER NOT NULL REFERENCES rounds(id),
    player_id   INTEGER NOT NULL,
    hole_cards  TEXT    NOT NULL,
    best_hand   TEXT    NOT NULL,
    is_winner   INTEGER NOT NULL DEFAULT 0
);
"""

# Aggregate table — updated after every batch for fast querying
CREATE_HAND_STATS = """
CREATE TABLE IF NOT EXISTS hand_stats (
    hand_name   TEXT    PRIMARY KEY,
    seen_count  INTEGER NOT NULL DEFAULT 0,
    win_count   INTEGER NOT NULL DEFAULT 0
);
"""

ALL_HAND_NAMES = [
    "High Card", "One Pair", "Two Pair", "Three of a Kind",
    "Straight", "Flush", "Full House", "Four of a Kind",
    "Straight Flush", "Royal Flush",
]


# ── Connection context manager ────────────────────────────────────────────────

@contextmanager
def get_conn(db_path: str = DB_PATH):
    """Yield a connection; commit on success, rollback on error, always close."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # faster concurrent writes
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Initialisation ────────────────────────────────────────────────────────────

def init_db(db_path: str = DB_PATH):
    """
    Create all tables if they don't exist and seed hand_stats rows.
    Safe to call multiple times (idempotent).
    """
    with get_conn(db_path) as conn:
        conn.execute(CREATE_ROUNDS)
        conn.execute(CREATE_PLAYER_HANDS)
        conn.execute(CREATE_HAND_STATS)

        # Seed one row per hand type so stats queries always return all 10 rows
        for name in ALL_HAND_NAMES:
            conn.execute(
                "INSERT OR IGNORE INTO hand_stats (hand_name) VALUES (?)",
                (name,)
            )
    print(f"Database ready: {db_path}")


# ── Insert ────────────────────────────────────────────────────────────────────

def insert_result(result: RoundResult, db_path: str = DB_PATH) -> int:
    """
    Persist one RoundResult.

    Returns:
        The new round_id (INTEGER PRIMARY KEY).
    """
    record   = round_to_record(result)
    is_tie   = 1 if len(result.winner_ids) > 1 else 0

    with get_conn(db_path) as conn:
        # ── rounds table ──────────────────────────────────────────────────────
        cur = conn.execute(
            """
            INSERT INTO rounds
                (num_players, community_cards, winner_ids, winning_hand, is_tie)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["num_players"],
                record["community_cards"],
                record["winner_ids"],
                record["winning_hand"],
                is_tie,
            ),
        )
        round_id = cur.lastrowid

        # ── player_hands table ────────────────────────────────────────────────
        for player in result.players:
            pid       = player.player_id
            hand_name = record[f"p{pid}_hand"]
            is_winner = 1 if pid in result.winner_ids else 0

            conn.execute(
                """
                INSERT INTO player_hands
                    (round_id, player_id, hole_cards, best_hand, is_winner)
                VALUES (?, ?, ?, ?, ?)
                """,
                (round_id, pid, record[f"p{pid}_hole"], hand_name, is_winner),
            )

            # ── update hand_stats ─────────────────────────────────────────────
            conn.execute(
                """
                UPDATE hand_stats
                SET seen_count = seen_count + 1,
                    win_count  = win_count  + ?
                WHERE hand_name = ?
                """,
                (is_winner, hand_name),
            )

    return round_id


def insert_batch(results: list[RoundResult], db_path: str = DB_PATH):
    """
    Insert many RoundResults efficiently inside a single transaction.
    Much faster than calling insert_result() in a loop for large simulations.
    """
    with get_conn(db_path) as conn:
        for result in results:
            record  = round_to_record(result)
            is_tie  = 1 if len(result.winner_ids) > 1 else 0

            cur = conn.execute(
                """
                INSERT INTO rounds
                    (num_players, community_cards, winner_ids, winning_hand, is_tie)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record["num_players"],
                    record["community_cards"],
                    record["winner_ids"],
                    record["winning_hand"],
                    is_tie,
                ),
            )
            round_id = cur.lastrowid

            for player in result.players:
                pid       = player.player_id
                hand_name = record[f"p{pid}_hand"]
                is_winner = 1 if pid in result.winner_ids else 0

                conn.execute(
                    """
                    INSERT INTO player_hands
                        (round_id, player_id, hole_cards, best_hand, is_winner)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (round_id, pid, record[f"p{pid}_hole"], hand_name, is_winner),
                )

                conn.execute(
                    """
                    UPDATE hand_stats
                    SET seen_count = seen_count + 1,
                        win_count  = win_count  + ?
                    WHERE hand_name = ?
                    """,
                    (is_winner, hand_name),
                )


# ── Queries ───────────────────────────────────────────────────────────────────

def query_hand_frequency(db_path: str = DB_PATH) -> list[dict]:
    """
    Return how often each hand type appeared across all simulated rounds,
    as both a raw count and a percentage.

    Returns list of dicts sorted rarest → most common:
        [{'hand_name': 'Royal Flush', 'seen': 3, 'pct': 0.003}, ...]
    """
    with get_conn(db_path) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM player_hands"
        ).fetchone()[0]

        if total == 0:
            return []

        rows = conn.execute(
            """
            SELECT hand_name,
                   seen_count                              AS seen,
                   ROUND(100.0 * seen_count / ?, 4)       AS pct
            FROM   hand_stats
            ORDER  BY seen_count DESC
            """,
            (total,),
        ).fetchall()

    return [dict(r) for r in rows]


def query_win_rates(db_path: str = DB_PATH) -> list[dict]:
    """
    For each hand type that has appeared, return its win rate:
    how often it won when it appeared.

    Returns list of dicts sorted by win rate descending:
        [{'hand_name': 'Royal Flush', 'seen': 3, 'wins': 3, 'win_rate_pct': 100.0}, ...]
    """
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT hand_name,
                   seen_count                                            AS seen,
                   win_count                                             AS wins,
                   ROUND(100.0 * win_count / MAX(seen_count, 1), 2)     AS win_rate_pct
            FROM   hand_stats
            WHERE  seen_count > 0
            ORDER  BY win_rate_pct DESC, seen_count DESC
            """,
        ).fetchall()

    return [dict(r) for r in rows]


def query_winning_hand_distribution(db_path: str = DB_PATH) -> list[dict]:
    """
    Among rounds that were decided (no tie), how often did each hand
    type WIN the round?

    Returns list of dicts sorted by frequency descending:
        [{'winning_hand': 'One Pair', 'rounds_won': 4523, 'pct': 45.23}, ...]
    """
    with get_conn(db_path) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM rounds WHERE is_tie = 0"
        ).fetchone()[0]

        if total == 0:
            return []

        rows = conn.execute(
            """
            SELECT winning_hand,
                   COUNT(*)                                  AS rounds_won,
                   ROUND(100.0 * COUNT(*) / ?, 4)           AS pct
            FROM   rounds
            WHERE  is_tie = 0
            GROUP  BY winning_hand
            ORDER  BY rounds_won DESC
            """,
            (total,),
        ).fetchall()

    return [dict(r) for r in rows]


def query_summary_stats(db_path: str = DB_PATH) -> dict:
    """
    High-level summary numbers about the simulation so far.

    Returns:
        {
          'total_rounds': int,
          'total_hands':  int,
          'total_ties':   int,
          'tie_rate_pct': float,
        }
    """
    with get_conn(db_path) as conn:
        total_rounds = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
        total_hands  = conn.execute("SELECT COUNT(*) FROM player_hands").fetchone()[0]
        total_ties   = conn.execute(
            "SELECT COUNT(*) FROM rounds WHERE is_tie = 1"
        ).fetchone()[0]

    tie_rate = round(100.0 * total_ties / max(total_rounds, 1), 4)
    return {
        "total_rounds": total_rounds,
        "total_hands":  total_hands,
        "total_ties":   total_ties,
        "tie_rate_pct": tie_rate,
    }


def reset_db(db_path: str = DB_PATH):
    """Drop all tables and reinitialise. Use with caution."""
    with get_conn(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS player_hands")
        conn.execute("DROP TABLE IF EXISTS rounds")
        conn.execute("DROP TABLE IF EXISTS hand_stats")
    init_db(db_path)
    print("Database reset.")


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    from game import play_round

    TEST_DB = "/tmp/poker_test.db"

    # Fresh start
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    init_db(TEST_DB)

    # Insert 500 rounds as a batch
    random.seed(0)
    NUM = 500
    print(f"\nSimulating and storing {NUM} rounds ...")
    results = [play_round(num_players=4) for _ in range(NUM)]
    insert_batch(results, TEST_DB)
    print("Done.\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    stats = query_summary_stats(TEST_DB)
    print("── Summary ──────────────────────────────────────────")
    for k, v in stats.items():
        print(f"  {k:<20} {v}")

    # ── Hand frequency ────────────────────────────────────────────────────────
    print("\n── Hand frequency (all players) ─────────────────────")
    print(f"  {'Hand':<20} {'Seen':>7}  {'%':>8}")
    print("  " + "-" * 40)
    for row in query_hand_frequency(TEST_DB):
        print(f"  {row['hand_name']:<20} {row['seen']:>7}  {row['pct']:>7.3f}%")

    # ── Win rates ─────────────────────────────────────────────────────────────
    print("\n── Win rate per hand type ───────────────────────────")
    print(f"  {'Hand':<20} {'Seen':>6}  {'Wins':>6}  {'Win %':>8}")
    print("  " + "-" * 46)
    for row in query_win_rates(TEST_DB):
        print(f"  {row['hand_name']:<20} {row['seen']:>6}  {row['wins']:>6}  {row['win_rate_pct']:>7.2f}%")

    # ── Winning hand distribution ─────────────────────────────────────────────
    print("\n── Winning hand distribution (decided rounds) ───────")
    print(f"  {'Hand':<20} {'Rounds won':>12}  {'%':>8}")
    print("  " + "-" * 46)
    for row in query_winning_hand_distribution(TEST_DB):
        print(f"  {row['winning_hand']:<20} {row['rounds_won']:>12}  {row['pct']:>7.3f}%")

    # Cleanup
    os.remove(TEST_DB)