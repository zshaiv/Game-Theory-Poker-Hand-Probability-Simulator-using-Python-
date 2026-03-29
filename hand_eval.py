from itertools import combinations
from collections import Counter
from card import Card

# ── Hand rank constants (higher = better) ─────────────────────────────────────

HIGH_CARD       = 1
ONE_PAIR        = 2
TWO_PAIR        = 3
THREE_OF_A_KIND = 4
STRAIGHT        = 5
FLUSH           = 6
FULL_HOUSE      = 7
FOUR_OF_A_KIND  = 8
STRAIGHT_FLUSH  = 9
ROYAL_FLUSH     = 10

HAND_NAMES = {
    HIGH_CARD:       "High Card",
    ONE_PAIR:        "One Pair",
    TWO_PAIR:        "Two Pair",
    THREE_OF_A_KIND: "Three of a Kind",
    STRAIGHT:        "Straight",
    FLUSH:           "Flush",
    FULL_HOUSE:      "Full House",
    FOUR_OF_A_KIND:  "Four of a Kind",
    STRAIGHT_FLUSH:  "Straight Flush",
    ROYAL_FLUSH:     "Royal Flush",
}


# ── Core 5-card evaluator ─────────────────────────────────────────────────────

def evaluate_five(cards: list[Card]) -> tuple:
    """
    Evaluate exactly 5 cards and return a rank tuple.

    The tuple is structured so that Python's default tuple comparison
    correctly orders hands from worst to best:

        (hand_rank, [tiebreaker values ...])

    Examples:
        One pair of Kings, kickers Q J 9  →  (2, [13, 12, 11, 9])
        Full house Aces over Kings         →  (7, [14, 13])

    Args:
        cards: exactly 5 Card objects

    Returns:
        tuple starting with the hand-rank integer (1–10)
    """
    if len(cards) != 5:
        raise ValueError(f"evaluate_five expects exactly 5 cards, got {len(cards)}")

    values  = sorted([c.value for c in cards], reverse=True)
    suits   = [c.suit for c in cards]
    counts  = Counter(values)                 # {value: count, ...}
    freq    = sorted(counts.values(), reverse=True)   # e.g. [2, 2, 1] for two-pair

    is_flush    = len(set(suits)) == 1
    is_straight = _is_straight(values)
    straight_high = _straight_high(values)

    # ── Royal Flush ───────────────────────────────────────────────────────────
    if is_flush and is_straight and straight_high == 14:
        return (ROYAL_FLUSH,)

    # ── Straight Flush ────────────────────────────────────────────────────────
    if is_flush and is_straight:
        return (STRAIGHT_FLUSH, straight_high)

    # ── Four of a Kind ────────────────────────────────────────────────────────
    if freq == [4, 1]:
        quad  = _values_with_count(counts, 4)
        kicker = _values_with_count(counts, 1)
        return (FOUR_OF_A_KIND, quad, kicker)

    # ── Full House ────────────────────────────────────────────────────────────
    if freq == [3, 2]:
        trips = _values_with_count(counts, 3)
        pair  = _values_with_count(counts, 2)
        return (FULL_HOUSE, trips, pair)

    # ── Flush ─────────────────────────────────────────────────────────────────
    if is_flush:
        return (FLUSH, values)

    # ── Straight ──────────────────────────────────────────────────────────────
    if is_straight:
        return (STRAIGHT, straight_high)

    # ── Three of a Kind ───────────────────────────────────────────────────────
    if freq == [3, 1, 1]:
        trips   = _values_with_count(counts, 3)
        kickers = sorted(_values_with_count(counts, 1, all_=True), reverse=True)
        return (THREE_OF_A_KIND, trips, kickers)

    # ── Two Pair ──────────────────────────────────────────────────────────────
    if freq == [2, 2, 1]:
        pairs  = sorted(_values_with_count(counts, 2, all_=True), reverse=True)
        kicker = _values_with_count(counts, 1)
        return (TWO_PAIR, pairs[0], pairs[1], kicker)

    # ── One Pair ──────────────────────────────────────────────────────────────
    if freq == [2, 1, 1, 1]:
        pair    = _values_with_count(counts, 2)
        kickers = sorted(_values_with_count(counts, 1, all_=True), reverse=True)
        return (ONE_PAIR, pair, kickers)

    # ── High Card ─────────────────────────────────────────────────────────────
    return (HIGH_CARD, values)


