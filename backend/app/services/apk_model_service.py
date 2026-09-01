"""APK Analysis Mode model service.

Loads the frozen TUANDROMD RandomForest and scores an app from the manifest
permissions that the current runtime can reproduce.  The estimator expects a
mixed 241-feature contract: permission-like columns plus static API/code
columns.  The latter are deliberately left at zero because the historical
extractor semantics are not available; diagnostics report this contract as
partial instead of pretending that guessed proxy values are equivalent.

This is separate from ``model_service.ModelService`` (the Installed App Mode
model that also uses store metadata). Keeping them apart implements the
two-mode architecture: each mode uses the model suited to the data it has.
"""

from __future__ import annotations

from functools import lru_cache

import joblib
import pandas as pd

from ..config import APK_MODEL_PATH, APK_MODEL_THRESHOLD
from .risk_score import assess_with_threshold, classify_model_prediction

# Reuse the extractor's normaliser so 'android.permission.SEND_SMS' -> 'SEND_SMS'.
from ...apk_analysis.permission_mapping import normalize_permission


BINARY_INPUT_CONTRACT = "partial"
BINARY_EXPECTED_FEATURE_COUNT = 241
BINARY_RUNTIME_AVAILABLE_FEATURE_COUNT = 208
BINARY_RUNTIME_MISSING_FEATURE_COUNT = 33
BINARY_STATIC_API_FEATURES_AVAILABLE = 0


class APKModelService:
    """Permission-only model for APK Analysis Mode."""

    def __init__(self) -> None:
        if not APK_MODEL_PATH.exists():
            raise FileNotFoundError(f"APK model artifact missing: {APK_MODEL_PATH}")
        model = joblib.load(APK_MODEL_PATH)
        # The artifact may be a bare estimator or a dict bundle.
        if isinstance(model, dict):
            model = model.get("model") or model.get("estimator") or model.get("clf")
        self.model = model
        self.model_name = type(model).__name__
        self.threshold = float(APK_MODEL_THRESHOLD)
        # Score strictly in the estimator's embedded training order.  The
        # contract audit records which names are reachable by this runtime.
        self.feature_names = [
            str(name) for name in getattr(model, "feature_names_in_", [])
        ]
        if len(self.feature_names) != BINARY_EXPECTED_FEATURE_COUNT:
            raise ValueError(
                "Binary APK model does not expose the expected 241-feature contract."
            )
        self.feature_name_set = frozenset(self.feature_names)

    def _vectorize(self, raw_permissions: list[str]) -> pd.DataFrame:
        """Build the model's feature row from raw android.permission.* strings."""
        active = {normalize_permission(p) for p in raw_permissions if p}
        values = [1 if name in active else 0 for name in self.feature_names]
        return pd.DataFrame([values], columns=self.feature_names)

    def _normalization_collisions(self, raw_permissions: list[str]) -> list[dict]:
        """Return distinct full permission names that collapse to one token."""
        by_token: dict[str, list[str]] = {}
        for permission in raw_permissions:
            if not permission:
                continue
            original = str(permission).strip()
            token = normalize_permission(original)
            if not original or not token:
                continue
            originals = by_token.setdefault(token, [])
            if original not in originals:
                originals.append(original)

        return [
            {
                "normalized_token": token,
                "original_permissions": sorted(originals),
                "affects_model_feature": token in self.feature_name_set,
            }
            for token, originals in sorted(by_token.items())
            if len(originals) > 1
        ]

    def predict_from_permissions(self, raw_permissions: list[str]) -> dict:
        """Score one app from its declared permissions."""
        row = self._vectorize(raw_permissions)
        proba = float(self.model.predict_proba(row)[0, 1])
        assessment = assess_with_threshold(proba, self.threshold)
        model_prediction = classify_model_prediction(proba, self.threshold)
        matched = int(row.values.sum())
        return {
            "risk_score": assessment["risk_score"],
            "risk_level": assessment["risk_level"],
            "model_prediction": model_prediction,
            "malware_probability": round(proba, 4),
            "band_range": assessment["band_range"],
            "confidence": assessment["confidence"],
            # Deprecated compatibility aliases.
            "prediction": model_prediction,
            "probability_malware": round(proba, 4),
            "model_name": self.model_name,
            "decision_threshold": self.threshold,
            "matched_model_permissions": matched,
            "model_feature_count": len(self.feature_names),
            "binary_input_contract": BINARY_INPUT_CONTRACT,
            "binary_feature_coverage": {
                "expected": BINARY_EXPECTED_FEATURE_COUNT,
                "available": BINARY_RUNTIME_AVAILABLE_FEATURE_COUNT,
                "missing": BINARY_RUNTIME_MISSING_FEATURE_COUNT,
                "static_api_features_available": (
                    BINARY_STATIC_API_FEATURES_AVAILABLE
                ),
                "matched_current_input": matched,
            },
            "normalization_collisions": self._normalization_collisions(
                raw_permissions
            ),
        }


@lru_cache(maxsize=1)
def get_apk_model_service() -> APKModelService:
    """Return the process-wide APKModelService, loading the model on first use."""
    return APKModelService()
