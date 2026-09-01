import { fireEvent, render, screen } from "@testing-library/react-native";
import { router } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";

import SettingsScreen from "../../app/(tabs)/settings";
import type { AlertState } from "../../store/useAlertStore";
import type { SettingsState } from "../../store/useSettingsStore";

let mockAlertState: AlertState;
let mockSettingsState: SettingsState;

jest.mock("expo-router", () => ({
  router: { push: jest.fn() },
  useFocusEffect: () => undefined,
}));

jest.mock("../../store/useAlertStore", () => ({
  useAlertStore: (selector: (state: AlertState) => unknown) =>
    selector(mockAlertState),
}));

jest.mock("../../store/useSettingsStore", () => ({
  useSettingsStore: (selector: (state: SettingsState) => unknown) =>
    selector(mockSettingsState),
}));

const renderSettings = () =>
  render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { x: 0, y: 0, width: 360, height: 720 },
        insets: { top: 0, right: 0, bottom: 0, left: 0 },
      }}>
      <SettingsScreen />
    </SafeAreaProvider>,
  );

describe("truthful persisted settings controls", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSettingsState = {
      privacyMode: false,
      status: "ready",
      error: null,
      hydrate: jest.fn().mockResolvedValue(true),
      setPrivacyMode: jest.fn().mockResolvedValue(true),
    };
    mockAlertState = {
      accessStatus: "granted",
      accessError: null,
      accessChanges: [],
      loadStatus: "success",
      loadError: null,
      summaries: [],
      events: [],
      analysisByEventKey: {},
      spamBannerDismissed: false,
      checkAccessAndLoad: jest.fn().mockResolvedValue(undefined),
      refresh: jest.fn().mockResolvedValue(undefined),
      openAccessSettings: jest.fn().mockResolvedValue(undefined),
      clearLocalHistory: jest.fn().mockResolvedValue(undefined),
      analyzeEvent: jest.fn().mockResolvedValue(undefined),
      dismissSpamBanner: jest.fn(),
      resetSpamBanner: jest.fn(),
    };
  });

  it("shows actual notification access and does not claim download monitoring", async () => {
    await renderSettings();

    expect(screen.getByText("Notification monitoring")).toBeTruthy();
    expect(screen.getByText("Enabled")).toBeTruthy();
    expect(screen.getByText("Planned - not active")).toBeTruthy();
    expect(screen.queryByText(/Real-time protection/i)).toBeNull();
    expect(
      screen.getByLabelText("Auto-scan downloads planned and unavailable").props
        .disabled,
    ).toBe(true);
  });

  it("wires privacy and notification controls to their real actions", async () => {
    await renderSettings();

    await fireEvent(
      screen.getByLabelText("Privacy mode"),
      "valueChange",
      true,
    );
    expect(mockSettingsState.setPrivacyMode).toHaveBeenCalledWith(true);

    await fireEvent.press(
      screen.getByLabelText("Manage notification access in Android settings"),
    );
    expect(mockAlertState.openAccessSettings).toHaveBeenCalledTimes(1);

    await fireEvent.press(screen.getByLabelText("Installed app visibility"));
    expect(router.push).toHaveBeenCalledWith({
      pathname: "/settings-info",
      params: { topic: "visibility" },
    });
  });
});
