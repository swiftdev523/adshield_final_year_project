"""Freeze model artifacts and thresholds around notification event handling.

The notification event-level fix is intentionally confined to the Android and
frontend orchestration layers.  These assertions fail if any protected model,
feature contract, or scoring threshold changes accidentally.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.app import config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(relative_path: str) -> str:
    digest = hashlib.sha256()
    with (PROJECT_ROOT / relative_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_notification_classifier_artifacts_and_threshold_are_frozen() -> None:
    expected_hashes = {
        "models/notification_spam_model_v2.joblib": (
            "8bcb6512a3e8d96296b6d2ac1089533c92bc417e28f18b1f7c3b84753384889e"
        ),
        "models/notification_vectorizer_v2.joblib": (
            "8925cbb5643320be333295f82cda0c62b1c955109515f13c91ae86f0d2d64b2f"
        ),
        "models/notification_threshold.json": (
            "c848d85d6ac32efde42292ce32c39aefc6085b2ddfc4d3a293378a4e6c1d61d8"
        ),
    }

    assert {
        path: _sha256(path) for path in expected_hashes
    } == expected_hashes

    threshold_document = json.loads(
        (PROJECT_ROOT / "models/notification_threshold.json").read_text(
            encoding="utf-8"
        )
    )
    assert threshold_document["threshold"] == 0.29
    assert config.NOTIFICATION_DECISION_THRESHOLD == 0.29


def test_malware_models_and_scoring_thresholds_are_unchanged() -> None:
    expected_hashes = {
        "models/final_model.joblib": (
            "a1185c43c3aee82461ccebb6b2a62ab09bc471e328adf4390c63bf6388d24ac4"
        ),
        "models/feature_columns.joblib": (
            "e3a3205e15f50d4e4c5cdefac0c6c55734694f43874582fc1821ad02b413d7fa"
        ),
        "models/adware_detection_rf_model.pkl": (
            "54b7560bf7845b5eb5fb7a60057fd9a166c2843c5c8e65c133ad78d80d2aeba5"
        ),
        "models/category_final_validation/artifacts/selected_category_model_provisional.joblib": (
            "9b2f3b2a880372ff077fdc37e6e3d7909c9ba3ba28cabce371a58d1f6b80f3b9"
        ),
    }

    assert {
        path: _sha256(path) for path in expected_hashes
    } == expected_hashes
    assert config.APK_MODEL_THRESHOLD == 0.5
    assert config.CATEGORY_MARGIN_THRESHOLD == 0.70
    assert config.SAFE_MAX_SCORE == 30
    assert config.SUSPICIOUS_MAX_SCORE == 70
