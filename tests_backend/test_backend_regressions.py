from __future__ import annotations

import asyncio
import importlib.util
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from backend.apk_analysis.permission_extractor import analyze_permission_list
from backend.app.api import routes_notification, routes_predict, routes_upload
from backend.app.config import RUNTIME_TEMP_DIR
from backend.app.main import app, root
from backend.app.schemas.predict import AnalyzeAPKRequest, AnalyzeAPKResponse, PredictAPKRequest
from backend.app.services.install_source_service import analyze_install_source
from backend.app.services.category_model_service import (
    CATEGORY_INSUFFICIENT_EVIDENCE_MESSAGE,
    CATEGORY_NO_FEATURES_REASON,
    CATEGORY_UNCERTAIN_MESSAGE,
    SUPPORTED_CATEGORIES,
)
from backend.app.services.model_service import ModelService
from backend.app.services.apk_model_service import APKModelService


MOVIEBOX_PERMISSIONS = [
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.ACCESS_WIFI_STATE",
    "android.permission.WAKE_LOCK",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.SYSTEM_ALERT_WINDOW",
]


def _permission_result() -> dict:
    return {
        "risk_score": 16,
        "risk_level": "Safe",
        "model_prediction": "Benign",
        "malware_probability": 0.16,
        "band_range": "0-30",
        "confidence": 0.84,
        "prediction": "Benign",
        "probability_malware": 0.16,
        "model_name": "test-model",
        "decision_threshold": 0.5,
        "matched_model_permissions": 6,
        "model_feature_count": 241,
        "binary_input_contract": "partial",
        "binary_feature_coverage": {
            "expected": 241,
            "available": 208,
            "missing": 33,
            "static_api_features_available": 0,
            "matched_current_input": 6,
        },
        "normalization_collisions": [],
    }


def _malicious_permission_result() -> dict:
    return {
        "risk_score": 82,
        "risk_level": "High Risk",
        "model_prediction": "Malicious",
        "malware_probability": 0.82,
        "band_range": "71-100",
        "confidence": 0.82,
        "prediction": "Malicious",
        "probability_malware": 0.82,
        "model_name": "test-model",
        "decision_threshold": 0.5,
        "matched_model_permissions": 6,
        "model_feature_count": 241,
        "binary_input_contract": "partial",
        "binary_feature_coverage": {
            "expected": 241,
            "available": 208,
            "missing": 33,
            "static_api_features_available": 0,
            "matched_current_input": 6,
        },
        "normalization_collisions": [],
    }


def _classified_category_result(category: str = "Banking Malware") -> dict:
    return {
        "threat_assessment": {
            "status": "classified",
            "likely_category": category,
            "supported_categories": list(SUPPORTED_CATEGORIES),
            "method": "selective_category_classification",
        },
        "diagnostics": {
            "top_score": 0.86,
            "second_score": 0.14,
            "margin": 0.72,
            "threshold": 0.70,
            "matched_category_feature_count": 3,
        },
    }


def _uncertain_category_result() -> dict:
    return {
        "threat_assessment": {
            "status": "uncertain",
            "likely_category": None,
            "supported_categories": list(SUPPORTED_CATEGORIES),
            "method": "selective_category_classification",
            "message": CATEGORY_UNCERTAIN_MESSAGE,
        },
        "diagnostics": {
            "top_score": 0.54,
            "second_score": 0.31,
            "margin": 0.23,
            "threshold": 0.70,
            "matched_category_feature_count": 3,
        },
    }


def _zero_feature_category_result() -> dict:
    return {
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


def _post_without_lifespan(path: str, **kwargs):
    """Exercise ASGI serialization without running startup model warming."""
    client = TestClient(app)
    try:
        return client.post(path, **kwargs)
    finally:
        client.close()


def _analyze_moviebox(monkeypatch, install_source: str = "apk_sideload"):
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(predict_from_permissions=lambda _permissions: _permission_result()),
    )
    return routes_predict.analyze_apk(
        AnalyzeAPKRequest(
            package="com.example.moviebox",
            permissions=MOVIEBOX_PERMISSIONS,
            install_source=install_source,
        )
    )


