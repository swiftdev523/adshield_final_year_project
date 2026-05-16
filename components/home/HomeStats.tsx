import { AlertTriangle, Gauge, ShieldCheck } from "lucide-react-native";
import { Text, View } from "react-native";

import Card from "../ui/Card";

type HomeStatsProps = {
  safeApps: number;
  threats: number;
  score: number;
};

export default function HomeStats({
  safeApps,
  threats,
  score,
}: HomeStatsProps) {
  const stats = [
    {
      label: "Safe Apps",
      value: String(safeApps),
      color: "#00C853",
      Icon: ShieldCheck,
    },
    {
      label: "Threats",
      value: String(threats),
      color: "#FF4444",
      Icon: AlertTriangle,
    },
    {
      label: "Score",
      value: `${score}%`,
      color: "#00D4FF",
      Icon: Gauge,
    },
  ];

  return (
    <View className="flex-row gap-3">
      {stats.map(({ label, value, color, Icon }) => (
        <Card key={label} className="flex-1 items-center bg-surfaceHigh/80">
          <View
            className="h-9 w-9 items-center justify-center rounded-2xl"
            style={{ backgroundColor: `${color}20` }}>
            <Icon color={color} size={16} />
          </View>
          <Text className="mt-3 text-xl font-bold text-textPrimary font-sans">
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
