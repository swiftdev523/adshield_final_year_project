import type { ScanHistoryEntry } from "../../types/scan-history";

export const installedHistoryEntry: ScanHistoryEntry = {
  id: "history-installed-1",
  source: "Installed App",
  appName: "Example Bank",
  packageOrFilename: "com.example.bank",
  timestamp: "2026-08-27T12:00:00.000Z",
  overallScore: 82,
  overallLevel: "High Risk",
  binaryResult: "Malicious",
  threatCategoryStatus: "classified",
  threatCategory: "Banking Malware",
  installSourceDisplay: "Google Play Store",
};

export const apkHistoryEntry: ScanHistoryEntry = {
  id: "history-apk-1",
  source: "APK",
  appName: "",
  packageOrFilename: "calculator-lite.apk",
  timestamp: "2026-08-27T11:00:00.000Z",
  overallScore: 12,
  overallLevel: "Safe",
  binaryResult: "Benign",
  threatCategoryStatus: "not_applicable",
  threatCategory: null,
  installSourceDisplay: "APK sideload",
};
