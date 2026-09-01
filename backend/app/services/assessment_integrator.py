"""Build a layered, non-contradictory application-risk assessment."""

from __future__ import annotations

from collections.abc import Iterable

from .install_source_service import combine_risk_assessment
from .risk_score import classify_model_prediction, classify_risk


_RISK_LEVELS = {"Safe", "Suspicious", "High Risk"}


def _unique_strings(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _permission_level(permission_result: dict) -> str:
    level = permission_result.get("risk_level") or permission_result.get("permission_risk_level")
    if level in _RISK_LEVELS:
        return str(level)

    # Accept the historical test/service shape while migrating. A tier-valued
    # legacy ``prediction`` is consumed internally only and is never returned as
    # the new API's binary prediction field.
    historical = permission_result.get("prediction")
    if historical in _RISK_LEVELS:
        return str(historical)
    return classify_risk(int(permission_result["risk_score"]))


def _malware_probability(permission_result: dict) -> float:
    value = permission_result.get("malware_probability")
    if value is None:
        value = permission_result.get("probability_malware")
    if value is None:
        raise ValueError("Permission model result is missing malware_probability.")
    return max(0.0, min(1.0, float(value)))


def _permission_review_label(permission_level: str) -> str:
    return {
        "Safe": "Low Permission Concern",
        "Suspicious": "Permission Review Recommended",
        "High Risk": "Elevated Permission Concern",
    }[permission_level]


def _recommendation(
    model_prediction: str,
    permission_level: str,
    overall_level: str,
) -> str:
    if model_prediction == "Benign":
        review_label = _permission_review_label(permission_level)
        guidance = {
            "Safe": (
                "Confirm that the requested permissions match the app's purpose and "
                "review any install-source uncertainty."
            ),
            "Suspicious": (
                "Review the highlighted sensitive permissions, confirm that they match "
                "the app's purpose, and verify any install-source uncertainty."
            ),
            "High Risk": (
                "Carefully review the highlighted sensitive permissions and the app's "
                "provenance before installing or keeping it."
            ),
        }[permission_level]
        return (
            f"{review_label}: The declared-permission model did not indicate malware. "
            f"{guidance}"
        )

    return {
        "Safe": (
            "Review the malware indication and verify the publisher, requested permissions, "
            "and install source before proceeding."
        ),
        "Suspicious": (
            "Verify the publisher and install source, then review the highlighted "
            "permissions before installing or keeping the app."
        ),
        "High Risk": (
            "Avoid installing, or remove the app, unless its publisher and permission "
            "needs can be independently verified."
        ),
    }[overall_level]


def _source_context_text(source: dict) -> str:
    source_points = int(source["source_risk_points"])
    source_display = source["install_source_display"]
    if source_points > 0:
        return (
            f"{source_display} added {source_points} contextual risk points because the "
            "app's provenance is harder to verify; this adjustment is not evidence that "
            "the app is malware."
        )
    return f"{source_display} added no contextual risk points."


def _final_explanation(
    permission_score: int,
    permission_level: str,
    model_prediction: str,
    overall_score: int,
    overall_level: str,
    source: dict,
) -> str:
    if model_prediction == "Benign":
        permission_text = {
            "Safe": (
                f"Its permission profile produced a low review score ({permission_score}/100)."
            ),
            "Suspicious": (
                "Its permission profile produced a moderate review score "
                f"({permission_score}/100), so reviewing sensitive permissions is recommended."
            ),
            "High Risk": (
                "Its permission profile produced an elevated review score "
                f"({permission_score}/100), so careful review of sensitive permissions "
                "is recommended."
            ),
        }[permission_level]
        combined_text = ""
        if overall_score != permission_score:
            combined_text = f" The combined review score is {overall_score}/100."
        return (
            "The declared-permission model did not classify this app as malware. "
            f"{permission_text} {_source_context_text(source)}{combined_text} "
            "This result is not evidence that the app is malware, and it is not a "
            "guarantee that the app is safe."
        )

    assessment_text = {
        "Safe": "The combined assessment found limited risk indicators.",
        "Suspicious": "The combined assessment found factors that warrant careful review.",
        "High Risk": "The combined assessment found significant indicators that require caution.",
    }[overall_level]

    if source["source_risk_points"] > 0:
        context_text = (
            f"{source['install_source_display']} adds contextual uncertainty about the "
            "app's provenance; the install source alone is not evidence that the app is malware."
        )
    else:
        context_text = (
            f"The reported install source ({source['install_source_display']}) adds no "
            "contextual concern, but source alone does not guarantee safety."
        )

    return (
        f"Overall risk is {overall_level} ({overall_score}/100). "
        f"{assessment_text} {context_text}"
    )


def _important_reasons(
    permission_findings: list[str],
    curated_count: int,
    total_permission_count: int,
    source_explanation: str,
) -> list[str]:
    # Reserve space for the curated-count and install-context reasons. This
    # keeps the normal summary focused on the strongest permission findings
    # rather than filling it with routine capabilities such as network status.
    findings = _unique_strings(permission_findings)[:2]
    if not findings:
        findings.append("No high-priority permission combination was identified by the current rules.")

    curated_noun = "permission" if curated_count == 1 else "permissions"
    total_noun = "permission" if total_permission_count == 1 else "permissions"
    findings.append(
        f"The project's curated catalog identified {curated_count} sensitive {curated_noun} "
        f"among {total_permission_count} requested {total_noun}."
    )
    findings.append(source_explanation)
    return _unique_strings(findings)[:5]


def integrate_assessment(
    permission_result: dict,
    install_source: str | None,
    permission_explanation: dict,
    *,
    package: str | None = None,
    filename: str | None = None,
    permissions: Iterable[str] = (),
    legacy_flagged_permission_count: int = 0,
    legacy_safe_permission_count: int = 0,
    mode: str = "APK Analysis Mode",
) -> dict:
    """Combine model and context, then generate the sole final explanation."""
    permission_score = int(permission_result["risk_score"])
    permission_level = _permission_level(permission_result)
    malware_probability = _malware_probability(permission_result)
    decision_threshold = permission_result.get("decision_threshold")
    threshold = 0.5 if decision_threshold is None else float(decision_threshold)
    model_prediction = permission_result.get("model_prediction")
    if model_prediction not in {"Benign", "Malicious"}:
        model_prediction = classify_model_prediction(malware_probability, threshold)

    combined = combine_risk_assessment(permission_score, permission_level, install_source)
    raw_permissions = _unique_strings(permissions)
    total_permission_count = len(raw_permissions)
    curated = list(permission_explanation.get("curated_sensitive_permissions", []))
    curated_count = len(curated)
    permission_findings = _unique_strings(permission_explanation.get("reasons", []))
    important_reasons = _important_reasons(
        permission_findings,
        curated_count,
        total_permission_count,
        combined["source_explanation"],
    )
    final_explanation = _final_explanation(
        permission_score,
        permission_level,
        model_prediction,
        combined["overall_risk_score"],
        combined["overall_risk_level"],
        combined,
    )
    recommendation = _recommendation(
        model_prediction,
        permission_level,
        combined["overall_risk_level"],
    )

    legacy_confidence = permission_result.get("confidence")
    if legacy_confidence is None:
        legacy_confidence = (
            1.0 - malware_probability if permission_level == "Safe" else malware_probability
        )
    legacy_confidence = round(float(legacy_confidence), 4)

    summary = {
        "app": {"package": package, "filename": filename},
        "overall_risk_score": combined["overall_risk_score"],
        "overall_risk_level": combined["overall_risk_level"],
        "recommendation": recommendation,
        "final_explanation": final_explanation,
        "important_reasons": important_reasons,
        "install_source_display": combined["install_source_display"],
        "total_permission_count": total_permission_count,
        "curated_sensitive_permission_count": curated_count,
    }
    risk_components = {
        "permission_assessment": {
            "risk_score": permission_score,
            "risk_level": permission_level,
            "model_prediction": model_prediction,
            "malware_probability": malware_probability,
        },
        "contextual_adjustment": {
            "install_source_display": combined["install_source_display"],
            "score_adjustment": combined["source_risk_points"],
            "context_level": combined["source_risk_level"],
            "explanation": combined["source_explanation"],
        },
    }
    advanced_details = {
        "permissions": raw_permissions,
        "total_permission_count": total_permission_count,
        "curated_sensitive_permission_count": curated_count,
        "curated_sensitive_permissions": curated,
        "permission_findings": permission_findings,
        "legacy_flagged_permission_count": int(legacy_flagged_permission_count),
        "legacy_safe_permission_count": int(legacy_safe_permission_count),
    }
    diagnostics = {
        "model_name": str(permission_result.get("model_name", "Unknown")),
        "mode": mode,
        "permission_band_range": str(permission_result.get("band_range", "")),
        "overall_band_range": combined["overall_band_range"],
        "integration_note": combined["integration_note"],
        "internal_install_source": combined["install_source"],
        "decision_threshold": decision_threshold,
        "matched_model_permissions": permission_result.get("matched_model_permissions"),
        "model_feature_count": permission_result.get("model_feature_count"),
        "binary_input_contract": permission_result.get("binary_input_contract"),
        "binary_feature_coverage": permission_result.get("binary_feature_coverage"),
        "normalization_collisions": permission_result.get(
            "normalization_collisions", []
        ),
        "legacy_confidence": legacy_confidence,
    }

    return {
        **combined,
        "summary": summary,
        "risk_components": risk_components,
        "advanced_details": advanced_details,
        "diagnostics": diagnostics,
        "model_prediction": model_prediction,
        "malware_probability": malware_probability,
        "overall_risk_score": combined["overall_risk_score"],
        "overall_risk_level": combined["overall_risk_level"],
        # Deprecated flat compatibility fields.
        "risk_score": combined["overall_risk_score"],
        "risk_level": combined["overall_risk_level"],
        "prediction": model_prediction,
        "probability_malware": malware_probability,
        "confidence": legacy_confidence,
        "explanation": final_explanation,
        "reasons": important_reasons,
        "permission_risk_score": permission_score,
        "permission_risk_level": permission_level,
        "integration_note": combined["integration_note"],
        "band_range": combined["overall_band_range"],
        "model_name": diagnostics["model_name"],
        "dangerous_permission_count": int(legacy_flagged_permission_count),
        "safe_permission_count": int(legacy_safe_permission_count),
    }
