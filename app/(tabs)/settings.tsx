import { router, useFocusEffect } from "expo-router";
import {
  Bell,
  ChevronRight,
  Download,
  Eye,
  Info,
  LockKeyhole,
  Smartphone,
} from "lucide-react-native";
import { useCallback, type ReactNode } from "react";
import { Pressable, ScrollView, Switch, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import Card from "../../components/ui/Card";
import { useAlertStore } from "../../store/useAlertStore";
import { useSettingsStore } from "../../store/useSettingsStore";

function SettingCard({ children }: { children: ReactNode }) {
  return (
    <Card className="mb-3 flex-row items-center gap-3 bg-surfaceHigh/80">
      {children}
    </Card>
  );
}

function InformationLink({
  title,
  description,
  topic,
  icon,
}: {
  title: string;
  description: string;
  topic: "privacy" | "permissions" | "notifications" | "visibility";
  icon: ReactNode;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      onPress={() =>
        router.push({ pathname: "/settings-info", params: { topic } })
      }
      className="mb-3">
      <Card className="flex-row items-center gap-3 bg-surfaceHigh/80">
        <View className="h-10 w-10 items-center justify-center rounded-2xl bg-accent/15">
          {icon}
        </View>
        <View className="flex-1">
          <Text className="text-sm font-semibold text-textPrimary font-sans">
            {title}
          </Text>
          <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
            {description}
          </Text>
        </View>
        <ChevronRight size={18} color="#8EA0C6" />
      </Card>
    </Pressable>
  );
}

function accessText(status: string): {
  label: string;
  description: string;
} {
  if (status === "granted") {
    return {
      label: "Enabled",
      description:
        "Android notification access is enabled. Monitoring can run while AdShield is installed.",
    };
  }
  if (status === "not_granted") {
    return {
      label: "Not enabled",
      description:
        "Enable Android notification access to monitor notification activity.",
    };
  }
  if (status === "checking" || status === "unknown") {
    return {
      label: "Checking",
      description: "Reading the current Android notification-access setting.",
    };
  }
  if (status === "unavailable") {
    return {
      label: "Unavailable",
      description: "Notification monitoring is not available in this build.",
    };
  }
  return {
    label: "Check failed",
    description:
      "Open Android settings or try again to verify notification access.",
  };
}

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const privacyMode = useSettingsStore((state) => state.privacyMode);
  const settingsStatus = useSettingsStore((state) => state.status);
  const settingsError = useSettingsStore((state) => state.error);
  const hydrate = useSettingsStore((state) => state.hydrate);
  const setPrivacyMode = useSettingsStore((state) => state.setPrivacyMode);
  const accessStatus = useAlertStore((state) => state.accessStatus);
  const checkAccess = useAlertStore((state) => state.checkAccessAndLoad);
  const openAccessSettings = useAlertStore(
    (state) => state.openAccessSettings,
  );
  const notification = accessText(accessStatus);

  useFocusEffect(
    useCallback(() => {
      void hydrate();
      void checkAccess();
    }, [checkAccess, hydrate]),
  );

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top"]}>
      <ScrollView
        contentContainerStyle={{
          paddingHorizontal: 24,
          paddingTop: 24,
          paddingBottom: 110 + insets.bottom,
        }}>
        <Text className="font-heading text-2xl text-textPrimary">Settings</Text>
        <Text className="mt-1 text-sm text-textMuted font-sans">
          Control privacy and connected Android features
        </Text>

        <Text className="mb-3 mt-6 text-xs font-semibold uppercase tracking-wider text-textMuted font-sans">
          Controls
        </Text>

        <SettingCard>
          <View className="h-10 w-10 items-center justify-center rounded-2xl bg-warning/15">
            <Eye size={18} color="#F59E0B" />
          </View>
          <View className="flex-1">
            <Text className="text-sm font-semibold text-textPrimary font-sans">
              Privacy mode
            </Text>
            <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
              Shorten app names on summaries and reports. This does not encrypt
              or anonymize data.
            </Text>
          </View>
          <Switch
            value={privacyMode}
            disabled={settingsStatus === "loading"}
            onValueChange={(enabled) => void setPrivacyMode(enabled)}
            trackColor={{ false: "#22304A", true: "#58D6FF" }}
            thumbColor={privacyMode ? "#0B1020" : "#5B6A8C"}
            accessibilityLabel="Privacy mode"
          />
        </SettingCard>

        {settingsStatus === "error" ? (
          <View className="mb-3 rounded-2xl border border-danger/30 bg-danger/10 p-4">
            <Text className="text-sm font-semibold text-danger font-sans">
              Settings were not saved
            </Text>
            <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
              {settingsError ?? "Local settings storage is unavailable."}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Retry loading settings"
              onPress={() => void hydrate(true)}
              className="mt-3 self-start rounded-xl border border-accent/40 px-4 py-2">
              <Text className="text-xs font-semibold text-accent font-sans">
                Try again
              </Text>
            </Pressable>
          </View>
        ) : null}

        <SettingCard>
          <View className="h-10 w-10 items-center justify-center rounded-2xl bg-safe/15">
            <Bell size={18} color="#22C55E" />
          </View>
          <View className="flex-1">
            <Text className="text-sm font-semibold text-textPrimary font-sans">
              Notification monitoring
            </Text>
            <Text className="mt-1 text-xs font-semibold text-accent font-sans">
              {notification.label}
            </Text>
            <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
              {notification.description}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Manage notification access in Android settings"
              onPress={() => void openAccessSettings()}
              className="mt-3 self-start rounded-xl border border-accent/40 bg-accent/10 px-3 py-2">
              <Text className="text-xs font-semibold text-accent font-sans">
                Manage Android access
              </Text>
            </Pressable>
          </View>
        </SettingCard>

        <SettingCard>
          <View className="h-10 w-10 items-center justify-center rounded-2xl bg-accent/15">
            <Download size={18} color="#58D6FF" />
          </View>
          <View className="flex-1">
            <Text className="text-sm font-semibold text-textPrimary font-sans">
              Auto-scan downloads
            </Text>
            <Text className="mt-1 text-xs font-semibold text-warning font-sans">
              Planned - not active
            </Text>
            <Text className="mt-1 text-xs leading-5 text-textMuted font-sans">
              AdShield scans only APK files you choose. It does not monitor your
              Downloads folder.
            </Text>
          </View>
          <Switch
            value={false}
            disabled
            accessibilityLabel="Auto-scan downloads planned and unavailable"
            trackColor={{ false: "#22304A", true: "#22304A" }}
            thumbColor="#5B6A8C"
          />
        </SettingCard>

        <Text className="mb-3 mt-5 text-xs font-semibold uppercase tracking-wider text-textMuted font-sans">
          Information
        </Text>
        <InformationLink
          title="How privacy mode works"
          description="What is hidden and what privacy mode does not claim"
          topic="privacy"
          icon={<LockKeyhole size={18} color="#58D6FF" />}
        />
        <InformationLink
          title="Permissions used by AdShield"
          description="Why network, file, app-list and notification access are used"
          topic="permissions"
          icon={<Info size={18} color="#58D6FF" />}
        />
        <InformationLink
          title="Notification access status"
          description={`Current Android status: ${notification.label}`}
          topic="notifications"
          icon={<Bell size={18} color="#58D6FF" />}
        />
        <InformationLink
          title="Installed app visibility"
          description="Why Android may not show every installed package"
          topic="visibility"
          icon={<Smartphone size={18} color="#58D6FF" />}
        />

        <View className="mt-2 flex-row items-start rounded-2xl border border-border bg-surfaceHigh/60 p-4">
          <LockKeyhole size={17} color="#8EA0C6" />
          <Text className="ml-2 flex-1 text-xs leading-5 text-textMuted font-sans">
            Settings are stored locally on this device. AdShield does not claim
            that these preferences provide encryption or anonymity.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
