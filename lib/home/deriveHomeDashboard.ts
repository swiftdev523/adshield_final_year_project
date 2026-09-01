import { isAnalysisCurrentForEvent } from "../notifications/eventSummary";
import type { NotificationAnalysisByEventKey } from "../notifications/eventSummary";
import { displayAppName, displayHistoryName } from "../privacy/displayIdentity";
import type {
  NotificationAccessChange,
  ObservedNotification,
} from "../../types/notifications";
import type {
  ScanHistoryEntry,
  ScanHistoryOverallLevel,
} from "../../types/scan-history";

export type HomeHistoryStatus = "idle" | "loading" | "ready" | "error";

export type HomeNotificationAccessStatus =
  | "unknown"
  | "checking"
  | "not_granted"
  | "granted"
  | "unavailable"
  | "error";

export type HomeActivityLevel = "safe" | "caution" | "dangerous";

export type HomeActivityItem = {
  id: string;
  level: HomeActivityLevel;
  text: string;
  occurredAt: number;
};

export type HomeDashboardMetrics = {
  completedScans: number | null;
  safeResults: number | null;
  threats: number | null;
  latestScanStatus: ScanHistoryOverallLevel | "No scans" | "Loading" | "Unavailable";
  latestScanAt: number | null;
};

export type HomeAccessPresentation = {
  badgeLabel: string;
  title: string;
  badgeVariant: "safe" | "caution";
  iconColor: string;
};

