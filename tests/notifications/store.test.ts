import { deriveNotificationAppSummaries } from "../../lib/notifications/eventSummary";
import {
  NotificationAnalysisError,
} from "../../services/notifications/analyzeNotification";
import {
  NotificationMonitorUnavailableError,
} from "../../services/notifications/notificationMonitor";
import {
  createAlertStore,
  NOTIFICATION_ACCESS_CHANGE_LIMIT,
  NOTIFICATION_HISTORY_LIMIT,
  type AlertDependencies,
} from "../../store/useAlertStore";
import type {
  NotificationAnalysisResult,
  NotificationAnalysisText,
} from "../../types/notifications";
import {
  notificationAnalysisText,
  notificationSummary,
  observedNotification,
  packageName,
} from "./fixtures";

function dependencies(
  overrides: Partial<AlertDependencies> = {},
): jest.Mocked<AlertDependencies> {
  return {
    hasNotificationAccess: jest.fn().mockResolvedValue(true),
    openNotificationAccessSettings: jest.fn().mockResolvedValue(undefined),
    getRecentNotifications: jest
      .fn()
      .mockResolvedValue([observedNotification()]),
    getNotificationAnalysisText: jest
      .fn()
      .mockResolvedValue(notificationAnalysisText()),
    clearLocalNotificationHistory: jest.fn().mockResolvedValue(undefined),
    analyzeNotification: jest
      .fn()
      .mockResolvedValue({ prediction: "Spam", modelScorePercent: 92 }),
    ...overrides,
  } as jest.Mocked<AlertDependencies>;
}

async function loadedStore(overrides: Partial<AlertDependencies> = {}) {
  const deps = dependencies(overrides);
  const store = createAlertStore(deps);
  await store.getState().checkAccessAndLoad();
  return { deps, store };
}

