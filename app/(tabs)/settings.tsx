import { Download, Eye, Zap } from "lucide-react-native";
import type { ComponentType } from "react";
import { FlatList, Switch, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import Card from "../../components/ui/Card";
import { useSettingsStore } from "../../store/useSettingsStore";

type IconComponent = ComponentType<{ size?: number; color?: string }>;

const settingIcons: Record<string, { Icon: IconComponent; color: string }> = {
  "1": { Icon: Download, color: "#58D6FF" },
  "2": { Icon: Zap, color: "#22C55E" },
  "3": { Icon: Eye, color: "#F59E0B" },
};

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const tabBarHeight = 70;
  const bottomOffset = insets.bottom + 8;
  const contentPaddingBottom = tabBarHeight + bottomOffset + 16;

  const settings = useSettingsStore((state) => state.settings);
  const toggleSetting = useSettingsStore((state) => state.toggleSetting);

  const header = (
    <View className="px-6 pt-6 pb-3">
      <Text className="font-heading text-2xl text-textPrimary">Settings</Text>
      <Text className="mt-1 text-sm text-textMuted font-sans">
        Customize how AdShield protects your device
      </Text>
    </View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top"]}
    >
      <FlatList
        data={settings}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingBottom: 32 + contentPaddingBottom }}
        renderItem={({ item }) => {
          const iconData = settingIcons[item.id];
          const Icon = iconData?.Icon;
          const iconColor = iconData?.color ?? "#58D6FF";

          return (
            <View className="px-6 pb-3">
              <Card className="flex-row items-center gap-3">
                {Icon && (
                  <View
                    className="h-10 w-10 items-center justify-center rounded-2xl flex-shrink-0"
                    style={{ backgroundColor: `${iconColor}20` }}
                  >
                    <Icon size={18} color={iconColor} />
                  </View>
                )}
                <View className="flex-1">
                  <Text className="text-sm font-semibold text-textPrimary font-sans">
                    {item.title}
                  </Text>
                  <Text className="mt-1 text-xs text-textMuted font-sans">
                    {item.description}
                  </Text>
                </View>
                <Switch
                  value={item.value}
                  onValueChange={() => toggleSetting(item.id)}
                  trackColor={{ false: "#22304A", true: "#58D6FF" }}
                  thumbColor={item.value ? "#0B1020" : "#5B6A8C"}
                  accessibilityLabel={item.title}
                />
              </Card>
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}
