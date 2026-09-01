import type {
  ScanHistoryBinaryResult,
  ScanHistoryEntry,
  ScanHistoryOverallLevel,
  ScanHistoryThreatCategory,
  ThreatCategoryStatus,
} from "../../types/scan-history";

export interface ScanHistoryAssessmentInput {
  app: {
    appName: string | null;
    packageName: string | null;
    filename?: string | null;
  };
  overallRiskScore: number;
  overallRiskLevel: ScanHistoryOverallLevel;
  modelPrediction: ScanHistoryBinaryResult;
  installSourceDisplay: string;
  threatAssessment:
    | {
        status: "classified";
        likelyCategory: ScanHistoryThreatCategory;
      }
    | {
        status: "uncertain";
        message?: string;
      }
    | null;
}

export interface ScanHistoryEntryIdentity {
  id: string;
  timestamp: string;
}

interface CategorySummary {
  threatCategoryStatus: ThreatCategoryStatus;
  threatCategory: ScanHistoryThreatCategory | null;
}

function requireText(
  value: string | null | undefined,
  fieldName: string,
): string {
  const normalized = value?.trim() ?? "";

  if (!normalized) {
    throw new Error(`${fieldName} is required to create scan history.`);
  }

  return normalized;
}

function summarizeThreatCategory(
  assessment: ScanHistoryAssessmentInput,
): CategorySummary {
  if (assessment.modelPrediction === "Benign") {
    return {
      threatCategoryStatus: "not_applicable",
      threatCategory: null,
    };
  }

  if (assessment.threatAssessment?.status === "classified") {
    return {
      threatCategoryStatus: "classified",
      threatCategory: assessment.threatAssessment.likelyCategory,
    };
  }

  if (assessment.threatAssessment?.status === "uncertain") {
    return {
      threatCategoryStatus: "uncertain",
      threatCategory: null,
    };
  }

  return {
    threatCategoryStatus: "unavailable",
    threatCategory: null,
  };
}

function createBaseEntry(
  assessment: ScanHistoryAssessmentInput,
  identity: ScanHistoryEntryIdentity,
): Omit<ScanHistoryEntry, "source" | "appName" | "packageOrFilename"> {
  if (!Number.isFinite(assessment.overallRiskScore)) {
    throw new Error("overallRiskScore must be a finite number.");
  }

  return {
    id: requireText(identity.id, "History ID"),
    timestamp: requireText(identity.timestamp, "History timestamp"),
    overallScore: assessment.overallRiskScore,
    overallLevel: assessment.overallRiskLevel,
    binaryResult: assessment.modelPrediction,
    ...summarizeThreatCategory(assessment),
    installSourceDisplay: requireText(
      assessment.installSourceDisplay,
      "Install-source display",
    ),
  };
}

export function createApkScanHistoryEntry(
  assessment: ScanHistoryAssessmentInput,
  filename: string | null | undefined,
  identity: ScanHistoryEntryIdentity,
): ScanHistoryEntry {
  const packageOrFilename = requireText(
    filename ?? assessment.app.filename ?? assessment.app.packageName,
    "APK filename or package",
  );

  return {
    ...createBaseEntry(assessment, identity),
    source: "APK",
    appName: requireText(
      assessment.app.appName ?? packageOrFilename,
      "App name",
    ),
    packageOrFilename,
  };
}

export function createInstalledAppScanHistoryEntry(
  assessment: ScanHistoryAssessmentInput,
  identity: ScanHistoryEntryIdentity,
): ScanHistoryEntry {
  const packageName = requireText(
    assessment.app.packageName,
    "Installed-app package",
  );

  return {
    ...createBaseEntry(assessment, identity),
    source: "Installed App",
    appName: requireText(assessment.app.appName ?? packageName, "App name"),
    packageOrFilename: packageName,
  };
}
