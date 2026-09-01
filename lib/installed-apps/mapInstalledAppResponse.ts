import type {
  CuratedSensitivePermission,
  InstalledAppAssessment,
  ModelPrediction,
  OverallRiskLevel,
  SupportedThreatCategory,
  ThreatAssessment,
} from "../../types/installed-app-assessment";
import type { InstalledAppInfo } from "../../types/installed-apps";

type JsonObject = Record<string, unknown>;

const riskLevels = new Set<OverallRiskLevel>([
  "Safe",
  "Suspicious",
  "High Risk",
]);
const predictions = new Set<ModelPrediction>(["Benign", "Malicious"]);
const categories = new Set<SupportedThreatCategory>([
  "Adware",
  "Banking Malware",
  "SMS Malware",
  "Riskware",
]);

function object(value: unknown, field: string): JsonObject {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Backend response is missing ${field}.`);
  }
  return value as JsonObject;
}

function string(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Backend response contains an invalid ${field}.`);
  }
  return value;
}

function number(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Backend response contains an invalid ${field}.`);
  }
  return value;
}

function nonnegativeInteger(value: unknown, field: string): number {
  const result = number(value, field);
  if (!Number.isInteger(result) || result < 0) {
    throw new Error(`Backend response contains an invalid ${field}.`);
  }
  return result;
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function sensitivePermissions(value: unknown): CuratedSensitivePermission[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) return [];
    const item = entry as JsonObject;
    if (
      typeof item.label !== "string" ||
      typeof item.description !== "string" ||
      typeof item.group !== "string" ||
      typeof item.category !== "string" ||
      (item.severity !== "high" && item.severity !== "medium")
    ) {
      return [];
    }
    return [
      {
        label: item.label,
        description: item.description,
        group: item.group,
        category: item.category,
        severity: item.severity,
      },
    ];
  });
}

function threat(value: unknown, modelPrediction: ModelPrediction): ThreatAssessment | null {
  if (modelPrediction !== "Malicious" || value == null) return null;
  if (typeof value !== "object" || Array.isArray(value)) return null;
  const item = value as JsonObject;
  if (item.status === "classified" && categories.has(item.likely_category as SupportedThreatCategory)) {
    return {
      status: "classified",
      likelyCategory: item.likely_category as SupportedThreatCategory,
    };
  }
  if (item.status === "uncertain" && typeof item.message === "string") {
    return { status: "uncertain", message: item.message };
  }
  return null;
}

export function mapInstalledAppResponse(
  value: unknown,
  app: InstalledAppInfo,
): InstalledAppAssessment {
  const root = object(value, "response body");
  const summary = object(root.summary, "summary");
  const riskComponents = object(root.risk_components, "risk_components");
  const permissionAssessment = object(
    riskComponents.permission_assessment,
    "risk_components.permission_assessment",
  );
  const contextualAdjustment = object(
    riskComponents.contextual_adjustment,
    "risk_components.contextual_adjustment",
  );
  const advanced = object(root.advanced_details, "advanced_details");
  const riskLevel = string(summary.overall_risk_level, "overall_risk_level");
  const modelPrediction = string(root.model_prediction, "model_prediction");
  const permissionRiskLevel = string(
    permissionAssessment.risk_level,
    "permission_assessment.risk_level",
  );
  if (!riskLevels.has(riskLevel as OverallRiskLevel)) {
    throw new Error("Backend response contains an unsupported overall risk level.");
  }
  if (!predictions.has(modelPrediction as ModelPrediction)) {
    throw new Error("Backend response contains an unsupported model prediction.");
  }
  if (!riskLevels.has(permissionRiskLevel as OverallRiskLevel)) {
    throw new Error("Backend response contains an unsupported permission risk level.");
  }

  const prediction = modelPrediction as ModelPrediction;
  return {
    app: { appName: app.appName, packageName: app.packageName },
    overallRiskScore: nonnegativeInteger(summary.overall_risk_score, "overall_risk_score"),
    overallRiskLevel: riskLevel as OverallRiskLevel,
    recommendation: string(summary.recommendation, "recommendation"),
    finalExplanation: string(summary.final_explanation, "final_explanation"),
    importantReasons: strings(summary.important_reasons).slice(0, 5),
    installSourceDisplay: string(summary.install_source_display, "install_source_display"),
    totalPermissionCount: nonnegativeInteger(summary.total_permission_count, "total_permission_count"),
    curatedSensitivePermissionCount: nonnegativeInteger(
      summary.curated_sensitive_permission_count,
      "curated_sensitive_permission_count",
    ),
    permissions: strings(advanced.permissions),
    curatedSensitivePermissions: sensitivePermissions(advanced.curated_sensitive_permissions),
    permissionFindings: strings(advanced.permission_findings),
    permissionRiskScore: nonnegativeInteger(
      permissionAssessment.risk_score,
      "permission_assessment.risk_score",
    ),
    permissionRiskLevel: permissionRiskLevel as OverallRiskLevel,
    installContextExplanation: string(
      contextualAdjustment.explanation,
      "contextual_adjustment.explanation",
    ),
    modelPrediction: prediction,
    threatAssessment: threat(root.threat_assessment, prediction),
  };
}
