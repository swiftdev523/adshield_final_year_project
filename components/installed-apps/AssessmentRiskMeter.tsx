import { Text, View } from "react-native";

import type { OverallRiskLevel } from "../../types/installed-app-assessment";

const colors: Record<OverallRiskLevel, string> = {
  Safe: "#22C55E",
  Suspicious: "#F59E0B",
  "High Risk": "#EF4444",
};

export default function AssessmentRiskMeter({
  score,
  level,
  reviewLabel,
}: {
  score: number;
  level: OverallRiskLevel;
  reviewLabel: string;
}) {
  const color = colors[level];
  return (
    <View className="items-center rounded-3xl border border-border bg-surface p-5">
      <View
        className="h-24 w-24 items-center justify-center rounded-full border-8"
        style={{ borderColor: color }}>
        <Text className="font-heading text-3xl text-textPrimary">{score}</Text>
        <Text className="text-[10px] text-textMuted">out of 100</Text>
      </View>
      <Text className="mt-3 font-heading text-lg" style={{ color }}>
        {reviewLabel}
      </Text>
      <Text className="mt-1 text-center text-xs text-textMuted">
        Overall review
      </Text>
    </View>
  );
}
