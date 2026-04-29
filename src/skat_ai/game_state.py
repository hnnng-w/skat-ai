from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameState:
    game_type: str
    player_role: str
    hand: list[str]
    current_trick: list[str]
    played_cards: list[str] = field(default_factory=list)
    skat: list[str] = field(default_factory=list)
    player_position: str = "unknown"
    trick_leader: str = "unknown"
    completed_tricks: list[dict[str, Any]] = field(default_factory=list)
    declarer_points: int = 0
    defender_points: int = 0
    next_player: str = "unknown"