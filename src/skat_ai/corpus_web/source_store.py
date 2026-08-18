from __future__ import annotations

from dataclasses import dataclass, field

from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherReportSourceV1,
)
from skat_ai.match_analysis_contracts import MatchDecisionAnalysisResultV1
from skat_ai.recommendation_workflow import VALID_RECOMMENDATION_METHODS

from .contracts import (
    LEARNING_CORPUS_STRATEGY_SOURCE_BINDING_STATUSES,
    LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION,
    LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES,
)

_METHOD_ORDER = {method: index for index, method in enumerate(VALID_RECOMMENDATION_METHODS)}


def _require_binding_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("source_binding_id must be a lowercase SHA-256 hexadecimal value.")
    return value


def _source_sort_key(
    source: LearningCorpusStrategyTeacherReportSourceV1,
) -> tuple[object, ...]:
    value = source.report.value
    if type(value) is not MatchDecisionAnalysisResultV1:
        raise ValueError("Strategy Teacher source must contain Decision Analysis.")
    return (
        value.match_id,
        value.match_position,
        value.decision_index,
        _METHOD_ORDER[value.options.recommendation_method],
        source.source_report_fingerprint,
        source.source_binding_id,
    )


@dataclass(slots=True)
class LearningCorpusStrategyTeacherSourceStoreV1:
    """One bounded process-local exact Strategy Teacher source store."""

    learning_corpus_strategy_source_store_version: int = (
        LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION
    )
    max_sources: int = LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES
    revision: int = 0
    _sources_by_id: dict[str, LearningCorpusStrategyTeacherReportSourceV1] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.learning_corpus_strategy_source_store_version) is not int
            or self.learning_corpus_strategy_source_store_version
            != LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION
        ):
            raise ValueError("learning_corpus_strategy_source_store_version must equal 1.")
        if (
            type(self.max_sources) is not int
            or not 1 <= self.max_sources <= LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES
        ):
            raise ValueError("max_sources must be a positive integer no greater than 2048.")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("revision must be a non-negative integer.")

    @property
    def sources(self) -> tuple[LearningCorpusStrategyTeacherReportSourceV1, ...]:
        return tuple(sorted(self._sources_by_id.values(), key=_source_sort_key))

    @property
    def source_binding_ids(self) -> tuple[str, ...]:
        return tuple(source.source_binding_id for source in self.sources)

    def add(self, source: LearningCorpusStrategyTeacherReportSourceV1) -> str:
        if type(source) is not LearningCorpusStrategyTeacherReportSourceV1:
            raise ValueError("source must be an exact LearningCorpusStrategyTeacherReportSourceV1.")
        source._validate(verify_identities=True, validate_report=True)
        existing = self._sources_by_id.get(source.source_binding_id)
        if existing is not None:
            if existing != source:
                raise ValueError("An existing Source Binding ID has different content.")
            return "unchanged"
        if len(self._sources_by_id) >= self.max_sources:
            raise ValueError(f"Strategy Teacher source limit of {self.max_sources} was reached.")
        self._sources_by_id[source.source_binding_id] = source
        self.revision += 1
        return "applied"

    def remove(self, source_binding_id: str) -> str:
        binding_id = _require_binding_id(source_binding_id)
        if binding_id not in self._sources_by_id:
            return "unchanged"
        del self._sources_by_id[binding_id]
        self.revision += 1
        return "applied"

    def clear(self) -> str:
        if not self._sources_by_id:
            return "unchanged"
        self._sources_by_id.clear()
        self.revision += 1
        return "applied"

    def binding_status(
        self,
        source: LearningCorpusStrategyTeacherReportSourceV1,
        store: LearningCorpusStoreResumeResultV1,
    ) -> str:
        if type(source) is not LearningCorpusStrategyTeacherReportSourceV1:
            raise ValueError("source must use the exact Strategy Teacher contract.")
        if type(store) is not LearningCorpusStoreResumeResultV1:
            raise ValueError("store must be an exact Learning Corpus Store.")
        current_ids = {
            selection.match_snapshot_id for selection in store.document.catalog.current_matches
        }
        return LEARNING_CORPUS_STRATEGY_SOURCE_BINDING_STATUSES[
            0 if source.match_snapshot_id in current_ids else 1
        ]

    def classified_sources(
        self,
        store: LearningCorpusStoreResumeResultV1,
    ) -> tuple[tuple[LearningCorpusStrategyTeacherReportSourceV1, str], ...]:
        return tuple((source, self.binding_status(source, store)) for source in self.sources)
