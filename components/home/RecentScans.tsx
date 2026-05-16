import { FlatList, Pressable, Text, View } from "react-native";

import { RecentScan } from "../../lib/mockData";
import Badge from "../ui/Badge";

type RecentScansProps = {
  data: RecentScan[];
  onSelect?: (item: RecentScan) => void;
};

const statusLabel: Record<RecentScan["status"], string> = {
  safe: "Safe",
  caution: "Caution",
  dangerous: "High Risk",
};

export default function RecentScans({ data, onSelect }: RecentScansProps) {
  return (
    <FlatList
      data={data}
      horizontal
      keyExtractor={(item) => item.id}
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{
        paddingHorizontal: 24,
        paddingTop: 10,
        paddingBottom: 8,
      }}
      renderItem={({ item }) => (
        <Pressable
          className="mr-3 items-center"
          onPress={() => onSelect?.(item)}
          disabled={!onSelect}>
          <View
            className="h-14 w-14 items-center justify-center rounded-2xl border border-border"
            style={{ backgroundColor: item.color }}>
            <Text className="text-lg font-bold text-white font-sans">
              {item.initials}
            </Text>
          </View>
          <Text className="mt-2 text-xs font-semibold text-textPrimary font-sans">
            {item.name}
          </Text>
          <Badge
            variant={item.status}
            label={statusLabel[item.status]}
            className="mt-1"
          />
        </Pressable>
      )}
    />
  );
}
