import { Text, View } from "react-native";

import { NotificationApp } from "../../lib/mockData";
import Badge from "../ui/Badge";

type NotificationListItemProps = {
  item: NotificationApp;
  rank?: number;
};

const tagLabel: Record<NotificationApp["tag"], string> = {
  spam: "Spam",
  suspicious: "Suspicious",
  normal: "Normal",
};

const tagVariant: Record<
  NotificationApp["tag"],
  "spam" | "suspicious" | "normal"
> = {
  spam: "spam",
  suspicious: "suspicious",
  normal: "normal",
};

const iconColors: Record<string, string> = {
  "ShopDeals Pro": "#EF4444",
  "News Flash": "#F59E0B",
  GameMaster: "#8B5CF6",
  "CashLoan Fast": "#DC2626",
  WhatsApp: "#22C55E",
  BetNow: "#FF375F",
  PrizeAlert: "#E879F9",
  DailyDeals: "#FB923C",
  MapTracker: "#34D399",
  NewsLine: "#60A5FA",
};

export default function NotificationListItem({
  item,
  rank,
}: NotificationListItemProps) {
  const iconColor = iconColors[item.name] || "#00D4FF";

  return (
    <View
      className="flex-row items-center justify-between rounded-2xl border border-border overflow-hidden bg-surfaceHigh/80"
      style={{
        borderLeftWidth: 4,
        borderLeftColor: iconColor,
        backgroundColor:
          item.tag === "spam"
            ? "#FF375F1A"
            : item.tag === "suspicious"
              ? "#F59E0B1A"
              : "#19243A",
      }}
    >
      <View className="flex-row items-center gap-3 flex-1 p-4">
        <View className="relative flex-shrink-0">
          <View
            className="h-10 w-10 items-center justify-center rounded-2xl"
            style={{ backgroundColor: `${iconColor}20` }}
          >
            <Text
              className="text-base font-bold font-sans"
              style={{ color: iconColor }}
            >
              {item.name.charAt(0)}
            </Text>
          </View>
          {rank !== undefined && (
            <View className="absolute -top-1.5 -left-1.5 h-4 w-4 items-center justify-center rounded-full bg-surfaceHigh border border-border">
              <Text className="text-[9px] font-bold text-textMuted font-sans leading-none">
                {rank}
              </Text>
            </View>
          )}
        </View>
        <View className="flex-1">
          <Text className="text-sm font-semibold text-textPrimary font-sans">
            {item.name}
          </Text>
          <Text className="text-xs text-textMuted font-sans">
            {item.category} · {item.last}
          </Text>
        </View>
      </View>
      <View className="items-end gap-1 pr-4">
        <Text className="text-lg font-bold text-textPrimary font-sans">
          {item.count}
        </Text>
        <Badge variant={tagVariant[item.tag]} label={tagLabel[item.tag]} />
      </View>
    </View>
  );
}
