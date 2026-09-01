"""Shared schemas for clear, layered application-risk responses.

The normal mobile UI should read only ``summary``. Model output, contextual
adjustments, permission details, and implementation diagnostics are deliberately
kept in separate objects so they cannot be mistaken for the final assessment.
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .install_source import InstallSourceAssessment


RiskLevel = Literal["Safe", "Suspicious", "High Risk"]
ModelPrediction = Literal["Benign", "Malicious"]
SupportedCategory = Literal[
    "Adware",
    "Banking Malware",
    "SMS Malware",
    "Riskware",
]
CategoryMethod = Literal["selective_category_classification"]
_SUPPORTED_CATEGORY_ORDER = [
    "Adware",
    "Banking Malware",
    "SMS Malware",
    "Riskware",
]


def _require_supported_category_order(
    categories: List[SupportedCategory],
) -> List[SupportedCategory]:
    if categories != _SUPPORTED_CATEGORY_ORDER:
        raise ValueError(
            "supported_categories must contain the four locked categories in order"
        )
    return categories


class ClassifiedThreatAssessment(BaseModel):
    """Accepted output from the experimental selective category classifier."""

    status: Literal["classified"]
    likely_category: SupportedCategory
    supported_categories: List[SupportedCategory] = Field(
        ..., min_length=4, max_length=4
    )
    method: CategoryMethod

    _validate_supported_categories = field_validator("supported_categories")(
        _require_supported_category_order
    )


class UncertainThreatAssessment(BaseModel):
    """Rejected category output; uncertainty does not change binary malware risk."""

    status: Literal["uncertain"]
    likely_category: None = None
    supported_categories: List[SupportedCategory] = Field(
        ..., min_length=4, max_length=4
    )
    method: CategoryMethod
    message: Literal[
        "The app's permission pattern does not clearly match one supported threat category.",
        "The app does not contain enough supported permission evidence to assign a threat category.",
    ]

    _validate_supported_categories = field_validator("supported_categories")(
        _require_supported_category_order
    )


ThreatAssessment = Annotated[
    ClassifiedThreatAssessment | UncertainThreatAssessment,
    Field(discriminator="status"),
]


class ScoredCategoryClassificationDiagnostics(BaseModel):
    """Raw-score diagnostics; values are neither confidence nor calibrated probability."""

    top_score: float = Field(..., ge=0, le=1)
    second_score: float = Field(..., ge=0, le=1)
    margin: float = Field(..., ge=0, le=1)
    threshold: Literal[0.70]
    matched_category_feature_count: int = Field(..., ge=1)


class CategoryEligibilityDiagnostics(BaseModel):
    """Scoreless diagnostic emitted when category inference is ineligible."""

    reason: Literal["no_supported_category_features"]
    matched_category_feature_count: Literal[0]


CategoryClassificationDiagnostics = (
    ScoredCategoryClassificationDiagnostics | CategoryEligibilityDiagnostics
)


class AppIdentity(BaseModel):
    package: Optional[str] = None
    filename: Optional[str] = None


class UserFacingSummary(BaseModel):
    """Concise assessment intended for the main mobile result screen."""

    app: AppIdentity
    overall_risk_score: int = Field(..., ge=0, le=100)
    overall_risk_level: RiskLevel
    recommendation: str
    final_explanation: str
    important_reasons: List[str] = Field(..., min_length=3, max_length=5)
    install_source_display: str
    total_permission_count: int = Field(..., ge=0)
    curated_sensitive_permission_count: int = Field(..., ge=0)


class PermissionAssessment(BaseModel):
    """Advanced view of the permission model before contextual adjustment."""

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    model_prediction: ModelPrediction
    malware_probability: float = Field(..., ge=0, le=1)


class ContextualAdjustment(BaseModel):
    """Non-model context that adjusts risk but is not malware evidence."""

    install_source_display: str
    score_adjustment: int = Field(..., ge=0, le=100)
    context_level: str
    explanation: str


class RiskComponents(BaseModel):
    permission_assessment: PermissionAssessment
    contextual_adjustment: ContextualAdjustment


class CuratedSensitivePermission(BaseModel):
    """One permission matched by the project's curated concern catalog."""

    label: str
    description: str
    group: str
    category: str
    severity: Literal["high", "medium"]


