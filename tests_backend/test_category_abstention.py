from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.config import CATEGORY_MARGIN_THRESHOLD
from backend.app.schemas.assessment import (
    ClassifiedThreatAssessment,
    UncertainThreatAssessment,
)
from backend.app.services.category_model_service import (
    CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE,
    CATEGORY_CLASS_MAPPING,
    CATEGORY_NO_FEATURES_REASON,
    CATEGORY_UNCERTAIN_MESSAGE,
    SUPPORTED_CATEGORIES,
    CategoryModelService,
    select_category_from_scores,
)


def _scores_with_margin(
    margin: float,
    *,
    winning_index: int = 0,
    second_index: int = 1,
) -> list[float]:
    """Build a valid four-score row with the requested top-two margin."""
    second_score = 0.10
    top_score = second_score + margin
    remaining_score = (1.0 - top_score - second_score) / 2.0
    scores = [remaining_score, remaining_score, remaining_score, remaining_score]
    scores[winning_index] = top_score
    scores[second_index] = second_score
    return scores


def _service_with_test_feature_contract(model) -> CategoryModelService:
    service = CategoryModelService.__new__(CategoryModelService)
    service.model = model
    service.normalized_feature_names = (
        "READ_SMS",
        *(f"UNMATCHED_CATEGORY_FEATURE_{index}" for index in range(152)),
    )
    service.feature_count = 153
    return service


def test_locked_category_margin_threshold_is_exactly_070() -> None:
    assert CATEGORY_MARGIN_THRESHOLD == 0.70


def test_margin_exactly_070_is_accepted() -> None:
    # Constructing the top score from the same threshold makes the subtraction
    # exercise the inclusive boundary exactly, rather than only approximately.
    scores = _scores_with_margin(CATEGORY_MARGIN_THRESHOLD)

    result = select_category_from_scores(scores)

    assert result["diagnostics"]["margin"] == CATEGORY_MARGIN_THRESHOLD
    assert result["diagnostics"]["threshold"] == 0.70
    assert result["threat_assessment"] == {
        "status": "classified",
        "likely_category": "Adware",
        "supported_categories": list(SUPPORTED_CATEGORIES),
        "method": "selective_category_classification",
    }


def test_margin_below_070_returns_uncertain() -> None:
    result = select_category_from_scores(
        _scores_with_margin(CATEGORY_MARGIN_THRESHOLD - 1e-6)
    )

    assert result["diagnostics"]["margin"] < CATEGORY_MARGIN_THRESHOLD
    assert result["threat_assessment"] == {
        "status": "uncertain",
        "likely_category": None,
        "supported_categories": list(SUPPORTED_CATEGORIES),
        "method": "selective_category_classification",
        "message": CATEGORY_UNCERTAIN_MESSAGE,
    }


def test_margin_above_070_returns_winning_category() -> None:
    result = select_category_from_scores(
        _scores_with_margin(
            CATEGORY_MARGIN_THRESHOLD + 1e-6,
            winning_index=1,
            second_index=0,
        )
    )

    assert result["diagnostics"]["margin"] > CATEGORY_MARGIN_THRESHOLD
    assert result["threat_assessment"]["status"] == "classified"
    assert result["threat_assessment"]["likely_category"] == "Banking Malware"


def test_all_zero_category_vector_returns_uncertain_without_model_inference() -> None:
    class ModelThatMustNotRun:
        def predict_proba(self, _row):
            pytest.fail("predict_proba must not run for an all-zero category vector")

    service = _service_with_test_feature_contract(ModelThatMustNotRun())

    result = service.classify_from_permissions(["android.permission.INTERNET"])

    assert result == {
        "threat_assessment": {
            "status": "uncertain",
            "likely_category": None,
            "supported_categories": list(SUPPORTED_CATEGORIES),
            "method": "selective_category_classification",
            "message": CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE,
        },
        "diagnostics": {
            "reason": CATEGORY_NO_FEATURES_REASON,
            "matched_category_feature_count": 0,
        },
    }


