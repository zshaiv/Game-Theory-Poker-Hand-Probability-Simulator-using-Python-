from dataclasses import dataclass, field
from card import Card, Deck
from hand_eval import best_hand, hand_name


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Player:
    """Represents one player at the table."""
    player_id: int
    hole_cards: list[Card] = field(default_factory=list)

    def __str__(self):
        cards = ' '.join(str(c) for c in self.hole_cards)
        return f"Player {self.player_id} [{cards}]"


@dataclass
class RoundResult:
    """
    Full result of one Texas Hold'em round.

    Attributes:
        players         : all players and their hole cards
        community_cards : the 5 shared cards (flop + turn + river)
        player_hands    : {player_id: (rank_tuple, best_5_cards)}
        winner_ids      : list of player_ids who won (>1 means a tie/split pot)
        winning_rank    : rank tuple of the winning hand
    """
    players:         list[Player]
    community_cards: list[Card]
    player_hands:    dict          # player_id → (rank_tuple, [Card,...])
    winner_ids:      list[int]
    winning_rank:    tuple

    def winner_hand_name(self) -> str:
        return hand_name(self.winning_rank)

    def summary(self) -> str:
        """Human-readable round summary."""
        lines = []
        board = ' '.join(str(c) for c in self.community_cards)
        lines.append(f"Board : {board}")
        lines.append("")

        for p in self.players:
            rank_tuple, best_five = self.player_hands[p.player_id]
            best_str  = ' '.join(str(c) for c in best_five)
            hand_str  = hand_name(rank_tuple)
            tag = " ← WINNER" if p.player_id in self.winner_ids else ""
            lines.append(f"  {p}  →  {hand_str} ({best_str}){tag}")

        lines.append("")
        if len(self.winner_ids) == 1:
            lines.append(f"Winner: Player {self.winner_ids[0]} "
                         f"with {self.winner_hand_name()}")
        else:
            ids = ', '.join(str(i) for i in self.winner_ids)
            lines.append(f"Tie between Players {ids} "
                         f"with {self.winner_hand_name()}")
        return '\n'.join(lines)


# ── Main game function ────────────────────────────────────────────────────────

def play_round(num_players: int = 2) -> RoundResult:
    """
    Simulate one complete Texas Hold'em round.

    Args:
        num_players: 2–9 players (standard table limits)

    Returns:
        RoundResult with all cards, hands, and winner info
    """
    if not (2 <= num_players <= 9):
        raise ValueError(f"num_players must be 2–9, got {num_players}")

    # ── Setup ─────────────────────────────────────────────────────────────────
    deck    = Deck()
    deck.shuffle()
    players = [Player(player_id=i + 1) for i in range(num_players)]

    # ── Deal hole cards (2 per player, alternating like a real deal) ──────────
    for _ in range(2):
        for player in players:
            player.hole_cards.append(deck.deal_one())

    # ── Deal community cards ──────────────────────────────────────────────────
    deck.burn()                        # burn before flop
    flop  = deck.deal(3)               # flop  : 3 cards

    deck.burn()                        # burn before turn
    turn  = deck.deal(1)               # turn  : 1 card

    deck.burn()                        # burn before river
    river = deck.deal(1)               # river : 1 card

    community = flop + turn + river    # 5 community cards total

    # ── Evaluate each player's best hand ─────────────────────────────────────
    player_hands = {}
    for player in players:
        rank_tuple, best_five = best_hand(player.hole_cards + community)
        player_hands[player.player_id] = (rank_tuple, best_five)

    # ── Determine winner(s) ───────────────────────────────────────────────────
    best_rank   = max(rank for rank, _ in player_hands.values())
    winner_ids  = [
        pid for pid, (rank, _) in player_hands.items()
        if rank == best_rank
    ]

    return RoundResult(
        players         = players,
        community_cards = community,
        player_hands    = player_hands,
        winner_ids      = winner_ids,
        winning_rank    = best_rank,
    )


# ── Convenience: extract flat result dict for database layer ──────────────────

def round_to_record(result: RoundResult) -> dict:
    """
    Flatten a RoundResult into a plain dict suitable for SQL insertion.

    Keys:
        num_players, community_cards, winner_ids, winning_hand,
        p{i}_hole, p{i}_hand  (for each player i)
    """
    record = {
        "num_players":      len(result.players),
        "community_cards":  ' '.join(str(c) for c in result.community_cards),
        "winner_ids":       ','.join(str(i) for i in result.winner_ids),
        "winning_hand":     result.winner_hand_name(),
    }
    for p in result.players:
        rank_tuple, best_five = result.player_hands[p.player_id]
        record[f"p{p.player_id}_hole"] = ' '.join(str(c) for c in p.hole_cards)
        record[f"p{p.player_id}_hand"] = hand_name(rank_tuple)
    return record


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    random.seed(42)

    for n in [2, 4, 6]:
        print(f"{'='*60}")
        print(f"  {n}-player round")
        print(f"{'='*60}")
        result = play_round(num_players=n)
        print(result.summary())
        print()

    print("── Flat record (for DB layer) ──")
    result = play_round(num_players=3)
    record = round_to_record(result)
    for k, v in record.items():
        print(f"  {k:<22} {v}")