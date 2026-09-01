"""Model loading and scoring service.

Responsibilities:
    * Load the trained model and feature contract ONCE (singleton).
    * Turn a sparse set of permission features into the full, correctly ordered
      157-column row the model expects (imputing missing metadata with the
      training medians).
    * Produce explicit P(malware), a binary model verdict, and a permission-risk tier.

This is the only place that calls the ML model.
"""

from __future__ import annotations

import math
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from ..config import FEATURE_COLUMNS_PATH, FINAL_MODEL_PATH
from .risk_score import assess_with_threshold, classify_model_prediction


class ModelService:
    """Loads artifacts and scores apps. Instantiate once via get_model_service()."""

    def __init__(self) -> None:
        if not FINAL_MODEL_PATH.exists():
            raise FileNotFoundError(f"Model artifact missing: {FINAL_MODEL_PATH}")
        if not FEATURE_COLUMNS_PATH.exists():
            raise FileNotFoundError(f"Feature schema missing: {FEATURE_COLUMNS_PATH}")

        model_bundle = joblib.load(FINAL_MODEL_PATH)
        columns_bundle = joblib.load(FEATURE_COLUMNS_PATH)

        self.model = model_bundle["model"]
        self.model_name = model_bundle["model_name"]
        self.decision_threshold = float(model_bundle["decision_threshold"])

        # Feature contract comes from feature_columns.joblib (the schema file).
        self.feature_names = list(columns_bundle["feature_names"])
        recipe = columns_bundle["feature_recipe"]
        self.permission_features = list(recipe["active_permission_features"])
        self.metadata_features = list(recipe["metadata_features"])
        self.metadata_medians = dict(recipe["metadata_medians"])

    # -- feature assembly ------------------------------------------------
    def _count_dangerous_safe(self, features: dict[str, float]) -> tuple[int, int]:
        """Count active (D)/(S) permission columns supplied by the caller."""
        dangerous = safe = 0
        for col in self.permission_features:
            if float(features.get(col, 0)) >= 1:
                if col.rstrip().endswith("(D)"):
                    dangerous += 1
                elif col.rstrip().endswith("(S)"):
                    safe += 1
        return dangerous, safe

    def build_row(self, features: dict[str, float], metadata: dict | None) -> tuple[pd.DataFrame, int, int]:
        """Build the full ordered 157-column DataFrame the model expects.

        Permissions default to 0. Metadata defaults to the training median
        (because APK mode cannot observe store data). Counts are computed from
        the supplied permissions unless explicitly overridden in metadata.
        """
        metadata = metadata or {}
        row: dict[str, float] = {}

        # 1) Permission columns: 1 if requested, else 0.
        for col in self.permission_features:
            row[col] = 1.0 if float(features.get(col, 0)) >= 1 else 0.0

        # 2) Derive permission counts from the supplied permissions.
        dangerous_count, safe_count = self._count_dangerous_safe(features)

        # 3) Metadata columns: caller value -> median fallback.
        meta_input = {
            "Rating": metadata.get("rating"),
            "Number of ratings": metadata.get("number_of_ratings"),
            "Price": metadata.get("price"),
            "Dangerous permissions count": metadata.get("dangerous_permission_count", dangerous_count),
            "Safe permissions count": metadata.get("safe_permission_count", safe_count),
        }
        for col in self.metadata_features:
            value = meta_input.get(col)
            if value is None:
                value = self.metadata_medians.get(col, 0.0)
            row[col] = float(value)

        # 4) Engineered feature derived from the (possibly imputed) ratings count.
        row["log_number_of_ratings"] = float(math.log1p(row["Number of ratings"]))

        # Order exactly as the model was trained.
        df = pd.DataFrame([[row[c] for c in self.feature_names]], columns=self.feature_names)
        return df, dangerous_count, safe_count

    # -- prediction ------------------------------------------------------
    def predict(self, features: dict[str, float], metadata: dict | None = None) -> dict:
        """Score one app and return the full result payload.

        Scoring/tiering is delegated to the Risk Score Engine (risk_score.py)
        so the band policy lives in exactly one place.
        """
        df, dangerous_count, safe_count = self.build_row(features, metadata)

        proba = float(self.model.predict_proba(df)[0, 1])  # P(malware)
        assessment = assess_with_threshold(proba, self.decision_threshold)
        model_prediction = classify_model_prediction(proba, self.decision_threshold)

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
            "dangerous_permission_count": dangerous_count,
            "safe_permission_count": safe_count,
            "model_name": self.model_name,
        }


@lru_cache(maxsize=1)
def get_model_service() -> ModelService:
    """Return the process-wide ModelService, loading artifacts on first use."""
    return ModelService()