class AdvancedDetails(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    total_permission_count: int = Field(..., ge=0)
    curated_sensitive_permission_count: int = Field(..., ge=0)
    curated_sensitive_permissions: List[CuratedSensitivePermission] = Field(default_factory=list)
    permission_findings: List[str] = Field(default_factory=list)
    legacy_flagged_permission_count: int = Field(
        ...,
        ge=0,
        description="Legacy dataset (D)-suffix count; not Android protectionLevel.",
    )
    legacy_safe_permission_count: int = Field(
        ...,
        ge=0,
        description="Legacy dataset (S)-suffix count.",
    )


class BinaryFeatureCoverageDiagnostics(BaseModel):
    """Capability of the frozen 241-feature input contract, not a risk score."""

    expected: Literal[241]
    available: Literal[208]
    missing: Literal[33]
    static_api_features_available: Literal[0]
    matched_current_input: int = Field(..., ge=0, le=241)


class PermissionNormalizationCollision(BaseModel):
    """Distinct full permission strings collapsed by final-token normalization."""

    normalized_token: str
    original_permissions: List[str] = Field(..., min_length=2)
    affects_model_feature: bool


class AssessmentDiagnostics(BaseModel):
    model_name: str
    mode: str
    permission_band_range: str
    overall_band_range: str
    integration_note: str
    internal_install_source: str
    decision_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    matched_model_permissions: Optional[int] = Field(default=None, ge=0)
    model_feature_count: Optional[int] = Field(default=None, ge=0)
    binary_input_contract: Optional[Literal["partial"]] = Field(
        default=None,
        description=(
            "Internal capability flag: the frozen model expects features that "
            "the permission-only runtime cannot fully reproduce."
        ),
    )
    binary_feature_coverage: Optional[BinaryFeatureCoverageDiagnostics] = Field(
        default=None,
        description="Internal feature-contract capability metadata; never confidence.",
    )
    normalization_collisions: List[PermissionNormalizationCollision] = Field(
        default_factory=list,
        description=(
            "Internal record of distinct full permission names collapsed to the "
            "same model token."
        ),
    )
    legacy_confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Deprecated class-dependent value retained for diagnostics only.",
    )
    category_classification: Optional[CategoryClassificationDiagnostics] = Field(
        default=None,
        description=(
            "Experimental selective-category raw-score diagnostics. These values "
            "are not confidence and require new independent validation."
        ),
    )


class IntegratedAssessmentResponse(InstallSourceAssessment):
    """Canonical assessment plus temporarily retained flat legacy fields."""

    # These override the shared install-source schema only for integrated app
    # assessments; the standalone install-source endpoint keeps its own normal
    # contract.
    install_source: str = Field(
        ...,
        deprecated="Use diagnostics.internal_install_source.",
    )
    install_source_display: str = Field(
        ...,
        deprecated="Use summary.install_source_display.",
    )
    source_risk_level: str = Field(
        ...,
        deprecated="Use risk_components.contextual_adjustment.context_level.",
    )
    source_risk_points: int = Field(
        ...,
        ge=0,
        le=100,
        deprecated="Use risk_components.contextual_adjustment.score_adjustment.",
    )
    source_explanation: str = Field(
        ...,
        deprecated="Use risk_components.contextual_adjustment.explanation.",
    )

    summary: UserFacingSummary
    risk_components: RiskComponents
    advanced_details: AdvancedDetails
    diagnostics: AssessmentDiagnostics
    threat_assessment: Optional[ThreatAssessment] = Field(
        default=None,
        description=(
            "Experimental selective category result for binary-malicious raw-permission "
            "APK paths only; null when category classification did not run."
        ),
    )

    # Canonical concepts. These names must never be used interchangeably.
    model_prediction: ModelPrediction
    malware_probability: float = Field(..., ge=0, le=1)
    overall_risk_score: int = Field(..., ge=0, le=100)
    overall_risk_level: RiskLevel

    # Deprecated flat compatibility fields. ``prediction`` is deliberately a
    # binary model verdict, never a Safe/Suspicious/High-Risk overall tier.
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        deprecated="Use overall_risk_score or summary.overall_risk_score.",
    )
    risk_level: RiskLevel = Field(
        ...,
        deprecated="Use overall_risk_level or summary.overall_risk_level.",
    )
    prediction: ModelPrediction = Field(
        ...,
        deprecated="Use model_prediction. This field no longer carries an overall risk tier.",
    )
    probability_malware: float = Field(
        ...,
        ge=0,
        le=1,
        deprecated="Use malware_probability.",
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        deprecated="Ambiguous legacy value. Use malware_probability.",
    )
    explanation: str = Field(
        ...,
        deprecated="Use summary.final_explanation.",
    )
    reasons: List[str] = Field(
        default_factory=list,
        deprecated="Use summary.important_reasons.",
    )
    permission_risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        deprecated="Use risk_components.permission_assessment.risk_score.",
    )
    permission_risk_level: RiskLevel = Field(
        ...,
        deprecated="Use risk_components.permission_assessment.risk_level.",
    )
    integration_note: str = Field(
        ...,
        deprecated="Use diagnostics.integration_note.",
    )
    band_range: str = Field(
        ...,
        deprecated="Use diagnostics.overall_band_range.",
    )
    model_name: str = Field(
        ...,
        deprecated="Use diagnostics.model_name.",
    )
    dangerous_permission_count: int = Field(
        ...,
        ge=0,
        deprecated=(
            "Legacy dataset (D)-suffix count. Use advanced_details."
            "legacy_flagged_permission_count; do not present it as the curated count."
        ),
    )
    safe_permission_count: int = Field(
        ...,
        ge=0,
        deprecated="Use advanced_details.legacy_safe_permission_count.",
    )
