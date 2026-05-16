import type { ReactElement } from "react";
import { FileText } from "lucide-react-native";
import { FlatList, Pressable, Text, View } from "react-native";

import { ScanExample } from "../../lib/mockData";
import Badge from "../ui/Badge";
import Card from "../ui/Card";

const badgeLabel: Record<ScanExample["risk"], string> = {
  dangerous: "HIGH",
  caution: "MOD.",
  safe: "SAFE",
};

type ScanExampleListProps = {
  data: ScanExample[];
  header?: ReactElement | null;
  onSelect: (example: ScanExample) => void;
  contentPaddingBottom?: number;
};

export default function ScanExampleList({
  data,
  header,
  onSelect,
  contentPaddingBottom,
}: ScanExampleListProps) {
  const paddingBottom = 32 + (contentPaddingBottom ?? 0);

  return (
    <FlatList
      data={data}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header ?? null}
      contentContainerStyle={{ paddingBottom }}
      renderItem={({ item }) => (
        <View className="px-6 pb-3">
          <Pressable onPress={() => onSelect(item)}>
            <Card className="flex-row items-center bg-surfaceHigh/80">
              <View className="flex-row items-center gap-3 flex-1 pr-3">
                <View className="h-10 w-10 items-center justify-center rounded-2xl bg-surface">
                  <FileText size={18} color="#58D6FF" />
                </View>
                <View className="flex-1">
                  <Text
                    className="text-sm font-semibold text-textPrimary font-sans"
                    numberOfLines={1}
                    ellipsizeMode="tail"
                  >
                    {item.name}
                  </Text>
                  <Text className="text-xs text-textMuted font-sans">
                    {item.size}
                  </Text>
                </View>
              </View>
              <Badge
                variant={item.risk}
                label={badgeLabel[item.risk]}
                className="shrink-0"
              />
            </Card>
          </Pressable>
        </View>
      )}
    />
  );
}
