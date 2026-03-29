import random
 
# ── Suits and Ranks ───────────────────────────────────────────────────────────
 
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
 
# Map rank string → integer value (2=2, ..., 10=10, J=11, Q=12, K=13, A=14)
RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}
 
 
# ── Card ──────────────────────────────────────────────────────────────────────
 
class Card:
    """
    Represents a single playing card.
 
    Attributes:
        suit  (str): One of 'Hearts', 'Diamonds', 'Clubs', 'Spades'
        rank  (str): One of '2'..'10', 'J', 'Q', 'K', 'A'
        value (int): Numeric value 2–14 (Ace = 14)
    """
 
    def __init__(self, rank: str, suit: str):
        if rank not in RANK_VALUES:
            raise ValueError(f"Invalid rank: {rank!r}. Must be one of {RANKS}")
        if suit not in SUITS:
            raise ValueError(f"Invalid suit: {suit!r}. Must be one of {SUITS}")
        self.rank  = rank
        self.suit  = suit
        self.value = RANK_VALUES[rank]
 
    # ── display ───────────────────────────────────────────────────────────────
 
    # Short suit symbols for compact display
    _SUIT_SYMBOLS = {'Hearts': '♥', 'Diamonds': '♦', 'Clubs': '♣', 'Spades': '♠'}
 
    def __str__(self) -> str:
        """e.g.  'A♠'  '10♥'"""
        return f"{self.rank}{self._SUIT_SYMBOLS[self.suit]}"
 
    def __repr__(self) -> str:
        return f"Card('{self.rank}', '{self.suit}')"
 
    # ── comparison (by numeric value only — suit never breaks ties in poker) ──
 
    def __eq__(self, other) -> bool:
        return isinstance(other, Card) and self.value == other.value and self.suit == other.suit
 
    def __lt__(self, other) -> bool:
        return self.value < other.value
 
    def __le__(self, other) -> bool:
        return self.value <= other.value
 
    def __gt__(self, other) -> bool:
        return self.value > other.value
 
    def __ge__(self, other) -> bool:
        return self.value >= other.value
 
    def __hash__(self):
        return hash((self.rank, self.suit))
 
 
# ── Deck ──────────────────────────────────────────────────────────────────────
 
class Deck:
    """
    A standard 52-card deck.
 
    Usage:
        deck = Deck()
        deck.shuffle()
        hand = deck.deal(5)        # list of 5 Card objects
        remaining = len(deck)      # 47
    """
 
    def __init__(self):
        self.reset()
 
    def reset(self):
        """Rebuild and return a full 52-card unshuffled deck."""
        self._cards: list[Card] = [
            Card(rank, suit)
            for suit in SUITS
            for rank in RANKS
        ]
 
    def shuffle(self):
        """Shuffle the remaining cards in place."""
        random.shuffle(self._cards)
 
    def deal(self, n: int = 1) -> list[Card]:
        """
        Remove and return the top n cards from the deck.
 
        Raises:
            ValueError: if fewer than n cards remain.
        """
        if n > len(self._cards):
            raise ValueError(
                f"Cannot deal {n} cards — only {len(self._cards)} remain."
            )
        dealt = self._cards[:n]
        self._cards = self._cards[n:]
        return dealt
 
    def deal_one(self) -> Card:
        """Convenience wrapper — deal a single card."""
        return self.deal(1)[0]
 
    def burn(self, n: int = 1):
        """Discard n cards without returning them (standard poker burn rule)."""
        self.deal(n)
 
    # ── dunder helpers ────────────────────────────────────────────────────────
 
    def __len__(self) -> int:
        return len(self._cards)
 
    def __repr__(self) -> str:
        return f"Deck({len(self._cards)} cards remaining)"
 
    def __iter__(self):
        return iter(self._cards)
 
 
# ── Quick self-test ───────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    deck = Deck()
    print(f"Fresh deck : {len(deck)} cards")
 
    deck.shuffle()
    hand = deck.deal(5)
    print(f"Dealt hand : {' '.join(str(c) for c in hand)}")
    print(f"Remaining  : {len(deck)} cards")
 
    # Test comparison
    c1 = Card('A', 'Spades')
    c2 = Card('K', 'Hearts')
    print(f"\nAce > King : {c1 > c2}")   # True
    print(f"Repr       : {c1!r}")