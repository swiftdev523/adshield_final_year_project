import type { ReactElement } from "react";
import { FlatList, Text, View } from "react-native";

import {
  formatActivityTime,
  type HomeActivityItem,
} from "../../lib/home/deriveHomeDashboard";
import Card from "../ui/Card";

type ActivityFeedProps = {
  data: HomeActivityItem[];
  header?: ReactElement | null;
  contentPaddingBottom?: number;
  loading?: boolean;
};

const levelColor: Record<HomeActivityItem["level"], string> = {
  safe: "#00C853",
  caution: "#FF8C00",
  dangerous: "#FF4444",
};

export default function ActivityFeed({
  data,
  header,
  contentPaddingBottom,
  loading = false,
}: ActivityFeedProps) {
  const paddingBottom = 32 + (contentPaddingBottom ?? 0);

  return (
    <FlatList
      data={data}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header ?? null}
      contentContainerStyle={{ paddingBottom }}
      ListEmptyComponent={
        <View className="px-6 pb-3">
          <Card className="bg-surfaceHigh/80">
            <Text className="text-center text-sm font-semibold text-textPrimary font-sans">
              {loading
                ? "Loading recent security activity..."
                : "No recorded security activity yet"}
            </Text>
            <Text className="mt-2 text-center text-xs leading-5 text-textMuted font-sans">
              {loading
                ? "AdShield is reading local scan and notification state."
                : "Completed scans, notification alerts, and verified access changes will appear here."}
            </Text>
          </Card>
        </View>
      }
      renderItem={({ item }) => (
        <View className="px-6 pb-3">
          <Card className="flex-row items-center justify-between bg-surfaceHigh/80">
            <View className="flex-1 flex-row items-center gap-3">
              <View
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: levelColor[item.level] }}
              />
              <Text className="text-sm text-textPrimary font-sans">
                {item.text}
              </Text>
            </View>
            <Text className="text-xs text-textDim font-sans">
              {formatActivityTime(item.occurredAt)}
            </Text>
          </Card>
        </View>
      )}
    />
  );
}
