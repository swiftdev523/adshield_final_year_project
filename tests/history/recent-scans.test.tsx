import { fireEvent, render, screen } from "@testing-library/react-native";

import RecentScans from "../../components/home/RecentScans";
import { installedHistoryEntry } from "./fixtures";

describe("Home recent scan summaries", () => {
  it("renders real saved assessment fields and opens the selected summary", async () => {
    const onSelect = jest.fn();

    await render(
      <RecentScans
        data={[installedHistoryEntry]}
        status="ready"
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("Example Bank")).toBeTruthy();
    expect(screen.getByText("High Risk")).toBeTruthy();
    expect(screen.getByText("82 / 100")).toBeTruthy();

    fireEvent.press(
      screen.getByLabelText("Open saved scan for Example Bank"),
    );
    expect(onSelect).toHaveBeenCalledWith(installedHistoryEntry);
  });

  it("presents a truthful empty state instead of demonstration scans", async () => {
    await render(
      <RecentScans data={[]} status="ready" onSelect={jest.fn()} />,
    );

    expect(screen.getByText("No completed scans yet")).toBeTruthy();
    expect(screen.queryByText("TikTok")).toBeNull();
    expect(screen.queryByText("WhatsApp")).toBeNull();
  });

  it("shows a recoverable load error without inventing scan results", async () => {
    const onRetry = jest.fn();
    await render(
      <RecentScans
        data={[]}
        status="error"
        error="Local history is unavailable."
        onRetry={onRetry}
        onSelect={jest.fn()}
      />,
    );

    expect(screen.getByText("Scan history could not be loaded")).toBeTruthy();
    expect(screen.getByText("Local history is unavailable.")).toBeTruthy();
    fireEvent.press(screen.getByLabelText("Retry loading scan history"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
