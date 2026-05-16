import { useMemo, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import NotificationListItem from "../../components/alerts/NotificationListItem";
import SpamBanner from "../../components/alerts/SpamBanner";
import StatBar from "../../components/alerts/StatBar";
import { notificationApps } from "../../lib/mockData";
import { useAlertStore } from "../../store/useAlertStore";

const filters = ["All Apps", "Spam", "Suspicious", "Normal"];
const filterMap = {
  Spam: "spam",
  Suspicious: "suspicious",
  Normal: "normal",
} as const;

type SortOption = "frequency" | "score";

export default function AlertsScreen() {
  const insets = useSafeAreaInsets();
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;

  const spamBannerDismissed = useAlertStore(
    (state) => state.spamBannerDismissed,
  );
  const dismissSpamBanner = useAlertStore((state) => state.dismissSpamBanner);
  const [activeFilter, setActiveFilter] =
    useState<(typeof filters)[number]>("All Apps");
  const [sortBy, setSortBy] = useState<SortOption>("score");

  const stats = useMemo(() => {
    const spamApps = notificationApps.filter(
      (app) => app.tag === "spam",
    ).length;
    const suspiciousApps = notificationApps.filter(
      (app) => app.tag === "suspicious",
    ).length;
    const totalNotifs = notificationApps.reduce(
      (sum, app) => sum + app.count,
      0,
    );
    const spamNotifs = notificationApps
      .filter((app) => app.tag === "spam")
      .reduce((sum, app) => sum + app.count, 0);
    const suspiciousNotifs = notificationApps
      .filter((app) => app.tag === "suspicious")
      .reduce((sum, app) => sum + app.count, 0);
    const normalNotifs = notificationApps
      .filter((app) => app.tag === "normal")
      .reduce((sum, app) => sum + app.count, 0);

    return {
      spamApps,
      suspiciousApps,
      totalNotifs,
      spamNotifs,
      suspiciousNotifs,
      normalNotifs,
    };
  }, []);

  const filteredApps = useMemo(() => {
    const filtered =
      activeFilter === "All Apps"
        ? notificationApps
        : notificationApps.filter(
            (app) =>
              app.tag === filterMap[activeFilter as keyof typeof filterMap],
          );

    return [...filtered].sort((a, b) =>
      sortBy === "frequency" ? b.count - a.count : b.score - a.score,
    );
  }, [activeFilter, sortBy]);

  const header = (
    <View className="px-6 pt-6 pb-3">
      <Text className="font-heading text-2xl font-bold text-textPrimary">
        Notification Monitor
      </Text>
      <Text className="mt-0.5 text-sm text-textMuted font-sans">
        Last 24 hours · 10 apps monitored
      </Text>

      {!spamBannerDismissed && (
        <View className="mt-6">
          <SpamBanner onClose={dismissSpamBanner} />
        </View>
      )}

      <View className="mt-6">
        <StatBar
          spamApps={stats.spamApps}
          suspiciousApps={stats.suspiciousApps}
          totalNotifs={stats.totalNotifs}
          spamNotifs={stats.spamNotifs}
          suspiciousNotifs={stats.suspiciousNotifs}
          normalNotifs={stats.normalNotifs}
        />
      </View>

      <View className="mt-6 flex-row gap-3">
        <Pressable
          onPress={() => setSortBy("frequency")}
          className={`rounded-full border px-4 py-2 ${
            sortBy === "frequency"
              ? "border-accent/30 bg-accent/15"
              : "border-border bg-surfaceHigh"
          }`}
        >
          <Text
            className={`text-xs font-semibold font-sans ${
              sortBy === "frequency" ? "text-accent" : "text-textMuted"
            }`}
          >
            Frequency
          </Text>
        </Pressable>
        <Pressable
          onPress={() => setSortBy("score")}
          className={`rounded-full border px-4 py-2 ${
            sortBy === "score"
              ? "border-accent/30 bg-accent/15"
              : "border-border bg-surfaceHigh"
          }`}
        >
          <Text
            className={`text-xs font-semibold font-sans ${
              sortBy === "score" ? "text-accent" : "text-textMuted"
            }`}
          >
            Spam Score
          </Text>
        </Pressable>
      </View>

      <View className="mt-4 flex-row gap-2">
        {filters.map((filter) => {
          const active = filter === activeFilter;
          const activeStyles =
            filter === "All Apps"
              ? "bg-accent/15 border-accent/40"
              : filter === "Spam"
                ? "bg-danger/15 border-danger/40"
                : filter === "Suspicious"
                  ? "bg-warning/15 border-warning/40"
                  : "bg-safe/15 border-safe/40";
          const activeText =
            filter === "All Apps"
              ? "text-accent"
              : filter === "Spam"
                ? "text-danger"
                : filter === "Suspicious"
                  ? "text-warning"
                  : "text-safe";
          return (
            <Pressable
              key={filter}
              onPress={() => setActiveFilter(filter)}
              className={`rounded-full px-3 py-1 border ${
                active ? activeStyles : "bg-surfaceHigh border-border"
              }`}
            >
              <Text
                className={`text-xs font-medium ${
                  active ? activeText : "text-textMuted"
                } font-sans`}
              >
                {filter}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text className="mt-6 text-base font-semibold text-textPrimary font-sans">
        Ranked apps
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
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingBottom: 32 + contentPaddingBottom }}
        ListEmptyComponent={
          <View className="px-6 py-8">
            <Text className="text-sm text-textMuted font-sans">
              No apps match this filter.
            </Text>
          </View>
        }
        renderItem={({ item, index }) => (
          <View className="px-6 pb-3">
            <NotificationListItem item={item} rank={index + 1} />
          </View>
        )}
      />
    </SafeAreaView>
  );
}
