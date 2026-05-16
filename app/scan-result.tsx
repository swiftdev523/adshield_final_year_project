import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  Camera,
  Contact,
  MapPin,
  MessageSquare,
  Mic,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Wifi,
} from "lucide-react-native";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  Text,
  View,
} from "react-native";
import Animated, { FadeIn } from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import PermissionItem from "../components/scan/PermissionItem";
import Badge from "../components/ui/Badge";
import Card from "../components/ui/Card";
import RiskMeter from "../components/ui/RiskMeter";
import { useScanStore } from "../store/useScanStore";

type PermissionLevel = "safe" | "caution" | "dangerous";

type Permission = {
  id: string;
  name: string;
  description: string;
  level: PermissionLevel;
  icon: typeof Wifi;
};

const dangerousPermissions: Permission[] = [
  {
    id: "1",
    name: "Internet Access",
    description: "Basic network connectivity",
    level: "safe",
    icon: Wifi,
  },
  {
    id: "2",
    name: "Read Contacts",
    description: "Access your contact list",
    level: "caution",
    icon: Contact,
  },
  {
    id: "3",
    name: "GPS Location",
    description: "Precise device location",
    level: "dangerous",
    icon: MapPin,
  },
  {
    id: "4",
    name: "Push Notifications",
    description: "Flood device with alerts",
    level: "caution",
    icon: Bell,
  },
  {
    id: "5",
    name: "Send SMS",
    description: "Send messages from your device",
    level: "dangerous",
    icon: MessageSquare,
  },
  {
    id: "6",
    name: "Camera Access",
    description: "Access device camera",
    level: "dangerous",
    icon: Camera,
  },
  {
    id: "7",
    name: "Read Call Log",
    description: "Access call history",
    level: "dangerous",
    icon: Phone,
  },
  {
    id: "8",
    name: "Storage Write",
    description: "Modify device storage",
    level: "safe",
    icon: ShieldCheck,
  },
];

const cautionPermissions: Permission[] = [
  {
    id: "1",
    name: "Internet Access",
    description: "Basic network connectivity",
    level: "safe",
    icon: Wifi,
  },
  {
    id: "2",
    name: "Read Contacts",
    description: "Access your contact list",
    level: "caution",
    icon: Contact,
  },
  {
    id: "3",
    name: "GPS Location",
    description: "Approximate location access",
    level: "caution",
    icon: MapPin,
  },
  {
    id: "4",
    name: "Push Notifications",
    description: "Send alerts and reminders",
    level: "safe",
    icon: Bell,
  },
  {
    id: "5",
    name: "Microphone",
    description: "Record audio when in use",
    level: "caution",
    icon: Mic,
  },
  {
    id: "6",
    name: "Storage Read",
    description: "Read device storage",
    level: "safe",
    icon: ShieldCheck,
  },
];

const safePermissions: Permission[] = [
  {
    id: "1",
    name: "Internet Access",
    description: "Basic network connectivity",
    level: "safe",
    icon: Wifi,
  },
  {
    id: "2",
    name: "Push Notifications",
    description: "Send alerts and reminders",
    level: "safe",
    icon: Bell,
  },
  {
    id: "3",
    name: "Storage Read",
    description: "Read device storage",
    level: "safe",
    icon: ShieldCheck,
  },
  {
    id: "4",
    name: "Vibration",
    description: "Control device vibration",
    level: "safe",
    icon: ShieldCheck,
  },
  {
    id: "5",
    name: "Network State",
    description: "Check network connectivity",
    level: "safe",
    icon: Wifi,
  },
  {
    id: "6",
    name: "Wake Lock",
    description: "Keep screen on",
    level: "caution",
    icon: ShieldAlert,
  },
];

const permCounts = {
  dangerous: { dangerCount: 4, cautionCount: 2, safeCount: 2 },
  caution: { dangerCount: 1, cautionCount: 3, safeCount: 2 },
  safe: { dangerCount: 0, cautionCount: 1, safeCount: 5 },
};

