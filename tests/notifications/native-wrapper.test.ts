import {
  createNotificationMonitorClient,
  type NotificationMonitorNativeModule,
} from "../../services/notifications/notificationMonitor";
import {
  nativeNotificationSummary,
  notificationAnalysisText,
  observedNotification,
} from "./fixtures";

function nativeModule(): jest.Mocked<NotificationMonitorNativeModule> {
  return {
    hasNotificationAccess: jest.fn().mockResolvedValue(true),
    openNotificationAccessSettings: jest.fn().mockResolvedValue(undefined),
    getNotificationSummary: jest
      .fn()
      .mockResolvedValue([nativeNotificationSummary()]),
    getRecentNotifications: jest
      .fn()
      .mockResolvedValue([observedNotification()]),
    getNotificationAnalysisText: jest
      .fn()
      .mockResolvedValue(notificationAnalysisText()),
    clearLocalNotificationHistory: jest.fn().mockResolvedValue(undefined),
  };
}

describe("NotificationMonitor native wrapper", () => {
  it("forwards the exact native contract", async () => {
    const native = nativeModule();
    const client = createNotificationMonitorClient(native);

    await expect(client.hasNotificationAccess()).resolves.toBe(true);
    await expect(client.openNotificationAccessSettings()).resolves.toBeUndefined();
    await expect(client.getNotificationSummary()).resolves.toEqual([
      nativeNotificationSummary(),
    ]);
    await expect(client.getRecentNotifications(25)).resolves.toEqual([
      observedNotification(),
    ]);
    await expect(client.getNotificationAnalysisText("event-1")).resolves.toEqual(
      notificationAnalysisText(),
    );
    await expect(client.clearLocalNotificationHistory()).resolves.toBeUndefined();

    expect(native.hasNotificationAccess).toHaveBeenCalledTimes(1);
    expect(native.openNotificationAccessSettings).toHaveBeenCalledTimes(1);
    expect(native.getNotificationSummary).toHaveBeenCalledTimes(1);
    expect(native.getRecentNotifications).toHaveBeenCalledWith(25);
    expect(native.getNotificationAnalysisText).toHaveBeenCalledWith("event-1");
    expect(native.clearLocalNotificationHistory).toHaveBeenCalledTimes(1);
  });

  it("omits the optional argument when no history limit is supplied", async () => {
    const native = nativeModule();
    await createNotificationMonitorClient(native).getRecentNotifications();
    expect(native.getRecentNotifications).toHaveBeenCalledWith();
  });

  it.each([0, -1, 1.5])(
    "rejects invalid history limit %s before crossing the native bridge",
    async (limit) => {
      const native = nativeModule();
      await expect(
        createNotificationMonitorClient(native).getRecentNotifications(limit),
      ).rejects.toThrow("positive integer");
      expect(native.getRecentNotifications).not.toHaveBeenCalled();
    },
  );

  it("rejects an empty event key before crossing the native bridge", async () => {
    const native = nativeModule();
    await expect(
      createNotificationMonitorClient(native).getNotificationAnalysisText("   "),
    ).rejects.toThrow("must not be empty");
    expect(native.getNotificationAnalysisText).not.toHaveBeenCalled();
  });
});
