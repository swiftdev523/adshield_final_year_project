import { router, useFocusEffect } from "expo-router";
import { ArrowLeft, ChevronRight, History, Trash2 } from "lucide-react-native";
import { useCallback } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Badge, { type BadgeVariant } from "../components/ui/Badge";
import Card from "../components/ui/Card";
import {
  displayHistoryIdentifier,
  displayHistoryName,
} from "../lib/privacy/displayIdentity";
import { useScanHistoryStore } from "../store/useScanHistoryStore";
import { useSettingsStore } from "../store/useSettingsStore";
import type { ScanHistoryEntry } from "../types/scan-history";

const riskVariant = (level: string): BadgeVariant => {
  if (level === "Safe") return "safe";
  if (level === "High Risk") return "dangerous";
  return "caution";
};

const formattedTimestamp = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
};

export default function ScanHistoryScreen() {
  const privacyMode = useSettingsStore((state) => state.privacyMode);
  const entries = useScanHistoryStore((state) => state.entries);
  const status = useScanHistoryStore((state) => state.status);
  const error = useScanHistoryStore((state) => state.error);
  const loadHistory = useScanHistoryStore((state) => state.loadHistory);
  const deleteEntry = useScanHistoryStore((state) => state.deleteEntry);
  const clearHistory = useScanHistoryStore((state) => state.clearHistory);

  useFocusEffect(
    useCallback(() => {
      if (status === "idle") void loadHistory();
    }, [loadHistory, status]),
  );

  const confirmClear = () => {
    if (entries.length === 0) return;
    Alert.alert(
      "Clear scan history?",
      "This removes all locally saved scan summaries from this device. It does not change any analyzed app.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Clear history",
          style: "destructive",
          onPress: () => void clearHistory(),
        },
      ],
    );
  };

  const header = (
    <View className="px-5 pb-4 pt-2">
      <View className="flex-row items-center">
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Go back"
          onPress={() => router.back()}
          className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh">
          <ArrowLeft size={19} color="#8EA0C6" />
        </Pressable>
        <View className="ml-3 flex-1">
          <Text className="font-heading text-2xl text-textPrimary">
            Scan History
          </Text>
          <Text className="mt-0.5 text-xs text-textMuted font-sans">
            Locally saved successful scan summaries
          </Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Clear scan history"
          disabled={entries.length === 0}
          onPress={confirmClear}
          className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
          style={{ opacity: entries.length === 0 ? 0.4 : 1 }}>
          <Trash2 size={18} color="#EF4444" />
        </Pressable>
      </View>

      {status === "error" ? (
        <View className="mt-4 rounded-2xl border border-danger/30 bg-danger/10 p-4">
          <Text className="text-sm font-semibold text-danger font-sans">
            Scan history could not be loaded
          </Text>
          <Text className="mt-2 text-xs leading-5 text-textMuted font-sans">
            {error ?? "Your existing local summaries were not changed."}
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Retry loading scan history"
            onPress={() => void loadHistory(true)}
            className="mt-3 self-start rounded-xl border border-accent/40 bg-accent/10 px-4 py-2">
            <Text className="text-xs font-semibold text-accent font-sans">
              Try again
            </Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      {status === "loading" && entries.length === 0 ? (
        <View className="flex-1">
          {header}
          <View className="flex-1 items-center justify-center px-6">
            <ActivityIndicator size="large" color="#58D6FF" />
            <Text className="mt-4 text-sm text-textMuted font-sans">
              Loading saved summaries...
            </Text>
          </View>
        </View>
      ) : (
        <FlatList
          data={entries}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerStyle={{ paddingBottom: 36, flexGrow: 1 }}
          ListEmptyComponent={
            status === "error" ? null : (
              <View className="flex-1 items-center justify-center px-8 py-16">
                <View className="h-16 w-16 items-center justify-center rounded-3xl bg-surfaceHigh">
                  <History size={28} color="#58D6FF" />
                </View>
                <Text className="mt-5 text-center font-heading text-lg text-textPrimary">
                  No completed scans yet
                </Text>
                <Text className="mt-2 text-center text-sm leading-5 text-textMuted font-sans">
                  Successful APK and installed-app analyses will be saved here on this device.
                </Text>
              </View>
            )
          }
          renderItem={({ item }) => (
            <View className="px-5 pb-3">
              <Card className="bg-surfaceHigh/80">
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Open saved scan for ${displayHistoryName(item, privacyMode)}`}
                  onPress={() =>
                    router.push({
                      pathname: "/scan-history-detail",
                      params: { id: item.id },
                    })
                  }>
                  <View className="flex-row items-start justify-between gap-3">
                    <View className="flex-1">
                      <Text
                        className="text-base font-semibold text-textPrimary font-sans"
                        numberOfLines={1}>
                        {displayHistoryName(item, privacyMode)}
                      </Text>
                      <Text className="mt-1 text-xs text-textMuted font-sans">
                        {item.source} - {formattedTimestamp(item.timestamp)}
                      </Text>
                      <Text
                        className="mt-1 text-xs text-textDim font-sans"
                        numberOfLines={1}>
                        {displayHistoryIdentifier(item, privacyMode)}
                      </Text>
                    </View>
                    <ChevronRight size={19} color="#8EA0C6" />
                  </View>
                  <View className="mt-4 flex-row items-center justify-between">
                    <Badge
                      variant={riskVariant(item.overallLevel)}
                      label={item.overallLevel}
                    />
                    <Text className="text-sm font-semibold text-textPrimary font-sans">
                      {item.overallScore} / 100
                    </Text>
                  </View>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Delete saved scan for ${displayHistoryName(item, privacyMode)}`}
                  onPress={() => void deleteEntry(item.id)}
                  className="mt-4 flex-row items-center justify-center rounded-xl border border-danger/30 bg-danger/10 py-2.5">
                  <Trash2 size={15} color="#EF4444" />
                  <Text className="ml-2 text-xs font-semibold text-danger font-sans">
                    Delete
                  </Text>
                </Pressable>
              </Card>
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}
