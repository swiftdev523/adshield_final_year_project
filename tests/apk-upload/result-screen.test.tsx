import { fireEvent, render, screen } from "@testing-library/react-native";

import ScanResultScreen from "../../app/scan-result";
import { mapUploadApkResponse } from "../../lib/scan/mapUploadApkResponse";
import type { ScanProcess } from "../../store/useScanStore";
import { benignModerateUploadResponse, uploadResponse } from "./fixtures";

let mockProcess: ScanProcess;

jest.mock("expo-router", () => ({
  router: {
    back: jest.fn(),
    canGoBack: jest.fn(() => true),
    replace: jest.fn(),
  },
}));

jest.mock("../../store/useScanStore", () => ({
  useScanStore: (selector: (state: { process: ScanProcess }) => unknown) =>
    selector({ process: mockProcess }),
}));

const asset = {
  uri: "file:///downloads/sample.apk",
  name: "sample.apk",
  mimeType: "application/vnd.android.package-archive",
};

describe("APK result screen presentation", () => {
  it("renders a generic Benign 40/100 result without calling it malware", async () => {
    mockProcess = {
      status: "success",
      asset,
      assessment: mapUploadApkResponse(benignModerateUploadResponse()),
    };

    const view = await render(<ScanResultScreen />);

    expect(
      screen.getAllByText("Permission Review Recommended").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("40")).toBeTruthy();
    expect(screen.getByText("Not applicable")).toBeTruthy();
    expect(
      screen.getByText("No malicious classification was made."),
    ).toBeTruthy();
    expect(screen.getByText(/did not find a malware pattern/)).toBeTruthy();
    expect(screen.queryByText("No malware indicated")).toBeNull();
    expect(screen.queryByText("40 / 100")).toBeNull();
    expect(screen.queryByText("Benign")).toBeNull();
    expect(screen.queryByText("Overall risk is Suspicious (40/100).")).toBeNull();

    await fireEvent.press(
      screen.getByLabelText("More information about this APK"),
    );
    expect(screen.getByText("No malware indicated")).toBeTruthy();
    expect(screen.getByText("40 / 100")).toBeTruthy();

    const rendered = JSON.stringify(view.toJSON());
    for (const forbidden of [
      "malware_probability",
      "confidence",
      "decision_threshold",
      "top_score",
      "margin",
      "must-not-leak",
    ]) {
      expect(rendered).not.toContain(forbidden);
    }
  });

  it("renders malicious null category data as unavailable", async () => {
    mockProcess = {
      status: "success",
      asset,
      assessment: mapUploadApkResponse(uploadResponse()),
    };

    await render(<ScanResultScreen />);

    expect(screen.getByText("Unavailable")).toBeTruthy();
    expect(
      screen.getByText(
        "The primary malware assessment completed, but category analysis was unavailable.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("Malware characteristics detected")).toBeNull();
    expect(screen.queryByText("Uncertain")).toBeNull();

    await fireEvent.press(
      screen.getByLabelText("More information about this APK"),
    );
    expect(screen.getByText("Malware characteristics detected")).toBeTruthy();
  });
});
