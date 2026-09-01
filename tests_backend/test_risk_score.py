from backend.app.services.risk_score import (
    assess_with_threshold,
    classify_model_prediction,
    classify_risk,
    compute_risk_score,
)


def test_compute_risk_score_clamps_probabilities() -> None:
    assert compute_risk_score(-1) == 0
    assert compute_risk_score(0.5) == 50
    assert compute_risk_score(2) == 100


def test_risk_band_boundaries() -> None:
    assert classify_risk(30) == "Safe"
    assert classify_risk(31) == "Suspicious"
    assert classify_risk(70) == "Suspicious"
    assert classify_risk(71) == "High Risk"


def test_tuned_threshold_maps_to_middle_of_risk_scale() -> None:
    result = assess_with_threshold(0.23, 0.23)

    assert result["risk_score"] == 50
    assert result["risk_level"] == "Suspicious"


def test_binary_model_prediction_uses_operational_threshold() -> None:
    assert classify_model_prediction(0.22, 0.23) == "Benign"
    assert classify_model_prediction(0.23, 0.23) == "Malicious"
