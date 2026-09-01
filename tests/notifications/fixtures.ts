import type {
  NativeNotificationAppSummary,
  NotificationAnalysisText,
  NotificationAppSummary,
  ObservedNotification,
} from "../../types/notifications";

export const packageName = "com.example.news";

export function nativeNotificationSummary(
  overrides: Partial<NativeNotificationAppSummary> = {},
): NativeNotificationAppSummary {
  return {
    packageName,
    appName: "Example News",
    totalObserved: 1,
    eligibleCount: 1,
    skippedCount: 0,
    latestNotificationAt: 1_723_000_000_000,
    latestEligibleEventKey: "event-1",
    ...overrides,
  };
}

export function notificationSummary(
  overrides: Partial<NotificationAppSummary> = {},
): NotificationAppSummary {
  return {
    packageName,
    appName: "Example News",
    totalObserved: 1,
    analyzedCount: 0,
    spamFlaggedCount: 0,
    normalCount: 0,
    skippedCount: 0,
    notAnalyzedCount: 1,
    analysisErrorCount: 0,
    latestNotificationAt: 1_723_000_000_000,
    latestEligibleEventKey: "event-1",
    ...overrides,
  };
}

export function observedNotification(
  overrides: Partial<ObservedNotification> = {},
): ObservedNotification {
  return {
    eventKey: "event-1",
    packageName,
    appName: "Example News",
    postedAt: 1_723_000_000_000,
    updatedAt: 1_723_000_000_000,
    removedAt: null,
    contentState: "available",
    eligibility: { eligible: true, reason: "meaningful_content" },
    contentFingerprint: "fingerprint-1",
    ...overrides,
  };
}

export function notificationAnalysisText(
  overrides: Partial<NotificationAnalysisText> = {},
): NotificationAnalysisText {
  return {
    eventKey: "event-1",
    packageName,
    postedAt: 1_723_000_000_000,
    updatedAt: 1_723_000_000_000,
    contentFingerprint: "fingerprint-1",
    text: "Breaking offer available today",
    ...overrides,
  };
}