def test_root_endpoint_returns_api_landing_response() -> None:
    response = root()

    assert response == {
        "status": "ok",
        "message": "Android Adware Detection System API is running.",
        "docs": "/docs",
        "health": "/health",
    }


def test_runtime_temp_dir_is_on_project_drive() -> None:
    assert RUNTIME_TEMP_DIR.is_dir()
    assert Path(tempfile.gettempdir()).resolve() == RUNTIME_TEMP_DIR.resolve()


def test_notification_alerts_route_precedes_dynamic_package_route() -> None:
    paths = [route.path for route in routes_notification.router.routes]

    assert paths.index("/monitor/notifications/alerts") < paths.index(
        "/monitor/notifications/{package}"
    )


@pytest.mark.parametrize(
    "scenario", ["classified", "uncertain", "zero_features", "benign"]
)
def test_analyze_apk_asgi_serializes_category_contract(monkeypatch, scenario: str) -> None:
    if scenario == "classified":
        binary_result = _malicious_permission_result()
        category_result = _classified_category_result("Adware")
    elif scenario == "uncertain":
        binary_result = _malicious_permission_result()
        category_result = _uncertain_category_result()
    elif scenario == "zero_features":
        binary_result = _malicious_permission_result()
        category_result = _zero_feature_category_result()
    else:
        binary_result = _permission_result()
        category_result = None

    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: binary_result
        ),
    )
    if category_result is None:
        monkeypatch.setattr(
            routes_predict,
            "get_category_model_service",
            lambda: pytest.fail("category classifier must not load for a benign APK"),
        )
    else:
        monkeypatch.setattr(
            routes_predict,
            "get_category_model_service",
            lambda: SimpleNamespace(
                classify_from_permissions=lambda _permissions: category_result
            ),
        )

    response = _post_without_lifespan(
        "/analyze/apk",
        json={
            "package": f"com.example.{scenario}",
            "permissions": MOVIEBOX_PERMISSIONS,
            "install_source": "google_play_store",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    if category_result is None:
        assert payload["threat_assessment"] is None
        assert payload["diagnostics"]["category_classification"] is None
    else:
        assert payload["threat_assessment"] == category_result["threat_assessment"]
        assert (
            payload["diagnostics"]["category_classification"]
            == category_result["diagnostics"]
        )


def test_analyze_apk_category_failure_fails_open_without_changing_risk(
    monkeypatch,
) -> None:
    def fail_category(_permissions):
        raise RuntimeError("simulated experimental category failure")

    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: _malicious_permission_result()
        ),
    )
    monkeypatch.setattr(
        routes_predict,
        "get_category_model_service",
        lambda: SimpleNamespace(classify_from_permissions=fail_category),
    )

    response = _post_without_lifespan(
        "/analyze/apk",
        json={
            "package": "com.example.category-failure",
            "permissions": MOVIEBOX_PERMISSIONS,
            "install_source": "google_play_store",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threat_assessment"] is None
    assert payload["diagnostics"]["category_classification"] is None
    assert payload["model_prediction"] == "Malicious"
    assert payload["malware_probability"] == 0.82
    assert payload["overall_risk_score"] == 82
    assert payload["overall_risk_level"] == "High Risk"
    assert payload["summary"]["overall_risk_score"] == 82
    assert payload["summary"]["overall_risk_level"] == "High Risk"
    assert payload["risk_components"]["permission_assessment"] == {
        "risk_score": 82,
        "risk_level": "High Risk",
        "model_prediction": "Malicious",
        "malware_probability": 0.82,
    }


def test_upload_apk_asgi_serializes_category_sidecar(monkeypatch) -> None:
    mapped = analyze_permission_list(MOVIEBOX_PERMISSIONS)
    extraction = SimpleNamespace(
        package="com.example.serialized-upload",
        raw_permissions=MOVIEBOX_PERMISSIONS,
        mapped_features=mapped.mapped_features,
        dangerous_permission_count=mapped.dangerous_permission_count,
        safe_permission_count=mapped.safe_permission_count,
    )
    category_result = _classified_category_result("Riskware")
    monkeypatch.setattr(routes_upload, "analyze_apk", lambda _path: extraction)
    monkeypatch.setattr(
        routes_upload,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: _malicious_permission_result()
        ),
    )
    monkeypatch.setattr(
        routes_upload,
        "get_category_model_service",
        lambda: SimpleNamespace(
            classify_from_permissions=lambda _permissions: category_result
        ),
    )

    response = _post_without_lifespan(
        "/upload-apk",
        files={
            "file": (
                "serialized.apk",
                b"test apk bytes",
                "application/vnd.android.package-archive",
            )
        },
        data={"install_source": "google_play_store"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "serialized.apk"
    assert payload["threat_assessment"] == category_result["threat_assessment"]
    assert (
        payload["diagnostics"]["category_classification"]
        == category_result["diagnostics"]
    )
    assert payload["model_prediction"] == "Malicious"
    assert payload["malware_probability"] == 0.82
    assert payload["overall_risk_score"] == 82
    assert payload["overall_risk_level"] == "High Risk"


def test_model_service_uses_saved_decision_threshold() -> None:
    class FixedProbabilityModel:
        def predict_proba(self, _row):
            return np.array([[0.70, 0.30]])

    service = ModelService.__new__(ModelService)
    service.model = FixedProbabilityModel()
    service.model_name = "test-model"
    service.decision_threshold = 0.23
    service.build_row = lambda _features, _metadata: (object(), 0, 0)

    result = service.predict({})

    assert result["risk_score"] == 55
    assert result["risk_level"] == "Suspicious"
    assert result["model_prediction"] == "Malicious"
    assert result["malware_probability"] == 0.3
    assert result["prediction"] == "Malicious"
    assert result["probability_malware"] == 0.3


def test_upload_apk_builds_response_without_duplicate_risk_level(monkeypatch) -> None:
    mapped = analyze_permission_list(["android.permission.INTERNET"])
    extraction = SimpleNamespace(
        package="com.example.app",
        raw_permissions=["android.permission.INTERNET"],
        mapped_features=mapped.mapped_features,
        dangerous_permission_count=mapped.dangerous_permission_count,
        safe_permission_count=mapped.safe_permission_count,
    )
    score = _permission_result()

    monkeypatch.setattr(routes_upload, "analyze_apk", lambda _path: extraction)
    monkeypatch.setattr(
        routes_upload,
        "get_apk_model_service",
        lambda: SimpleNamespace(predict_from_permissions=lambda _permissions: score),
    )
    monkeypatch.setattr(
        routes_upload,
        "explain",
        lambda *_args, **_kwargs: {"explanation": "Test explanation.", "reasons": []},
    )
    monkeypatch.setattr(
        routes_upload,
        "get_category_model_service",
        lambda: pytest.fail("category classifier must not load for a benign APK"),
    )

    upload = UploadFile(filename="sample.apk", file=BytesIO(b"test apk bytes"))
    response = asyncio.run(routes_upload.upload_apk(upload, "google_play_store"))

    assert response.overall_risk_level == "Safe"
    assert response.model_dump()["filename"] == "sample.apk"
    assert response.summary.app.package == "com.example.app"
    assert response.summary.total_permission_count == 1
    assert response.threat_assessment is None
    assert response.diagnostics.category_classification is None


def test_upload_preserves_permissions_in_advanced_details(monkeypatch) -> None:
    mapped = analyze_permission_list(MOVIEBOX_PERMISSIONS)
    extraction = SimpleNamespace(
        package="com.example.moviebox",
        raw_permissions=MOVIEBOX_PERMISSIONS,
        mapped_features=mapped.mapped_features,
        dangerous_permission_count=mapped.dangerous_permission_count,
        safe_permission_count=mapped.safe_permission_count,
    )
    monkeypatch.setattr(routes_upload, "analyze_apk", lambda _path: extraction)
    monkeypatch.setattr(
        routes_upload,
        "get_apk_model_service",
        lambda: SimpleNamespace(predict_from_permissions=lambda _permissions: _permission_result()),
    )

    upload = UploadFile(filename="moviebox-style.apk", file=BytesIO(b"test apk bytes"))
    response = asyncio.run(routes_upload.upload_apk(upload, "apk_sideload"))

    assert response.advanced_details.permissions == MOVIEBOX_PERMISSIONS
    assert response.advanced_details.total_permission_count == 6
    assert response.advanced_details.curated_sensitive_permission_count == 3
    assert response.model_dump()["permissions"] == MOVIEBOX_PERMISSIONS


def test_moviebox_sideload_keeps_risk_layers_separate(monkeypatch) -> None:
    response = _analyze_moviebox(monkeypatch)

    permission = response.risk_components.permission_assessment
    context = response.risk_components.contextual_adjustment
    assert permission.risk_score == 16
    assert permission.risk_level == "Safe"
    assert permission.model_prediction == "Benign"
    assert permission.malware_probability == 0.16
    assert context.install_source_display == "APK sideload"
    assert context.score_adjustment == 20
    assert response.overall_risk_score == 36
    assert response.overall_risk_level == "Suspicious"
    assert response.model_prediction == "Benign"


def test_category_classification_does_not_run_for_benign_path(monkeypatch) -> None:
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: _permission_result()
        ),
    )
    monkeypatch.setattr(
        routes_predict,
        "get_category_model_service",
        lambda: pytest.fail("category classifier must not load for a benign APK"),
    )

    response = routes_predict.analyze_apk(
        AnalyzeAPKRequest(
            package="com.example.benign",
            permissions=["android.permission.INTERNET"],
            install_source="google_play_store",
        )
    )

    assert response.model_prediction == "Benign"
    assert response.threat_assessment is None
    assert response.diagnostics.category_classification is None


def test_uncertain_category_does_not_alter_binary_or_overall_risk(monkeypatch) -> None:
    category_results = iter(
        [_uncertain_category_result(), _classified_category_result()]
    )
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: _malicious_permission_result()
        ),
    )
    monkeypatch.setattr(
        routes_predict,
        "get_category_model_service",
        lambda: SimpleNamespace(
            classify_from_permissions=lambda _permissions: next(category_results)
        ),
    )
    request = AnalyzeAPKRequest(
        package="com.example.malware",
        permissions=MOVIEBOX_PERMISSIONS,
        install_source="google_play_store",
    )

    uncertain = routes_predict.analyze_apk(request)
    classified = routes_predict.analyze_apk(request)

    def risk_snapshot(response):
        return {
            "model_prediction": response.model_prediction,
            "malware_probability": response.malware_probability,
            "overall_risk_score": response.overall_risk_score,
            "overall_risk_level": response.overall_risk_level,
            "summary_score": response.summary.overall_risk_score,
            "summary_level": response.summary.overall_risk_level,
            "permission_score": response.risk_components.permission_assessment.risk_score,
            "permission_level": response.risk_components.permission_assessment.risk_level,
            "permission_prediction": (
                response.risk_components.permission_assessment.model_prediction
            ),
            "permission_malware_probability": (
                response.risk_components.permission_assessment.malware_probability
            ),
        }

    assert risk_snapshot(uncertain) == risk_snapshot(classified) == {
        "model_prediction": "Malicious",
        "malware_probability": 0.82,
        "overall_risk_score": 82,
        "overall_risk_level": "High Risk",
        "summary_score": 82,
        "summary_level": "High Risk",
        "permission_score": 82,
        "permission_level": "High Risk",
        "permission_prediction": "Malicious",
        "permission_malware_probability": 0.82,
    }
    assert uncertain.threat_assessment.model_dump() == {
        "status": "uncertain",
        "likely_category": None,
        "supported_categories": list(SUPPORTED_CATEGORIES),
        "method": "selective_category_classification",
        "message": CATEGORY_UNCERTAIN_MESSAGE,
    }


