import {
  createApkScanHistoryEntry,
  createInstalledAppScanHistoryEntry,
  type ScanHistoryAssessmentInput,
} from "../../lib/history/createScanHistoryEntry";
import { SCAN_HISTORY_PERSISTED_FIELDS } from "../../types/scan-history";

const identity = {
  id: "history-001",
  timestamp: "2026-08-27T12:00:00.000Z",
};

function assessment(
  overrides: Partial<ScanHistoryAssessmentInput> = {},
): ScanHistoryAssessmentInput {
  return {
    app: {
      appName: "Example App",
      packageName: "com.example.app",
      filename: "example.apk",
    },
    overallRiskScore: 64,
    overallRiskLevel: "Suspicious",
    modelPrediction: "Malicious",
    installSourceDisplay: "APK sideload",
    threatAssessment: {
      status: "classified",
      likelyCategory: "Riskware",
    },
    ...overrides,
  };
}

describe("scan-history entry builders", () => {
  it("builds an APK entry from the approved summary fields only", () => {
    const entry = createApkScanHistoryEntry(
      assessment(),
      "selected-example.apk",
      identity,
    );

    expect(entry).toEqual({
      id: "history-001",
      source: "APK",
      appName: "Example App",
      packageOrFilename: "selected-example.apk",
      timestamp: "2026-08-27T12:00:00.000Z",
      overallScore: 64,
      overallLevel: "Suspicious",
      binaryResult: "Malicious",
      threatCategoryStatus: "classified",
      threatCategory: "Riskware",
      installSourceDisplay: "APK sideload",
    });
    expect(Object.keys(entry).sort()).toEqual(
      [...SCAN_HISTORY_PERSISTED_FIELDS].sort(),
    );
  });

  it("supports an APK response whose package and app name are unavailable", () => {
    const entry = createApkScanHistoryEntry(
      assessment({
        app: {
          appName: null,
          packageName: null,
          filename: "fallback.apk",
        },
      }),
      null,
      identity,
    );

    expect(entry.appName).toBe("fallback.apk");
    expect(entry.packageOrFilename).toBe("fallback.apk");
  });

  it("uses the package for an installed-app entry", () => {
    const entry = createInstalledAppScanHistoryEntry(
      assessment({ installSourceDisplay: "Google Play" }),
      identity,
    );

    expect(entry.source).toBe("Installed App");
    expect(entry.packageOrFilename).toBe("com.example.app");
    expect(entry.installSourceDisplay).toBe("Google Play");
  });

  it("records an abstained category as uncertain without a category label", () => {
    const entry = createInstalledAppScanHistoryEntry(
      assessment({
        threatAssessment: {
          status: "uncertain",
          message: "The supported categories could not be separated safely.",
        },
      }),
      identity,
    );

    expect(entry.threatCategoryStatus).toBe("uncertain");
    expect(entry.threatCategory).toBeNull();
  });

  it("marks a benign result with no category assessment as not applicable", () => {
    const entry = createInstalledAppScanHistoryEntry(
      assessment({
        modelPrediction: "Benign",
        threatAssessment: null,
      }),
      identity,
    );

    expect(entry.threatCategoryStatus).toBe("not_applicable");
    expect(entry.threatCategory).toBeNull();
  });

  it("does not retain a stale category sidecar for a benign result", () => {
    const entry = createInstalledAppScanHistoryEntry(
      assessment({
        modelPrediction: "Benign",
        threatAssessment: {
          status: "classified",
          likelyCategory: "Riskware",
        },
      }),
      identity,
    );

    expect(entry.threatCategoryStatus).toBe("not_applicable");
    expect(entry.threatCategory).toBeNull();
  });

  it("marks a malicious result with no category assessment as unavailable", () => {
    const entry = createInstalledAppScanHistoryEntry(
      assessment({ threatAssessment: null }),
      identity,
    );

    expect(entry.threatCategoryStatus).toBe("unavailable");
    expect(entry.threatCategory).toBeNull();
  });
});
