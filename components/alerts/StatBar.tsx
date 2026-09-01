import {
  AlertOctagon,
  BellDot,
  ShieldCheck,
} from "lucide-react-native";
import { Text, View } from "react-native";

type StatBarProps = {
  possibleSpamCount: number;
  normalCount: number;
  skippedCount: number;
  awaitingAnalysisCount: number;
  analysisErrorCount: number;
  totalObserved: number;
};

export default function StatBar({
  possibleSpamCount,
  normalCount,
  skippedCount,
  awaitingAnalysisCount,
  analysisErrorCount,
  totalObserved,
}: StatBarProps) {
  return (
    <View className="gap-3">
      <View className="flex-row items-center justify-between gap-4">
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <AlertOctagon color="#FF375F" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {possibleSpamCount}
          </Text>
          <Text className="text-center text-[10px] text-textMuted font-sans">
            Possible Spam
          </Text>
        </View>
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <ShieldCheck color="#22C55E" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {normalCount}
          </Text>
          <Text className="text-[10px] text-textMuted font-sans">Normal</Text>
        </View>
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <BellDot color="#5B6A8C" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {totalObserved}
          </Text>
          <Text className="text-[10px] text-textMuted font-sans">Observed</Text>
        </View>
      </View>

      <View
        accessibilityLabel={`${possibleSpamCount} possible spam notifications, ${normalCount} normal notifications, ${skippedCount} skipped notifications, ${awaitingAnalysisCount} awaiting analysis, ${analysisErrorCount} analysis errors`}
        className="h-1.5 flex-row overflow-hidden rounded-full bg-surfaceHigh"
        style={{ gap: totalObserved > 0 ? 2 : 0 }}
      >
        {possibleSpamCount > 0 && (
          <View style={{ flex: possibleSpamCount, backgroundColor: "#FF375F" }} />
        )}
        {normalCount > 0 && (
          <View style={{ flex: normalCount, backgroundColor: "#22C55E" }} />
        )}
        {skippedCount > 0 && (
          <View style={{ flex: skippedCount, backgroundColor: "#5B6A8C" }} />
        )}
        {awaitingAnalysisCount > 0 && (
          <View
            style={{ flex: awaitingAnalysisCount, backgroundColor: "#58D6FF" }}
          />
        )}
        {analysisErrorCount > 0 && (
          <View
            style={{ flex: analysisErrorCount, backgroundColor: "#F59E0B" }}
          />
        )}
      </View>

      <Text className="text-[11px] leading-5 text-textMuted font-sans">
        {skippedCount} skipped service/status | {awaitingAnalysisCount} awaiting
        analysis | {analysisErrorCount} analysis {analysisErrorCount === 1 ? "error" : "errors"}
      </Text>
    </View>
  );
}
