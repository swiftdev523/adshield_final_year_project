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
  | "service_notification"
  | "progress_notification"
  | "group_summary"
  | "generic_background_status"
  | "metadata_unavailable";

export type NotificationEligibility = {
  eligible: boolean;
  reason: NotificationEligibilityReason;
};

/**
 * The native aggregate is useful for diagnostics, but classifier counts are
 * deliberately derived from individual events in the frontend.
 */
export type NativeNotificationAppSummary = {
  packageName: string;
  appName: string;
  totalObserved: number;
  eligibleCount: number;
  skippedCount: number;
  latestNotificationAt: number | null;
  latestEligibleEventKey: string | null;
};

/** Metadata-only history item. Notification text is never returned in bulk. */
export type ObservedNotification = {
  eventKey: string;
  packageName: string;
  appName: string;
  postedAt: number;
  updatedAt: number;
  removedAt: number | null;
  contentState: NotificationContentState;
  eligibility: NotificationEligibility;
  /** SHA-256 of the sanitized analysis text, not the text itself. */
  contentFingerprint: string | null;
};

/**
 * A one-event, user-requested native read. This is the only frontend bridge
 * response that contains notification text.
 */
export type NotificationAnalysisText = {
  eventKey: string;
  packageName: string;
  postedAt: number;
  updatedAt: number;
  contentFingerprint: string;
  text: string;
};

export type NotificationPrediction = "Spam" | "Ham";

/** Exact transport result from the existing frozen backend classifier. */
export type NotificationAnalysisResult = {
  prediction: NotificationPrediction;
  /** Raw backend model output; this is not a calibrated confidence value. */
  modelScorePercent: number;
};

export type NotificationAnalysisErrorKind =
  | "backend_unavailable"
  | "analysis_error";

/**
 * A body-free, current-session record created only after Android reports an
 * actual granted <-> not-granted transition. The first observed state is a
 * baseline and is not recorded as a change.
 */
export type NotificationAccessChange = {
  id: string;
  status: "granted" | "not_granted";
  observedAt: number;
};

export type NotificationAnalysisRevision = {
  eventKey: string;
  packageName: string;
  postedAt: number;
  eventUpdatedAt: number;
  contentFingerprint: string;
};

export type NotificationEventAnalysisState =
  | ({ status: "loading" } & NotificationAnalysisRevision)
  | ({
      status: "success";
      analyzedAt: number;
    } & NotificationAnalysisRevision &
      NotificationAnalysisResult)
  | ({
      status: "error";
      analyzedAt: number;
      kind: NotificationAnalysisErrorKind;
      message: string;
    } & NotificationAnalysisRevision);

export type NotificationEventPresentationState =
  | "spam"
  | "normal"
  | "not_analyzed"
  | "analysis_error"
  | "analyzing";

/** UI-ready aggregate calculated only from events and current event results. */
export type NotificationAppSummary = {
  packageName: string;
  appName: string;
  totalObserved: number;
  analyzedCount: number;
  spamFlaggedCount: number;
  normalCount: number;
  /** Events rejected by the package-neutral eligibility layer. */
  skippedCount: number;
  /** Eligible events that have not completed analysis (including loading). */
  notAnalyzedCount: number;
  analysisErrorCount: number;
  latestNotificationAt: number | null;
  latestEligibleEventKey: string | null;
};
