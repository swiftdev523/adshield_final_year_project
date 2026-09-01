import { Alert, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import FilePicker from "../../components/scan/FilePicker";
import ScanExampleList from "../../components/scan/ScanExampleList";
import { ScanExample, scanExamples } from "../../lib/mockData";

export default function ScanScreen() {
  const insets = useSafeAreaInsets();
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;

  const handleExample = (example: ScanExample) => {
    Alert.alert(
      "Demonstration example",
      `${example.name} is a visual example only. Select a real APK above to receive a backend assessment.`,
    );
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
        Demonstration examples — not live scans
      </Text>
      <Text className="mt-1 text-xs leading-5 text-textDim font-sans">
        These cards illustrate the design and never generate analysis results.
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
