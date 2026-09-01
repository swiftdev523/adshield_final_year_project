import { fireEvent, render, screen } from "@testing-library/react-native";

import InstalledAppDetailsScreen from "../../app/installed-app-details";
import { useInstalledAppsStore } from "../../store/useInstalledAppsStore";
import { installedApp } from "./fixtures";

jest.mock("expo-router", () => ({
  router: { back: jest.fn(), push: jest.fn() },
  useLocalSearchParams: jest.fn(() => ({
    packageName: "com.example.messenger",
  })),
}));

describe("installed app permission disclosure", () => {
  beforeEach(() => {
    useInstalledAppsStore.setState({
      apps: [installedApp],
      inventoryStatus: "success",
      inventoryError: null,
      selectedApp: installedApp,
      analysis: { status: "idle" },
    });
  });

  it("keeps a long permission list hidden until its count is pressed", async () => {
    await render(<InstalledAppDetailsScreen />);

    expect(screen.getByText("Declared permissions (2)")).toBeTruthy();
    expect(screen.queryByText("• android.permission.CAMERA")).toBeNull();

    await fireEvent.press(screen.getByLabelText("Declared permissions (2)"));

    expect(screen.getByText("• android.permission.CAMERA")).toBeTruthy();
    expect(screen.getByText("• android.permission.INTERNET")).toBeTruthy();
  });
});
