import time
import random
import argparse
import os
from game import play_round
from database import init_db, insert_batch, query_summary_stats, DB_PATH

# ── Config defaults ────────────────────────────────────────────────────────────

DEFAULT_ROUNDS      = 10_000
DEFAULT_PLAYERS     = 4
DEFAULT_BATCH_SIZE  = 500     # rounds inserted per DB transaction
DEFAULT_SEED        = None    # None = non-deterministic


# ── Progress bar (no external libs needed) ────────────────────────────────────

def _progress_bar(done: int, total: int, width: int = 40) -> str:
    filled = int(width * done / total)
    bar    = "█" * filled + "░" * (width - filled)
    pct    = 100.0 * done / total
    return f"[{bar}] {pct:5.1f}%  {done:,}/{total:,}"


# ── Core simulation function ──────────────────────────────────────────────────

def run_simulation(
    num_rounds:  int  = DEFAULT_ROUNDS,
    num_players: int  = DEFAULT_PLAYERS,
    batch_size:  int  = DEFAULT_BATCH_SIZE,
    seed:        int  = DEFAULT_SEED,
    db_path:     str  = DB_PATH,
    verbose:     bool = True,
) -> dict:
    """
    Run a Monte Carlo simulation of Texas Hold'em.

    Each round is a full game: shuffle, deal, evaluate, determine winner.
    Results are stored in SQLite in batches for efficiency.

    Args:
        num_rounds  : total rounds to simulate
        num_players : players per round (2–9)
        batch_size  : rounds per DB transaction (tune for speed vs memory)
        seed        : random seed for reproducibility (None = random)
        db_path     : path to SQLite database file
        verbose     : print progress to stdout

    Returns:
        dict with timing and summary stats
    """
    if seed is not None:
        random.seed(seed)

    # ── Init DB ───────────────────────────────────────────────────────────────
    init_db(db_path)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Poker Hand Probability Simulator — Monte Carlo Engine")
        print(f"{'='*60}")
        print(f"  Rounds      : {num_rounds:,}")
        print(f"  Players     : {num_players}")
        print(f"  Batch size  : {batch_size:,}")
        print(f"  Seed        : {seed if seed is not None else 'random'}")
        print(f"  Database    : {db_path}")
        print(f"{'='*60}\n")

    # ── Simulation loop ───────────────────────────────────────────────────────
    t_start     = time.perf_counter()
    completed   = 0
    batch       = []

    while completed < num_rounds:
        # Fill one batch
        this_batch = min(batch_size, num_rounds - completed)
        for _ in range(this_batch):
            batch.append(play_round(num_players=num_players))

        # Flush batch to DB
        insert_batch(batch, db_path)
        completed += len(batch)
        batch.clear()

        # Progress report
        if verbose:
            elapsed   = time.perf_counter() - t_start
            rps       = completed / max(elapsed, 1e-9)   # rounds per second
            remaining = (num_rounds - completed) / max(rps, 1e-9)
            bar       = _progress_bar(completed, num_rounds)
            print(
                f"\r  {bar}  {rps:,.0f} r/s  ETA {remaining:.1f}s   ",
                end="",
                flush=True,
            )

    t_elapsed = time.perf_counter() - t_start

    if verbose:
        print()   # newline after progress bar
        print(f"\n  Finished in {t_elapsed:.2f}s  "
              f"({num_rounds / t_elapsed:,.0f} rounds/sec)\n")

    # ── Final summary from DB ─────────────────────────────────────────────────
    stats = query_summary_stats(db_path)

    if verbose:
        _print_summary(stats, db_path)

    return {
        "elapsed_sec":   round(t_elapsed, 3),
        "rounds_per_sec": round(num_rounds / t_elapsed),
        **stats,
    }


# ── Pretty summary printer ────────────────────────────────────────────────────

def _print_summary(stats: dict, db_path: str = DB_PATH):
    from database import (
        query_hand_frequency,
        query_win_rates,
        query_winning_hand_distribution,
    )

    print(f"{'─'*60}")
    print(f"  {'Metric':<28} {'Value':>12}")
    print(f"{'─'*60}")
    print(f"  {'Total rounds simulated':<28} {stats['total_rounds']:>12,}")
    print(f"  {'Total hands evaluated':<28} {stats['total_hands']:>12,}")
    print(f"  {'Split-pot ties':<28} {stats['total_ties']:>12,}")
    print(f"  {'Tie rate':<28} {stats['tie_rate_pct']:>11.3f}%")
    print(f"{'─'*60}\n")

    # Hand frequency
    freqs = query_hand_frequency(db_path)
    print(f"  {'Hand':<22} {'Seen':>8}  {'Frequency':>10}")
    print(f"  {'─'*44}")
    for r in freqs:
        bar = "▌" * int(r["pct"] / 2)
        print(f"  {r['hand_name']:<22} {r['seen']:>8,}  {r['pct']:>8.3f}%  {bar}")

    # Win rates
    rates = query_win_rates(db_path)
    print(f"\n  {'Hand':<22} {'Win rate':>10}")
    print(f"  {'─'*35}")
    for r in rates:
        print(f"  {r['hand_name']:<22} {r['win_rate_pct']:>9.2f}%")

    # Winning hand distribution
    dist = query_winning_hand_distribution(db_path)
    print(f"\n  {'Winning hand':<22} {'Rounds won':>12}  {'Share':>8}")
    print(f"  {'─'*46}")
    for r in dist:
        print(f"  {r['winning_hand']:<22} {r['rounds_won']:>12,}  {r['pct']:>7.3f}%")
    print()


# ── CLI entry point ───────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Poker Hand Probability Simulator — Monte Carlo Engine"
    )
    p.add_argument(
        "-n", "--rounds",
        type=int, default=DEFAULT_ROUNDS,
        help=f"Number of rounds to simulate (default: {DEFAULT_ROUNDS:,})"
    )
    p.add_argument(
        "-p", "--players",
        type=int, default=DEFAULT_PLAYERS,
        help=f"Players per round 2–9 (default: {DEFAULT_PLAYERS})"
    )
    p.add_argument(
        "-b", "--batch",
        type=int, default=DEFAULT_BATCH_SIZE,
        help=f"DB batch size (default: {DEFAULT_BATCH_SIZE})"
    )
    p.add_argument(
        "-s", "--seed",
        type=int, default=None,
        help="Random seed for reproducibility (default: random)"
    )
    p.add_argument(
        "-d", "--db",
        type=str, default=DB_PATH,
        help=f"SQLite database path (default: {DB_PATH})"
    )
    p.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the database before running"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.reset:
        from database import reset_db
        reset_db(args.db)

    result = run_simulation(
        num_rounds  = args.rounds,
        num_players = args.players,
        batch_size  = args.batch,
        seed        = args.seed,
        db_path     = args.db,
        verbose     = True,
    )