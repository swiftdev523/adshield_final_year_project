import { ArrowLeft, RefreshCw, Search } from "lucide-react-native";
import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import InstalledAppListItem from "../components/installed-apps/InstalledAppListItem";
import { useInstalledAppsStore } from "../store/useInstalledAppsStore";
import type { InstalledAppFilter } from "../types/installed-apps";

export default function InstalledAppsScreen() {
  const apps = useInstalledAppsStore((state) => state.apps);
  const status = useInstalledAppsStore((state) => state.inventoryStatus);
  const error = useInstalledAppsStore((state) => state.inventoryError);
  const loadApps = useInstalledAppsStore((state) => state.loadApps);
  const refreshApps = useInstalledAppsStore((state) => state.refreshApps);
  const selectApp = useInstalledAppsStore((state) => state.selectApp);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<InstalledAppFilter>("all");

  useEffect(() => {
    if (status === "idle") void loadApps();
  }, [loadApps, status]);

  const visibleApps = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return apps.filter((app) => {
      const matchesFilter = filter === "all" || (filter === "system" ? app.isSystemApp : app.isUserInstalledApp);
      const matchesSearch = !normalized || app.appName.toLocaleLowerCase().includes(normalized) || app.packageName.toLocaleLowerCase().includes(normalized);
      return matchesFilter && matchesSearch;
    });
  }, [apps, filter, query]);

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <View className="flex-row items-center px-5 py-4">
        <Pressable accessibilityLabel="Go back" onPress={() => router.back()} className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surface">
          <ArrowLeft size={19} color="#EAF0FF" />
        </Pressable>
        <View className="ml-3 flex-1">
          <Text className="font-heading text-xl text-textPrimary">Installed Apps</Text>
          <Text className="text-xs text-textMuted">Launcher-visible Android apps</Text>
        </View>
        <Pressable accessibilityLabel="Refresh installed apps" onPress={() => void refreshApps()} className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surface">
          <RefreshCw size={18} color="#58D6FF" />
        </Pressable>
      </View>

      <View className="px-5">
        <View className="flex-row items-center rounded-2xl border border-border bg-surface px-4">
          <Search size={17} color="#8EA0C6" />
          <TextInput
            accessibilityLabel="Search installed apps"
            value={query}
            onChangeText={setQuery}
            placeholder="Search app or package"
            placeholderTextColor="#627093"
            className="ml-3 flex-1 py-3 text-sm text-textPrimary"
          />
        </View>
        <View className="mt-3 flex-row gap-2">
          {(["all", "user", "system"] as const).map((item) => (
            <Pressable key={item} onPress={() => setFilter(item)} className={`rounded-full border px-4 py-2 ${filter === item ? "border-accent bg-accent/15" : "border-border bg-surface"}`}>
              <Text className={`text-xs capitalize ${filter === item ? "text-accent" : "text-textMuted"}`}>{item}</Text>
            </Pressable>
          ))}
        </View>
        <Text className="my-4 text-xs leading-5 text-textDim">
          Android limits app visibility. This list includes launcher-visible apps only and is read locally; only the app you select is submitted for analysis.
        </Text>
      </View>

      {status === "loading" && apps.length === 0 ? (
        <View className="flex-1 items-center justify-center"><ActivityIndicator color="#58D6FF" /><Text className="mt-3 text-sm text-textMuted">Reading visible apps…</Text></View>
      ) : status === "error" ? (
        <View className="flex-1 justify-center px-6"><Text className="text-center text-base text-danger">{error}</Text><Pressable onPress={() => void loadApps()} className="mt-4 items-center rounded-2xl bg-accent py-3"><Text className="font-semibold text-background">Try again</Text></Pressable></View>
      ) : (
        <FlatList
          data={visibleApps}
          keyExtractor={(item) => item.packageName}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 32, flexGrow: 1 }}
          ListEmptyComponent={<View className="flex-1 items-center justify-center"><Text className="text-center text-sm text-textMuted">No visible apps match this search and filter.</Text></View>}
          renderItem={({ item }) => <InstalledAppListItem app={item} onPress={() => { selectApp(item); router.push({ pathname: "/installed-app-details", params: { packageName: item.packageName } }); }} />}
        />
      )}
    </SafeAreaView>
  );
}
