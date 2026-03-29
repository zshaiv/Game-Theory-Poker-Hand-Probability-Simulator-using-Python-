
import argparse
import os
import sys
import random

from database import DB_PATH, init_db, reset_db, query_summary_stats

# ── ANSI colours (graceful fallback on Windows) ────────────────────────────────

if sys.platform == "win32":
    os.system("color")   # enable ANSI on Windows 10+

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"


def c(text, colour):
    return f"{colour}{text}{RESET}"


# ── Banner ─────────────────────────────────────────────────────────────────────

BANNER = f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════╗
║       Poker Hand Probability Simulator  🂡              ║
║       Game Theory · Monte Carlo · SQLite               ║
╠══════════════════════════════════════════════════════════╣
║  Students : Kumar Shaiv Sah / Soutrik Ghosh            ║
║  Enroll   : 2428010002 / 2428010003                    ║
║  Branch   : Computer & Communication Engineering       ║
╚══════════════════════════════════════════════════════════╝{RESET}
"""


# ── Interactive menu ───────────────────────────────────────────────────────────

MENU = f"""
  {BOLD}What would you like to do?{RESET}

  {CYAN}[1]{RESET}  Run simulation          (Monte Carlo rounds → SQLite)
  {CYAN}[2]{RESET}  Generate charts         (analysis.py → PNG files)
  {CYAN}[3]{RESET}  Play a demo round       (watch a live 4-player hand)
  {CYAN}[4]{RESET}  View database stats     (quick summary from DB)
  {CYAN}[5]{RESET}  Reset database          (wipe all stored results)
  {CYAN}[0]{RESET}  Exit

