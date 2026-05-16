import type { ComponentType } from "react";
import { Text, View } from "react-native";

import Badge from "../ui/Badge";
import Card from "../ui/Card";

type IconType = ComponentType<{ color?: string; size?: number }>;

type PermissionItemProps = {
  icon: IconType;
  name: string;
  description: string;
  level: "safe" | "caution" | "dangerous";
};

const levelColor: Record<PermissionItemProps["level"], string> = {
  safe: "#00C853",
  caution: "#FF8C00",
  dangerous: "#FF4444",
};

export default function PermissionItem({
  icon: Icon,
  name,
  description,
  level,
}: PermissionItemProps) {
  return (
    <Card className="flex-row items-center justify-between bg-surfaceHigh/80">
      <View className="flex-row items-center gap-3 flex-1">
        <View
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: levelColor[level] }}
        />
        <View className="h-10 w-10 items-center justify-center rounded-2xl bg-surface">
          <Icon size={18} color={levelColor[level]} />
        </View>
        <View className="flex-1">
          <Text className="text-sm font-semibold text-textPrimary font-sans">
            {name}
          </Text>
          <Text className="text-xs text-textMuted font-sans">
            {description}
          </Text>
        </View>
      </View>
      <Badge variant={level} />
    </Card>
  );
}
