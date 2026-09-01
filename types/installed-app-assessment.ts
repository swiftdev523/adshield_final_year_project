import type { InstalledAppInfo } from "./installed-apps";

export type OverallRiskLevel = "Safe" | "Suspicious" | "High Risk";
export type ModelPrediction = "Benign" | "Malicious";
export type SupportedThreatCategory =
  | "Adware"
  | "Banking Malware"
  | "SMS Malware"
  | "Riskware";

export type CuratedSensitivePermission = {
  label: string;
  description: string;
  group: string;
  category: string;
  severity: "high" | "medium";
};

export type ThreatAssessment =
  | { status: "classified"; likelyCategory: SupportedThreatCategory }
  | { status: "uncertain"; message: string };

export type InstalledAppAssessment = {
  app: Pick<InstalledAppInfo, "appName" | "packageName">;
  overallRiskScore: number;
  overallRiskLevel: OverallRiskLevel;
  recommendation: string;
  finalExplanation: string;
  importantReasons: string[];
  installSourceDisplay: string;
  totalPermissionCount: number;
  curatedSensitivePermissionCount: number;
  permissions: string[];
  curatedSensitivePermissions: CuratedSensitivePermission[];
  permissionFindings: string[];
  permissionRiskScore: number;
  permissionRiskLevel: OverallRiskLevel;
  installContextExplanation: string;
  modelPrediction: ModelPrediction;
  threatAssessment: ThreatAssessment | null;
};
