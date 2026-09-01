import {
  deriveHomeActivity,
  deriveHomeMetrics,
  formatActivityTime,
  latestScanSummary,
  notificationAccessPresentation,
} from "../../lib/home/deriveHomeDashboard";
import type { NotificationAnalysisByEventKey } from "../../lib/notifications/eventSummary";
import type { ScanHistoryEntry } from "../../types/scan-history";
import { apkHistoryEntry, installedHistoryEntry } from "../history/fixtures";
import { observedNotification } from "../notifications/fixtures";

const benignReviewEntry: ScanHistoryEntry = {
  ...apkHistoryEntry,
  id: "history-review-1",
  appName: "Reviewed App",
  timestamp: "2026-08-27T13:00:00.000Z",
  overallScore: 36,
  overallLevel: "Suspicious",
  binaryResult: "Benign",
};

describe("real Home dashboard derivation", () => {
  it("does not present unknown or failed empty history as zero scans", () => {
    expect(deriveHomeMetrics([], "loading")).toEqual({
      completedScans: null,
      safeResults: null,
      threats: null,
      latestScanStatus: "Loading",
      latestScanAt: null,
    });
    expect(deriveHomeMetrics([], "error")).toEqual({
      completedScans: null,
      safeResults: null,
      threats: null,
      latestScanStatus: "Unavailable",
      latestScanAt: null,
    });
    expect(deriveHomeMetrics([], "ready")).toEqual({
      completedScans: 0,
      safeResults: 0,
      threats: 0,
      latestScanStatus: "No scans",
      latestScanAt: null,
    });
  });

  it("counts completed analyses, conservative Safe results, and binary threats separately", () => {
    const maliciousUncertain: ScanHistoryEntry = {
      ...installedHistoryEntry,
      id: "history-malicious-uncertain",
      timestamp: "2026-08-27T10:00:00.000Z",
      overallLevel: "Suspicious",
      binaryResult: "Malicious",
      threatCategoryStatus: "uncertain",
      threatCategory: null,
    };

    const metrics = deriveHomeMetrics(
      [maliciousUncertain, apkHistoryEntry, benignReviewEntry],
      "ready",
    );

    expect(metrics).toEqual({
      completedScans: 3,
      safeResults: 1,
      threats: 1,
      latestScanStatus: "Suspicious",
      latestScanAt: Date.parse(benignReviewEntry.timestamp),
    });
    expect(metrics).not.toHaveProperty("securityScore");
  });

  it("uses the newest real timestamp even when history input is unsorted", () => {
    const metrics = deriveHomeMetrics(
      [apkHistoryEntry, installedHistoryEntry, benignReviewEntry],
      "ready",
    );
    const now = Date.parse("2026-08-27T14:00:00.000Z");

    expect(metrics.latestScanStatus).toBe("Suspicious");
    expect(latestScanSummary(metrics, now)).toBe("Last completed scan: 1h ago");
    expect(formatActivityTime(now - 30_000, now)).toBe("Just now");
  });

  it("describes every notification-access state without a protection claim", () => {
    const statuses = [
      "unknown",
      "checking",
      "not_granted",
      "granted",
      "unavailable",
      "error",
    ] as const;

    for (const status of statuses) {
      const presentation = notificationAccessPresentation(status);
      expect(presentation.badgeLabel).toBeTruthy();
      expect(presentation.title).toBeTruthy();
      expect(`${presentation.badgeLabel} ${presentation.title}`).not.toMatch(
        /device protected|all systems active/i,
      );
    }

    expect(notificationAccessPresentation("granted")).toMatchObject({
      badgeLabel: "MONITORING ACTIVE",
      title: "Protection tools active",
      badgeVariant: "safe",
    });
  });

  it("merges only real current scan, alert, and access-change activity", () => {
    const spamEvent = observedNotification({
      eventKey: "spam-event",
      appName: "Example Chat",
      contentFingerprint: "spam-fingerprint",
    });
    const staleEvent = observedNotification({
      eventKey: "stale-event",
      appName: "Old Result App",
      contentFingerprint: "new-fingerprint",
    });
    const analyses: NotificationAnalysisByEventKey = {
      "spam-event": {
        status: "success",
        eventKey: "spam-event",
        packageName: spamEvent.packageName,
        postedAt: spamEvent.postedAt,
        eventUpdatedAt: spamEvent.updatedAt,
        contentFingerprint: "spam-fingerprint",
        analyzedAt: 1_800_000_200_000,
        prediction: "Spam",
        modelScorePercent: 99,
      },
      "stale-event": {
        status: "success",
        eventKey: "stale-event",
        packageName: staleEvent.packageName,
        postedAt: staleEvent.postedAt,
        eventUpdatedAt: staleEvent.updatedAt,
        contentFingerprint: "old-fingerprint",
        analyzedAt: 1_800_000_300_000,
        prediction: "Spam",
        modelScorePercent: 100,
      },
    };

    const activity = deriveHomeActivity({
      historyEntries: [apkHistoryEntry, benignReviewEntry],
      notificationEvents: [spamEvent, staleEvent],
      analysisByEventKey: analyses,
      accessChanges: [
        {
          id: "access-1",
          status: "granted",
          observedAt: 1_800_000_100_000,
        },
      ],
      limit: 3,
    });

    expect(activity).toHaveLength(3);
    expect(activity[0]).toMatchObject({
      level: "caution",
      text: "A notification from Example Chat was flagged as possible spam",
      occurredAt: 1_800_000_200_000,
    });
    expect(activity[1]).toMatchObject({
      level: "safe",
      text: "Notification access was enabled",
      occurredAt: 1_800_000_100_000,
    });
    expect(activity.some((item) => item.text.includes("Old Result App"))).toBe(
      false,
    );
    expect(activity.some((item) => item.text.includes("Permission Review Recommended"))).toBe(
      true,
    );
    expect(JSON.stringify(activity)).not.toMatch(
      /modelScorePercent|contentFingerprint|Breaking offer|99/,
    );
  });
});