def test_category_scores_are_contained_in_diagnostics(monkeypatch) -> None:
    category_result = _classified_category_result("SMS Malware")
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: _malicious_permission_result()
        ),
    )
    monkeypatch.setattr(
        routes_predict,
        "get_category_model_service",
        lambda: SimpleNamespace(
            classify_from_permissions=lambda _permissions: category_result
        ),
    )

    response = routes_predict.analyze_apk(
        AnalyzeAPKRequest(
            package="com.example.sms-malware",
            permissions=MOVIEBOX_PERMISSIONS,
            install_source="google_play_store",
        )
    )
    payload = response.model_dump()
    category_diagnostics = payload["diagnostics"]["category_classification"]

    assert payload["threat_assessment"] == category_result["threat_assessment"]
    assert category_diagnostics == category_result["diagnostics"]
    assert set(category_diagnostics) == {
        "top_score",
        "second_score",
        "margin",
        "threshold",
        "matched_category_feature_count",
    }
    assert all(
        "confidence" not in key and "probability" not in key
        for key in category_diagnostics
    )
    for public_container in (
        payload,
        payload["summary"],
        payload["threat_assessment"],
    ):
        for diagnostic_key in category_diagnostics:
            assert diagnostic_key not in public_container
        assert "class_scores" not in public_container
        assert "predict_proba" not in public_container


