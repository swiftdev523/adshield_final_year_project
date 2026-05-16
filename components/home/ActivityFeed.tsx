import type { ReactElement } from "react";
import { FlatList, Text, View } from "react-native";

import { ActivityItem } from "../../lib/mockData";
import Card from "../ui/Card";

type ActivityFeedProps = {
  data: ActivityItem[];
  header?: ReactElement | null;
  contentPaddingBottom?: number;
};

const levelColor: Record<ActivityItem["level"], string> = {
  safe: "#00C853",
  caution: "#FF8C00",
  dangerous: "#FF4444",
};

export default function ActivityFeed({
  data,
  header,
  contentPaddingBottom,
}: ActivityFeedProps) {
  const paddingBottom = 32 + (contentPaddingBottom ?? 0);

  return (
    <FlatList
      data={data}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header ?? null}
      contentContainerStyle={{ paddingBottom }}
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
            <Text className="text-xs text-textDim font-sans">{item.time}</Text>
          </Card>
        </View>
      )}
    />
  );
}
