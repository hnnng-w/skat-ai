from dataclasses import fields

import skat_ai
import skat_ai.api
import skat_ai.api.v1 as api_v1
import skat_ai.errors
from skat_ai.hidden_card_inference import HiddenCardEvidence, HiddenCardInferenceConstraints
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.replay_coaching_evidence import DecisionTimeReplayCoachingEvidence
from skat_ai.training_dataset import TrainingProvenance


def test_field_provenance_is_not_exported_through_public_namespaces() -> None:
    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert skat_ai.api.__all__ == ("v1",)
    assert "FieldProvenanceEntry" not in api_v1.__all__
    assert "FieldProvenanceLedger" not in api_v1.__all__
    assert "InformationUseContext" not in api_v1.__all__
    assert "execute" in api_v1.__all__
    assert "provenance" not in {field.name for field in fields(api_v1.ExecutionOptionsV1)}
    assert "FieldProvenanceEntry" not in skat_ai.errors.__all__


def test_existing_specialized_provenance_contract_fields_are_unchanged() -> None:
    assert tuple(field.name for field in fields(PublicHandConstraint)) == (
        "player",
        "cards",
        "visibility_scope",
        "source",
    )
    assert tuple(field.name for field in fields(HiddenCardEvidence)) == (
        "evidence_type",
        "player",
        "effective_category",
        "cards",
        "confidence",
        "source_trick_number",
        "source_play_index",
        "source",
    )
    assert "provenance_status" in {
        field.name for field in fields(HiddenCardInferenceConstraints)
    }
    assert tuple(field.name for field in fields(TrainingProvenance)) == (
        "source_type",
        "source_name",
        "source_record_id",
        "collected_at",
        "notes",
    )
    assert "information_cutoff" in {
        field.name for field in fields(HistoricalDecisionSnapshot)
    }
    assert "information_policy" in {
        field.name for field in fields(DecisionTimeReplayCoachingEvidence)
    }


def test_confidence_remains_a_specialized_hidden_card_contract() -> None:
    evidence = HiddenCardEvidence(
        evidence_type="failed_to_follow",
        player="left",
        effective_category="clubs",
        cards=("D7",),
        confidence="confirmed",
        source_trick_number=1,
        source_play_index=2,
        source="completed_tricks",
    )
    assert evidence.confidence == "confirmed"
