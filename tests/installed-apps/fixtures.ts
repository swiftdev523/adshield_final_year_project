import type { InstalledAppInfo } from "../../types/installed-apps";

export const installedApp: InstalledAppInfo = {
  appName: "Example Messenger",
  packageName: "com.example.messenger",
  versionName: "2.4.0",
  versionCode: 24,
  firstInstallTime: 1_700_000_000_000,
  lastUpdateTime: 1_710_000_000_000,
  isSystemApp: false,
  isUserInstalledApp: true,
  isEnabled: true,
  requestedPermissions: ["android.permission.INTERNET", "android.permission.CAMERA"],
  installerPackageName: "com.android.vending",
  installSource: "google_play_store",
  installSourceDisplay: "Google Play Store",
  totalPermissionCount: 2,
};

export function response(overrides: Record<string, unknown> = {}) {
  return {
    summary: {
      app: { package: installedApp.packageName, filename: null },
      overall_risk_score: 37,
      overall_risk_level: "Suspicious",
      recommendation: "Review whether these permissions match the app's purpose.",
      final_explanation: "Overall risk is Suspicious (37/100).",
      important_reasons: ["Camera access is declared.", "Internet access is declared.", "Install source was reported as Google Play Store."],
      install_source_display: "Google Play Store",
      total_permission_count: 2,
      curated_sensitive_permission_count: 1,
    },
    advanced_details: {
      permissions: installedApp.requestedPermissions,
      curated_sensitive_permissions: [{
        label: "Camera (D)",
        description: "can use the camera",
        group: "camera access",
        category: "camera",
        severity: "high",
      }],
      permission_findings: ["This app can use the camera."],
      legacy_flagged_permission_count: 9,
    },
    risk_components: {
      permission_assessment: {
        risk_score: 37,
        risk_level: "Suspicious",
        model_prediction: "Malicious",
        malware_probability: 0.73,
      },
      contextual_adjustment: {
        install_source_display: "Google Play Store",
        score_adjustment: 0,
        context_level: "Low",
        explanation:
          "Reported as installed from Google Play Store. This source adds no contextual risk adjustment, but store origin alone does not guarantee safety.",
      },
    },
    model_prediction: "Malicious",
    threat_assessment: null,
    diagnostics: { model_name: "must-not-leak", decision_threshold: 0.5 },
    malware_probability: 0.73,
    confidence: 0.73,
    category_scores: [0.2, 0.8],
    ...overrides,
  };
}

export function benignModerateResponse() {
  const value = response({
    model_prediction: "Benign",
    malware_probability: 0.4,
    threat_assessment: null,
  });
  value.summary = {
    ...value.summary,
    overall_risk_score: 40,
    overall_risk_level: "Suspicious",
    recommendation: "Review whether these permissions match the app's purpose.",
    final_explanation: "Overall risk is Suspicious (40/100).",
    important_reasons: [
      "Camera access is declared.",
      "Contacts access is declared.",
      "The reported install source adds no contextual adjustment.",
    ],
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
