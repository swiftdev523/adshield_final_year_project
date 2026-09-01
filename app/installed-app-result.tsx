import { ArrowLeft } from "lucide-react-native";
import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import InstalledAppResultContent from "../components/installed-apps/InstalledAppResultContent";
import { useInstalledAppsStore } from "../store/useInstalledAppsStore";

export default function InstalledAppResultScreen() {
  const analysis = useInstalledAppsStore((state) => state.analysis);
  const analyzeSelectedApp = useInstalledAppsStore((state) => state.analyzeSelectedApp);
  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <View className="flex-row items-center px-5 py-4">
        <Pressable accessibilityLabel="Go back" onPress={() => router.back()} className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surface"><ArrowLeft size={19} color="#EAF0FF" /></Pressable>
        <Text className="ml-3 font-heading text-xl text-textPrimary">Installed App Result</Text>
      </View>
      <InstalledAppResultContent state={analysis} onRetry={() => void analyzeSelectedApp()} />
    </SafeAreaView>
  );
}