def test_upload_malicious_path_runs_category_after_binary_and_returns_sidecar(
    monkeypatch,
) -> None:
    mapped = analyze_permission_list(MOVIEBOX_PERMISSIONS)
    extraction = SimpleNamespace(
        package="com.example.uploaded-malware",
        raw_permissions=MOVIEBOX_PERMISSIONS,
        mapped_features=mapped.mapped_features,
        dangerous_permission_count=mapped.dangerous_permission_count,
        safe_permission_count=mapped.safe_permission_count,
    )
    events: list[str] = []
    category_result = _classified_category_result("Riskware")

    def binary_predict(permissions):
        assert permissions == MOVIEBOX_PERMISSIONS
        events.append("binary")
        return _malicious_permission_result()

    def category_predict(permissions):
        assert permissions == MOVIEBOX_PERMISSIONS
        events.append("category")
        return category_result

    monkeypatch.setattr(routes_upload, "analyze_apk", lambda _path: extraction)
    monkeypatch.setattr(
        routes_upload,
        "get_apk_model_service",
        lambda: SimpleNamespace(predict_from_permissions=binary_predict),
    )
    monkeypatch.setattr(
        routes_upload,
        "get_category_model_service",
        lambda: SimpleNamespace(classify_from_permissions=category_predict),
    )

    upload = UploadFile(filename="malicious.apk", file=BytesIO(b"test apk bytes"))
    response = asyncio.run(routes_upload.upload_apk(upload, "google_play_store"))

    assert events == ["binary", "category"]
    assert response.threat_assessment.model_dump() == category_result["threat_assessment"]
    assert (
        response.diagnostics.category_classification.model_dump()
        == category_result["diagnostics"]
    )
    assert response.model_prediction == "Malicious"
    assert response.malware_probability == 0.82
    assert response.overall_risk_score == 82
    assert response.overall_risk_level == "High Risk"


