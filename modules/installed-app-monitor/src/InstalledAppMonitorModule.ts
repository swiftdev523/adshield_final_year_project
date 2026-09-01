import { requireNativeModule } from "expo-modules-core";

import type { InstalledAppMonitorNativeModule } from "./InstalledAppMonitor.types";

export default requireNativeModule<InstalledAppMonitorNativeModule>(
  "InstalledAppMonitor",
);
