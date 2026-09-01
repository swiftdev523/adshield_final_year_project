"""Experimental selective category classification for binary-malicious APKs.

This service loads the existing, unchanged four-class Random Forest and applies
the locked top-two-margin abstention rule. It is a post-binary sidecar: callers
must invoke it only after the existing APK detector returns ``Malicious``.

The returned model values are raw Random Forest class scores. They are not
calibrated probabilities or confidence, and only the top score, second score,
margin, and locked threshold may leave this service under diagnostics.

This experimental feature still requires new independent validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

import joblib
import numpy as np

from ...apk_analysis.permission_mapping import normalize_permission
from ..config import CATEGORY_MARGIN_THRESHOLD, CATEGORY_MODEL_PATH


CATEGORY_CLASS_MAPPING = {
    0: "Adware",
    1: "Banking Malware",
    2: "SMS Malware",
    3: "Riskware",
}
SUPPORTED_CATEGORIES = tuple(CATEGORY_CLASS_MAPPING.values())
CATEGORY_METHOD = "selective_category_classification"
CATEGORY_UNCERTAIN_MESSAGE = (
    "The app's permission pattern does not clearly match one supported threat category."
)
CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The app does not contain enough supported permission evidence to assign a threat category."
)
CATEGORY_NO_FEATURES_REASON = "no_supported_category_features"

_EXPECTED_FEATURE_COUNT = 153
_EXPECTED_FEATURE_SHA256 = (
    "7aecf3b202c88d707e458a3705b4e3a326a9ee062c9b1e0f209a6b9a5c087c34"
)
_EXPECTED_MODEL_SHA256 = (
    "9b2f3b2a880372ff077fdc37e6e3d7909c9ba3ba28cabce371a58d1f6b80f3b9"
)


def _ordered_feature_sha256(feature_names: Sequence[str]) -> str:
    payload = json.dumps(
        list(feature_names), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256() -> str:
    digest = hashlib.sha256()
    with CATEGORY_MODEL_PATH.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_category_from_scores(class_scores: Sequence[float]) -> dict[str, Any]:
    """Apply the locked inclusive 0.70 margin rule to four ordered class scores."""
    scores = np.asarray(class_scores, dtype=np.float64)
    if scores.shape != (len(SUPPORTED_CATEGORIES),):
        raise ValueError(
            f"Expected {len(SUPPORTED_CATEGORIES)} category class scores, "
            f"received shape {scores.shape}."
        )
    if not np.isfinite(scores).all():
        raise ValueError("Category class scores contain a non-finite value.")
    if np.any(scores < 0.0) or np.any(scores > 1.0):
        raise ValueError("Category class scores fall outside [0, 1].")
    if not np.isclose(scores.sum(), 1.0, atol=1e-10, rtol=0.0):
        raise ValueError("Category class scores do not sum to one.")

    # Stable ordering preserves the model's class order for an exact tie. A tie
    # has margin zero and is therefore rejected by the locked rule.
    ranked_positions = np.argsort(-scores, kind="stable")
    top_position = int(ranked_positions[0])
    second_position = int(ranked_positions[1])
    top_score = float(scores[top_position])
    second_score = float(scores[second_position])
    category_margin = top_score - second_score

    supported = list(SUPPORTED_CATEGORIES)
    if category_margin >= CATEGORY_MARGIN_THRESHOLD:
        threat_assessment: dict[str, Any] = {
            "status": "classified",
            "likely_category": CATEGORY_CLASS_MAPPING[top_position],
            "supported_categories": supported,
            "method": CATEGORY_METHOD,
        }
    else:
        threat_assessment = {
            "status": "uncertain",
            "likely_category": None,
            "supported_categories": supported,
            "method": CATEGORY_METHOD,
            "message": CATEGORY_UNCERTAIN_MESSAGE,
        }

    return {
        "threat_assessment": threat_assessment,
        "diagnostics": {
            "top_score": top_score,
            "second_score": second_score,
            "margin": category_margin,
            "threshold": CATEGORY_MARGIN_THRESHOLD,
        },
    }


class CategoryModelService:
    """Load and score the frozen experimental four-class Random Forest."""

    def __init__(self) -> None:
        if not CATEGORY_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Experimental category model artifact missing: {CATEGORY_MODEL_PATH}"
            )
        if _file_sha256() != _EXPECTED_MODEL_SHA256:
            raise ValueError("Experimental category model artifact hash changed.")

        bundle = joblib.load(CATEGORY_MODEL_PATH)
        if not isinstance(bundle, dict):
            raise ValueError("Category model artifact is not the expected bundle.")
        if bundle.get("model_name") != "Random Forest":
            raise ValueError("Category model bundle is not the locked Random Forest.")
        if bundle.get("experimental") is not True:
            raise ValueError("Category model bundle is not marked experimental.")
        if bundle.get("probabilities_calibrated") is not False:
            raise ValueError("Category model bundle unexpectedly changed calibration state.")
        if bundle.get("user_facing_confidence_allowed") is not False:
            raise ValueError("Category model bundle unexpectedly permits confidence display.")

        model = bundle.get("model")
        if model is None:
            raise ValueError("Category model bundle is missing its estimator.")
        model_classes = np.asarray(getattr(model, "classes_", []), dtype=int)
        expected_classes = np.asarray(list(CATEGORY_CLASS_MAPPING), dtype=int)
        if not np.array_equal(model_classes, expected_classes):
            raise ValueError(
                "Category model classes changed; expected [0, 1, 2, 3]."
            )
        if bundle.get("class_names_in_probability_order") != list(
            SUPPORTED_CATEGORIES
        ):
            raise ValueError("Category model class-name mapping changed.")

        feature_names = bundle.get("feature_names")
        if not isinstance(feature_names, list) or len(feature_names) != _EXPECTED_FEATURE_COUNT:
            raise ValueError("Category model feature contract is not the expected 153-name list.")
        if any(not isinstance(name, str) or not name.strip() for name in feature_names):
            raise ValueError("Category model feature contract contains an invalid name.")
        if _ordered_feature_sha256(feature_names) != _EXPECTED_FEATURE_SHA256:
            raise ValueError("Category model ordered feature contract changed.")
        if bundle.get("feature_list_sha256") != _EXPECTED_FEATURE_SHA256:
            raise ValueError("Category model bundle feature hash changed.")
        if int(getattr(model, "n_features_in_", -1)) != _EXPECTED_FEATURE_COUNT:
            raise ValueError("Category model estimator does not expect 153 features.")

        normalized_feature_names = tuple(
            normalize_permission(name) for name in feature_names
        )
        if any(not name for name in normalized_feature_names):
            raise ValueError("Category feature normalization produced a blank key.")
        if len(set(normalized_feature_names)) != _EXPECTED_FEATURE_COUNT:
            raise ValueError("Category features collide under permission normalization.")

        self.model = model
        self.feature_names = tuple(feature_names)
        self.normalized_feature_names = normalized_feature_names
        self.feature_count = _EXPECTED_FEATURE_COUNT

    def _vectorize(self, raw_permissions: Sequence[str]) -> np.ndarray:
        """Build one binary-presence row in the frozen 153-feature order."""
        active_permissions: set[str] = set()
        for permission in raw_permissions:
            normalized = normalize_permission(permission)
            if normalized:
                active_permissions.add(normalized)
        return np.asarray(
            [
                [
                    1 if feature in active_permissions else 0
                    for feature in self.normalized_feature_names
                ]
            ],
            dtype=np.int8,
        )

    def classify_from_permissions(
        self, raw_permissions: Sequence[str]
    ) -> dict[str, Any]:
        """Return a classified/uncertain sidecar for a binary-malicious APK."""
        row = self._vectorize(raw_permissions)
        matched_category_feature_count = int(np.count_nonzero(row))
        if matched_category_feature_count == 0:
            return {
                "threat_assessment": {
                    "status": "uncertain",
                    "likely_category": None,
                    "supported_categories": list(SUPPORTED_CATEGORIES),
                    "method": CATEGORY_METHOD,
                    "message": CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE,
                },
                "diagnostics": {
                    "reason": CATEGORY_NO_FEATURES_REASON,
                    "matched_category_feature_count": 0,
                },
            }

        scores = np.asarray(self.model.predict_proba(row), dtype=np.float64)
        if scores.shape != (1, len(SUPPORTED_CATEGORIES)):
            raise ValueError(
                "Category model returned an unexpected class-score shape: "
                f"{scores.shape}."
            )
        result = select_category_from_scores(scores[0])
        result["diagnostics"]["matched_category_feature_count"] = (
            matched_category_feature_count
        )
        return result


@lru_cache(maxsize=1)
def get_category_model_service() -> CategoryModelService:
    """Lazily load the experimental category model on the first malicious path."""
    return CategoryModelService()