def test_installed_app_route_uses_same_canonical_assessment_shape(monkeypatch) -> None:
    result = {
        **_permission_result(),
        "dangerous_permission_count": 1,
        "safe_permission_count": 0,
    }
    monkeypatch.setattr(
        routes_predict,
        "get_model_service",
        lambda: SimpleNamespace(predict=lambda _features, _metadata: result),
    )
    response = routes_predict.predict_apk(
        PredictAPKRequest(
            features={"System tools : display system-level alerts (D)": 1},
            install_source="google_play_store",
        )
    )

    assert response.model_prediction == "Benign"
    assert response.overall_risk_level == "Safe"
    assert response.summary.app.package is None
    assert response.summary.curated_sensitive_permission_count == 1


def test_install_context_does_not_change_model_probability(monkeypatch) -> None:
    play = _analyze_moviebox(monkeypatch, "google_play_store")
    sideload = _analyze_moviebox(monkeypatch, "apk_sideload")

    assert play.malware_probability == sideload.malware_probability == 0.16
    assert play.model_prediction == sideload.model_prediction == "Benign"
    assert play.risk_components.permission_assessment.risk_score == 16
    assert sideload.risk_components.permission_assessment.risk_score == 16
    assert (play.overall_risk_score, play.overall_risk_level) == (16, "Safe")
    assert (sideload.overall_risk_score, sideload.overall_risk_level) == (36, "Suspicious")
    assert "added no contextual risk points" in play.summary.final_explanation.lower()
    assert "added 20 contextual risk points" in sideload.summary.final_explanation.lower()
    assert "not evidence that the app is malware" in sideload.summary.final_explanation.lower()


