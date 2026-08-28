from skatmind.exact_search_state import (
    ExactSearchState,
    get_exact_search_terminal_facts,
)
from skatmind.final_settlement import build_final_settlement_summary
from skatmind.game_declaration import SUIT_GAME_TYPES, GameDeclaration
from skatmind.game_result import (
    apply_completed_null_contract_result,
    build_game_result_summary_from_points,
)
from skatmind.game_value import build_game_value_summary
from skatmind.overbid import build_overbid_summary
from skatmind.terminal_utility import TerminalUtility, build_terminal_utility


def has_supported_terminal_utility_inputs(declaration: GameDeclaration) -> bool:
    """Returns whether normal terminal settlement is supported for a declaration."""
    if not isinstance(declaration, GameDeclaration) or declaration.bid_value is None:
        return False
    if declaration.game_type != "null":
        return declaration.matadors is not None

    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(
        game_value_summary=game_value,
        bid_value=declaration.bid_value,
        game_end_reason="normal_completion",
    )
    return overbid["is_overbid"] is False


def build_exact_terminal_utility(
    *,
    state: ExactSearchState,
    local_side: str,
) -> TerminalUtility:
    """Builds exact normal-completion utility for a supported game type."""
    if state.declaration.game_type == "null":
        return build_exact_null_terminal_utility(state=state, local_side=local_side)
    return build_exact_suit_or_grand_terminal_utility(
        state=state,
        local_side=local_side,
    )


def build_exact_suit_or_grand_terminal_utility(
    *,
    state: ExactSearchState,
    local_side: str,
) -> TerminalUtility:
    """Builds exact normal-completion utility through existing settlement logic."""
    game_type = state.declaration.game_type
    if game_type not in {*SUIT_GAME_TYPES, "grand"}:
        raise ValueError("Exact terminal utility supports only Suit and Grand games.")
    if state.declaration.matadors is None or state.declaration.bid_value is None:
        raise ValueError("Exact terminal utility requires matadors and a bid value.")

    return _build_exact_terminal_utility(
        state=state,
        local_side=local_side,
        apply_null_result=False,
    )


def build_exact_null_terminal_utility(
    *,
    state: ExactSearchState,
    local_side: str,
) -> TerminalUtility:
    """Builds exact normal-completion Null utility through existing settlement logic."""
    if state.declaration.game_type != "null":
        raise ValueError("Exact Null terminal utility supports only Null games.")
    if state.declaration.bid_value is None:
        raise ValueError("Exact Null terminal utility requires a bid value.")

    return _build_exact_terminal_utility(
        state=state,
        local_side=local_side,
        apply_null_result=True,
    )


def _build_exact_terminal_utility(
    *,
    state: ExactSearchState,
    local_side: str,
    apply_null_result: bool,
) -> TerminalUtility:
    facts = get_exact_search_terminal_facts(state)
    completed_tricks = [
        *({"winner_role": "declarer"} for _ in range(facts.declarer_trick_count)),
        *({"winner_role": "defenders"} for _ in range(facts.defender_trick_count)),
    ]
    game_result = build_game_result_summary_from_points(
        declarer_points=facts.declarer_final_points,
        defender_points=facts.defender_final_points,
    )
    if apply_null_result:
        game_result = apply_completed_null_contract_result(
            game_result,
            completed_tricks,
        )
    game_value = build_game_value_summary(state.declaration)
    overbid = build_overbid_summary(
        game_value_summary=game_value,
        bid_value=state.declaration.bid_value,
        game_end_reason="normal_completion",
    )
    settlement = build_final_settlement_summary(
        game_value_summary=game_value,
        game_result_summary=game_result,
        overbid_summary=overbid,
        completed_tricks=completed_tricks,
    )
    is_loss = settlement.get("is_loss")
    settlement_score = settlement.get("settlement_score")
    if settlement.get("is_complete") is not True:
        raise ValueError(
            "Exact terminal utility requires complete settlement: "
            f"{settlement.get('missing_inputs', [])}."
        )
    if not isinstance(is_loss, bool):
        raise ValueError("Exact terminal utility requires boolean settlement is_loss.")
    if isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
        raise ValueError("Exact terminal utility requires an integer settlement score.")

    return build_terminal_utility(
        game_type=state.declaration.game_type,
        local_side=local_side,
        winner="defenders" if is_loss else "declarer",
        declarer_settlement_score=settlement_score,
        declarer_points=facts.declarer_final_points,
        defender_points=facts.defender_final_points,
    )
