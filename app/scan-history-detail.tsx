import { router, useLocalSearchParams } from "expo-router";
import { ArrowLeft, FileClock, ShieldAlert, ShieldCheck } from "lucide-react-native";
import { useEffect } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
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

const binaryLabel = (entry: ScanHistoryEntry) =>
  entry.binaryResult === "Malicious"
    ? "Malware characteristics detected"
    : "No malware indicated";

const categoryLabel = (entry: ScanHistoryEntry) => {
  switch (entry.threatCategoryStatus) {
    case "classified":
      return entry.threatCategory ?? "Unavailable";
    case "uncertain":
      return "Uncertain";
    case "not_applicable":
      return "Not applicable";
    case "unavailable":
      return "Unavailable";
  }
};

const formattedTimestamp = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
};

function Header() {
  return (
    <View className="mb-5 flex-row items-center gap-3">
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go back"
        onPress={() => router.back()}
        className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh">
        <ArrowLeft size={18} color="#8EA0C6" />
      </Pressable>
      <View className="flex-1">
        <Text className="font-heading text-2xl text-textPrimary">
          Saved Scan Summary
        </Text>
        <Text className="text-xs text-textMuted font-sans">
          Stored locally on this device
        </Text>
      </View>
    </View>
  );
}

export default function ScanHistoryDetailScreen() {
  const privacyMode = useSettingsStore((state) => state.privacyMode);
  const params = useLocalSearchParams<{ id?: string | string[] }>();
  const id = typeof params.id === "string" ? params.id : null;
  const entries = useScanHistoryStore((state) => state.entries);
  const status = useScanHistoryStore((state) => state.status);
  const error = useScanHistoryStore((state) => state.error);
  const loadHistory = useScanHistoryStore((state) => state.loadHistory);
  const getEntryById = useScanHistoryStore((state) => state.getEntryById);
  const entry = id ? getEntryById(id) : undefined;

  useEffect(() => {
    if (status === "idle") void loadHistory();
  }, [loadHistory, status]);

  // Keep this screen subscribed so it rerenders after asynchronous hydration.
  void entries;

  if ((status === "idle" || status === "loading") && !entry) {
    return (
      <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
        <View className="px-6 pt-4">
          <Header />
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <ActivityIndicator size="large" color="#58D6FF" />
          <Text className="mt-4 text-sm text-textMuted font-sans">
            Loading saved summary...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!entry) {
    return (
      <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
        <View className="px-6 pt-4">
          <Header />
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <FileClock size={42} color="#8EA0C6" />
          <Text className="mt-5 text-center font-heading text-xl text-textPrimary">
            Saved scan not found
          </Text>
          <Text className="mt-2 text-center text-sm leading-5 text-textMuted font-sans">
            {status === "error"
              ? error ?? "The local scan history could not be loaded."
              : "This summary may have been deleted from local history."}
          </Text>
          {status === "error" ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Retry loading scan history"
              onPress={() => void loadHistory(true)}
              className="mt-5 rounded-2xl bg-accent px-6 py-3">
              <Text className="font-semibold text-background font-sans">
                Try again
              </Text>
            </Pressable>
          ) : null}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 48 }}>
        <Header />

        <Card className="bg-surfaceHigh/80">
          <View className="flex-row items-start justify-between gap-3">
            <View className="flex-1">
              <Text className="text-lg font-semibold text-textPrimary font-sans">
                {displayHistoryName(entry, privacyMode)}
              </Text>
              <Text className="mt-1 text-xs text-textMuted font-sans">
                {displayHistoryIdentifier(entry, privacyMode)}
              </Text>
              <Text className="mt-2 text-xs text-textDim font-sans">
                {entry.source} - {formattedTimestamp(entry.timestamp)}
              </Text>
            </View>
            <Badge
              variant={riskVariant(entry.overallLevel)}
              label={entry.overallLevel}
            />
          </View>
        </Card>

        <Card className="mt-4 items-center bg-surfaceHigh/80">
          {entry.binaryResult === "Malicious" ? (
            <ShieldAlert size={25} color="#EF4444" />
          ) : (
            <ShieldCheck size={25} color="#22C55E" />
          )}
          <Text className="mt-3 text-4xl font-bold text-textPrimary font-sans">
            {entry.overallScore}
          </Text>
          <Text className="mt-1 text-xs text-textMuted font-sans">
            Overall assessment out of 100
          </Text>
        </Card>

        <Card className="mt-4 bg-surfaceHigh/80">
          <Text className="font-heading text-base text-textPrimary">
            Saved assessment
          </Text>
          <View className="mt-4">
            <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
              Binary malware assessment
            </Text>
            <Text className="mt-1 text-sm font-semibold text-textPrimary font-sans">
              {binaryLabel(entry)}
            </Text>
          </View>
          <View className="mt-4">
            <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
              Threat category
            </Text>
            <Text className="mt-1 text-sm font-semibold text-textPrimary font-sans">
              {categoryLabel(entry)}
            </Text>
          </View>
          <View className="mt-4">
            <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
              Install source
            </Text>
            <Text className="mt-1 text-sm text-textPrimary font-sans">
              {entry.installSourceDisplay}
            </Text>
          </View>
        </Card>

        <Text className="mt-4 text-center text-xs leading-5 text-textDim font-sans">
          This is the summary saved when the scan completed. Viewing it does not rerun analysis or contact the backend.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
