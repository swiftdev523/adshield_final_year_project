"""Risk Score Engine.

Converts the model's malware probability (0-1) into a simple, explainable
0-100 risk score and a three-band verdict.

Bands (inclusive):
    0  - 30   -> Safe
    31 - 70   -> Suspicious
    71 - 100  -> High Risk

The raw malware probability remains separate from this risk-band policy. Callers
must expose it explicitly as ``malware_probability`` rather than describing a
class-dependent value as generic confidence.
"""

from __future__ import annotations

from ..config import (
    SAFE_MAX_SCORE,
    SUSPICIOUS_MAX_SCORE,
    TIER_HIGH_RISK,
    TIER_SAFE,
    TIER_SUSPICIOUS,
)


def compute_risk_score(probability: float) -> int:
    """Scoring formula: risk_score = round(P(malware) * 100), clamped to 0-100.

    The model already outputs a calibrated-enough probability, so the most
    explainable score is simply that probability expressed as a percentage:
    "the model is X% confident this app is malicious".
    """
    p = max(0.0, min(1.0, float(probability)))
    return int(round(p * 100))


def classify_risk(score: int) -> str:
    """Map a 0-100 score to its band label."""
    if score <= SAFE_MAX_SCORE:
        return TIER_SAFE
    if score <= SUSPICIOUS_MAX_SCORE:
        return TIER_SUSPICIOUS
    return TIER_HIGH_RISK


def band_range(tier: str) -> str:
    """Human-friendly band range for a tier (for UI labels)."""
    return {
        TIER_SAFE: f"0-{SAFE_MAX_SCORE}",
        TIER_SUSPICIOUS: f"{SAFE_MAX_SCORE + 1}-{SUSPICIOUS_MAX_SCORE}",
        TIER_HIGH_RISK: f"{SUSPICIOUS_MAX_SCORE + 1}-100",
    }.get(tier, "")


def classify_model_prediction(probability: float, threshold: float = 0.5) -> str:
    """Return the binary model verdict using its operational threshold."""
    p = max(0.0, min(1.0, float(probability)))
    t = max(0.0, min(1.0, float(threshold)))
    return "Malicious" if p >= t else "Benign"


def assess(probability: float) -> dict:
    """Full assessment from a model probability.

    Returns the risk score, risk level, band range, and a deprecated
    class-dependent confidence value retained for compatibility.
    """
    score = compute_risk_score(probability)
    tier = classify_risk(score)
    p = max(0.0, min(1.0, float(probability)))
    # Confidence = probability mass behind the verdict.
    confidence = (1.0 - p) if tier == TIER_SAFE else p
    return {
        "risk_score": score,
        "risk_level": tier,
        "band_range": band_range(tier),
        "confidence": round(confidence, 4),
    }


def score_with_threshold(probability: float, threshold: float) -> int:
    """Map a probability to 0-100 where the model's decision threshold = 50.

    Some models (e.g. the tuned APK RandomForest) have compressed probabilities
    whose malware boundary sits well below 0.5. Scaling raw probability by 100
    would then mislabel malware as low risk. Instead we piecewise-linearly map:
        p == 0          -> 0
        p == threshold  -> 50   (exactly on the decision boundary)
        p == 1          -> 100
    so the 0-30 / 31-70 / 71-100 bands stay meaningful for any threshold.
    """
    p = max(0.0, min(1.0, float(probability)))
    t = min(max(float(threshold), 1e-6), 1 - 1e-6)
    if p <= t:
        score = 50.0 * (p / t)
    else:
        score = 50.0 + 50.0 * ((p - t) / (1.0 - t))
    return int(round(max(0.0, min(100.0, score))))


def assess_with_threshold(probability: float, threshold: float) -> dict:
    """Like ``assess`` but for models with a non-default decision threshold."""
    score = score_with_threshold(probability, threshold)
    tier = classify_risk(score)
    p = max(0.0, min(1.0, float(probability)))
    confidence = (1.0 - p) if tier == TIER_SAFE else p
    return {
        "risk_score": score,
        "risk_level": tier,
        "band_range": band_range(tier),
        "confidence": round(confidence, 4),
    }