function parsedTimestamp(value: string): number | null {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function latestHistoryEntry(
  entries: readonly ScanHistoryEntry[],
): ScanHistoryEntry | null {
  let latest: ScanHistoryEntry | null = null;
  let latestAt = Number.NEGATIVE_INFINITY;

  for (const entry of entries) {
    const timestamp = parsedTimestamp(entry.timestamp);
    if (timestamp !== null && timestamp > latestAt) {
      latest = entry;
      latestAt = timestamp;
    }
  }

  return latest;
}

/**
 * Counts completed analyses, not unique packages. A result is shown as Safe
 * only when both the binary model and final integrated tier support that
 * wording. Benign + Suspicious remains review-needed, not a threat and not a
 * safely cleared result.
 */
export function deriveHomeMetrics(
  entries: readonly ScanHistoryEntry[],
  historyStatus: HomeHistoryStatus,
): HomeDashboardMetrics {
  const historyIsKnown = entries.length > 0 || historyStatus === "ready";
  if (!historyIsKnown) {
    return {
      completedScans: null,
      safeResults: null,
      threats: null,
      latestScanStatus: historyStatus === "error" ? "Unavailable" : "Loading",
      latestScanAt: null,
    };
  }

  const latest = latestHistoryEntry(entries);
  return {
    completedScans: entries.length,
    safeResults: entries.filter(
      (entry) =>
        entry.binaryResult === "Benign" && entry.overallLevel === "Safe",
    ).length,
    threats: entries.filter((entry) => entry.binaryResult === "Malicious")
      .length,
    latestScanStatus: latest?.overallLevel ?? "No scans",
    latestScanAt: latest ? parsedTimestamp(latest.timestamp) : null,
  };
}

export function notificationAccessPresentation(
  status: HomeNotificationAccessStatus,
): HomeAccessPresentation {
  switch (status) {
    case "granted":
      return {
        badgeLabel: "MONITORING ACTIVE",
        title: "Protection tools active",
        badgeVariant: "safe",
        iconColor: "#22C55E",
      };
    case "not_granted":
      return {
        badgeLabel: "ACCESS NOT ENABLED",
        title: "Notification monitoring is off",
        badgeVariant: "caution",
        iconColor: "#FF8C00",
      };
    case "checking":
      return {
        badgeLabel: "CHECKING ACCESS",
        title: "Checking notification access",
        badgeVariant: "caution",
        iconColor: "#58D6FF",
      };
    case "unavailable":
      return {
        badgeLabel: "MONITOR UNAVAILABLE",
        title: "Notification monitoring unavailable",
        badgeVariant: "caution",
        iconColor: "#FF8C00",
      };
    case "error":
      return {
        badgeLabel: "STATUS UNAVAILABLE",
        title: "Notification access could not be checked",
        badgeVariant: "caution",
        iconColor: "#FF8C00",
      };
    case "unknown":
      return {
        badgeLabel: "ACCESS STATUS",
        title: "Notification status not checked",
        badgeVariant: "caution",
        iconColor: "#8EA0C6",
      };
  }
}

export function formatActivityTime(
  occurredAt: number,
  now = Date.now(),
): string {
  if (!Number.isFinite(occurredAt)) return "Time unavailable";

  const elapsedSeconds = Math.max(0, Math.floor((now - occurredAt) / 1000));
  if (elapsedSeconds < 60) return "Just now";

  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  if (elapsedMinutes < 60) return `${elapsedMinutes}m ago`;

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours}h ago`;

  const elapsedDays = Math.floor(elapsedHours / 24);
  if (elapsedDays < 7) return `${elapsedDays}d ago`;

  return new Date(occurredAt).toISOString().slice(0, 10);
}

export function latestScanSummary(
  metrics: HomeDashboardMetrics,
  now = Date.now(),
): string {
  if (metrics.latestScanAt !== null) {
    return `Last completed scan: ${formatActivityTime(metrics.latestScanAt, now)}`;
  }
  if (metrics.completedScans === 0) return "No completed scans saved yet";
  if (metrics.latestScanStatus === "Unavailable") {
    return "Saved scan history unavailable";
  }
  return "Loading saved scan history...";
}

function scanActivity(
  entry: ScanHistoryEntry,
  privacyMode: boolean,
): HomeActivityItem | null {
  const occurredAt = parsedTimestamp(entry.timestamp);
  if (occurredAt === null) return null;

  const name = displayHistoryName(entry, privacyMode);
  if (entry.binaryResult === "Malicious") {
    const category =
      entry.threatCategoryStatus === "classified" && entry.threatCategory
        ? ` (${entry.threatCategory})`
        : "";
    return {
      id: `scan-${entry.id}`,
      level: "dangerous",
      text: `${name} scan completed: malware indicated${category}`,
      occurredAt,
    };
  }

  if (entry.overallLevel === "Safe") {
    return {
      id: `scan-${entry.id}`,
      level: "safe",
      text: `${name} scan completed: Safe`,
      occurredAt,
    };
  }

  return {
    id: `scan-${entry.id}`,
    level: "caution",
    text: `${name} scan completed: Permission Review Recommended`,
    occurredAt,
  };
}

export type DeriveHomeActivityInput = {
  historyEntries: readonly ScanHistoryEntry[];
  notificationEvents: readonly ObservedNotification[];
  analysisByEventKey: NotificationAnalysisByEventKey;
  accessChanges: readonly NotificationAccessChange[];
  privacyMode?: boolean;
  limit?: number;
};

export function deriveHomeActivity({
  historyEntries,
  notificationEvents,
  analysisByEventKey,
  accessChanges,
  privacyMode = false,
  limit = 8,
}: DeriveHomeActivityInput): HomeActivityItem[] {
  const items: HomeActivityItem[] = [];

  for (const entry of historyEntries) {
    const activity = scanActivity(entry, privacyMode);
    if (activity) items.push(activity);
  }

  for (const event of notificationEvents) {
    const analysis = analysisByEventKey[event.eventKey];
    if (
      !isAnalysisCurrentForEvent(event, analysis) ||
      analysis.status !== "success"
    ) {
      continue;
    }

    const appName = displayAppName(event.appName, privacyMode);
    items.push({
      id: `notification-analysis-${event.eventKey}-${analysis.analyzedAt}`,
      level: analysis.prediction === "Spam" ? "caution" : "safe",
      text:
        analysis.prediction === "Spam"
          ? `A notification from ${appName} was flagged as possible spam`
          : `A notification from ${appName} was analyzed as normal`,
      occurredAt: analysis.analyzedAt,
    });
  }

  for (const change of accessChanges) {
    if (!Number.isFinite(change.observedAt)) continue;
    items.push({
      id: `access-${change.id}`,
      level: change.status === "granted" ? "safe" : "caution",
      text:
        change.status === "granted"
          ? "Notification access was enabled"
          : "Notification access was disabled",
      occurredAt: change.observedAt,
    });
  }

  const normalizedLimit = Math.max(0, Math.floor(limit));
  return items
    .sort(
      (left, right) =>
        right.occurredAt - left.occurredAt || left.id.localeCompare(right.id),
    )
    .slice(0, normalizedLimit);
}
