import { ChevronRight, Package } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import type { InstalledAppInfo } from "../../types/installed-apps";

type Props = { app: InstalledAppInfo; onPress(): void };

export default function InstalledAppListItem({ app, onPress }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`View ${app.appName}`}
      onPress={onPress}
      className="mb-3 flex-row items-center rounded-3xl border border-border bg-surface p-4">
      <View className="h-11 w-11 items-center justify-center rounded-2xl bg-accent/15">
        <Package size={20} color="#58D6FF" />
      </View>
      <View className="ml-3 flex-1">
        <Text className="font-heading text-base text-textPrimary" numberOfLines={1}>
          {app.appName}
        </Text>
        <Text className="mt-0.5 text-xs text-textMuted" numberOfLines={1}>
          {app.packageName}
        </Text>
        <Text className="mt-1 text-[11px] text-textDim">
          {app.isSystemApp ? "System app" : "User-installed app"} · {app.totalPermissionCount} declared permissions
        </Text>
      </View>
      <ChevronRight size={18} color="#8EA0C6" />
    </Pressable>
  );
}
