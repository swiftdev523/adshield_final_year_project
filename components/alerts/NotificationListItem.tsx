import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { getNotificationEventPresentationState } from "../../lib/notifications/eventSummary";
import {
  displayAppName,
  displayPackageName,
} from "../../lib/privacy/displayIdentity";
import type {
  NotificationAppSummary,
  NotificationEligibilityReason,
  NotificationEventAnalysisState,
  ObservedNotification,
} from "../../types/notifications";
import Badge, { type BadgeVariant } from "../ui/Badge";

type NotificationListItemProps = {
  summary: NotificationAppSummary;
  events: ObservedNotification[];
  analysisByEventKey: Record<string, NotificationEventAnalysisState>;
  rank?: number;
  privacyMode?: boolean;
  onAnalyzeEvent: (eventKey: string) => void;
};

const iconPalette = [
  "#58D6FF",
  "#22C55E",
  "#F59E0B",
  "#8B5CF6",
  "#FB7185",
  "#34D399",
];

function colorForPackage(packageName: string): string {
  const hash = [...packageName].reduce(
    (value, character) => (value * 31 + character.charCodeAt(0)) >>> 0,
    0,
  );
  return iconPalette[hash % iconPalette.length];
}

function formatTimestamp(timestamp: number | null): string {
  if (timestamp === null) return "No notification timestamp";
  return new Date(timestamp).toLocaleString();
}

function pluralize(count: number, singular: string, plural = `${singular}s`) {
  return count === 1 ? singular : plural;
}

function skippedReasonLabel(reason: NotificationEligibilityReason): string {
  switch (reason) {
    case "empty_content":
      return "No meaningful notification text was available.";
    case "sensitive_content":
      return "Sensitive notification content was protected.";
    case "ongoing_notification":
      return "Ongoing background/status notification.";
    case "foreground_service":
      return "Foreground service status notification.";
    case "service_notification":
      return "Service status notification.";
    case "progress_notification":
      return "Progress/status notification.";
    case "group_summary":
      return "Grouped notification summary.";
    case "generic_background_status":
      return "Background/service status notification.";
    case "metadata_unavailable":
      return "Notification metadata was not available for safe analysis.";
    case "meaningful_content":
      return "Eligible for notification text analysis.";
  }

  return "This notification was not eligible for text analysis.";
}

function eventPresentation(
  event: ObservedNotification,
  analysisByEventKey: Record<string, NotificationEventAnalysisState>,
): {
  label: string;
  variant: BadgeVariant;
  explanation: string;
} {
  const state = getNotificationEventPresentationState(
    event,
    analysisByEventKey,
  );
  const analysis = analysisByEventKey[event.eventKey];

  if (state === "spam") {
    return {
      label: "POSSIBLE SPAM",
      variant: "spam",
      explanation: "This result applies only to this notification.",
    };
  }

  if (state === "normal") {
    return {
      label: "NORMAL",
      variant: "normal",
      explanation: "This result applies only to this notification.",
    };
  }

  if (state === "analyzing") {
    return {
      label: "ANALYZING",
      variant: "caution",
      explanation: "Analyzing this notification event only.",
    };
  }

  if (state === "analysis_error") {
    return {
      label: "ANALYSIS ERROR",
      variant: "caution",
      explanation:
        analysis?.status === "error"
          ? analysis.message
          : "This notification could not be analyzed.",
    };
  }

  if (!event.eligibility.eligible) {
    return {
      label: "NOT ANALYZED",
      variant: "caution",
      explanation: skippedReasonLabel(event.eligibility.reason),
    };
  }

  return {
    label: "NOT ANALYZED",
    variant: "caution",
    explanation: "Eligible for notification text analysis.",
  };
}

type NotificationEventRowProps = {
  event: ObservedNotification;
  analysisByEventKey: Record<string, NotificationEventAnalysisState>;
  onAnalyzeEvent: (eventKey: string) => void;
};