def test_exactly_one_matched_category_feature_permits_unchanged_inference() -> None:
    class RecordingModel:
        def __init__(self) -> None:
            self.calls = 0
            self.last_row = None

        def predict_proba(self, row):
            self.calls += 1
            self.last_row = np.asarray(row)
            return np.asarray([[0.90, 0.10, 0.0, 0.0]])

    model = RecordingModel()
    service = _service_with_test_feature_contract(model)

    result = service.classify_from_permissions(
        ["android.permission.READ_SMS", "android.permission.INTERNET"]
    )

    assert model.calls == 1
    assert model.last_row.shape == (1, 153)
    assert set(np.unique(model.last_row)).issubset({0, 1})
    assert int(model.last_row.sum()) == 1
    assert result["threat_assessment"] == {
        "status": "classified",
        "likely_category": "Adware",
        "supported_categories": list(SUPPORTED_CATEGORIES),
        "method": "selective_category_classification",
    }
    assert result["diagnostics"] == {
        "top_score": 0.90,
        "second_score": 0.10,
        "margin": 0.80,
        "threshold": 0.70,
        "matched_category_feature_count": 1,
    }


@pytest.mark.parametrize(
    ("winning_index", "expected_category"),
    list(CATEGORY_CLASS_MAPPING.items()),
)
def test_category_class_mapping_remains_locked(
    winning_index: int,
    expected_category: str,
) -> None:
    scores = [0.02, 0.02, 0.02, 0.02]
    scores[winning_index] = 0.94

    result = select_category_from_scores(scores)

    assert CATEGORY_CLASS_MAPPING == {
        0: "Adware",
        1: "Banking Malware",
        2: "SMS Malware",
        3: "Riskware",
    }
    assert SUPPORTED_CATEGORIES == (
        "Adware",
        "Banking Malware",
        "SMS Malware",
        "Riskware",
    )
    assert result["threat_assessment"]["likely_category"] == expected_category


@pytest.mark.parametrize(
    "schema",
    [ClassifiedThreatAssessment, UncertainThreatAssessment],
)
def test_threat_assessment_schema_requires_supported_categories(schema) -> None:
    payload = {
        "status": "classified",
        "likely_category": "Adware",
        "method": "selective_category_classification",
    }
    if schema is UncertainThreatAssessment:
        payload.update(
            status="uncertain",
            likely_category=None,
            message=CATEGORY_UNCERTAIN_MESSAGE,
        )

    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.parametrize(
    "message",
    [CATEGORY_UNCERTAIN_MESSAGE, CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE],
    ids=["ambiguous-scores", "no-supported-features"],
)
def test_uncertain_schema_accepts_both_supported_messages(message: str) -> None:
    result = UncertainThreatAssessment.model_validate(
        {
            "status": "uncertain",
            "likely_category": None,
            "supported_categories": list(SUPPORTED_CATEGORIES),
            "method": "selective_category_classification",
            "message": message,
        }
    )

    assert result.message == message


@pytest.mark.parametrize(
    "malformed_categories",
    [
        ["Adware", "Banking Malware", "SMS Malware"],
        ["Adware", "Banking Malware", "SMS Malware", "SMS Malware"],
        ["Banking Malware", "Adware", "SMS Malware", "Riskware"],
    ],
    ids=["missing-category", "duplicate-category", "reordered-categories"],
)
@pytest.mark.parametrize(
    "schema",
    [ClassifiedThreatAssessment, UncertainThreatAssessment],
)
def test_threat_assessment_schema_rejects_noncanonical_supported_categories(
    schema,
    malformed_categories: list[str],
) -> None:
    payload = {
        "status": "classified",
        "likely_category": "Adware",
        "supported_categories": malformed_categories,
        "method": "selective_category_classification",
    }
    if schema is UncertainThreatAssessment:
        payload.update(
            status="uncertain",
            likely_category=None,
            message=CATEGORY_UNCERTAIN_MESSAGE,
        )

    with pytest.raises(ValidationError):
        schema.model_validate(payload)
