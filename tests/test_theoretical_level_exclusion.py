from skat_ai.theoretical_level_exclusion import (
    JackOwnershipEvidence,
    assess_theoretical_schwarz_exclusion,
)


def build_evidence(ownership_by_card: dict[str, str]):
    return tuple(
        JackOwnershipEvidence(card, ownership_by_card.get(card, "unknown"), ())
        for card in ["CJ", "SJ", "HJ", "DJ"]
    )


def test_top_jack_excludes_theoretical_schwarz() -> None:
    assessment = assess_theoretical_schwarz_exclusion(
        "defenders",
        build_evidence({"CJ": "defenders"}),
    )

    assert assessment.status == "excluded"
    assert assessment.exclusion_basis == "losing_party_owned_top_jack"


def test_all_three_lower_jacks_exclude_theoretical_schwarz() -> None:
    assessment = assess_theoretical_schwarz_exclusion(
        "declarer",
        build_evidence({card: "declarer" for card in ["SJ", "HJ", "DJ"]}),
    )

    assert assessment.status == "excluded"
    assert assessment.exclusion_basis == "losing_party_owned_all_three_lower_jacks"


def test_unknown_skat_and_partial_lower_jacks_do_not_establish_exclusion() -> None:
    assessment = assess_theoretical_schwarz_exclusion(
        "defenders",
        build_evidence(
            {
                "CJ": "skat",
                "SJ": "defenders",
                "HJ": "defenders",
                "DJ": "unknown",
            }
        ),
    )

    assert assessment.status == "not_excluded"
    assert assessment.exclusion_basis is None
