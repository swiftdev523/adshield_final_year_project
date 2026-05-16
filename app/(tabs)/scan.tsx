import { router } from "expo-router";
import { Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import FilePicker from "../../components/scan/FilePicker";
import ScanExampleList from "../../components/scan/ScanExampleList";
import { ScanExample, scanExamples } from "../../lib/mockData";
import { useScanStore } from "../../store/useScanStore";

const scoreMap: Record<ScanExample["risk"], number> = {
  dangerous: 82,
  caution: 55,
  safe: 18,
};

// More granular per-file scores for realism
const exampleScores: Record<string, number> = {
  "suspicious_game_v2.3.apk": 87,
  "shopping_app_free.apk": 58,
  "calculator_lite.apk": 12,
  "flashlight_pro.apk": 16,
  "weather_plus.apk": 51,
};

export default function ScanScreen() {
  const insets = useSafeAreaInsets();
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;

  const setScan = useScanStore((state) => state.setScan);

  const handleExample = (example: ScanExample) => {
    const score = exampleScores[example.name] ?? scoreMap[example.risk];
    setScan(example.name, score);
    router.push("/scan-result");
  };

  const header = (
    <View className="px-6 pt-6 pb-3">
      <Text className="font-heading text-2xl font-bold text-textPrimary">
        APK Scanner
      </Text>
      <Text className="mt-0.5 text-sm text-textMuted font-sans">
        AI-powered risk analysis
      </Text>
      <FilePicker />
      <Text className="mt-6 text-base font-semibold text-textPrimary font-sans">
        Quick scan examples:
      </Text>
    </View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top"]}
    >
      <ScanExampleList
        data={scanExamples}
        header={header}
        onSelect={handleExample}
        contentPaddingBottom={contentPaddingBottom}
      />
    </SafeAreaView>
  );
}
