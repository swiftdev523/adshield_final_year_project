import {
  InvalidUploadApkResponseError,
  mapUploadApkResponse,
} from "../../lib/scan/mapUploadApkResponse";
import {
  classifiedThreat,
  uncertainMessage,
  uncertainThreat,
  uploadResponse,
} from "./fixtures";

describe("APK upload response adapter", () => {
  it("maps only the approved source-neutral UI fields", () => {
    const result = mapUploadApkResponse(uploadResponse());

    expect(result).toEqual({
      app: {
        appName: null,
        packageName: "com.example.sample",
        filename: "sample.apk",
      },
      overallRiskScore: 56,
      overallRiskLevel: "Suspicious",
      recommendation: "Review this app before installing it.",
      finalExplanation: "Overall risk is Suspicious (56/100).",
      importantReasons: [
        "The binary model classified this permission profile as malicious.",
        "The app requests access to SMS messages.",
        "The APK was provided outside a recognised app store.",
      ],
      installSourceDisplay: "APK sideload",
      totalPermissionCount: 12,
      curatedSensitivePermissionCount: 3,
      permissionFindings: [
        "SMS access can expose message content.",
        "Boot access can allow automatic startup.",
      ],
      permissionRiskScore: 56,
      permissionRiskLevel: "Suspicious",
      installContextExplanation:
        "APK sideload adds contextual uncertainty about the app's provenance; the install source alone is not evidence that the app is malware.",
      modelPrediction: "Malicious",
      threatAssessment: null,
    });

    const serialized = JSON.stringify(result);
    for (const forbidden of [
      "must-not-leak",
      "malwareProbability",
      "probability_malware",
      "confidence",
      "diagnostics",
      "model_name",
      "threshold",
      "top_score",
      "margin",
      "dangerous_permission_count",
      "legacy",
      "requestedPermissions",
      "sensitivePermissions",
      "malware_probability",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });

  it("applies the benign binary gate before category mapping", () => {
    const result = mapUploadApkResponse(
      uploadResponse({
        model_prediction: "Benign",
        // A stale value must never create a user-facing category for Benign.
        threat_assessment: classifiedThreat("Adware"),
      }),
    );

    expect(result.modelPrediction).toBe("Benign");
    expect(result.threatAssessment).toBeNull();
  });

  it("maps classified, uncertain and unavailable malicious category states", () => {
    expect(
      mapUploadApkResponse(
        uploadResponse({ threat_assessment: classifiedThreat() }),
      ).threatAssessment,
    ).toEqual({
      status: "classified",
      likelyCategory: "Banking Malware",
    });

    expect(
      mapUploadApkResponse(
        uploadResponse({ threat_assessment: uncertainThreat() }),
      ).threatAssessment,
    ).toEqual({ status: "uncertain", message: uncertainMessage });

    expect(
      mapUploadApkResponse(uploadResponse({ threat_assessment: null }))
        .threatAssessment,
    ).toBeNull();
  });

  it("rejects invalid canonical fields instead of fabricating a result", () => {
    const response = uploadResponse();
    (response.summary as Record<string, unknown>).overall_risk_level = "Medium";

    expect(() => mapUploadApkResponse(response)).toThrow(
      InvalidUploadApkResponseError,
    );

    const tooFewReasons = uploadResponse();
    (tooFewReasons.summary as Record<string, unknown>).important_reasons = [
      "Only one reason",
    ];
    expect(() => mapUploadApkResponse(tooFewReasons)).toThrow(
      "summary.important_reasons",
    );
  });

  it("requires the permission and neutral install-context presentation fields", () => {
    const response = uploadResponse();
    delete (response as Record<string, unknown>).risk_components;
    expect(() => mapUploadApkResponse(response)).toThrow("risk_components");

    const invalidPermissionLevel = uploadResponse();
    (
      (
        invalidPermissionLevel.risk_components as Record<string, unknown>
      ).permission_assessment as Record<string, unknown>
    ).risk_level = "Moderate";
    expect(() => mapUploadApkResponse(invalidPermissionLevel)).toThrow(
      "risk_components.permission_assessment.risk_level",
    );
  });

  it("rejects a malformed malicious threat assessment", () => {
    expect(() =>
      mapUploadApkResponse(
        uploadResponse({
          threat_assessment: {
            ...classifiedThreat(),
            likely_category: "Ransomware",
          },
        }),
      ),
    ).toThrow("threat_assessment.likely_category");
  });
});
