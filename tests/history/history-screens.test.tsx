import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react-native";
import { router } from "expo-router";
import { Alert } from "react-native";

import ScanHistoryDetailScreen from "../../app/scan-history-detail";
import ScanHistoryScreen from "../../app/scan-history";
import type { ScanHistoryState } from "../../store/useScanHistoryStore";
import { installedHistoryEntry } from "./fixtures";

let mockParams: { id?: string } = {};
let mockHistoryState: ScanHistoryState;

jest.mock("expo-router", () => ({
  router: {
    back: jest.fn(),
    push: jest.fn(),
  },
  useFocusEffect: jest.fn(),
  useLocalSearchParams: () => mockParams,
}));

jest.mock("../../store/useScanHistoryStore", () => ({
  useScanHistoryStore: (selector: (state: ScanHistoryState) => unknown) =>
    selector(mockHistoryState),
}));

function readyState(
  overrides: Partial<ScanHistoryState> = {},
): ScanHistoryState {
  const entries = [installedHistoryEntry];
  return {
    entries,
    status: "ready",
    error: null,
    loadHistory: jest.fn().mockResolvedValue(true),
    recordApkScan: jest.fn().mockResolvedValue(true),
    recordInstalledAppScan: jest.fn().mockResolvedValue(true),
    deleteEntry: jest.fn().mockResolvedValue(true),
    clearHistory: jest.fn().mockResolvedValue(true),
    getEntryById: (id) => entries.find((entry) => entry.id === id),
    ...overrides,
  };
}

describe("saved scan history screens", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockParams = {};
    mockHistoryState = readyState();
  });

  it("opens exactly the selected local summary", async () => {
    await render(<ScanHistoryScreen />);

    fireEvent.press(
      screen.getByLabelText("Open saved scan for Example Bank"),
    );
    expect(router.push).toHaveBeenCalledWith({
      pathname: "/scan-history-detail",
      params: { id: installedHistoryEntry.id },
    });

  });

  it("deletes exactly the selected local summary", async () => {
    await render(<ScanHistoryScreen />);

    fireEvent.press(
      screen.getByLabelText("Delete saved scan for Example Bank"),
    );

    await waitFor(() =>
      expect(mockHistoryState.deleteEntry).toHaveBeenCalledWith(
        installedHistoryEntry.id,
      ),
    );
  });

  it("requires confirmation before clearing local history", async () => {
    const alert = jest.spyOn(Alert, "alert").mockImplementation(jest.fn());
    await render(<ScanHistoryScreen />);

    fireEvent.press(screen.getByLabelText("Clear scan history"));
    expect(alert).toHaveBeenCalledTimes(1);

    const buttons = alert.mock.calls[0][2] ?? [];
    buttons.find(({ text }) => text === "Cancel")?.onPress?.();
    expect(mockHistoryState.clearHistory).not.toHaveBeenCalled();

    buttons.find(({ text }) => text === "Clear history")?.onPress?.();
    await waitFor(() =>
      expect(mockHistoryState.clearHistory).toHaveBeenCalledTimes(1),
    );
    alert.mockRestore();
  });

  it("shows only the saved summary and does not offer an automatic rerun", async () => {
    mockParams = { id: installedHistoryEntry.id };
    await render(<ScanHistoryDetailScreen />);

    expect(screen.getByText("Saved Scan Summary")).toBeTruthy();
    expect(screen.getByText("Example Bank")).toBeTruthy();
    expect(screen.getByText("82")).toBeTruthy();
    expect(screen.getByText("Banking Malware")).toBeTruthy();
    expect(screen.getByText("Google Play Store")).toBeTruthy();
    expect(
      screen.getByText(/Viewing it does not rerun analysis or contact the backend/),
    ).toBeTruthy();
    expect(screen.queryByText(/Analyze again/i)).toBeNull();
    expect(mockHistoryState.loadHistory).not.toHaveBeenCalled();
  });

  it("renders a truthful missing-summary state", async () => {
    mockParams = { id: "deleted-entry" };
    await render(<ScanHistoryDetailScreen />);

    expect(screen.getByText("Saved scan not found")).toBeTruthy();
    expect(screen.getByText(/may have been deleted/)).toBeTruthy();
  });
});
