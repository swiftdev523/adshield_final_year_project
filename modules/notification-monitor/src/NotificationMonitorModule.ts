import { requireNativeModule } from "expo-modules-core";

import type { NotificationMonitorNativeModule } from "./NotificationMonitor.types";

export default requireNativeModule<NotificationMonitorNativeModule>(
  "NotificationMonitor",
);