# ── Best-hand finder for 6 or 7 cards (Texas Hold'em) ────────────────────────

def best_hand(cards: list[Card]) -> tuple[tuple, list[Card]]:
    """
    From 5–7 cards find the best possible 5-card hand.

    Returns:
        (rank_tuple, best_five_cards)

    Usage (Texas Hold'em):
        rank, hand = best_hand(hole_cards + community_cards)
    """
    if len(cards) < 5:
        raise ValueError(f"Need at least 5 cards, got {len(cards)}")

    best_rank  = None
    best_five  = None

    for combo in combinations(cards, 5):
        rank = evaluate_five(list(combo))
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_five = list(combo)

    return best_rank, best_five


def hand_name(rank_tuple: tuple) -> str:
    """Return the human-readable name for a rank tuple."""
    return HAND_NAMES.get(rank_tuple[0], "Unknown")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_straight(values: list[int]) -> bool:
    """Check if 5 sorted-descending values form a straight (including A-2-3-4-5)."""
    unique = sorted(set(values), reverse=True)
    if len(unique) != 5:
        return False
    # Normal straight: highest - lowest == 4
    if unique[0] - unique[4] == 4:
        return True
    # Wheel (A-2-3-4-5): Ace treated as 1
    if unique == [14, 5, 4, 3, 2]:
        return True
    return False


def _straight_high(values: list[int]) -> int:
    """Return the high card of a straight (handles the wheel A-2-3-4-5 → 5)."""
    unique = sorted(set(values), reverse=True)
    if unique == [14, 5, 4, 3, 2]:
        return 5   # wheel — 5-high straight
    return unique[0]


def _values_with_count(counts: Counter, n: int, all_: bool = False):
    """
    Return value(s) that appear exactly n times in counts.

    all_=False → return the single highest such value (int)
    all_=True  → return list of all such values
    """
    matched = sorted([v for v, c in counts.items() if c == n], reverse=True)
    if all_:
        return matched
    return matched[0] if matched else None


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from card import Card

    def make(cards_str: str) -> list[Card]:
        """Parse 'As Kh Qd Jc 10s' style strings."""
        suit_map = {'s': 'Spades', 'h': 'Hearts', 'd': 'Diamonds', 'c': 'Clubs'}
        result = []
        for token in cards_str.split():
            rank = token[:-1].upper().replace('A','A').replace('J','J').replace('Q','Q').replace('K','K')
            suit = suit_map[token[-1]]
            result.append(Card(rank, suit))
        return result

    test_cases = [
        ("Royal Flush",     "As Ks Qs Js 10s"),
        ("Straight Flush",  "9h 8h 7h 6h 5h"),
        ("Four of a Kind",  "Ac Ad Ah As Kd"),
        ("Full House",      "Qc Qd Qh Kc Kd"),
        ("Flush",           "2d 5d 8d Jd Ad"),
        ("Straight",        "9c 8d 7h 6s 5c"),
        ("Three of a Kind", "7c 7d 7h As Kd"),
        ("Two Pair",        "Jc Jd 9h 9s Ad"),
        ("One Pair",        "10c 10d 8h 5s 2d"),
        ("High Card",       "Ac Jd 9h 6s 2c"),
        ("Wheel Straight",  "As 2d 3h 4c 5s"),
    ]

    print(f"{'Expected':<20} {'Detected':<20} {'Tuple'}")
    print("-" * 70)
    for name, cards_str in test_cases:
        cards = make(cards_str)
        rank  = evaluate_five(cards)
        print(f"{name:<20} {hand_name(rank):<20} {rank}")

    print("\n--- 7-card best_hand test (Texas Hold'em) ---")
    hole      = make("As Kd")
    community = make("Qh Jc 10s 2d 7h")
    rank, best = best_hand(hole + community)
    print(f"Hole: {' '.join(str(c) for c in hole)}")
    print(f"Board: {' '.join(str(c) for c in community)}")
    print(f"Best hand: {hand_name(rank)} → {' '.join(str(c) for c in best)}")