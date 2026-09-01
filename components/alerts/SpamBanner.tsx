import { AlertTriangle, X } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import Card from "../ui/Card";

type SpamBannerProps = {
  flaggedNotificationCount: number;
  affectedAppCount: number;
  onClose: () => void;
};

function pluralize(count: number, singular: string, plural = `${singular}s`) {
  return count === 1 ? singular : plural;
}

export default function SpamBanner({
  flaggedNotificationCount,
  affectedAppCount,
  onClose,
}: SpamBannerProps) {
  return (
    <Card className="flex-row items-start gap-3 border-danger/30 bg-danger/10">
      <View className="mt-1 h-10 w-10 items-center justify-center rounded-2xl bg-danger/20">
        <AlertTriangle size={20} color="#EF4444" />
      </View>
      <View className="flex-1">
        <Text className="text-sm font-semibold text-textPrimary font-sans">
          Possible spam notifications detected
        </Text>
        <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
          {flaggedNotificationCount}{" "}
          {pluralize(flaggedNotificationCount, "notification")} flagged for
          review across {affectedAppCount} observed {pluralize(affectedAppCount, "app")}.
          Each result applies only to its individual notification.
        </Text>
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Dismiss possible spam notification banner"
        onPress={onClose}
        className="rounded-full p-1"
      >
        <X size={16} color="#EF4444" />
      </Pressable>
    </Card>
  );
}