describe("event-level notification alert store", () => {
  it("loads the complete retained metadata history and never auto-uploads", async () => {
    const deps = dependencies();
    const store = createAlertStore(deps);
    const pending = store.getState().checkAccessAndLoad();
    expect(store.getState().accessStatus).toBe("checking");
    await pending;

    expect(store.getState()).toMatchObject({
      accessStatus: "granted",
      accessError: null,
      loadStatus: "success",
      loadError: null,
      summaries: [notificationSummary()],
      events: [observedNotification()],
      analysisByEventKey: {},
    });
    expect(deps.getRecentNotifications).toHaveBeenCalledWith(
      NOTIFICATION_HISTORY_LIMIT,
    );
    expect(NOTIFICATION_HISTORY_LIMIT).toBe(500);
    expect(deps.getNotificationAnalysisText).not.toHaveBeenCalled();
    expect(deps.analyzeNotification).not.toHaveBeenCalled();
    expect(store.getState().events[0]).not.toHaveProperty("analysisText");
  });

  it("shows not_granted without reading or uploading notification data", async () => {
    const deps = dependencies({
      hasNotificationAccess: jest.fn().mockResolvedValue(false),
    });
    const store = createAlertStore(deps);
    await store.getState().checkAccessAndLoad();

    expect(store.getState()).toMatchObject({
      accessStatus: "not_granted",
      loadStatus: "idle",
      summaries: [],
      events: [],
      analysisByEventKey: {},
    });
    expect(deps.getRecentNotifications).not.toHaveBeenCalled();
    expect(deps.getNotificationAnalysisText).not.toHaveBeenCalled();
    expect(deps.analyzeNotification).not.toHaveBeenCalled();
  });

  it("distinguishes an unavailable native module from a native access error", async () => {
    const unavailable = createAlertStore(
      dependencies({
        hasNotificationAccess: jest
          .fn()
          .mockRejectedValue(new NotificationMonitorUnavailableError("Android only")),
      }),
    );
    await unavailable.getState().checkAccessAndLoad();
    expect(unavailable.getState()).toMatchObject({
      accessStatus: "unavailable",
      accessError: "Android only",
    });

    const failed = createAlertStore(
      dependencies({
        hasNotificationAccess: jest
          .fn()
          .mockRejectedValue(new Error("Native read failed")),
      }),
    );
    await failed.getState().checkAccessAndLoad();
    expect(failed.getState()).toMatchObject({
      accessStatus: "error",
      accessError: "Native read failed",
    });
  });

  it("opens Android access settings without granting access optimistically", async () => {
    const deps = dependencies();
    const store = createAlertStore(deps);
    await store.getState().openAccessSettings();
    expect(deps.openNotificationAccessSettings).toHaveBeenCalledTimes(1);
    expect(store.getState().accessStatus).toBe("unknown");
  });

  it("records only verified access changes after the first Android baseline", async () => {
    let granted = true;
    const deps = dependencies({
      hasNotificationAccess: jest.fn().mockImplementation(async () => granted),
    });
    const store = createAlertStore(deps);
    const now = jest
      .spyOn(Date, "now")
      .mockReturnValueOnce(1_800_000_000_000)
      .mockReturnValueOnce(1_800_000_100_000);

    try {
      await store.getState().checkAccessAndLoad();
      expect(store.getState().accessChanges).toEqual([]);

      granted = false;
      await store.getState().checkAccessAndLoad();
      expect(store.getState().accessChanges).toEqual([
        {
          id: "notification-access-1800000000000-1",
          status: "not_granted",
          observedAt: 1_800_000_000_000,
        },
      ]);

      await store.getState().checkAccessAndLoad();
      expect(store.getState().accessChanges).toHaveLength(1);

      granted = true;
      await store.getState().checkAccessAndLoad();
      expect(store.getState().accessChanges).toEqual([
        {
          id: "notification-access-1800000100000-2",
          status: "granted",
          observedAt: 1_800_000_100_000,
        },
        {
          id: "notification-access-1800000000000-1",
          status: "not_granted",
          observedAt: 1_800_000_000_000,
        },
      ]);
      expect(NOTIFICATION_ACCESS_CHANGE_LIMIT).toBe(20);
    } finally {
      now.mockRestore();
    }
  });

  it("reads and submits only the one explicitly selected event", async () => {
    let resolve!: (result: NotificationAnalysisResult) => void;
    const deferred = new Promise<NotificationAnalysisResult>((done) => {
      resolve = done;
    });
    const { deps, store } = await loadedStore({
      analyzeNotification: jest.fn().mockReturnValue(deferred),
    });

    const pending = store.getState().analyzeEvent("event-1");
    expect(deps.getNotificationAnalysisText).toHaveBeenCalledWith("event-1");
    expect(store.getState().analysisByEventKey["event-1"]).toEqual({
      status: "loading",
      eventKey: "event-1",
      packageName,
      postedAt: 1_723_000_000_000,
      eventUpdatedAt: 1_723_000_000_000,
      contentFingerprint: "fingerprint-1",
    });
    await Promise.resolve();
    expect(deps.analyzeNotification).toHaveBeenCalledWith(
      "Breaking offer available today",
    );

    resolve({ prediction: "Spam", modelScorePercent: 91.2 });
    await pending;
    expect(store.getState().analysisByEventKey["event-1"]).toMatchObject({
      status: "success",
      eventKey: "event-1",
      packageName,
      prediction: "Spam",
      modelScorePercent: 91.2,
    });
    expect(store.getState().summaries[0]).toMatchObject({
      totalObserved: 1,
      analyzedCount: 1,
      spamFlaggedCount: 1,
      normalCount: 0,
      skippedCount: 0,
      notAnalyzedCount: 0,
      analysisErrorCount: 0,
    });
  });

  it.each([
    "You may have new messages",
    "Checking for new messages",
  ])("never invokes the classifier for skipped generic status: %s", async () => {
    const skipped = observedNotification({
      eligibility: { eligible: false, reason: "generic_background_status" },
      contentFingerprint: null,
    });
    const { deps, store } = await loadedStore({
      getRecentNotifications: jest.fn().mockResolvedValue([skipped]),
    });

    await store.getState().analyzeEvent(skipped.eventKey);

    expect(deps.getNotificationAnalysisText).not.toHaveBeenCalled();
    expect(deps.analyzeNotification).not.toHaveBeenCalled();
    expect(store.getState().analysisByEventKey).toEqual({});
    expect(store.getState().summaries[0]).toMatchObject({
      skippedCount: 1,
      normalCount: 0,
      analyzedCount: 0,
    });
  });

  it.each([
    "You have won a free prize. Click here to claim it.",
    "Meeting moved to 4 PM tomorrow",
  ])("keeps meaningful content eligible for the existing classifier: %s", async (text) => {
    const { deps, store } = await loadedStore({
      getNotificationAnalysisText: jest
        .fn()
        .mockResolvedValue(notificationAnalysisText({ text })),
    });

    await store.getState().analyzeEvent("event-1");

    expect(deps.analyzeNotification).toHaveBeenCalledWith(text);
  });

  it("allows an explicitly selected, retained removed event to be analyzed", async () => {
    const removed = observedNotification({ removedAt: 1_723_000_100_000 });
    const { deps, store } = await loadedStore({
      getRecentNotifications: jest.fn().mockResolvedValue([removed]),
    });

    await store.getState().analyzeEvent(removed.eventKey);

    expect(deps.getNotificationAnalysisText).toHaveBeenCalledWith(
      removed.eventKey,
    );
    expect(deps.analyzeNotification).toHaveBeenCalledWith(
      "Breaking offer available today",
    );
    expect(store.getState().analysisByEventKey[removed.eventKey]).toMatchObject({
      status: "success",
      eventKey: removed.eventKey,
    });
  });

  it("rechecks the event revision and eligibility immediately before the backend", async () => {
    let resolveText!: (result: NotificationAnalysisText) => void;
    const textDeferred = new Promise<NotificationAnalysisText>((done) => {
      resolveText = done;
    });
    const oldEvent = observedNotification();
    const changedEvent = observedNotification({
      updatedAt: oldEvent.updatedAt + 1,
      eligibility: { eligible: false, reason: "ongoing_notification" },
      contentFingerprint: "fingerprint-2",
    });
    const getRecentNotifications = jest
      .fn()
      .mockResolvedValueOnce([oldEvent])
      .mockResolvedValueOnce([changedEvent]);
    const { deps, store } = await loadedStore({
      getRecentNotifications,
      getNotificationAnalysisText: jest.fn().mockReturnValue(textDeferred),
    });

    const pending = store.getState().analyzeEvent("event-1");
    await store.getState().refresh();
    resolveText(notificationAnalysisText());
    await pending;

    expect(deps.analyzeNotification).not.toHaveBeenCalled();
    expect(store.getState().analysisByEventKey["event-1"]).toBeUndefined();
    expect(store.getState().summaries[0]).toMatchObject({
      skippedCount: 1,
      normalCount: 0,
    });
  });

  it("does not let a newer same-package event inherit an older event result", async () => {
    const oldEvent = observedNotification();
    const newEvent = observedNotification({
      eventKey: "event-2",
      postedAt: oldEvent.postedAt + 1_000,
      updatedAt: oldEvent.updatedAt + 1_000,
      contentFingerprint: "fingerprint-2",
    });
    const getRecentNotifications = jest
      .fn()
      .mockResolvedValueOnce([oldEvent])
      .mockResolvedValueOnce([newEvent, oldEvent]);
    const { store } = await loadedStore({ getRecentNotifications });
    await store.getState().analyzeEvent(oldEvent.eventKey);
    await store.getState().refresh();

    expect(store.getState().analysisByEventKey[oldEvent.eventKey]).toMatchObject({
      status: "success",
      prediction: "Spam",
    });
    expect(store.getState().analysisByEventKey[newEvent.eventKey]).toBeUndefined();
    expect(store.getState().summaries[0]).toMatchObject({
      totalObserved: 2,
      analyzedCount: 1,
      spamFlaggedCount: 1,
      notAnalyzedCount: 1,
      latestEligibleEventKey: "event-2",
    });
  });

  it("invalidates an old result when the same event key has a new revision", async () => {
    const oldEvent = observedNotification();
    const updatedEvent = observedNotification({
      updatedAt: oldEvent.updatedAt + 10,
      contentFingerprint: "different-fingerprint",
    });
    const getRecentNotifications = jest
      .fn()
      .mockResolvedValueOnce([oldEvent])
      .mockResolvedValueOnce([updatedEvent]);
    const { store } = await loadedStore({ getRecentNotifications });
    await store.getState().analyzeEvent(oldEvent.eventKey);
    expect(store.getState().analysisByEventKey[oldEvent.eventKey]).toBeDefined();

    await store.getState().refresh();

    expect(store.getState().analysisByEventKey[oldEvent.eventKey]).toBeUndefined();
    expect(store.getState().summaries[0]).toMatchObject({
      analyzedCount: 0,
      spamFlaggedCount: 0,
      notAnalyzedCount: 1,
    });
  });

  it("keeps skipped, Normal, Spam and analysis-error events distinct", async () => {
    const events = [
      observedNotification({
        eventKey: "skipped",
        eligibility: { eligible: false, reason: "foreground_service" },
        contentFingerprint: null,
      }),
      observedNotification({ eventKey: "normal", contentFingerprint: "fp-normal" }),
      observedNotification({ eventKey: "spam", contentFingerprint: "fp-spam" }),
      observedNotification({ eventKey: "error", contentFingerprint: "fp-error" }),
    ];
    const baseRevision = {
      packageName,
      postedAt: events[0].postedAt,
      eventUpdatedAt: events[0].updatedAt,
    };
    const analyses = {
      normal: {
        status: "success" as const,
        eventKey: "normal",
        ...baseRevision,
        contentFingerprint: "fp-normal",
        analyzedAt: 10,
        prediction: "Ham" as const,
        modelScorePercent: 80,
      },
      spam: {
        status: "success" as const,
        eventKey: "spam",
        ...baseRevision,
        contentFingerprint: "fp-spam",
        analyzedAt: 11,
        prediction: "Spam" as const,
        modelScorePercent: 70,
      },
      error: {
        status: "error" as const,
        eventKey: "error",
        ...baseRevision,
        contentFingerprint: "fp-error",
        analyzedAt: 12,
        kind: "analysis_error" as const,
        message: "Backend rejected the event",
      },
    };

    expect(deriveNotificationAppSummaries(events, analyses)[0]).toMatchObject({
      totalObserved: 4,
      analyzedCount: 2,
      spamFlaggedCount: 1,
      normalCount: 1,
      skippedCount: 1,
      notAnalyzedCount: 0,
      analysisErrorCount: 1,
    });
  });

  it("maps a network failure to an event-level backend_unavailable error", async () => {
    const { store } = await loadedStore({
      analyzeNotification: jest
        .fn()
        .mockRejectedValue(
          new NotificationAnalysisError("network", "Backend offline"),
        ),
    });
    await store.getState().analyzeEvent("event-1");

    expect(store.getState().analysisByEventKey["event-1"]).toMatchObject({
      status: "error",
      eventKey: "event-1",
      packageName,
      kind: "backend_unavailable",
      message: "Backend offline",
    });
    expect(store.getState().summaries[0]).toMatchObject({
      analysisErrorCount: 1,
      normalCount: 0,
      analyzedCount: 0,
    });
  });

  it("clears native history and all event-level presentation state only on success", async () => {
    const { deps, store } = await loadedStore();
    await store.getState().analyzeEvent("event-1");
    await store.getState().clearLocalHistory();

    expect(deps.clearLocalNotificationHistory).toHaveBeenCalledTimes(1);
    expect(store.getState()).toMatchObject({
      summaries: [],
      events: [],
      analysisByEventKey: {},
      loadStatus: "success",
      loadError: null,
    });
  });

  it("retains existing local data when clearing native history fails", async () => {
    const { store } = await loadedStore({
      clearLocalNotificationHistory: jest
        .fn()
        .mockRejectedValue(new Error("Clear failed")),
    });
    await store.getState().clearLocalHistory();
    expect(store.getState()).toMatchObject({
      summaries: [notificationSummary()],
      events: [observedNotification()],
      loadStatus: "error",
      loadError: "Clear failed",
    });
  });
});