export default function ScanResultScreen() {
  const fileName = useScanStore((state) => state.fileName);
  const score = useScanStore((state) => state.score);
  const isNewScan = useScanStore((state) => state.isNewScan);
  const clearNewScan = useScanStore((state) => state.clearNewScan);

  const [scanning, setScanning] = useState(isNewScan);

  useEffect(() => {
    clearNewScan();
    if (isNewScan) {
      const timer = setTimeout(() => {
        setScanning(false);
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, []);

  const riskLevel: "dangerous" | "caution" | "safe" =
    score >= 70 ? "dangerous" : score >= 40 ? "caution" : "safe";

  const advice =
    score >= 70
      ? "Avoid installing"
      : score >= 40
        ? "Review carefully"
        : "Looks safe";
  const adviceColor =
    score >= 70 ? "#EF4444" : score >= 40 ? "#F59E0B" : "#22C55E";

  const permissions =
    riskLevel === "dangerous"
      ? dangerousPermissions
      : riskLevel === "caution"
        ? cautionPermissions
        : safePermissions;

  const { dangerCount, cautionCount, safeCount } = permCounts[riskLevel];

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(tabs)/scan");
    }
  };

  if (scanning) {
    return (
      <SafeAreaView
        style={{ flex: 1, backgroundColor: "#0B1020" }}
        edges={["top", "bottom"]}
      >
        <View className="px-6 pt-4">
          <Pressable
            onPress={handleBack}
            className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
          >
            <ArrowLeft size={18} color="#8EA0C6" />
          </Pressable>
        </View>
        <View className="flex-1 items-center justify-center gap-6">
          <View className="h-24 w-24 items-center justify-center rounded-3xl border border-accent/30 bg-accent/10">
            <ActivityIndicator size="large" color="#58D6FF" />
          </View>
          <View className="items-center gap-2">
            <Text className="text-xl font-bold text-textPrimary font-sans">
              Analyzing APK...
            </Text>
            <Text className="text-sm text-textMuted font-sans text-center px-8">
              Scanning for malware, adware & privacy risks
            </Text>
          </View>
          <View className="flex-row gap-2">
            {["Permissions", "Signatures", "Behavior"].map((step) => (
              <View
                key={step}
                className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1"
              >
                <Text className="text-[10px] text-accent font-sans font-semibold">
                  {step}
                </Text>
              </View>
            ))}
          </View>
        </View>
      </SafeAreaView>
    );
  }

  const header = (
    <Animated.View entering={FadeIn.duration(400)} className="px-6 pt-6">
      <View className="flex-row items-center gap-3 mb-4">
        <Pressable
          onPress={handleBack}
          className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
        >
          <ArrowLeft size={18} color="#8EA0C6" />
        </Pressable>
        <View className="flex-1">
          <Text className="font-heading text-2xl font-bold text-textPrimary">
            APK Scanner
          </Text>
          <Text className="text-xs text-textMuted font-sans">
            AI-powered risk analysis
          </Text>
        </View>
      </View>

      <Card className="flex-row items-center justify-between bg-surfaceHigh/80 mb-4">
        <View className="flex-1 pr-3">
          <Text
            className="text-sm font-semibold text-textPrimary font-sans"
            numberOfLines={1}
            ellipsizeMode="middle"
          >
            {fileName ?? "suspicious_game_v2.3.apk"}
          </Text>
          <Text className="text-xs text-textMuted font-sans mt-0.5">
            Analysis complete
          </Text>
        </View>
        <Badge variant={riskLevel} label="DONE" />
      </Card>

      <Text className="text-center text-sm font-semibold text-textPrimary font-sans mb-2">
        Risk Score
      </Text>

      <View className="items-center">
        <RiskMeter score={score} />
        <Text
          className="mt-2 text-sm font-semibold font-sans"
          style={{ color: adviceColor }}
        >
          {advice}
        </Text>
      </View>

      <View className="mt-6 flex-row gap-3">
        <Card className="flex-1 items-center bg-surfaceHigh/80">
          <AlertTriangle size={18} color="#EF4444" />
          <Text className="mt-2 text-2xl font-bold text-textPrimary font-sans">
            {dangerCount}
          </Text>
          <Text className="text-xs text-textMuted font-sans text-center">
            Dangerous
          </Text>
          <Text className="text-[9px] text-textDim font-sans">Perms</Text>
        </Card>
        <Card className="flex-1 items-center bg-surfaceHigh/80">
          <ShieldAlert size={18} color="#F59E0B" />
          <Text className="mt-2 text-2xl font-bold text-textPrimary font-sans">
            {cautionCount}
          </Text>
          <Text className="text-xs text-textMuted font-sans text-center">
            Caution
          </Text>
          <Text className="text-[9px] text-textDim font-sans">Perms</Text>
        </Card>
        <Card className="flex-1 items-center bg-surfaceHigh/80">
          <ShieldCheck size={18} color="#22C55E" />
          <Text className="mt-2 text-2xl font-bold text-textPrimary font-sans">
            {safeCount}
          </Text>
          <Text className="text-xs text-textMuted font-sans text-center">
            Safe
          </Text>
          <Text className="text-[9px] text-textDim font-sans">Perms</Text>
        </Card>
      </View>

      <Text className="mt-6 mb-2 text-base font-semibold text-textPrimary font-sans">
        Detected Permissions
      </Text>
    </Animated.View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top", "bottom"]}
    >
      <FlatList
        data={permissions}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingBottom: 32 }}
        renderItem={({ item }) => (
          <View className="px-6 pb-3">
            <PermissionItem
              icon={item.icon}
              name={item.name}
              description={item.description}
              level={item.level}
            />
          </View>
        )}
      />
    </SafeAreaView>
  );
}
