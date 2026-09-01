import { AlertTriangle, FileClock, ShieldCheck } from "lucide-react-native";
import { Text, View } from "react-native";

import type { HomeDashboardMetrics } from "../../lib/home/deriveHomeDashboard";
import Card from "../ui/Card";

type HomeStatsProps = {
  safeResults: number | null;
  threats: number | null;
  latestStatus: HomeDashboardMetrics["latestScanStatus"];
};

export default function HomeStats({
  safeResults,
  threats,
  latestStatus,
}: HomeStatsProps) {
  const latestColor =
    latestStatus === "Safe"
      ? "#00C853"
      : latestStatus === "Suspicious"
        ? "#FF8C00"
        : latestStatus === "High Risk"
          ? "#FF4444"
          : "#8EA0C6";
  const stats = [
    {
      label: "Safe Results",
      value: safeResults === null ? "—" : String(safeResults),
      color: "#00C853",
      Icon: ShieldCheck,
      compact: false,
    },
    {
      label: "Threats",
      value: threats === null ? "—" : String(threats),
      color: "#FF4444",
      Icon: AlertTriangle,
      compact: false,
    },
    {
      label: "Latest Scan",
      value: latestStatus,
      color: latestColor,
      Icon: FileClock,
      compact: true,
    },
  ];

  return (
    <View className="flex-row gap-3">
      {stats.map(({ label, value, color, Icon, compact }) => (
        <Card key={label} className="flex-1 items-center bg-surfaceHigh/80">
          <View
            className="h-9 w-9 items-center justify-center rounded-2xl"
            style={{ backgroundColor: `${color}20` }}>
            <Icon color={color} size={16} />
          </View>
          <Text
            adjustsFontSizeToFit
            numberOfLines={1}
            className={`mt-3 font-bold text-textPrimary font-sans ${
              compact ? "text-xs" : "text-xl"
            }`}>
            {value}
          </Text>
          <Text className="mt-1 text-[10px] text-textMuted font-sans">
            {label}
          </Text>
        </Card>
      ))}
    </View>
  );
}
