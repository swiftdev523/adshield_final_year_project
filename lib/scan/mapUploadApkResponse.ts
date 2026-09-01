import type {
  ScanAssessment,
  ScanModelPrediction,
  ScanOverallRiskLevel,
  ScanThreatAssessment,
  SupportedThreatCategory,
} from "../../types/scan-assessment";

type JsonObject = Record<string, unknown>;

const riskLevels = new Set<ScanOverallRiskLevel>([
  "Safe",
  "Suspicious",
  "High Risk",
]);

const modelPredictions = new Set<ScanModelPrediction>([
  "Benign",
  "Malicious",
]);

const supportedCategories: readonly SupportedThreatCategory[] = [
  "Adware",
  "Banking Malware",
  "SMS Malware",
  "Riskware",
];

const supportedCategorySet = new Set<SupportedThreatCategory>(
  supportedCategories,
);

export class InvalidUploadApkResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidUploadApkResponseError";
  }
}

function fail(field: string): never {
  throw new InvalidUploadApkResponseError(
    `Backend response contains an invalid ${field}.`,
  );
}

function object(value: unknown, field: string): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return fail(field);
  }
  return value as JsonObject;
}

function nonemptyString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    return fail(field);
  }
  return value;
}

function nullableString(value: unknown, field: string): string | null {
  if (value === null) return null;
  return nonemptyString(value, field);
}

function integerInRange(
  value: unknown,
  field: string,
  minimum: number,
  maximum = Number.MAX_SAFE_INTEGER,
): number {
  if (
    typeof value !== "number" ||
    !Number.isInteger(value) ||
    value < minimum ||
    value > maximum
  ) {
    return fail(field);
  }
  return value;
}

function stringArray(
  value: unknown,
  field: string,
  minimum = 0,
  maximum = Number.MAX_SAFE_INTEGER,
): string[] {
  if (
    !Array.isArray(value) ||
    value.length < minimum ||
    value.length > maximum ||
    value.some((item) => typeof item !== "string" || item.trim() === "")
  ) {
    return fail(field);
  }
  return [...value] as string[];
}

function hasCanonicalCategories(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.length === supportedCategories.length &&
    value.every((category, index) => category === supportedCategories[index])
  );
}

function mapThreatAssessment(
  value: unknown,
  modelPrediction: ScanModelPrediction,
): ScanThreatAssessment | null {
  // The binary verdict is authoritative. Category data is never presented for
  // a benign result, even if stale or malformed category data is present.
  if (modelPrediction === "Benign") return null;
  if (value === null) return null;

  const threat = object(value, "threat_assessment");
  if (
    threat.method !== "selective_category_classification" ||
    !hasCanonicalCategories(threat.supported_categories)
  ) {
    return fail("threat_assessment");
  }

  if (threat.status === "classified") {
    const category = threat.likely_category;
    if (!supportedCategorySet.has(category as SupportedThreatCategory)) {
      return fail("threat_assessment.likely_category");
    }
    return {
      status: "classified",
      likelyCategory: category as SupportedThreatCategory,
    };
  }

  if (threat.status === "uncertain") {
    if (threat.likely_category !== null) {
      return fail("threat_assessment.likely_category");
    }
    return {
      status: "uncertain",
      message: nonemptyString(threat.message, "threat_assessment.message"),
    };
  }

  return fail("threat_assessment.status");
}

/** Maps the canonical upload response into the deliberately narrow UI model. */
export function mapUploadApkResponse(value: unknown): ScanAssessment {
  const root = object(value, "response body");
  const summary = object(root.summary, "summary");
  const app = object(summary.app, "summary.app");
  const riskComponents = object(root.risk_components, "risk_components");
  const permissionAssessment = object(
    riskComponents.permission_assessment,
    "risk_components.permission_assessment",
  );
  const contextualAdjustment = object(
    riskComponents.contextual_adjustment,
    "risk_components.contextual_adjustment",
  );
  const advancedDetails = object(root.advanced_details, "advanced_details");

  const riskLevel = nonemptyString(
    summary.overall_risk_level,
    "summary.overall_risk_level",
  );
  if (!riskLevels.has(riskLevel as ScanOverallRiskLevel)) {
    return fail("summary.overall_risk_level");
  }

  const prediction = nonemptyString(
    root.model_prediction,
    "model_prediction",
  );
  if (!modelPredictions.has(prediction as ScanModelPrediction)) {
    return fail("model_prediction");
  }
  const modelPrediction = prediction as ScanModelPrediction;

  const permissionRiskLevel = nonemptyString(
    permissionAssessment.risk_level,
    "risk_components.permission_assessment.risk_level",
  );
  if (!riskLevels.has(permissionRiskLevel as ScanOverallRiskLevel)) {
    return fail("risk_components.permission_assessment.risk_level");
  }

  return {
    app: {
      // APK manifest extraction currently supplies no application display name.
      // Keep the missing value explicit rather than deriving or inventing one.
      appName: null,
      packageName: nullableString(app.package, "summary.app.package"),
      filename: nonemptyString(app.filename, "summary.app.filename"),
    },
    overallRiskScore: integerInRange(
      summary.overall_risk_score,
      "summary.overall_risk_score",
      0,
      100,
    ),
    overallRiskLevel: riskLevel as ScanOverallRiskLevel,
    recommendation: nonemptyString(
      summary.recommendation,
      "summary.recommendation",
    ),
    finalExplanation: nonemptyString(
      summary.final_explanation,
      "summary.final_explanation",
    ),
    importantReasons: stringArray(
      summary.important_reasons,
      "summary.important_reasons",
      3,
      5,
    ),
    installSourceDisplay: nonemptyString(
      summary.install_source_display,
      "summary.install_source_display",
    ),
    totalPermissionCount: integerInRange(
      summary.total_permission_count,
      "summary.total_permission_count",
      0,
    ),
    curatedSensitivePermissionCount: integerInRange(
      summary.curated_sensitive_permission_count,
      "summary.curated_sensitive_permission_count",
      0,
    ),
    permissionFindings: stringArray(
      advancedDetails.permission_findings,
      "advanced_details.permission_findings",
    ),
    permissionRiskScore: integerInRange(
      permissionAssessment.risk_score,
      "risk_components.permission_assessment.risk_score",
      0,
      100,
    ),
    permissionRiskLevel: permissionRiskLevel as ScanOverallRiskLevel,
    installContextExplanation: nonemptyString(
      contextualAdjustment.explanation,
      "risk_components.contextual_adjustment.explanation",
    ),
    modelPrediction,
    threatAssessment: mapThreatAssessment(
      root.threat_assessment,
      modelPrediction,
    ),
  };
}