function NotificationEventRow({
  event,
  analysisByEventKey,
  onAnalyzeEvent,
}: NotificationEventRowProps) {
  const analysis = analysisByEventKey[event.eventKey];
  const presentationState = getNotificationEventPresentationState(
    event,
    analysisByEventKey,
  );
  const presentation = eventPresentation(event, analysisByEventKey);
  const canAnalyze =
    event.eligibility.eligible &&
    presentationState !== "analyzing" &&
    presentationState !== "spam" &&
    presentationState !== "normal";

  return (
    <View
      accessibilityLabel={`Notification event from ${formatTimestamp(event.postedAt)}: ${presentation.label}`}
      className="border-t border-border/70 px-4 py-3"
    >
      <View className="flex-row items-start justify-between gap-3">
        <View className="min-w-0 flex-1">
          <Text className="text-xs font-semibold text-textPrimary font-sans">
            {formatTimestamp(event.postedAt)}
          </Text>
          <Text className="mt-1 text-[11px] leading-5 text-textMuted font-sans">
            {presentation.explanation}
          </Text>
        </View>
        <Badge variant={presentation.variant} label={presentation.label} />
      </View>

      {canAnalyze && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${presentationState === "analysis_error" ? "Retry analysis for" : "Analyze"} notification from ${formatTimestamp(event.postedAt)}`}
          onPress={() => onAnalyzeEvent(event.eventKey)}
          className="mt-3 self-start rounded-xl border border-accent/40 bg-accent/15 px-3 py-2"
        >
          <Text className="text-xs font-semibold text-accent font-sans">
            {analysis?.status === "error" ? "Retry analysis" : "Analyze"}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

export default function NotificationListItem({
  summary,
  events,
  analysisByEventKey,
  rank,
  privacyMode = false,
  onAnalyzeEvent,
}: NotificationListItemProps) {
  const [expanded, setExpanded] = useState(false);
  const iconColor = colorForPackage(summary.packageName);
  const displayName = displayAppName(
    summary.appName.trim() || summary.packageName,
    privacyMode,
  );
  const packageName = displayPackageName(summary.packageName, privacyMode);
  const sortedEvents = useMemo(
    () => [...events].sort((left, right) => right.postedAt - left.postedAt),
    [events],
  );

  return (
    <View
      className="overflow-hidden rounded-2xl border border-border bg-surfaceHigh/80"
      style={{ borderLeftWidth: 4, borderLeftColor: iconColor }}
    >
      <View className="flex-row items-start gap-3 p-4">
        <View className="relative flex-shrink-0">
          <View
            className="h-10 w-10 items-center justify-center rounded-2xl"
            style={{ backgroundColor: `${iconColor}20` }}
          >
            <Text
              className="text-base font-bold font-sans"
              style={{ color: iconColor }}
            >
              {displayName.charAt(0).toUpperCase()}
            </Text>
          </View>
          {rank !== undefined && (
            <View className="absolute -left-1.5 -top-1.5 h-4 w-4 items-center justify-center rounded-full border border-border bg-surfaceHigh">
              <Text className="text-[9px] font-bold leading-none text-textMuted font-sans">
                {rank}
              </Text>
            </View>
          )}
        </View>

        <View className="min-w-0 flex-1">
          <Text className="text-sm font-semibold text-textPrimary font-sans">
            {displayName}
          </Text>
          <Text
            className="mt-0.5 text-[11px] text-textMuted font-sans"
            numberOfLines={1}
          >
            {packageName}
          </Text>
          <Text className="mt-2 text-xs text-textPrimary font-sans">
            {summary.totalObserved} {pluralize(summary.totalObserved, "notification")} observed
          </Text>
          <Text className="mt-1 text-[11px] leading-5 text-textMuted font-sans">
            {summary.analyzedCount} analyzed | {summary.spamFlaggedCount} flagged
            for review | {summary.skippedCount} skipped
          </Text>
          {summary.analysisErrorCount > 0 && (
            <Text className="text-[11px] text-warning font-sans">
              {summary.analysisErrorCount} analysis {pluralize(summary.analysisErrorCount, "error")}
            </Text>
          )}
          <Text className="mt-1 text-[11px] text-textMuted font-sans">
            Latest {formatTimestamp(summary.latestNotificationAt)}
          </Text>
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${expanded ? "Hide" : "Show"} notification events for ${displayName}`}
        onPress={() => setExpanded((value) => !value)}
        className="border-t border-border/70 px-4 py-3"
      >
        <Text className="text-xs font-semibold text-accent font-sans">
          {expanded ? "Hide notification events" : `Show notification events (${sortedEvents.length})`}
        </Text>
      </Pressable>

      {expanded &&
        sortedEvents.map((event) => (
          <NotificationEventRow
            key={event.eventKey}
            event={event}
            analysisByEventKey={analysisByEventKey}
            onAnalyzeEvent={onAnalyzeEvent}
          />
        ))}
    </View>
  );
}
