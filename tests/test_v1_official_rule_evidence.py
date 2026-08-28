from skatmind.final_settlement import build_final_settlement_summary
from skatmind.game_declaration import GameDeclaration
from skatmind.game_value import (
    build_game_value_summary,
    calculate_game_value,
    calculate_suit_or_grand_game_level,
)
from skatmind.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    is_trump,
)

OFFICIAL_DECK = (
    "CA",
    "C10",
    "CK",
    "CQ",
    "CJ",
    "C9",
    "C8",
    "C7",
    "SA",
    "S10",
    "SK",
    "SQ",
    "SJ",
    "S9",
    "S8",
    "S7",
    "HA",
    "H10",
    "HK",
    "HQ",
    "HJ",
    "H9",
    "H8",
    "H7",
    "DA",
    "D10",
    "DK",
    "DQ",
    "DJ",
    "D9",
    "D8",
    "D7",
)

OFFICIAL_CARD_POINTS = {
    "A": 11,
    "10": 10,
    "K": 4,
    "Q": 3,
    "J": 2,
    "9": 0,
    "8": 0,
    "7": 0,
}

OFFICIAL_CATEGORY_SEQUENCES = (
    (
        "clubs",
        "TRUMP",
        ("CJ", "SJ", "HJ", "DJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7"),
    ),
    ("clubs", "S", ("SA", "S10", "SK", "SQ", "S9", "S8", "S7")),
    ("clubs", "H", ("HA", "H10", "HK", "HQ", "H9", "H8", "H7")),
    ("clubs", "D", ("DA", "D10", "DK", "DQ", "D9", "D8", "D7")),
    (
        "spades",
        "TRUMP",
        ("CJ", "SJ", "HJ", "DJ", "SA", "S10", "SK", "SQ", "S9", "S8", "S7"),
    ),
    ("spades", "C", ("CA", "C10", "CK", "CQ", "C9", "C8", "C7")),
    ("spades", "H", ("HA", "H10", "HK", "HQ", "H9", "H8", "H7")),
    ("spades", "D", ("DA", "D10", "DK", "DQ", "D9", "D8", "D7")),
    (
        "hearts",
        "TRUMP",
        ("CJ", "SJ", "HJ", "DJ", "HA", "H10", "HK", "HQ", "H9", "H8", "H7"),
    ),
    ("hearts", "C", ("CA", "C10", "CK", "CQ", "C9", "C8", "C7")),
    ("hearts", "S", ("SA", "S10", "SK", "SQ", "S9", "S8", "S7")),
    ("hearts", "D", ("DA", "D10", "DK", "DQ", "D9", "D8", "D7")),
    (
        "diamonds",
        "TRUMP",
        ("CJ", "SJ", "HJ", "DJ", "DA", "D10", "DK", "DQ", "D9", "D8", "D7"),
    ),
    ("diamonds", "C", ("CA", "C10", "CK", "CQ", "C9", "C8", "C7")),
    ("diamonds", "S", ("SA", "S10", "SK", "SQ", "S9", "S8", "S7")),
    ("diamonds", "H", ("HA", "H10", "HK", "HQ", "H9", "H8", "H7")),
    ("grand", "TRUMP", ("CJ", "SJ", "HJ", "DJ")),
    ("grand", "C", ("CA", "C10", "CK", "CQ", "C9", "C8", "C7")),
    ("grand", "S", ("SA", "S10", "SK", "SQ", "S9", "S8", "S7")),
    ("grand", "H", ("HA", "H10", "HK", "HQ", "H9", "H8", "H7")),
    ("grand", "D", ("DA", "D10", "DK", "DQ", "D9", "D8", "D7")),
    ("null", "C", ("CA", "CK", "CQ", "CJ", "C10", "C9", "C8", "C7")),
    ("null", "S", ("SA", "SK", "SQ", "SJ", "S10", "S9", "S8", "S7")),
    ("null", "H", ("HA", "HK", "HQ", "HJ", "H10", "H9", "H8", "H7")),
    ("null", "D", ("DA", "DK", "DQ", "DJ", "D10", "D9", "D8", "D7")),
)

OFFICIAL_BASE_VALUES = (
    ("clubs", 12),
    ("spades", 11),
    ("hearts", 10),
    ("diamonds", 9),
    ("grand", 24),
)

DECLARATION_VARIANTS = (
    ("simple", {}, (False, False, False, False), 0),
    ("hand", {"hand_game": True}, (True, False, False, False), 1),
    (
        "schneider_announced",
        {"schneider_announced": True},
        (True, True, False, False),
        2,
    ),
    (
        "schwarz_announced",
        {"schwarz_announced": True},
        (True, True, True, False),
        3,
    ),
    ("ouvert", {"ouvert": True}, (True, True, True, True), 4),
)

NORMALIZED_FLAG_ORDER = (
    "hand_game",
    "schneider_announced",
    "schwarz_announced",
    "ouvert",
)
SUIT_MATADOR_COUNTS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
GRAND_MATADOR_COUNTS = (1, 2, 3, 4)