"""


def prompt_menu() -> str:
    print(MENU)
    return input("  Choice → ").strip()


# ── Sub-commands ───────────────────────────────────────────────────────────────

def cmd_simulate(rounds: int, players: int, seed, db_path: str, reset: bool):
    """Run the Monte Carlo simulation."""
    from simulation import run_simulation
    if reset:
        reset_db(db_path)
    run_simulation(
        num_rounds  = rounds,
        num_players = players,
        seed        = seed,
        db_path     = db_path,
        verbose     = True,
    )


def cmd_analyse(db_path: str):
    """Generate all matplotlib charts."""
    from analysis import generate_all_charts
    generate_all_charts(db_path)


def cmd_demo(players: int = 4, seed=None):
    """Play 5 live demo rounds and print each result."""
    from game import play_round

    if seed is not None:
        random.seed(seed)

    print(f"\n{BOLD}  ── Live Demo: 5 rounds, {players} players ──{RESET}\n")

    for i in range(1, 6):
        result = play_round(num_players=players)
        print(c(f"  Round {i}", CYAN))
        for line in result.summary().splitlines():
            print(f"    {line}")
        print()

    print(c("  Demo complete.\n", GREEN))


def cmd_stats(db_path: str):
    """Print a quick summary from the database."""
    from database import (
        query_hand_frequency,
        query_win_rates,
        query_winning_hand_distribution,
    )

    stats = query_summary_stats(db_path)
    if stats["total_rounds"] == 0:
        print(c("\n  Database is empty — run a simulation first.\n", YELLOW))
        return

    print(f"\n{BOLD}  ── Database Summary ──{RESET}")
    print(f"  Total rounds  : {stats['total_rounds']:>10,}")
    print(f"  Total hands   : {stats['total_hands']:>10,}")
    print(f"  Ties          : {stats['total_ties']:>10,}  ({stats['tie_rate_pct']:.3f}%)")

    print(f"\n{BOLD}  ── Hand Frequency ──{RESET}")
    print(f"  {'Hand':<22} {'Seen':>8}  {'Freq':>8}")
    print(f"  {'─'*42}")
    for r in query_hand_frequency(db_path):
        print(f"  {r['hand_name']:<22} {r['seen']:>8,}  {r['pct']:>7.3f}%")

    print(f"\n{BOLD}  ── Win Rate per Hand ──{RESET}")
    print(f"  {'Hand':<22} {'Win rate':>10}")
    print(f"  {'─'*35}")
    for r in query_win_rates(db_path):
        print(f"  {r['hand_name']:<22} {r['win_rate_pct']:>9.2f}%")

    print(f"\n{BOLD}  ── Winning Hand Distribution ──{RESET}")
    print(f"  {'Hand':<22} {'Wins':>8}  {'Share':>8}")
    print(f"  {'─'*42}")
    for r in query_winning_hand_distribution(db_path):
        print(f"  {r['winning_hand']:<22} {r['rounds_won']:>8,}  {r['pct']:>7.3f}%")
    print()


def cmd_reset(db_path: str):
    confirm = input(
        c("\n  This will erase all simulation data. Type YES to confirm: ", YELLOW)
    ).strip()
    if confirm == "YES":
        reset_db(db_path)
        print(c("  Database reset.\n", GREEN))
    else:
        print(c("  Cancelled.\n", DIM))


# ── Interactive loop ───────────────────────────────────────────────────────────

def interactive_mode(db_path: str):
    """Present a menu and dispatch until the user exits."""
    print(BANNER)
    init_db(db_path)

    while True:
        choice = prompt_menu()

        if choice == "1":
            try:
                n = int(input(c("  Rounds to simulate [10000]: ", CYAN)).strip() or "10000")
                p = int(input(c("  Players per round  [4]:     ", CYAN)).strip() or "4")
                s = input(c("  Random seed        [Enter=random]: ", CYAN)).strip()
                seed = int(s) if s else None
                rst  = input(c("  Reset DB first?    [y/N]: ", CYAN)).strip().lower() == "y"
                cmd_simulate(n, p, seed, db_path, rst)
            except ValueError:
                print(c("  Invalid input — please enter integers.\n", RED))

        elif choice == "2":
            cmd_analyse(db_path)

        elif choice == "3":
            try:
                p = int(input(c("  Players per round  [4]: ", CYAN)).strip() or "4")
                cmd_demo(players=p)
            except ValueError:
                print(c("  Invalid input.\n", RED))

        elif choice == "4":
            cmd_stats(db_path)

        elif choice == "5":
            cmd_reset(db_path)

        elif choice == "0":
            print(c("\n  Goodbye!\n", DIM))
            sys.exit(0)

        else:
            print(c("  Unknown choice — please enter 0–5.\n", RED))


# ── CLI argument parser ────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Poker Hand Probability Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                        interactive menu
  python3 main.py sim -n 50000 -p 6     simulate 50k rounds, 6 players
  python3 main.py sim -n 10000 --reset  fresh simulation
  python3 main.py analyse               generate charts from stored data
  python3 main.py demo -p 3             3-player live demo
  python3 main.py stats                 print DB summary
  python3 main.py reset                 wipe database (no confirmation)
        """,
    )
    parser.add_argument(
        "-d", "--db", default=DB_PATH,
        help=f"SQLite database path (default: {DB_PATH})"
    )

    sub = parser.add_subparsers(dest="command")

    # sim
    sim_p = sub.add_parser("sim", help="Run Monte Carlo simulation")
    sim_p.add_argument("-n", "--rounds",  type=int, default=10_000)
    sim_p.add_argument("-p", "--players", type=int, default=4)
    sim_p.add_argument("-s", "--seed",    type=int, default=None)
    sim_p.add_argument("--reset", action="store_true",
                       help="Wipe DB before running")

    # analyse
    sub.add_parser("analyse", help="Generate matplotlib charts")

    # demo
    demo_p = sub.add_parser("demo", help="Play 5 live demo rounds")
    demo_p.add_argument("-p", "--players", type=int, default=4)
    demo_p.add_argument("-s", "--seed",    type=int, default=None)

    # stats
    sub.add_parser("stats", help="Print database summary")

    # reset
    sub.add_parser("reset", help="Wipe database (no confirmation prompt)")

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    # No sub-command → interactive menu
    if args.command is None:
        interactive_mode(args.db)
        return

    # Sub-commands always init DB first (idempotent)
    init_db(args.db)

    if args.command == "sim":
        cmd_simulate(args.rounds, args.players, args.seed, args.db, args.reset)

    elif args.command == "analyse":
        cmd_analyse(args.db)

    elif args.command == "demo":
        cmd_demo(players=args.players, seed=args.seed)

    elif args.command == "stats":
        cmd_stats(args.db)

    elif args.command == "reset":
        reset_db(args.db)
        print(c("  Database reset.\n", GREEN))


if __name__ == "__main__":
    main()