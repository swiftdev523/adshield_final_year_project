import { Text, View } from "react-native";

import type { InstalledAppInfo } from "../../types/installed-apps";

type Props = { app: InstalledAppInfo };

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between border-b border-border/60 py-3 last:border-b-0">
      <Text className="mr-4 text-xs text-textMuted">{label}</Text>
      <Text className="flex-1 text-right text-xs text-textPrimary">{value}</Text>
    </View>
  );
}

const date = (value: number) =>
  value > 0 ? new Date(value).toLocaleString() : "Unavailable";

export default function InstalledAppMetadata({ app }: Props) {
  return (
    <View className="rounded-3xl border border-border bg-surface px-4">
      <Row label="Package" value={app.packageName} />
      <Row label="Version" value={`${app.versionName ?? "Unknown"} (${app.versionCode})`} />
      <Row label="First installed" value={date(app.firstInstallTime)} />
      <Row label="Last updated" value={date(app.lastUpdateTime)} />
      <Row label="App type" value={app.isSystemApp ? "System app" : "User-installed app"} />
      <Row label="Enabled" value={app.isEnabled ? "Yes" : "No"} />
      <Row label="Install source" value={app.installSourceDisplay} />
      <Row label="Installer package" value={app.installerPackageName ?? "Unavailable"} />
    </View>
  );
}