def test_official_deck_and_card_points_are_exhaustive() -> None:
    assert len(OFFICIAL_DECK) == 32
    assert len(set(OFFICIAL_DECK)) == 32

    suit_point_totals = {}
    for suit in ("C", "S", "H", "D"):
        suit_cards = [card for card in OFFICIAL_DECK if card[0] == suit]
        assert len(suit_cards) == 8

        suit_point_totals[suit] = sum(OFFICIAL_CARD_POINTS[card[1:]] for card in suit_cards)
        assert suit_point_totals[suit] == 30

        for card in suit_cards:
            assert get_card_points(card) == OFFICIAL_CARD_POINTS[card[1:]]

    assert sum(suit_point_totals.values()) == 120


def test_official_effective_categories_and_orders_are_exhaustive() -> None:
    assert len(OFFICIAL_CATEGORY_SEQUENCES) == 25

    for game_type in ("clubs", "spades", "hearts", "diamonds", "grand", "null"):
        game_cards = [
            card
            for sequence_game_type, _, cards in OFFICIAL_CATEGORY_SEQUENCES
            if sequence_game_type == game_type
            for card in cards
        ]
        assert len(game_cards) == 32
        assert set(game_cards) == set(OFFICIAL_DECK)

    comparison_count = 0
    for game_type, effective_category, ordered_cards in OFFICIAL_CATEGORY_SEQUENCES:
        expects_trump = effective_category == "TRUMP"

        for card in ordered_cards:
            assert get_effective_suit(card, game_type) == effective_category
            assert is_trump(card, game_type) is expects_trump

        for stronger_index, stronger_card in enumerate(ordered_cards):
            for weaker_card in ordered_cards[stronger_index + 1 :]:
                assert get_card_strength(
                    stronger_card,
                    game_type,
                    effective_category,
                ) > get_card_strength(
                    weaker_card,
                    game_type,
                    effective_category,
                ), (game_type, effective_category, stronger_card, weaker_card)
                comparison_count += 1

    assert comparison_count == 674


def test_official_declared_suit_and_grand_values_are_exhaustive() -> None:
    suit_row_count = 0
    grand_row_count = 0

    for game_type, base_value in OFFICIAL_BASE_VALUES:
        matador_counts = GRAND_MATADOR_COUNTS if game_type == "grand" else SUIT_MATADOR_COUNTS

        for matadors in matador_counts:
            for variant_name, input_flags, expected_flags, modifier_count in DECLARATION_VARIANTS:
                case = (game_type, matadors, variant_name)
                declaration = GameDeclaration(
                    game_type=game_type,
                    matadors=matadors,
                    **input_flags,
                )
                actual_flags = tuple(
                    getattr(declaration, field_name) for field_name in NORMALIZED_FLAG_ORDER
                )
                expected_game_level = matadors + 1 + modifier_count
                expected_game_value = base_value * expected_game_level
                expected_summary = {
                    "game_type": game_type,
                    "is_null_game": False,
                    "base_value": base_value,
                    "game_level": expected_game_level,
                    "game_value": expected_game_value,
                    "details": {
                        "matadors": matadors,
                        "matador_multiplier": matadors + 1,
                        "hand_game": expected_flags[0],
                        "schneider_announced": expected_flags[1],
                        "schwarz_announced": expected_flags[2],
                        "ouvert": expected_flags[3],
                        "modifier_multiplier": modifier_count,
                        "is_complete": True,
                    },
                }

                assert actual_flags == expected_flags, case
                assert calculate_suit_or_grand_game_level(declaration) == expected_game_level, case
                assert calculate_game_value(declaration) == expected_game_value, case
                assert build_game_value_summary(declaration) == expected_summary, case

                if game_type == "grand":
                    grand_row_count += 1
                else:
                    suit_row_count += 1

    assert suit_row_count == 220
    assert grand_row_count == 20
    assert suit_row_count + grand_row_count == 240


def test_declared_value_and_achieved_settlement_levels_remain_separate() -> None:
    game_value_summary = build_game_value_summary(GameDeclaration(game_type="grand", matadors=1))

    assert game_value_summary == {
        "game_type": "grand",
        "is_null_game": False,
        "base_value": 24,
        "game_level": 2,
        "game_value": 48,
        "details": {
            "matadors": 1,
            "matador_multiplier": 2,
            "hand_game": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "ouvert": False,
            "modifier_multiplier": 0,
            "is_complete": True,
        },
    }

    final_settlement_summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
            "effective_schneider_status": "declarer_made_schneider",
            "game_end_reason": "normal_completion",
        },
        completed_tricks=[{"winner_role": "declarer"} for _ in range(10)],
    )

    assert game_value_summary["game_level"] == 2
    assert game_value_summary["game_value"] == 48
    assert final_settlement_summary["game_value"] == 48
    assert final_settlement_summary["effective_game_value"] == 96
    assert final_settlement_summary["settlement_score"] == 96
