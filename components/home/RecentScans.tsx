import { FlatList, Pressable, Text, View } from "react-native";

import type { ScanHistoryEntry } from "../../types/scan-history";
import { displayHistoryName } from "../../lib/privacy/displayIdentity";
import Badge, { type BadgeVariant } from "../ui/Badge";

type RecentScansProps = {
  data: ScanHistoryEntry[];
  status: "idle" | "loading" | "ready" | "error";
  error?: string | null;
  onSelect(item: ScanHistoryEntry): void;
  onRetry?(): void;
  privacyMode?: boolean;
};

const badgeVariant = (level: string): BadgeVariant => {
  if (level === "Safe") return "safe";
  if (level === "High Risk") return "dangerous";
  return "caution";
};

const cardColor = (level: string) => {
  if (level === "Safe") return "#166534";
  if (level === "High Risk") return "#991B1B";
  return "#92400E";
};

const initial = (item: ScanHistoryEntry, privacyMode: boolean) => {
  const match = displayHistoryName(item, privacyMode).match(/[A-Za-z0-9]/);
  return match ? match[0].toUpperCase() : "A";
};

export default function RecentScans({
  data,
  status,
  error,
  onSelect,
  onRetry,
  privacyMode = false,
}: RecentScansProps) {
  if ((status === "idle" || status === "loading") && data.length === 0) {
    return (
      <View className="mx-6 mt-3 rounded-2xl border border-border bg-surfaceHigh/80 px-4 py-5">
        <Text className="text-center text-sm text-textMuted font-sans">
          Loading saved scan history...
        </Text>
      </View>
    );
  }

  if (status === "error" && data.length === 0) {
    return (
      <View className="mx-6 mt-3 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-5">
        <Text className="text-center text-sm font-semibold text-danger font-sans">
          Scan history could not be loaded
        </Text>
        <Text className="mt-2 text-center text-xs leading-5 text-textMuted font-sans">
          {error ?? "Your saved scan summaries remain on this device."}
        </Text>
        {onRetry ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Retry loading scan history"
            onPress={onRetry}
            className="mt-3 self-center rounded-xl border border-accent/40 bg-accent/10 px-4 py-2">
            <Text className="text-xs font-semibold text-accent font-sans">
              Try again
            </Text>
          </Pressable>
        ) : null}
      </View>
    );
  }

  if (data.length === 0) {
    return (
      <View className="mx-6 mt-3 rounded-2xl border border-border bg-surfaceHigh/80 px-4 py-5">
        <Text className="text-center text-sm font-semibold text-textPrimary font-sans">
          No completed scans yet
        </Text>
        <Text className="mt-2 text-center text-xs leading-5 text-textMuted font-sans">
          Successful APK and installed-app analyses will appear here.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={data}
      horizontal
      keyExtractor={(item) => item.id}
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{
        paddingHorizontal: 24,
        paddingTop: 10,
        paddingBottom: 8,
      }}
      renderItem={({ item }) => (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Open saved scan for ${displayHistoryName(item, privacyMode)}`}
          className="mr-3 items-center"
          onPress={() => onSelect(item)}>
          <View
            className="h-14 w-14 items-center justify-center rounded-2xl border border-border"
            style={{ backgroundColor: cardColor(item.overallLevel) }}>
            <Text className="text-lg font-bold text-white font-sans">
              {initial(item, privacyMode)}
            </Text>
          </View>
          <Text
            className="mt-2 max-w-24 text-xs font-semibold text-textPrimary font-sans"
            numberOfLines={1}>
            {displayHistoryName(item, privacyMode)}
          </Text>
          <Badge
            variant={badgeVariant(item.overallLevel)}
            label={item.overallLevel}
            className="mt-1"
          />
          <Text className="mt-1 text-[10px] text-textDim font-sans">
            {item.overallScore} / 100
          </Text>
        </Pressable>
      )}
    />
  );
}
