import { StatusBar } from "expo-status-bar";
import { router, useFocusEffect } from "expo-router";
import { Bell, ChevronRight, Package, ShieldCheck, Smartphone } from "lucide-react-native";
import { useCallback, useMemo } from "react";
import { Pressable, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import ActivityFeed from "../../components/home/ActivityFeed";
import HomeStats from "../../components/home/HomeStats";
import RecentScans from "../../components/home/RecentScans";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import {
  deriveHomeActivity,
  deriveHomeMetrics,
  latestScanSummary,
  notificationAccessPresentation,
} from "../../lib/home/deriveHomeDashboard";
import { useAlertStore } from "../../store/useAlertStore";
import { useScanHistoryStore } from "../../store/useScanHistoryStore";
import { useSettingsStore } from "../../store/useSettingsStore";

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const historyEntries = useScanHistoryStore((state) => state.entries);
  const historyStatus = useScanHistoryStore((state) => state.status);
  const historyError = useScanHistoryStore((state) => state.error);
  const loadHistory = useScanHistoryStore((state) => state.loadHistory);
  const notificationAccessStatus = useAlertStore((state) => state.accessStatus);
  const notificationLoadStatus = useAlertStore((state) => state.loadStatus);
  const notificationEvents = useAlertStore((state) => state.events);
  const notificationAnalyses = useAlertStore(
    (state) => state.analysisByEventKey,
  );
  const notificationAccessChanges = useAlertStore(
    (state) => state.accessChanges,
  );
  const checkNotificationAccess = useAlertStore(
    (state) => state.checkAccessAndLoad,
  );
  const privacyMode = useSettingsStore((state) => state.privacyMode);
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;
  const recentHistory = historyEntries.slice(0, 5);
  const dashboardMetrics = useMemo(
    () => deriveHomeMetrics(historyEntries, historyStatus),
    [historyEntries, historyStatus],
  );
  const accessPresentation = useMemo(
    () => notificationAccessPresentation(notificationAccessStatus),
    [notificationAccessStatus],
  );
  const securityActivity = useMemo(
    () =>
      deriveHomeActivity({
        historyEntries,
        notificationEvents,
        analysisByEventKey: notificationAnalyses,
        accessChanges: notificationAccessChanges,
        privacyMode,
      }),
    [
      historyEntries,
      notificationAccessChanges,
      notificationAnalyses,
      notificationEvents,
      privacyMode,
    ],
  );
  const activityLoading =
    historyStatus === "idle" ||
    historyStatus === "loading" ||
    notificationAccessStatus === "checking" ||
    (notificationAccessStatus === "granted" &&
      notificationLoadStatus === "loading");

  useFocusEffect(
    useCallback(() => {
      if (historyStatus === "idle") {
        void loadHistory();
      }
    }, [historyStatus, loadHistory]),
  );

  useFocusEffect(
    useCallback(() => {
      void checkNotificationAccess();
    }, [checkNotificationAccess]),
  );

  const header = (
    <View>
      <StatusBar style="light" />
      <View className="px-6 pt-6 relative">
        <View className="absolute -left-12 -top-10 h-32 w-32 rounded-full bg-accent/10" />
        <View className="absolute right-0 top-10 h-52 w-52 rounded-full bg-accent/5" />
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center gap-3">
            <View className="h-11 w-11 items-center justify-center rounded-2xl border border-border bg-surfaceHigh">
              <ShieldCheck size={22} color="#58D6FF" />
            </View>
            <View>
              <Text className="font-heading text-xl text-textPrimary">
                AdShield
              </Text>
              <Text className="text-xs text-textMuted font-sans">
                AI-Powered Protection
              </Text>
            </View>
          </View>
          <Pressable
            onPress={() => router.push("/(tabs)/alerts")}
            className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
          >
            <Bell size={18} color="#8EA0C6" />
          </Pressable>
        </View>

        <Pressable onPress={() => router.push("/(tabs)/scan")} className="mt-6">
          <Card
            className="overflow-hidden border-accent/30 bg-surfaceHigh"
            glowColor="#58D6FF"
          >
            <View className="absolute -right-10 -top-12 h-28 w-28 rounded-full bg-accent/20" />
            <View className="absolute left-2 top-10 h-20 w-20 rounded-full bg-accent/10" />
            <View className="flex-row items-center justify-between">
              <View className="flex-row items-center gap-3 flex-1">
                <View className="h-12 w-12 items-center justify-center rounded-2xl bg-accent/20">
                  <Package size={22} color="#58D6FF" />
                </View>
                <View className="flex-1">
                  <Text className="text-sm font-semibold text-textPrimary font-sans">
                    Scan APK File
                  </Text>
                  <Text className="mt-1 text-xs text-textMuted font-sans">
                    Detect adware & hidden risks
                  </Text>
                </View>
              </View>
              <View className="h-9 w-9 items-center justify-center rounded-full border border-accent/40 bg-accent/20">
                <ChevronRight size={18} color="#58D6FF" />
              </View>
            </View>
          </Card>
        </Pressable>

        <Pressable onPress={() => router.push("/installed-apps")} className="mt-4">
          <Card className="border-border bg-surfaceHigh">
            <View className="flex-row items-center justify-between">
              <View className="flex-row items-center gap-3 flex-1">
                <View className="h-12 w-12 items-center justify-center rounded-2xl bg-accent/15">
                  <Smartphone size={22} color="#58D6FF" />
                </View>
                <View className="flex-1">
                  <Text className="text-sm font-semibold text-textPrimary font-sans">
                    Scan Installed App
                  </Text>
                  <Text className="mt-1 text-xs text-textMuted font-sans">
                    Review a launcher-visible Android app
                  </Text>
                </View>
              </View>
              <View className="h-9 w-9 items-center justify-center rounded-full border border-accent/30 bg-accent/10">
                <ChevronRight size={18} color="#58D6FF" />
              </View>
            </View>
          </Card>
        </Pressable>

        <Card
          className="mt-4 flex-row items-center justify-between border-accent/30 bg-surfaceHigh/80"
          glowColor={notificationAccessStatus === "granted" ? "#22C55E" : "#58D6FF"}
        >
          <View className="flex-row items-center gap-4 w-full">
            <View className="h-10 w-10 items-center justify-center rounded-2xl bg-safe/15">
              <ShieldCheck size={18} color={accessPresentation.iconColor} />
            </View>
            <View className="flex-1">
              <Badge
                variant={accessPresentation.badgeVariant}
                label={accessPresentation.badgeLabel}
                className="self-start"
              />
              <Text className="mt-2 text-base font-semibold text-textPrimary leading-tight font-sans">
                {accessPresentation.title}
              </Text>
              <Text className="text-xs text-textMuted mt-0.5 font-sans">
                {latestScanSummary(dashboardMetrics)}
              </Text>
            </View>
            <View className="items-center rounded-2xl border border-border bg-surfaceHigh px-3 py-2">
              <Text className="text-xl font-bold text-accent mb-0.5 font-sans">
                {dashboardMetrics.completedScans ?? "—"}
              </Text>
              <Text className="text-[10px] text-textDim font-sans">
                scans completed
              </Text>
            </View>
          </View>
        </Card>

        <View className="mt-4">
          <HomeStats
            safeResults={dashboardMetrics.safeResults}
            threats={dashboardMetrics.threats}
            latestStatus={dashboardMetrics.latestScanStatus}
          />
        </View>
      </View>

      <View className="px-6 pt-6 flex-row items-center justify-between">
        <Text className="text-base font-semibold text-textPrimary font-sans">
          Recently Scanned
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="View all saved scans"
          onPress={() => router.push("/scan-history")}>
          <Text className="text-xs text-accent font-sans">View all</Text>
        </Pressable>
      </View>
      <RecentScans
        data={recentHistory}
        status={historyStatus}
        error={historyError}
        privacyMode={privacyMode}
        onRetry={() => void loadHistory(true)}
        onSelect={(item) =>
          router.push({
            pathname: "/scan-history-detail",
            params: { id: item.id },
          })
        }
      />

      <Text className="px-6 pt-6 text-base font-semibold text-textPrimary font-sans">
        Recent Activity
      </Text>
    </View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top"]}
    >
      <ActivityFeed
        data={securityActivity}
        header={header}
        contentPaddingBottom={contentPaddingBottom}
        loading={activityLoading}
      />
    </SafeAreaView>
  );
}
