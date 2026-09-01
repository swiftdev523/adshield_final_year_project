import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { ArrowLeft, ExternalLink } from "lucide-react-native";
import { useCallback } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Card from "../components/ui/Card";
import { useAlertStore } from "../store/useAlertStore";

type Topic = "privacy" | "permissions" | "notifications" | "visibility";
type Page = {
  title: string;
  introduction: string;
  sections: { heading: string; body: string }[];
};

const isTopic = (value: string | string[] | undefined): value is Topic =>
  typeof value === "string" &&
  ["privacy", "permissions", "notifications", "visibility"].includes(value);

const notificationStatusText = (status: string): string => {
  if (status === "granted") return "Enabled in Android settings";
  if (status === "not_granted") return "Not enabled in Android settings";
  if (status === "checking" || status === "unknown") {
    return "Checking Android settings...";
  }
  if (status === "unavailable") return "Not available on this device";
  return "Status could not be checked";
};

const pages: Record<Exclude<Topic, "notifications">, Page> = {
  privacy: {
    title: "Privacy mode",
    introduction:
      "Privacy mode shortens app names on summary and report screens when someone may be looking over your shoulder.",
    sections: [
      {
        heading: "What it changes",
        body: "App names are shortened in Home, scan history, notification summaries and analysis results. Installed-app selection keeps full names so you can choose the correct app.",
      },
      {
        heading: "What it does not do",
        body: "Privacy mode does not encrypt, anonymize or delete data. It only changes how supported names are displayed.",
      },
    ],
  },
  permissions: {
    title: "Permissions used by AdShield",
    introduction:
      "AdShield uses access for the features you choose to use.",
    sections: [
      {
        heading: "Internet access",
        body: "Used to send an explicitly selected APK or selected app permission list to your configured analysis backend.",
      },
      {
        heading: "Notification access (optional)",
        body: "Android special access is required for notification monitoring. You grant or remove it in Android settings.",
      },
      {
        heading: "App visibility",
        body: "AdShield asks Android for launcher-visible apps. It does not request a complete list of every installed package.",
      },
      {
        heading: "Selected APK files",
        body: "Android's file picker grants access to the APK you select. AdShield does not automatically watch your Downloads folder.",
      },
    ],
  },
  visibility: {
    title: "Installed app visibility",
    introduction:
      "Android limits which installed apps another app can see.",
    sections: [
      {
        heading: "What appears in the scanner",
        body: "The list contains apps that Android reports as launcher-visible. Some system, background-only or hidden apps may not appear.",
      },
      {
        heading: "What leaves the phone",
        body: "The list is read locally. Only the app you select and its declared permissions are submitted for analysis.",
      },
    ],
  },
};

export default function SettingsInfoScreen() {
  const params = useLocalSearchParams<{ topic?: string | string[] }>();
  const topic: Topic = isTopic(params.topic) ? params.topic : "privacy";
  const accessStatus = useAlertStore((state) => state.accessStatus);
  const checkAccess = useAlertStore((state) => state.checkAccessAndLoad);
  const openAccessSettings = useAlertStore((state) => state.openAccessSettings);

  useFocusEffect(
    useCallback(() => {
      if (topic === "notifications") void checkAccess();
    }, [checkAccess, topic]),
  );

  const page: Page =
    topic === "notifications"
      ? {
          title: "Notification access status",
          introduction:
            "Notification monitoring works only while Android notification access is enabled for AdShield.",
          sections: [
            {
              heading: "Current status",
              body: notificationStatusText(accessStatus),
            },
            {
              heading: "How it works",
              body: "AdShield records eligible notification activity locally. Notification text is sent to the backend only when you explicitly choose Analyze for that event.",
            },
          ],
        }
      : pages[topic];

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 48 }}>
        <View className="mb-5 flex-row items-center gap-3">
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={() => router.back()}
            className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh">
            <ArrowLeft size={18} color="#8EA0C6" />
          </Pressable>
          <Text className="flex-1 font-heading text-2xl text-textPrimary">
            {page.title}
          </Text>
        </View>

        <Text className="text-sm leading-6 text-textMuted font-sans">
          {page.introduction}
        </Text>
        {page.sections.map((section) => (
          <Card key={section.heading} className="mt-4 bg-surfaceHigh/80">
            <Text className="font-heading text-base text-textPrimary">
              {section.heading}
            </Text>
            <Text className="mt-2 text-sm leading-6 text-textMuted font-sans">
              {section.body}
            </Text>
          </Card>
        ))}

        {topic === "notifications" ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Open Android notification access settings"
            onPress={() => void openAccessSettings()}
            className="mt-5 flex-row items-center justify-center rounded-2xl bg-accent px-5 py-4">
            <Text className="mr-2 font-semibold text-background font-sans">
              Open Android notification access
            </Text>
            <ExternalLink size={17} color="#0B1020" />
          </Pressable>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
