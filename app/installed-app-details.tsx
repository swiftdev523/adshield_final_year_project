import { ArrowLeft, ChevronDown, ChevronUp, ShieldCheck } from "lucide-react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import InstalledAppMetadata from "../components/installed-apps/InstalledAppMetadata";
import { NO_DECLARED_PERMISSIONS_MESSAGE } from "../services/installed-apps/analyzeInstalledApp";
import { useInstalledAppsStore } from "../store/useInstalledAppsStore";

export default function InstalledAppDetailsScreen() {
  const params = useLocalSearchParams<{ packageName?: string }>();
  const app = useInstalledAppsStore((state) => state.selectedApp);
  const loadSelectedApp = useInstalledAppsStore((state) => state.loadSelectedApp);
  const analyzeSelectedApp = useInstalledAppsStore((state) => state.analyzeSelectedApp);
  const [showDeclaredPermissions, setShowDeclaredPermissions] = useState(false);

  useEffect(() => {
    if (params.packageName && app?.packageName !== params.packageName) {
      void loadSelectedApp(params.packageName);
    }
  }, [app?.packageName, loadSelectedApp, params.packageName]);

  const analyze = () => {
    void analyzeSelectedApp();
    router.push("/installed-app-result");
  };

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <View className="flex-row items-center px-5 py-4">
        <Pressable accessibilityLabel="Go back" onPress={() => router.back()} className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surface"><ArrowLeft size={19} color="#EAF0FF" /></Pressable>
        <Text className="ml-3 font-heading text-xl text-textPrimary">App Details</Text>
      </View>
      {!app ? (
        <View className="flex-1 items-center justify-center px-6"><Text className="text-center text-sm text-textMuted">Unable to find this launcher-visible app.</Text></View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
          <Text className="font-heading text-2xl text-textPrimary">{app.appName}</Text>
          <Text className="mb-5 mt-1 text-xs text-textMuted">Observable PackageManager metadata</Text>
          <InstalledAppMetadata app={app} />

          <View className="mt-5 rounded-3xl border border-border bg-surface p-4">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Declared permissions (${app.totalPermissionCount})`}
              accessibilityState={{ expanded: showDeclaredPermissions }}
              onPress={() => setShowDeclaredPermissions((visible) => !visible)}
              className="flex-row items-center justify-between"
            >
              <Text className="flex-1 font-heading text-base text-textPrimary">
                Declared permissions ({app.totalPermissionCount})
              </Text>
              {showDeclaredPermissions ? (
                <ChevronUp size={20} color="#58D6FF" />
              ) : (
                <ChevronDown size={20} color="#58D6FF" />
              )}
            </Pressable>
            {showDeclaredPermissions ? (
              app.requestedPermissions.length === 0 ? (
                <Text className="mt-3 text-sm leading-5 text-warning">
                  {NO_DECLARED_PERMISSIONS_MESSAGE}
                </Text>
              ) : (
                app.requestedPermissions.map((permission) => (
                  <Text key={permission} className="mt-3 text-xs leading-5 text-textMuted">
                    {"\u2022"} {permission}
                  </Text>
                ))
              )
            ) : null}
          </View>

          <Text className="mt-4 text-xs leading-5 text-textDim">
            Analysis sends only this app's package name, declared permissions, and supported install-source value to the backend.
          </Text>
          <Pressable accessibilityRole="button" onPress={analyze} className="mt-5 flex-row items-center justify-center rounded-2xl bg-accent py-4">
            <ShieldCheck size={18} color="#0B1020" />
            <Text className="ml-2 font-semibold text-background">Analyze App</Text>
          </Pressable>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
