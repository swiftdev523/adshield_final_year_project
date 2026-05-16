import { AlertOctagon, BellDot, ShieldAlert } from "lucide-react-native";
import { Text, View } from "react-native";

type StatBarProps = {
  spamApps: number;
  suspiciousApps: number;
  totalNotifs: number;
  spamNotifs: number;
  suspiciousNotifs: number;
  normalNotifs: number;
};

export default function StatBar({
  spamApps,
  suspiciousApps,
  totalNotifs,
  spamNotifs,
  suspiciousNotifs,
  normalNotifs,
}: StatBarProps) {
  return (
    <View className="gap-3">
      <View className="flex-row items-center justify-between gap-4">
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <AlertOctagon color="#FF375F" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {spamApps}
          </Text>
          <Text className="text-[10px] text-textMuted font-sans">
            Spam Apps
          </Text>
        </View>
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <ShieldAlert color="#F59E0B" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {suspiciousApps}
          </Text>
          <Text className="text-[10px] text-textMuted font-sans">
            Suspicious
          </Text>
        </View>
        <View className="flex-1 items-center rounded-2xl border border-border bg-surfaceHigh/80 p-3">
          <BellDot color="#5B6A8C" size={16} />
          <Text className="mt-2 text-lg font-bold text-textPrimary font-sans">
            {totalNotifs}
          </Text>
          <Text className="text-[10px] text-textMuted font-sans">
            Total Notifs
          </Text>
        </View>
      </View>

      {/* Progress bar showing proportion of notifications by category */}
      <View
        className="h-1.5 flex-row rounded-full overflow-hidden"
        style={{ gap: 2 }}
      >
        <View style={{ flex: spamNotifs, backgroundColor: "#FF375F" }} />
        <View style={{ flex: suspiciousNotifs, backgroundColor: "#F59E0B" }} />
        <View style={{ flex: normalNotifs, backgroundColor: "#5B6A8C" }} />
      </View>
    </View>
  );
}
