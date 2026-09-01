export type InstallSource =
  | "google_play_store"
  | "website_download"
  | "apk_sideload"
  | "unknown_source";

export type InstalledAppInfo = {
  appName: string;
  packageName: string;
  versionName: string | null;
  versionCode: number;
  firstInstallTime: number;
  lastUpdateTime: number;
  isSystemApp: boolean;
  isUserInstalledApp: boolean;
  isEnabled: boolean;
  requestedPermissions: string[];
  installerPackageName: string | null;
  installSource: InstallSource;
  installSourceDisplay: string;
  totalPermissionCount: number;
};

export type InstalledAppMonitorNativeModule = {
  getInstalledApps(): Promise<InstalledAppInfo[]>;
  getInstalledApp(packageName: string): Promise<InstalledAppInfo | null>;
  refreshInstalledApps(): Promise<InstalledAppInfo[]>;
};
