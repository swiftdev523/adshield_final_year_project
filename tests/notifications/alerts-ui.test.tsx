import { readFileSync } from "fs";
import { resolve } from "path";

import { fireEvent, render, screen } from "@testing-library/react-native";

import NotificationListItem from "../../components/alerts/NotificationListItem";
import SpamBanner from "../../components/alerts/SpamBanner";
import StatBar from "../../components/alerts/StatBar";
import type { NotificationEventAnalysisState } from "../../store/useAlertStore";
import type {
  NotificationAppSummary,
  ObservedNotification,
} from "../../types/notifications";

const packageName = "com.example.messaging";
const postedAt = Date.UTC(2026, 7, 15, 12, 0);

function event(
  eventKey: string,
  overrides: Partial<ObservedNotification> = {},
): ObservedNotification {
  return {
    eventKey,
    packageName,
    appName: "Example Messenger",
    postedAt,
    updatedAt: postedAt,
    removedAt: null,
    contentState: "available",
    eligibility: { eligible: true, reason: "meaningful_content" },
    contentFingerprint: `fingerprint-${eventKey}`,
    ...overrides,
  };
}

function success(
  observed: ObservedNotification,
  prediction: "Spam" | "Ham",
  modelScorePercent = 75,
): NotificationEventAnalysisState {
  return {
    status: "success",
    eventKey: observed.eventKey,
    packageName: observed.packageName,
    postedAt: observed.postedAt,
    eventUpdatedAt: observed.updatedAt,
    contentFingerprint: observed.contentFingerprint!,
    analyzedAt: observed.updatedAt + 100,
    prediction,
    modelScorePercent,
  };
}

const summary: NotificationAppSummary = {
  packageName,
  appName: "Example Messenger",
  totalObserved: 3,
  analyzedCount: 2,
  spamFlaggedCount: 1,
  normalCount: 1,
  skippedCount: 1,
  notAnalyzedCount: 0,
  analysisErrorCount: 0,
  latestNotificationAt: postedAt + 2,
  latestEligibleEventKey: "spam-event",
};

