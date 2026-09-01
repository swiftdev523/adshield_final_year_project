export const SCAN_HISTORY_SOURCES = ["APK", "Installed App"] as const;

export type ScanHistorySource = (typeof SCAN_HISTORY_SOURCES)[number];

export const THREAT_CATEGORY_STATUSES = [
  "classified",
  "uncertain",
  "unavailable",
  "not_applicable",
] as const;

export type ThreatCategoryStatus =
  (typeof THREAT_CATEGORY_STATUSES)[number];

export const SCAN_HISTORY_OVERALL_LEVELS = [
  "Safe",
  "Suspicious",
  "High Risk",
] as const;

export type ScanHistoryOverallLevel =
  (typeof SCAN_HISTORY_OVERALL_LEVELS)[number];

export const SCAN_HISTORY_BINARY_RESULTS = ["Benign", "Malicious"] as const;

export type ScanHistoryBinaryResult =
  (typeof SCAN_HISTORY_BINARY_RESULTS)[number];

export const SCAN_HISTORY_THREAT_CATEGORIES = [
  "Adware",
  "Banking Malware",
  "SMS Malware",
  "Riskware",
] as const;

export type ScanHistoryThreatCategory =
  (typeof SCAN_HISTORY_THREAT_CATEGORIES)[number];

/**
 * Deliberately small, user-facing record persisted on the device.
 *
 * Do not add APK locations/bytes, permission lists, notification content,
 * model diagnostics, raw class scores, margins, or secrets to this type.
 */
export interface ScanHistoryEntry {
  id: string;
  source: ScanHistorySource;
  appName: string;
  packageOrFilename: string;
  timestamp: string;
  overallScore: number;
  overallLevel: ScanHistoryOverallLevel;
  binaryResult: ScanHistoryBinaryResult;
  threatCategoryStatus: ThreatCategoryStatus;
  threatCategory: ScanHistoryThreatCategory | null;
  installSourceDisplay: string;
}

export const SCAN_HISTORY_PERSISTED_FIELDS = [
  "id",
  "source",
  "appName",
  "packageOrFilename",
  "timestamp",
  "overallScore",
  "overallLevel",
  "binaryResult",
  "threatCategoryStatus",
  "threatCategory",
  "installSourceDisplay",
] as const satisfies readonly (keyof ScanHistoryEntry)[];
