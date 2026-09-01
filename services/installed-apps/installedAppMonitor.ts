import { requireNativeModule } from "expo-modules-core";
import { Platform } from "react-native";

import type { InstalledAppInfo } from "../../types/installed-apps";

type InstalledAppMonitorNativeModule = {
  getInstalledApps(): Promise<InstalledAppInfo[]>;
  getInstalledApp(packageName: string): Promise<InstalledAppInfo | null>;
  refreshInstalledApps(): Promise<InstalledAppInfo[]>;
};

function nativeModule(): InstalledAppMonitorNativeModule {
  if (Platform.OS !== "android") {
    throw new Error("Installed app scanning is available on Android only.");
  }
  return requireNativeModule<InstalledAppMonitorNativeModule>(
    "InstalledAppMonitor",
  );
}

export function getInstalledApps() {
  return nativeModule().getInstalledApps();
}

export function getInstalledApp(packageName: string) {
  return nativeModule().getInstalledApp(packageName);
}

export function refreshInstalledApps() {
  return nativeModule().refreshInstalledApps();
}
