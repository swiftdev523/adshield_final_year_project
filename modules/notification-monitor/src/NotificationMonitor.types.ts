export type NotificationContentState =
  | "available"
  | "empty"
  | "sensitive_redacted"
  | "legacy_redacted";

export type NotificationEligibilityReason =
  | "meaningful_content"
  | "empty_content"
  | "sensitive_content"
  | "ongoing_notification"
  | "foreground_service"
  | "progress_notification"
  | "group_summary"
  | "service_notification"
  | "generic_background_status"
  | "metadata_unavailable";

export type NotificationEligibility = {
  eligible: boolean;
  reason: NotificationEligibilityReason;
};

export type NotificationAppSummary = {
  packageName: string;
  appName: string;
  totalObserved: number;
  eligibleCount: number;
  skippedCount: number;
  latestNotificationAt: number | null;
  latestEligibleEventKey: string | null;
};

/** Bulk history metadata. Notification body text is intentionally omitted. */
export type ObservedNotification = {
  eventKey: string;
  packageName: string;
  appName: string;
  postedAt: number;
  updatedAt: number;
  removedAt: number | null;
  contentState: NotificationContentState;
  contentFingerprint: string | null;
  eligibility: NotificationEligibility;
};

/** Minimum one-event payload returned only for an explicit analysis action. */
export type NotificationAnalysisText = {
  eventKey: string;
  packageName: string;
  postedAt: number;
  updatedAt: number;
  contentFingerprint: string;
  text: string;
};

export type NotificationMonitorNativeModule = {
  hasNotificationAccess(): Promise<boolean>;
  openNotificationAccessSettings(): Promise<void>;
  getNotificationSummary(): Promise<NotificationAppSummary[]>;
  getRecentNotifications(limit?: number): Promise<ObservedNotification[]>;
  getNotificationAnalysisText(eventKey: string): Promise<NotificationAnalysisText>;
  clearLocalNotificationHistory(): Promise<void>;
};
