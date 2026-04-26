from dataclasses import dataclass, field


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
