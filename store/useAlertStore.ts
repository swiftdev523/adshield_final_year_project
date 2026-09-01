import { create } from "zustand";

import {
  deriveNotificationAppSummaries,
  isAnalysisCurrentForEvent,
  reconcileAnalysisWithEvents,
  type NotificationAnalysisByEventKey,
} from "../lib/notifications/eventSummary";
import {
  analyzeNotification,
  NotificationAnalysisError,
} from "../services/notifications/analyzeNotification";
import {
  clearLocalNotificationHistory,
  getNotificationAnalysisText,
  getRecentNotifications,
  hasNotificationAccess,
  NotificationMonitorUnavailableError,
  openNotificationAccessSettings,
} from "../services/notifications/notificationMonitor";
import type {
  NotificationAccessChange,
  NotificationAnalysisResult,
  NotificationAnalysisRevision,
  NotificationAnalysisText,
  NotificationAppSummary,
  NotificationEventAnalysisState,
  ObservedNotification,
} from "../types/notifications";

export type { NotificationEventAnalysisState } from "../types/notifications";

export type NotificationAccessStatus =
  | "unknown"
  | "checking"
  | "not_granted"
  | "granted"
  | "unavailable"
  | "error";

export type NotificationLoadStatus = "idle" | "loading" | "success" | "error";

export type AlertDependencies = {
  hasNotificationAccess(): Promise<boolean>;
  openNotificationAccessSettings(): Promise<void>;
  getRecentNotifications(limit?: number): Promise<ObservedNotification[]>;
  getNotificationAnalysisText(eventKey: string): Promise<NotificationAnalysisText>;
  clearLocalNotificationHistory(): Promise<void>;
  analyzeNotification(text: string): Promise<NotificationAnalysisResult>;
};

export type AlertState = {
  accessStatus: NotificationAccessStatus;
  accessError: string | null;
  accessChanges: NotificationAccessChange[];
  loadStatus: NotificationLoadStatus;
  loadError: string | null;
  summaries: NotificationAppSummary[];
  events: ObservedNotification[];
  analysisByEventKey: NotificationAnalysisByEventKey;
  spamBannerDismissed: boolean;
  checkAccessAndLoad(): Promise<void>;
  refresh(): Promise<void>;
  openAccessSettings(): Promise<void>;
  clearLocalHistory(): Promise<void>;
  analyzeEvent(eventKey: string): Promise<void>;
  dismissSpamBanner(): void;
  resetSpamBanner(): void;
};

// This equals the native repository cap, so derived summaries cover every
// retained event rather than an arbitrary first page.
export const NOTIFICATION_HISTORY_LIMIT = 500;
export const NOTIFICATION_ACCESS_CHANGE_LIMIT = 20;

const errorMessage = (error: unknown, fallback: string) =>
  error instanceof Error && error.message ? error.message : fallback;

function analysisRevision(
  event: ObservedNotification,
): NotificationAnalysisRevision | null {
  if (!event.contentFingerprint) return null;
  return {
    eventKey: event.eventKey,
    packageName: event.packageName,
    postedAt: event.postedAt,
    eventUpdatedAt: event.updatedAt,
    contentFingerprint: event.contentFingerprint,
  };
}

function textMatchesRevision(
  text: NotificationAnalysisText,
  revision: NotificationAnalysisRevision,
): boolean {
  return (
    text.eventKey === revision.eventKey &&
    text.packageName === revision.packageName &&
    text.postedAt === revision.postedAt &&
    text.updatedAt === revision.eventUpdatedAt &&
    text.contentFingerprint === revision.contentFingerprint &&
    text.text.trim() !== ""
  );
}

