import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useFocusEffect } from "expo-router";
import {
  ActivityIndicator,
  Alert,
  AppState,
  FlatList,
  Pressable,
  RefreshControl,
  Text,
  View,
} from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import NotificationListItem from "../../components/alerts/NotificationListItem";
import SpamBanner from "../../components/alerts/SpamBanner";
import StatBar from "../../components/alerts/StatBar";
import { useAlertStore } from "../../store/useAlertStore";
import { useSettingsStore } from "../../store/useSettingsStore";
import type { NotificationLoadStatus } from "../../store/useAlertStore";
import type {
  NotificationAppSummary,
  ObservedNotification,
} from "../../types/notifications";

const FILTERS = ["All", "Flagged", "Analyzed", "Skipped", "Errors"] as const;

type FilterOption = (typeof FILTERS)[number];
type SortOption = "activity" | "latest";

type StatusPanelProps = {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  loading?: boolean;
};

function StatusPanel({
  title,
  message,
  actionLabel,
  onAction,
  loading = false,
}: StatusPanelProps) {
  return (
    <View className="mx-6 mt-8 items-center rounded-3xl border border-border bg-surface p-6">
      {loading && <ActivityIndicator color="#58D6FF" />}
      <Text className="mt-3 text-center text-lg font-semibold text-textPrimary font-sans">
        {title}
      </Text>
      <Text className="mt-2 text-center text-sm leading-5 text-textMuted font-sans">
        {message}
      </Text>
      {actionLabel && onAction && (
        <Pressable
          accessibilityRole="button"
          onPress={onAction}
          className="mt-5 rounded-xl border border-accent/40 bg-accent/15 px-4 py-3"
        >
          <Text className="text-sm font-semibold text-accent font-sans">
            {actionLabel}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

function matchesFilter(
  filter: FilterOption,
  summary: NotificationAppSummary,
): boolean {
  if (filter === "All") return true;
  if (filter === "Flagged") return summary.spamFlaggedCount > 0;
  if (filter === "Analyzed") return summary.analyzedCount > 0;
  if (filter === "Skipped") return summary.skippedCount > 0;
  return summary.analysisErrorCount > 0;
}

function sortSummaries(
  summaries: NotificationAppSummary[],
  sortBy: SortOption,
): NotificationAppSummary[] {
  return [...summaries].sort((left, right) => {
    if (sortBy === "latest") {
      return (
        (right.latestNotificationAt ?? -1) -
        (left.latestNotificationAt ?? -1)
      );
    }

    return (
      right.totalObserved - left.totalObserved ||
      right.analyzedCount - left.analyzedCount ||
      (right.latestNotificationAt ?? -1) -
        (left.latestNotificationAt ?? -1)
    );
  });
}

function screenSubtitle(
  accessStatus: string,
  loadStatus: NotificationLoadStatus,
  appCount: number,
  eventCount: number,
): string {
  if (accessStatus === "checking") return "Rechecking notification access...";
  if (accessStatus !== "granted") return "On-device notification activity";
  if (loadStatus === "loading") return "Refreshing local notification history...";
  return `Monitoring active | ${eventCount} ${eventCount === 1 ? "notification" : "notifications"} across ${appCount} ${appCount === 1 ? "app" : "apps"}`;
}

function groupEventsByPackage(events: ObservedNotification[]) {
  const grouped = new Map<string, ObservedNotification[]>();

  for (const event of events) {
    const packageEvents = grouped.get(event.packageName) ?? [];
    packageEvents.push(event);
    grouped.set(event.packageName, packageEvents);
  }

  return grouped;
}

export default function AlertsScreen() {
  const insets = useSafeAreaInsets();
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;

  const accessStatus = useAlertStore((state) => state.accessStatus);
  const accessError = useAlertStore((state) => state.accessError);
  const loadStatus = useAlertStore((state) => state.loadStatus);
  const loadError = useAlertStore((state) => state.loadError);
  const summaries = useAlertStore((state) => state.summaries);
  const events = useAlertStore((state) => state.events);
  const analysisByEventKey = useAlertStore(
    (state) => state.analysisByEventKey,
  );
  const spamBannerDismissed = useAlertStore(
    (state) => state.spamBannerDismissed,
  );
  const checkAccessAndLoad = useAlertStore(
    (state) => state.checkAccessAndLoad,
  );
  const refresh = useAlertStore((state) => state.refresh);
  const openAccessSettings = useAlertStore(
    (state) => state.openAccessSettings,
  );
  const clearLocalHistory = useAlertStore(
    (state) => state.clearLocalHistory,
  );
  const analyzeEvent = useAlertStore((state) => state.analyzeEvent);
  const dismissSpamBanner = useAlertStore(
    (state) => state.dismissSpamBanner,
  );
  const privacyMode = useSettingsStore((state) => state.privacyMode);

  const [activeFilter, setActiveFilter] = useState<FilterOption>("All");
  const [sortBy, setSortBy] = useState<SortOption>("activity");

  useFocusEffect(
    useCallback(() => {
      void checkAccessAndLoad();
    }, [checkAccessAndLoad]),
  );

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState === "active") void checkAccessAndLoad();
    });

    return () => subscription.remove();
  }, [checkAccessAndLoad]);

  const eventStats = useMemo(() => {
    let possibleSpamCount = 0;
    let normalCount = 0;
    let skippedCount = 0;
    let awaitingAnalysisCount = 0;
    let analysisErrorCount = 0;
    let totalObserved = 0;
    let affectedAppCount = 0;

    for (const summary of summaries) {
      totalObserved += summary.totalObserved;
      possibleSpamCount += summary.spamFlaggedCount;
      normalCount += summary.normalCount;
      skippedCount += summary.skippedCount;
      awaitingAnalysisCount += summary.notAnalyzedCount;
      analysisErrorCount += summary.analysisErrorCount;
      if (summary.spamFlaggedCount > 0) affectedAppCount += 1;
    }

    return {
      possibleSpamCount,
      normalCount,
      skippedCount,
      awaitingAnalysisCount,
      analysisErrorCount,
      totalObserved,
      affectedAppCount,
    };
  }, [summaries]);

  const backendUnavailable = useMemo(
    () =>
      Object.values(analysisByEventKey).some(
        (analysis) =>
          analysis.status === "error" &&
          analysis.kind === "backend_unavailable",
      ),
    [analysisByEventKey],
  );

  const eventsByPackage = useMemo(
    () => groupEventsByPackage(events),
    [events],
  );

  const filteredApps = useMemo(
    () =>
      sortSummaries(
        summaries.filter((summary) => matchesFilter(activeFilter, summary)),
        sortBy,
      ),
    [activeFilter, sortBy, summaries],
  );

  const confirmClearHistory = useCallback(() => {
    Alert.alert(
      "Clear notification history?",
      "This removes locally stored notification events and their event-level analysis results from AdShield.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Clear",
          style: "destructive",
          onPress: () => {
            void clearLocalHistory();
          },
        },
      ],
    );
  }, [clearLocalHistory]);

  const pageHeading = (
    <View className="px-6 pt-6">
      <Text className="font-heading text-2xl font-bold text-textPrimary">
        Notification Monitor
      </Text>
      <Text className="mt-0.5 text-sm text-textMuted font-sans">
        {screenSubtitle(
          accessStatus,
          loadStatus,
          summaries.length,
          eventStats.totalObserved,
        )}
      </Text>
    </View>
  );

  const renderStatusScreen = (panel: ReactNode) => (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top"]}
    >
      {pageHeading}
      {panel}
    </SafeAreaView>
  );

  if (
    (accessStatus === "unknown" || accessStatus === "checking") &&
    summaries.length === 0
  ) {
    return renderStatusScreen(
      <StatusPanel
        loading
        title="Checking notification access"
        message="AdShield is checking whether on-device notification monitoring is available."
      />,
    );
  }

  if (accessStatus === "not_granted") {
    return renderStatusScreen(
      <StatusPanel
        title="Notification access is required"
        message="Grant Android Notification Access so AdShield can observe notification activity locally. Nothing is uploaded automatically."
        actionLabel="Open notification access settings"
        onAction={() => void openAccessSettings()}
      />,
    );
  }

  if (accessStatus === "unavailable") {
    return renderStatusScreen(
      <StatusPanel
        title="Notification monitoring is unavailable"
        message={
          accessError ??
          "This Android build does not provide the notification monitor."
        }
        actionLabel="Check again"
        onAction={() => void checkAccessAndLoad()}
      />,
    );
  }

  if (accessStatus === "error") {
    return renderStatusScreen(
      <StatusPanel
        title="Unable to check notification access"
        message={accessError ?? "Please try checking notification access again."}
        actionLabel="Try again"
        onAction={() => void checkAccessAndLoad()}
      />,
    );
  }

  if (
    (loadStatus === "idle" || loadStatus === "loading") &&
    summaries.length === 0
  ) {
    return renderStatusScreen(
      <StatusPanel
        loading
        title="Loading local notification activity"
        message="Notification history remains on this device while AdShield prepares event summaries."
      />,
    );
  }

  if (loadStatus === "error" && summaries.length === 0) {
    return renderStatusScreen(
      <StatusPanel
        title="Notification history could not be loaded"
        message={loadError ?? "Unable to read locally observed notifications."}
        actionLabel="Retry"
        onAction={() => void refresh()}
      />,
    );
  }

  if (loadStatus === "success" && summaries.length === 0) {
    return renderStatusScreen(
      <StatusPanel
        title="No notifications observed yet"
        message="Monitoring is active. New notification events will appear after Android delivers them to AdShield."
        actionLabel="Refresh"
        onAction={() => void refresh()}
      />,
    );
  }

  const header = (
    <View className="px-6 pb-3 pt-6">
      <Text className="font-heading text-2xl font-bold text-textPrimary">
        Notification Monitor
      </Text>
      <Text className="mt-0.5 text-sm text-textMuted font-sans">
        {screenSubtitle(
          accessStatus,
          loadStatus,
          summaries.length,
          eventStats.totalObserved,
        )}
      </Text>

      <View className="mt-4 rounded-2xl border border-accent/20 bg-accent/5 p-4">
        <Text className="text-xs leading-5 text-textMuted font-sans">
          Notification history stays on this device. Only the eligible
          notification text you explicitly choose is sent for analysis; app
          cards show event counts, not an app classification.
        </Text>
      </View>

      {loadError && (
        <View className="mt-4 rounded-2xl border border-warning/30 bg-warning/10 p-4">
          <Text className="text-sm font-semibold text-warning font-sans">
            Local refresh failed
          </Text>
          <Text className="mt-1 text-xs text-textMuted font-sans">
            {loadError}
          </Text>
        </View>
      )}

      {backendUnavailable && (
        <View className="mt-4 rounded-2xl border border-warning/30 bg-warning/10 p-4">
          <Text className="text-sm font-semibold text-warning font-sans">
            Backend unavailable
          </Text>
          <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
            Local monitoring is still active. Retry this notification after
            the backend connection is restored.
          </Text>
        </View>
      )}

      {eventStats.possibleSpamCount > 0 && !spamBannerDismissed && (
        <View className="mt-4">
          <SpamBanner
            flaggedNotificationCount={eventStats.possibleSpamCount}
            affectedAppCount={eventStats.affectedAppCount}
            onClose={dismissSpamBanner}
          />
        </View>
      )}

      <View className="mt-4 flex-row gap-3">
        <Pressable
          accessibilityRole="button"
          disabled={loadStatus === "loading"}
          onPress={() => void refresh()}
          className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2"
        >
          <Text className="text-xs font-semibold text-accent font-sans">
            {loadStatus === "loading" ? "Refreshing..." : "Refresh"}
          </Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          disabled={events.length === 0}
          onPress={confirmClearHistory}
          className={`rounded-xl border px-4 py-2 ${
            events.length > 0
              ? "border-danger/30 bg-danger/10"
              : "border-border bg-surfaceHigh opacity-50"
          }`}
        >
          <Text
            className={`text-xs font-semibold font-sans ${
              events.length > 0 ? "text-danger" : "text-textMuted"
            }`}
          >
            Clear history
          </Text>
        </Pressable>
      </View>

      <View className="mt-6">
        <StatBar {...eventStats} />
      </View>

      <View className="mt-6 flex-row gap-3">
        {(["activity", "latest"] as const).map((option) => {
          const active = sortBy === option;
          return (
            <Pressable
              key={option}
              accessibilityRole="button"
              onPress={() => setSortBy(option)}
              className={`rounded-full border px-4 py-2 ${
                active
                  ? "border-accent/30 bg-accent/15"
                  : "border-border bg-surfaceHigh"
              }`}
            >
              <Text
                className={`text-xs font-semibold font-sans ${
                  active ? "text-accent" : "text-textMuted"
                }`}
              >
                {option === "activity" ? "Most events" : "Latest"}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View className="mt-4 flex-row flex-wrap gap-2">
        {FILTERS.map((filter) => {
          const active = filter === activeFilter;
          return (
            <Pressable
              key={filter}
              accessibilityRole="button"
              onPress={() => setActiveFilter(filter)}
              className={`rounded-full border px-3 py-1 ${
                active
                  ? "border-accent/40 bg-accent/15"
                  : "border-border bg-surfaceHigh"
              }`}
            >
              <Text
                className={`text-xs font-medium font-sans ${
                  active ? "text-accent" : "text-textMuted"
                }`}
              >
                {filter}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text className="mt-6 text-base font-semibold text-textPrimary font-sans">
        Observed app summaries
      </Text>
    </View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top"]}
    >
      <FlatList
        data={filteredApps}
        keyExtractor={(item) => item.packageName}
        ListHeaderComponent={header}
        refreshControl={
          <RefreshControl
            refreshing={loadStatus === "loading"}
            onRefresh={() => void refresh()}
            tintColor="#58D6FF"
          />
        }
        contentContainerStyle={{ paddingBottom: 32 + contentPaddingBottom }}
        ListEmptyComponent={
          <View className="px-6 py-8">
            <Text className="text-sm text-textMuted font-sans">
              No app summaries contain notification events matching this filter.
            </Text>
          </View>
        }
        renderItem={({ item, index }) => (
          <View className="px-6 pb-3">
            <NotificationListItem
              summary={item}
              events={eventsByPackage.get(item.packageName) ?? []}
              analysisByEventKey={analysisByEventKey}
              rank={index + 1}
              privacyMode={privacyMode}
              onAnalyzeEvent={(eventKey) => void analyzeEvent(eventKey)}
            />
          </View>
        )}
      />
    </SafeAreaView>
  );
}
