import {
  deriveNotificationAppSummaries,
  getNotificationEventPresentationState,
  isAnalysisCurrentForEvent,
  reconcileAnalysisWithEvents,
} from "../../lib/notifications/eventSummary";
import type { NotificationEventAnalysisState } from "../../types/notifications";
import { observedNotification } from "./fixtures";

function result(
  overrides: Partial<NotificationEventAnalysisState> = {},
): NotificationEventAnalysisState {
  return {
    status: "success",
    eventKey: "event-1",
    packageName: "com.example.news",
    postedAt: 1_723_000_000_000,
    eventUpdatedAt: 1_723_000_000_000,
    contentFingerprint: "fingerprint-1",
    analyzedAt: 1_723_000_001_000,
    prediction: "Spam",
    modelScorePercent: 90,
    ...overrides,
  } as NotificationEventAnalysisState;
}

describe("notification event summaries", () => {
  it("requires the exact event revision before presenting a result", () => {
    const event = observedNotification();
    expect(isAnalysisCurrentForEvent(event, result())).toBe(true);
    expect(
      isAnalysisCurrentForEvent(
        event,
        result({ eventUpdatedAt: event.updatedAt + 1 }),
      ),
    ).toBe(false);
    expect(
      isAnalysisCurrentForEvent(
        event,
        result({ contentFingerprint: "different" }),
      ),
    ).toBe(false);
  });

  it("never presents an ineligible event as Normal even if stale analysis exists", () => {
    const skipped = observedNotification({
      eligibility: { eligible: false, reason: "generic_background_status" },
    });
    const state = getNotificationEventPresentationState(skipped, {
      "event-1": result({ prediction: "Ham" }),
    });
    expect(state).toBe("not_analyzed");
  });

  it("keeps raw classifier state event-specific rather than applying it to a package", () => {
    const spam = observedNotification();
    const newer = observedNotification({
      eventKey: "event-2",
      updatedAt: spam.updatedAt + 1,
      postedAt: spam.postedAt + 1,
      contentFingerprint: "fingerprint-2",
    });
    const analyses = { "event-1": result() };

    expect(getNotificationEventPresentationState(spam, analyses)).toBe("spam");
    expect(getNotificationEventPresentationState(newer, analyses)).toBe(
      "not_analyzed",
    );
    expect(deriveNotificationAppSummaries([spam, newer], analyses)[0]).toMatchObject({
      totalObserved: 2,
      analyzedCount: 1,
      spamFlaggedCount: 1,
      notAnalyzedCount: 1,
    });
  });

  it("drops cached results absent from history or no longer matching a revision", () => {
    const event = observedNotification({ updatedAt: 2 });
    const analyses = {
      "event-1": result(),
      missing: result({ eventKey: "missing" }),
    };
    expect(reconcileAnalysisWithEvents([event], analyses)).toEqual({});
  });

  it("allows an exact retained removed event to keep its event-level result", () => {
    const removed = observedNotification({ removedAt: 1_723_000_100_000 });
    expect(getNotificationEventPresentationState(removed, { "event-1": result() })).toBe(
      "spam",
    );
  });
});
