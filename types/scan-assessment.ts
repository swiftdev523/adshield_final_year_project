export type ScanOverallRiskLevel = "Safe" | "Suspicious" | "High Risk";

export type ScanModelPrediction = "Benign" | "Malicious";

export type SupportedThreatCategory =
  | "Adware"
  | "Banking Malware"
  | "SMS Malware"
  | "Riskware";

export type ScanAppIdentity = {
  appName: string | null;
  packageName: string | null;
  filename: string | null;
};

export type ScanThreatAssessment =
  | {
      status: "classified";
      likelyCategory: SupportedThreatCategory;
    }
  | {
      status: "uncertain";
      message: string;
    };

/**
 * Source-neutral, user-facing result shared by scan presentation code.
 *
 * Model diagnostics, probabilities, thresholds, raw permissions and deprecated
 * backend compatibility fields deliberately have no representation here.
 */
export type ScanAssessment = {
  app: ScanAppIdentity;
  overallRiskScore: number;
  overallRiskLevel: ScanOverallRiskLevel;
  recommendation: string;
  finalExplanation: string;
  importantReasons: string[];
  installSourceDisplay: string;
  totalPermissionCount: number;
  curatedSensitivePermissionCount: number;
  permissionFindings: string[];
  permissionRiskScore: number;
  permissionRiskLevel: ScanOverallRiskLevel;
  installContextExplanation: string;
  modelPrediction: ScanModelPrediction;
  threatAssessment: ScanThreatAssessment | null;
};
