export const uncertainMessage =
  "The app's permission pattern does not clearly match one supported threat category.";

export const canonicalCategories = [
  "Adware",
  "Banking Malware",
  "SMS Malware",
  "Riskware",
];

export function uploadResponse(overrides: Record<string, unknown> = {}) {
  return {
    summary: {
      app: {
        package: "com.example.sample",
        filename: "sample.apk",
      },
      overall_risk_score: 56,
      overall_risk_level: "Suspicious",
      recommendation: "Review this app before installing it.",
      final_explanation: "Overall risk is Suspicious (56/100).",
      important_reasons: [
        "The binary model classified this permission profile as malicious.",
        "The app requests access to SMS messages.",
        "The APK was provided outside a recognised app store.",
      ],
      install_source_display: "APK sideload",
      total_permission_count: 12,
      curated_sensitive_permission_count: 3,
    },
    advanced_details: {
      permissions: ["android.permission.READ_SMS", "must-not-leak-raw"],
      total_permission_count: 12,
      curated_sensitive_permission_count: 3,
      curated_sensitive_permissions: [
        {
          label: "must-not-leak-sensitive-object",
          description: "Internal advanced detail",
          group: "SMS",
          category: "Messages",
          severity: "high",
        },
      ],
      permission_findings: [
        "SMS access can expose message content.",
        "Boot access can allow automatic startup.",
      ],
      legacy_flagged_permission_count: 8,
      legacy_safe_permission_count: 4,
    },
    risk_components: {
      permission_assessment: {
        risk_score: 56,
        risk_level: "Suspicious",
        model_prediction: "Malicious",
        malware_probability: 0.913,
      },
      contextual_adjustment: {
        install_source_display: "APK sideload",
        score_adjustment: 20,
        context_level: "Elevated",
        explanation:
          "APK sideload adds contextual uncertainty about the app's provenance; the install source alone is not evidence that the app is malware.",
      },
    },
    model_prediction: "Malicious",
    malware_probability: 0.913,
    threat_assessment: null,
    diagnostics: {
      model_name: "must-not-leak-model",
      decision_threshold: 0.23,
      category_classification: {
        top_score: 0.75,
        margin: 0.12,
      },
    },
    confidence: 0.913,
    probability_malware: 0.913,
    risk_score: 56,
    risk_level: "Suspicious",
    prediction: "Malicious",
    dangerous_permission_count: 8,
    ...overrides,
  };
}

export function benignModerateUploadResponse() {
  const value = uploadResponse({
    model_prediction: "Benign",
    malware_probability: 0.4,
    threat_assessment: null,
  });

  value.summary = {
    ...value.summary,
    overall_risk_score: 40,
    overall_risk_level: "Suspicious",
    recommendation: "Review whether the requested access matches the app's purpose.",
    final_explanation: "Overall risk is Suspicious (40/100).",
    important_reasons: [
      "The app requests access to camera features.",
      "The app requests access to contacts.",
      "The reported install source adds no contextual adjustment.",
    ],
    install_source_display: "Google Play Store",
  };
  value.risk_components = {
    permission_assessment: {
      risk_score: 40,
      risk_level: "Suspicious",
      model_prediction: "Benign",
      malware_probability: 0.4,
    },
    contextual_adjustment: {
      install_source_display: "Google Play Store",
      score_adjustment: 0,
      context_level: "Low",
      explanation:
        "Reported as installed from Google Play Store. This source adds no contextual risk adjustment, but store origin alone does not guarantee safety.",
    },
  };
  return value;
}

export function classifiedThreat(category = "Banking Malware") {
  return {
    status: "classified",
    likely_category: category,
    supported_categories: canonicalCategories,
    method: "selective_category_classification",
  };
}

export function uncertainThreat(message = uncertainMessage) {
  return {
    status: "uncertain",
    likely_category: null,
    supported_categories: canonicalCategories,
    method: "selective_category_classification",
    message,
  };
}