@pytest.mark.parametrize(
    (
        "permission_score",
        "permission_level",
        "malware_probability",
        "review_label",
        "explanation_fragment",
    ),
    [
        (16, "Safe", 0.16, "Low Permission Concern", "low review score (16/100)"),
        (
            40,
            "Suspicious",
            0.40,
            "Permission Review Recommended",
            "moderate review score (40/100)",
        ),
        (
            75,
            "High Risk",
            0.49,
            "Elevated Permission Concern",
            "elevated review score (75/100)",
        ),
    ],
    ids=["low", "moderate", "high"],
)
def test_benign_permission_review_wording_is_state_based(
    monkeypatch,
    permission_score: int,
    permission_level: str,
    malware_probability: float,
    review_label: str,
    explanation_fragment: str,
) -> None:
    permission_result = {
        **_permission_result(),
        "risk_score": permission_score,
        "risk_level": permission_level,
        "malware_probability": malware_probability,
        "probability_malware": malware_probability,
        "model_prediction": "Benign",
        "prediction": "Benign",
    }
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(
            predict_from_permissions=lambda _permissions: permission_result
        ),
    )
    monkeypatch.setattr(
        routes_predict,
        "get_category_model_service",
        lambda: pytest.fail("category classifier must not run for a benign result"),
    )

    response = routes_predict.analyze_apk(
        AnalyzeAPKRequest(
            package="com.example.generic",
            permissions=["android.permission.INTERNET"],
            install_source="google_play_store",
        )
    )
    explanation = response.summary.final_explanation.lower()
    payload = response.model_dump()

    assert response.model_prediction == "Benign"
    assert response.malware_probability == malware_probability
    assert payload["permission_risk_score"] == permission_score
    assert payload["permission_risk_level"] == permission_level
    assert payload["source_risk_points"] == 0
    assert response.overall_risk_score == permission_score
    assert response.overall_risk_level == permission_level
    assert response.summary.recommendation.startswith(f"{review_label}:")
    assert explanation_fragment in explanation
    assert "did not classify this app as malware" in explanation
    assert "not evidence that the app is malware" in explanation
    assert "malware characteristics detected" not in explanation
    assert response.threat_assessment is None


def test_final_explanation_is_authoritative_and_noncontradictory(monkeypatch) -> None:
    response = _analyze_moviebox(monkeypatch)
    explanation = response.summary.final_explanation
    reasons = response.summary.important_reasons
    combined_text = " ".join([explanation, *reasons]).lower()

    assert "did not classify this app as malware" in explanation.lower()
    assert "low review score (16/100)" in explanation.lower()
    assert "combined review score is 36/100" in explanation.lower()
    assert "not evidence that the app is malware" in explanation.lower()
    assert response.summary.recommendation.startswith("Low Permission Concern:")
    assert response.model_dump()["explanation"] == explanation
    assert response.model_dump()["reasons"] == reasons
    assert 3 <= len(reasons) <= 5
    assert len(reasons) == len(set(reasons))
    for forbidden in (
        "consistent with typical safe applications",
        "appears low risk based on its permissions",
        "pattern typical of aggressive ad-display adware",
        "common adware distribution method",
    ):
        assert forbidden not in combined_text


def test_user_summary_contains_only_approved_ui_fields(monkeypatch) -> None:
    response = _analyze_moviebox(monkeypatch)
    summary = response.summary.model_dump()

    assert set(summary) == {
        "app",
        "overall_risk_score",
        "overall_risk_level",
        "recommendation",
        "final_explanation",
        "important_reasons",
        "install_source_display",
        "total_permission_count",
        "curated_sensitive_permission_count",
    }
    assert summary["app"]["package"] == "com.example.moviebox"
    assert summary["total_permission_count"] == 6
    assert summary["curated_sensitive_permission_count"] == 3
    assert "model_name" not in summary
    assert "malware_probability" not in summary
    assert "binary_input_contract" not in summary
    assert "binary_feature_coverage" not in summary
    assert "normalization_collisions" not in summary


def test_partial_binary_contract_is_diagnostics_only(monkeypatch) -> None:
    response = _analyze_moviebox(monkeypatch)
    diagnostics = response.diagnostics.model_dump()

    assert diagnostics["binary_input_contract"] == "partial"
    assert diagnostics["binary_feature_coverage"] == {
        "expected": 241,
        "available": 208,
        "missing": 33,
        "static_api_features_available": 0,
        "matched_current_input": 6,
    }
    assert diagnostics["normalization_collisions"] == []
    assert "binary_input_contract" not in response.summary.model_dump()


