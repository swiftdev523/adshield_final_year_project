"""Notification spam model service.

Loads the Random Forest + TF-IDF vectorizer once and classifies notification
text as Spam or Ham. Uses the tuned decision threshold from
``notification_threshold.json`` when available.
"""

from __future__ import annotations

import json
from functools import lru_cache

import joblib

from ..config import (
    MODELS_DIR,
    NOTIFICATION_DECISION_THRESHOLD,
    NOTIFICATION_MODEL_PATH,
    NOTIFICATION_THRESHOLD_JSON,
    NOTIFICATION_VECTORIZER_PATH,
)


class NotificationSpamService:
    """Classifies a single notification message."""

    SPAM_LABEL = "Spam"
    HAM_LABEL = "Ham"

    def __init__(self) -> None:
        if not NOTIFICATION_MODEL_PATH.exists():
            raise FileNotFoundError(f"Notification model missing: {NOTIFICATION_MODEL_PATH}")
        if not NOTIFICATION_VECTORIZER_PATH.exists():
            raise FileNotFoundError(f"Notification vectorizer missing: {NOTIFICATION_VECTORIZER_PATH}")

        self.model = joblib.load(NOTIFICATION_MODEL_PATH)
        self.vectorizer = joblib.load(NOTIFICATION_VECTORIZER_PATH)
        self.model_name = type(self.model).__name__
        self.threshold = float(self._load_threshold())

    def _load_threshold(self) -> float:
        if NOTIFICATION_THRESHOLD_JSON.exists():
            data = json.loads(NOTIFICATION_THRESHOLD_JSON.read_text(encoding="utf-8"))
            return float(data.get("threshold", NOTIFICATION_DECISION_THRESHOLD))
        return NOTIFICATION_DECISION_THRESHOLD

    def analyze(self, text: str) -> dict:
        """Classify one notification and return prediction + confidence (%)."""
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("Notification text must not be empty.")

        X = self.vectorizer.transform([cleaned])
        proba_spam = float(self.model.predict_proba(X)[0, 1])
        is_spam = proba_spam >= self.threshold
        prediction = self.SPAM_LABEL if is_spam else self.HAM_LABEL
        # Confidence = probability mass behind the predicted class, as 0-100%.
        confidence_pct = round((proba_spam if is_spam else 1.0 - proba_spam) * 100, 1)

        return {
            "prediction": prediction,
            "confidence": confidence_pct,
            "probability_spam": round(proba_spam, 4),
            "threshold": self.threshold,
            "model_name": self.model_name,
        }


@lru_cache(maxsize=1)
def get_notification_service() -> NotificationSpamService:
    return NotificationSpamService()
