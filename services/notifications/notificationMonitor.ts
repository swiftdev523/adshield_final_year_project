import { requireNativeModule } from "expo-modules-core";
import { Platform } from "react-native";

import type {
  NativeNotificationAppSummary,
  NotificationAnalysisText,
  ObservedNotification,
} from "../../types/notifications";

export type NotificationMonitorNativeModule = {
  hasNotificationAccess(): Promise<boolean>;
  openNotificationAccessSettings(): Promise<void>;
  getNotificationSummary(): Promise<NativeNotificationAppSummary[]>;
  getRecentNotifications(limit?: number): Promise<ObservedNotification[]>;
  getNotificationAnalysisText(eventKey: string): Promise<NotificationAnalysisText>;
  clearLocalNotificationHistory(): Promise<void>;
};

export type NotificationMonitorClient = NotificationMonitorNativeModule;

export class NotificationMonitorUnavailableError extends Error {
  constructor(message = "Notification monitoring is unavailable on this device.") {
    super(message);
    this.name = "NotificationMonitorUnavailableError";
  }
}

export function createNotificationMonitorClient(
  nativeModule: NotificationMonitorNativeModule,
): NotificationMonitorClient {
  return {
    hasNotificationAccess: () => nativeModule.hasNotificationAccess(),
    openNotificationAccessSettings: () =>
      nativeModule.openNotificationAccessSettings(),
    getNotificationSummary: () => nativeModule.getNotificationSummary(),
    getRecentNotifications: (limit?: number) => {
      if (
        limit !== undefined &&
        (!Number.isInteger(limit) || limit <= 0)
      ) {
        return Promise.reject(
          new RangeError("Notification history limit must be a positive integer."),
        );
      }

      return limit === undefined
        ? nativeModule.getRecentNotifications()
        : nativeModule.getRecentNotifications(limit);
    },
    getNotificationAnalysisText: (eventKey: string) => {
      const normalizedEventKey = eventKey.trim();
      if (!normalizedEventKey) {
        return Promise.reject(
          new RangeError("Notification event key must not be empty."),
        );
      }
      return nativeModule.getNotificationAnalysisText(normalizedEventKey);
    },
    clearLocalNotificationHistory: () =>
      nativeModule.clearLocalNotificationHistory(),
  };
}

function getNativeModule(): NotificationMonitorNativeModule {
  if (Platform.OS !== "android") {
    throw new NotificationMonitorUnavailableError(
      "Notification monitoring is available on Android only.",
    );
  }

  try {
    return requireNativeModule<NotificationMonitorNativeModule>(
      "NotificationMonitor",
    );
  } catch {
    throw new NotificationMonitorUnavailableError(
      "The notification monitoring module is not available in this app build.",
    );
  }
}

function client(): NotificationMonitorClient {
  return createNotificationMonitorClient(getNativeModule());
}

export function hasNotificationAccess(): Promise<boolean> {
  return client().hasNotificationAccess();
}

export function openNotificationAccessSettings(): Promise<void> {
  return client().openNotificationAccessSettings();
}

export function getNotificationSummary(): Promise<NativeNotificationAppSummary[]> {
  return client().getNotificationSummary();
}

export function getRecentNotifications(
  limit?: number,
): Promise<ObservedNotification[]> {
  return client().getRecentNotifications(limit);
}

export function getNotificationAnalysisText(
  eventKey: string,
): Promise<NotificationAnalysisText> {
  return client().getNotificationAnalysisText(eventKey);
}

export function clearLocalNotificationHistory(): Promise<void> {
  return client().clearLocalNotificationHistory();
}