def test_permission_normalization_collision_diagnostics_preserve_full_names() -> None:
    service = APKModelService.__new__(APKModelService)
    service.feature_name_set = frozenset({"READ", "RECEIVE"})
    raw_permissions = [
        "com.whatsapp.sticker.READ",
        "com.sec.android.provider.badge.permission.READ",
        "com.google.android.c2dm.permission.RECEIVE",
        "com.google.android.c2dm.permission.RECEIVE",
    ]

    collisions = service._normalization_collisions(raw_permissions)

    assert collisions == [
        {
            "normalized_token": "READ",
            "original_permissions": [
                "com.sec.android.provider.badge.permission.READ",
                "com.whatsapp.sticker.READ",
            ],
            "affects_model_feature": True,
        }
    ]
    assert raw_permissions[0] == "com.whatsapp.sticker.READ"


def test_legacy_permission_count_is_not_curated_sensitive_count(monkeypatch) -> None:
    monkeypatch.setattr(
        routes_predict,
        "get_apk_model_service",
        lambda: SimpleNamespace(predict_from_permissions=lambda _permissions: _permission_result()),
    )
    response = routes_predict.analyze_apk(
        AnalyzeAPKRequest(
            package="com.example.boot",
            permissions=["android.permission.RECEIVE_BOOT_COMPLETED"],
            install_source="google_play_store",
        )
    )

    assert response.summary.curated_sensitive_permission_count == 1
    assert response.advanced_details.legacy_flagged_permission_count == 0
    assert response.advanced_details.legacy_safe_permission_count == 1
    assert response.model_dump()["dangerous_permission_count"] == 0


def test_sideload_wording_is_contextual_not_malware_evidence() -> None:
    source = analyze_install_source("apk_sideload")

    assert source["source_risk_points"] == 20
    assert "contextual uncertainty" in source["source_explanation"].lower()
    assert "not evidence that the app is malware" in source["source_explanation"].lower()
    assert "common adware distribution" not in source["source_explanation"].lower()


def test_legacy_fields_are_retained_but_canonical_concepts_are_distinct(monkeypatch) -> None:
    response = _analyze_moviebox(monkeypatch)
    payload = response.model_dump()

    for field in (
        "risk_score",
        "risk_level",
        "prediction",
        "probability_malware",
        "confidence",
        "explanation",
        "reasons",
        "dangerous_permission_count",
        "safe_permission_count",
        "band_range",
        "model_name",
        "integration_note",
    ):
        assert field in payload
    assert payload["prediction"] == payload["model_prediction"] == "Benign"
    assert payload["overall_risk_level"] == "Suspicious"
    assert payload["prediction"] != payload["overall_risk_level"]


def test_legacy_fields_are_marked_deprecated_in_schema() -> None:
    properties = AnalyzeAPKResponse.model_json_schema()["properties"]

    for field in (
        "prediction",
        "confidence",
        "probability_malware",
        "dangerous_permission_count",
        "risk_score",
        "install_source",
    ):
        assert properties[field]["deprecated"] is True


def test_upload_apk_rejects_oversized_stream_before_analysis(monkeypatch) -> None:
    analyzed = False

    def fail_if_analyzed(_path):
        nonlocal analyzed
        analyzed = True

    monkeypatch.setattr(routes_upload, "_MAX_APK_BYTES", 3)
    monkeypatch.setattr(routes_upload, "_UPLOAD_CHUNK_BYTES", 2)
    monkeypatch.setattr(routes_upload, "analyze_apk", fail_if_analyzed)

    upload = UploadFile(filename="large.apk", file=BytesIO(b"1234"))
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(routes_upload.upload_apk(upload, "apk_sideload"))

    assert exc_info.value.status_code == 413
    assert analyzed is False


def test_notification_test_script_paths_are_script_relative() -> None:
    script = Path(__file__).resolve().parents[1] / "models" / "testing_notification_model.py"
    spec = importlib.util.spec_from_file_location("notification_model_smoke", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.MODEL_PATH.parent == script.parent
    assert module.VECTORIZER_PATH.parent == script.parent
    assert module.THRESHOLD_PATH.parent == script.parent