export function createAlertStore(dependencies: AlertDependencies) {
  let accessRequestSequence = 0;
  let loadRequestSequence = 0;
  let analysisGeneration = 0;
  let lastObservedAccess: "granted" | "not_granted" | null = null;
  let accessChangeSequence = 0;
  const analysisRequestSequence = new Map<string, number>();

  return create<AlertState>((set, get) => {
    const recordAccessObservation = (
      status: "granted" | "not_granted",
    ) => {
      const previous = lastObservedAccess;
      lastObservedAccess = status;

      // The first successful Android read establishes the baseline. Only a
      // later, verified granted <-> not-granted transition is an activity.
      if (previous === null || previous === status) return;

      const observedAt = Date.now();
      accessChangeSequence += 1;
      const change: NotificationAccessChange = {
        id: `notification-access-${observedAt}-${accessChangeSequence}`,
        status,
        observedAt,
      };
      set((state) => ({
        accessChanges: [change, ...state.accessChanges].slice(
          0,
          NOTIFICATION_ACCESS_CHANGE_LIMIT,
        ),
      }));
    };

    const setEventsAndAnalyses = (
      events: ObservedNotification[],
      analysisByEventKey: NotificationAnalysisByEventKey,
      additional: Partial<AlertState> = {},
    ) => {
      set({
        events,
        analysisByEventKey,
        summaries: deriveNotificationAppSummaries(events, analysisByEventKey),
        ...additional,
      });
    };

    const setAnalysis = (
      eventKey: string,
      analysis: NotificationEventAnalysisState,
    ) => {
      set((state) => {
        const analysisByEventKey = {
          ...state.analysisByEventKey,
          [eventKey]: analysis,
        };
        return {
          analysisByEventKey,
          summaries: deriveNotificationAppSummaries(
            state.events,
            analysisByEventKey,
          ),
        };
      });
    };

    const currentEventForRevision = (
      revision: NotificationAnalysisRevision,
    ): ObservedNotification | undefined => {
      const event = get().events.find(
        (candidate) => candidate.eventKey === revision.eventKey,
      );
      const syntheticAnalysis: NotificationEventAnalysisState = {
        status: "loading",
        ...revision,
      };
      return event && isAnalysisCurrentForEvent(event, syntheticAnalysis)
        ? event
        : undefined;
    };

    const loadLocalData = async () => {
      const requestId = ++loadRequestSequence;
      set({ loadStatus: "loading", loadError: null });

      try {
        const events = await dependencies.getRecentNotifications(
          NOTIFICATION_HISTORY_LIMIT,
        );
        if (requestId !== loadRequestSequence) return;
        const analysisByEventKey = reconcileAnalysisWithEvents(
          events,
          get().analysisByEventKey,
        );
        setEventsAndAnalyses(events, analysisByEventKey, {
          loadStatus: "success",
          loadError: null,
        });
      } catch (error) {
        if (requestId !== loadRequestSequence) return;
        set({
          loadStatus: "error",
          loadError: errorMessage(
            error,
            "Unable to read locally observed notifications.",
          ),
        });
      }
    };

    return {
      accessStatus: "unknown",
      accessError: null,
      accessChanges: [],
      loadStatus: "idle",
      loadError: null,
      summaries: [],
      events: [],
      analysisByEventKey: {},
      spamBannerDismissed: false,

      async checkAccessAndLoad() {
        const requestId = ++accessRequestSequence;
        set({ accessStatus: "checking", accessError: null });

        try {
          const granted = await dependencies.hasNotificationAccess();
          if (requestId !== accessRequestSequence) return;

          recordAccessObservation(granted ? "granted" : "not_granted");

          if (!granted) {
            loadRequestSequence += 1;
            setEventsAndAnalyses([], {}, {
              accessStatus: "not_granted",
              accessError: null,
              loadStatus: "idle",
              loadError: null,
            });
            return;
          }

          set({ accessStatus: "granted", accessError: null });
          await loadLocalData();
        } catch (error) {
          if (requestId !== accessRequestSequence) return;
          loadRequestSequence += 1;
          set({
            accessStatus:
              error instanceof NotificationMonitorUnavailableError
                ? "unavailable"
                : "error",
            accessError: errorMessage(
              error,
              "Unable to check notification access.",
            ),
            loadStatus: "idle",
          });
        }
      },

      async refresh() {
        await get().checkAccessAndLoad();
      },

      async openAccessSettings() {
        try {
          await dependencies.openNotificationAccessSettings();
        } catch (error) {
          set({
            accessStatus:
              error instanceof NotificationMonitorUnavailableError
                ? "unavailable"
                : "error",
            accessError: errorMessage(
              error,
              "Unable to open notification access settings.",
            ),
          });
        }
      },

      async clearLocalHistory() {
        try {
          await dependencies.clearLocalNotificationHistory();
          analysisGeneration += 1;
          analysisRequestSequence.clear();
          setEventsAndAnalyses([], {}, {
            loadStatus: "success",
            loadError: null,
          });
        } catch (error) {
          set({
            loadStatus: "error",
            loadError: errorMessage(
              error,
              "Unable to clear local notification history.",
            ),
          });
        }
      },

      async analyzeEvent(eventKey) {
        const normalizedEventKey = eventKey.trim();
        if (!normalizedEventKey) return;

        const event = get().events.find(
          (candidate) => candidate.eventKey === normalizedEventKey,
        );
        const revision = event ? analysisRevision(event) : null;

        // Ineligible/redacted/empty events remain Not analyzed. They are never
        // turned into analysis errors and never cross the backend boundary.
        if (
          !event ||
          !event.eligibility.eligible ||
          event.contentState !== "available" ||
          !revision
        ) {
          return;
        }

        const requestId =
          (analysisRequestSequence.get(normalizedEventKey) ?? 0) + 1;
        const generation = analysisGeneration;
        analysisRequestSequence.set(normalizedEventKey, requestId);
        setAnalysis(normalizedEventKey, { status: "loading", ...revision });

        const requestIsCurrent = () =>
          generation === analysisGeneration &&
          analysisRequestSequence.get(normalizedEventKey) === requestId;

        try {
          const analysisText = await dependencies.getNotificationAnalysisText(
            normalizedEventKey,
          );
          if (!requestIsCurrent()) return;

          // Re-read the live event immediately before the network call. Both
          // the metadata revision and native one-event payload must still be
          // the exact revision selected by the user.
          const currentEvent = currentEventForRevision(revision);
          if (
            !currentEvent ||
            !currentEvent.eligibility.eligible ||
            currentEvent.contentState !== "available" ||
            !textMatchesRevision(analysisText, revision)
          ) {
            return;
          }

          const result = await dependencies.analyzeNotification(
            analysisText.text.trim(),
          );
          if (!requestIsCurrent() || !currentEventForRevision(revision)) return;

          setAnalysis(normalizedEventKey, {
            status: "success",
            ...revision,
            analyzedAt: Date.now(),
            ...result,
          });
        } catch (error) {
          if (!requestIsCurrent() || !currentEventForRevision(revision)) return;
          setAnalysis(normalizedEventKey, {
            status: "error",
            ...revision,
            analyzedAt: Date.now(),
            kind:
              error instanceof NotificationAnalysisError &&
              error.kind === "network"
                ? "backend_unavailable"
                : "analysis_error",
            message: errorMessage(
              error,
              "Unable to analyze this notification.",
            ),
          });
        }
      },

      dismissSpamBanner() {
        set({ spamBannerDismissed: true });
      },

      resetSpamBanner() {
        set({ spamBannerDismissed: false });
      },
    };
  });
}

export const useAlertStore = createAlertStore({
  hasNotificationAccess,
  openNotificationAccessSettings,
  getRecentNotifications,
  getNotificationAnalysisText,
  clearLocalNotificationHistory,
  analyzeNotification,
});