describe("event-level notification presentation", () => {
  it("keeps the app card neutral and presents mixed event outcomes separately", async () => {
    const skipped = event("skipped-event", {
      postedAt: postedAt + 2,
      updatedAt: postedAt + 2,
      eligibility: {
        eligible: false,
        reason: "generic_background_status",
      },
    });
    const normal = event("normal-event", { postedAt: postedAt + 1 });
    const spam = event("spam-event");

    await render(
      <NotificationListItem
        summary={summary}
        events={[skipped, normal, spam]}
        analysisByEventKey={{
          [normal.eventKey]: success(normal, "Ham"),
          [spam.eventKey]: success(spam, "Spam"),
        }}
        onAnalyzeEvent={jest.fn()}
      />,
    );

    expect(screen.getByText("Example Messenger")).toBeTruthy();
    expect(screen.getByText("3 notifications observed")).toBeTruthy();
    expect(
      screen.getByText("2 analyzed | 1 flagged for review | 1 skipped"),
    ).toBeTruthy();
    expect(screen.queryByText(/^SPAM$/)).toBeNull();
    expect(screen.queryByText(/Example Messenger is spam/i)).toBeNull();

    await fireEvent.press(screen.getByText("Show notification events (3)"));

    expect(screen.getByText("POSSIBLE SPAM")).toBeTruthy();
    expect(screen.getByText("NORMAL")).toBeTruthy();
    expect(screen.getByText("NOT ANALYZED")).toBeTruthy();
    expect(
      screen.getAllByText("This result applies only to this notification."),
    ).toHaveLength(2);
    expect(
      screen.getByText("Background/service status notification."),
    ).toBeTruthy();
  });

  it("offers Analyze only for an eligible event", async () => {
    const skipped = event("skipped-event", {
      eligibility: {
        eligible: false,
        reason: "generic_background_status",
      },
    });
    const pending = event("pending-event", { postedAt: postedAt + 1 });
    const onAnalyzeEvent = jest.fn();

    await render(
      <NotificationListItem
        summary={{
          ...summary,
          totalObserved: 2,
          analyzedCount: 0,
          spamFlaggedCount: 0,
          normalCount: 0,
          skippedCount: 1,
          notAnalyzedCount: 1,
          latestEligibleEventKey: pending.eventKey,
        }}
        events={[skipped, pending]}
        analysisByEventKey={{}}
        onAnalyzeEvent={onAnalyzeEvent}
      />,
    );

    await fireEvent.press(screen.getByText("Show notification events (2)"));

    expect(screen.getAllByText("NOT ANALYZED")).toHaveLength(2);
    expect(screen.getAllByText("Analyze")).toHaveLength(1);
    await fireEvent.press(screen.getByText("Analyze"));
    expect(onAnalyzeEvent).toHaveBeenCalledTimes(1);
    expect(onAnalyzeEvent).toHaveBeenCalledWith("pending-event");
  });

  it("does not let a newer event inherit an older Spam result", async () => {
    const oldSpam = event("old-spam", { postedAt });
    const newerPending = event("new-pending", {
      postedAt: postedAt + 1_000,
      updatedAt: postedAt + 1_000,
    });

    await render(
      <NotificationListItem
        summary={{
          ...summary,
          totalObserved: 2,
          analyzedCount: 1,
          spamFlaggedCount: 1,
          normalCount: 0,
          skippedCount: 0,
          notAnalyzedCount: 1,
          latestNotificationAt: newerPending.postedAt,
          latestEligibleEventKey: newerPending.eventKey,
        }}
        events={[oldSpam, newerPending]}
        analysisByEventKey={{ [oldSpam.eventKey]: success(oldSpam, "Spam") }}
        onAnalyzeEvent={jest.fn()}
      />,
    );

    await fireEvent.press(screen.getByText("Show notification events (2)"));

    expect(screen.getByText("POSSIBLE SPAM")).toBeTruthy();
    expect(screen.getByText("NOT ANALYZED")).toBeTruthy();
    expect(screen.getByText("Analyze")).toBeTruthy();
  });

  it("shows analysis errors separately from Normal and permits a retry", async () => {
    const failed = event("failed-event");
    const analysis: NotificationEventAnalysisState = {
      status: "error",
      eventKey: failed.eventKey,
      packageName: failed.packageName,
      postedAt: failed.postedAt,
      eventUpdatedAt: failed.updatedAt,
      contentFingerprint: failed.contentFingerprint!,
      analyzedAt: failed.updatedAt + 100,
      kind: "backend_unavailable",
      message: "Backend is not available.",
    };
    const onAnalyzeEvent = jest.fn();

    await render(
      <NotificationListItem
        summary={{
          ...summary,
          totalObserved: 1,
          analyzedCount: 0,
          spamFlaggedCount: 0,
          normalCount: 0,
          skippedCount: 0,
          notAnalyzedCount: 0,
          analysisErrorCount: 1,
          latestEligibleEventKey: failed.eventKey,
        }}
        events={[failed]}
        analysisByEventKey={{ [failed.eventKey]: analysis }}
        onAnalyzeEvent={onAnalyzeEvent}
      />,
    );

    await fireEvent.press(screen.getByText("Show notification events (1)"));

    expect(screen.getByText("ANALYSIS ERROR")).toBeTruthy();
    expect(screen.queryByText("NORMAL")).toBeNull();
    await fireEvent.press(screen.getByText("Retry analysis"));
    expect(onAnalyzeEvent).toHaveBeenCalledWith("failed-event");
  });

  it("does not expose private notification text or the raw model score", async () => {
    const spam = event("spam-event");

    await render(
      <NotificationListItem
        summary={{ ...summary, totalObserved: 1, skippedCount: 0 }}
        events={[spam]}
        analysisByEventKey={{
          [spam.eventKey]: success(spam, "Spam", 77.5),
        }}
        onAnalyzeEvent={jest.fn()}
      />,
    );

    await fireEvent.press(screen.getByText("Show notification events (1)"));

    expect(screen.queryByText(/77\.5/)).toBeNull();
    expect(screen.queryByText(/confidence/i)).toBeNull();
    expect(screen.queryByText(/model score/i)).toBeNull();
  });

  it("counts notification events, not classified applications, in the banner and stats", async () => {
    await render(
      <>
        <SpamBanner
          flaggedNotificationCount={2}
          affectedAppCount={1}
          onClose={jest.fn()}
        />
        <StatBar
          possibleSpamCount={2}
          normalCount={3}
          skippedCount={4}
          awaitingAnalysisCount={1}
          analysisErrorCount={1}
          totalObserved={11}
        />
      </>,
    );

    expect(screen.getByText("Possible spam notifications detected")).toBeTruthy();
    expect(
      screen.getByText(/2 notifications flagged for review across 1 observed app/),
    ).toBeTruthy();
    expect(screen.getByText("Possible Spam")).toBeTruthy();
    expect(screen.getByText("Normal")).toBeTruthy();
    expect(screen.getByText("Observed")).toBeTruthy();
    expect(screen.queryByText(/Spam Apps/i)).toBeNull();
  });

  it("filters and sorts app summaries using event-derived counts", () => {
    const source = readFileSync(
      resolve(process.cwd(), "app/(tabs)/alerts.tsx"),
      "utf8",
    );

    expect(source).toContain('summary.spamFlaggedCount > 0');
    expect(source).toContain('summary.analyzedCount > 0');
    expect(source).toContain('summary.skippedCount > 0');
    expect(source).toContain('summary.analysisErrorCount > 0');
    expect(source).toContain('right.totalObserved - left.totalObserved');
    expect(source).not.toContain("analysisByPackage");
    expect(source).not.toContain("analyzePackage");
  });

  it("keeps mock data, package classification, text bodies, and score wording out of production UI", () => {
    const productionUiFiles = [
      "app/(tabs)/alerts.tsx",
      "components/alerts/NotificationListItem.tsx",
      "components/alerts/SpamBanner.tsx",
      "components/alerts/StatBar.tsx",
    ];

    for (const path of productionUiFiles) {
      const source = readFileSync(resolve(process.cwd(), path), "utf8");
      expect(source).not.toContain("mockData");
      expect(source).not.toContain("analysisText");
      expect(source).not.toContain("modelScorePercent");
      expect(source).not.toMatch(/Spam Apps|app is spam|confidence this is spam/i);
    }
  });

  it("requests a native listener rebind after confirmed Android access", () => {
    const controller = readFileSync(
      resolve(
        process.cwd(),
        "modules/notification-monitor/android/src/main/java/expo/modules/notificationmonitor/NotificationAccessController.kt",
      ),
      "utf8",
    );
    const moduleSource = readFileSync(
      resolve(
        process.cwd(),
        "modules/notification-monitor/android/src/main/java/expo/modules/notificationmonitor/NotificationMonitorModule.kt",
      ),
      "utf8",
    );

    expect(controller).toContain("NotificationListenerService.requestRebind");
    expect(moduleSource).toContain("if (granted) NotificationAccessController.requestRebind(context)");
  });
});
