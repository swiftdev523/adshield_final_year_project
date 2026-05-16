import { AlertTriangle, X } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import Card from "../ui/Card";

type SpamBannerProps = {
  onClose: () => void;
};

export default function SpamBanner({ onClose }: SpamBannerProps) {
  return (
    <Card className="flex-row items-start gap-3 border-danger/30 bg-danger/10">
      <View className="mt-1 h-10 w-10 items-center justify-center rounded-2xl bg-danger/20">
        <AlertTriangle size={20} color="#EF4444" />
      </View>
      <View className="flex-1">
        <Text className="text-sm font-semibold text-textPrimary font-sans">
          Active Spam Detected!
        </Text>
        <Text className="mt-1 text-xs text-textMuted font-sans">
          ShopDeals Pro, CashLoan Fast, BetNow & more are actively sending spam
          notifications.
        </Text>
      </View>
      <Pressable onPress={onClose} className="rounded-full p-1">
        <X size={16} color="#EF4444" />
      </Pressable>
    </Card>
  );
}
