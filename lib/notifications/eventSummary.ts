import type {
  NotificationAppSummary,
  NotificationEventAnalysisState,
  NotificationEventPresentationState,
  ObservedNotification,
} from "../../types/notifications";

export type NotificationAnalysisByEventKey = Record<
  string,
  NotificationEventAnalysisState
>;

export function isAnalysisCurrentForEvent(
  event: ObservedNotification,
  analysis: NotificationEventAnalysisState | undefined,
): analysis is NotificationEventAnalysisState {
  return Boolean(
    analysis &&
      analysis.eventKey === event.eventKey &&
      analysis.packageName === event.packageName &&
      analysis.postedAt === event.postedAt &&
      analysis.eventUpdatedAt === event.updatedAt &&
      analysis.contentFingerprint !== "" &&
      analysis.contentFingerprint === event.contentFingerprint,
  );
}

export function getNotificationEventPresentationState(
  event: ObservedNotification,
  analysisByEventKey: NotificationAnalysisByEventKey,
): NotificationEventPresentationState {
  if (!event.eligibility.eligible) return "not_analyzed";

  const analysis = analysisByEventKey[event.eventKey];
  if (!isAnalysisCurrentForEvent(event, analysis)) return "not_analyzed";
  if (analysis.status === "loading") return "analyzing";
  if (analysis.status === "error") return "analysis_error";
  return analysis.prediction === "Spam" ? "spam" : "normal";
}

function eventTime(event: ObservedNotification): number {
  return Math.max(event.postedAt, event.updatedAt);
}

function mostRecentEvent(
  current: ObservedNotification | undefined,
  candidate: ObservedNotification,
): ObservedNotification {
  if (!current) return candidate;
  const timeDifference = eventTime(candidate) - eventTime(current);
  if (timeDifference !== 0) return timeDifference > 0 ? candidate : current;
  return candidate.eventKey.localeCompare(current.eventKey) > 0
    ? candidate
    : current;
}

export function deriveNotificationAppSummaries(
  events: readonly ObservedNotification[],
  analysisByEventKey: NotificationAnalysisByEventKey,
): NotificationAppSummary[] {
  const eventsByPackage = new Map<string, ObservedNotification[]>();

  for (const event of events) {
    const packageEvents = eventsByPackage.get(event.packageName);
    if (packageEvents) packageEvents.push(event);
    else eventsByPackage.set(event.packageName, [event]);
  }

  const summaries = Array.from(eventsByPackage.entries()).map(
    ([packageName, packageEvents]): NotificationAppSummary => {
      let latest: ObservedNotification | undefined;
      let latestEligible: ObservedNotification | undefined;
      let analyzedCount = 0;
      let spamFlaggedCount = 0;
      let normalCount = 0;
      let skippedCount = 0;
      let notAnalyzedCount = 0;
      let analysisErrorCount = 0;

      for (const event of packageEvents) {
        latest = mostRecentEvent(latest, event);
        if (event.eligibility.eligible) {
          latestEligible = mostRecentEvent(latestEligible, event);
        }

        const presentation = getNotificationEventPresentationState(
          event,
          analysisByEventKey,
        );
        if (!event.eligibility.eligible) {
          skippedCount += 1;
        } else if (presentation === "spam") {
          analyzedCount += 1;
          spamFlaggedCount += 1;
        } else if (presentation === "normal") {
          analyzedCount += 1;
          normalCount += 1;
        } else if (presentation === "analysis_error") {
          analysisErrorCount += 1;
        } else {
          // Eligible-but-idle and in-flight events have not completed analysis.
          notAnalyzedCount += 1;
        }
      }

      return {
        packageName,
        appName: latest?.appName ?? packageName,
        totalObserved: packageEvents.length,
        analyzedCount,
        spamFlaggedCount,
        normalCount,
        skippedCount,
        notAnalyzedCount,
        analysisErrorCount,
        latestNotificationAt: latest ? eventTime(latest) : null,
        latestEligibleEventKey: latestEligible?.eventKey ?? null,
      };
    },
  );

  return summaries.sort(
    (left, right) =>
      (right.latestNotificationAt ?? 0) - (left.latestNotificationAt ?? 0) ||
      right.totalObserved - left.totalObserved ||
      left.appName.localeCompare(right.appName) ||
      left.packageName.localeCompare(right.packageName),
  );
}

export function reconcileAnalysisWithEvents(
  events: readonly ObservedNotification[],
  analysisByEventKey: NotificationAnalysisByEventKey,
): NotificationAnalysisByEventKey {
  const eventByKey = new Map(events.map((event) => [event.eventKey, event]));
  const reconciled: NotificationAnalysisByEventKey = {};

  for (const [eventKey, analysis] of Object.entries(analysisByEventKey)) {
    const event = eventByKey.get(eventKey);
    if (event && isAnalysisCurrentForEvent(event, analysis)) {
      reconciled[eventKey] = analysis;
    }
  }

  return reconciled;
}
