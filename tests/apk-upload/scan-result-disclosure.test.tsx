import { fireEvent, render, screen } from "@testing-library/react-native";

import ScanResultScreen from "../../app/scan-result";
import { mapUploadApkResponse } from "../../lib/scan/mapUploadApkResponse";
import { useScanStore } from "../../store/useScanStore";
import { classifiedThreat, uploadResponse } from "./fixtures";

jest.setTimeout(30_000);

jest.mock("expo-router", () => ({
  router: {
    back: jest.fn(),
    canGoBack: jest.fn(() => true),
    replace: jest.fn(),
  },
}));

describe("APK result information disclosure", () => {
  beforeEach(() => {
    useScanStore.setState({
      process: {
        status: "success",
        asset: {
          uri: "file:///sample.apk",
          name: "sample.apk",
          mimeType: "application/vnd.android.package-archive",
        },
        assessment: mapUploadApkResponse(
          uploadResponse({ threat_assessment: classifiedThreat("Adware") }),
        ),
      },
    });
  });

  it("keeps threat category visible before optional assessment details", async () => {
    await render(<ScanResultScreen />);

    expect(screen.getByText("Likely Threat Category")).toBeTruthy();
    expect(screen.getByText("Adware")).toBeTruthy();
    expect(screen.getByText("Permissions worth reviewing")).toBeTruthy();
    expect(screen.queryByText("Assessment overview")).toBeNull();
    expect(screen.queryByText("Permission findings")).toBeNull();

    await fireEvent.press(
      screen.getByLabelText("More information about this APK"),
    );

    expect(screen.getByText("Assessment overview")).toBeTruthy();
    expect(screen.getByText("Malware assessment")).toBeTruthy();
    expect(screen.getByText("Permission findings")).toBeTruthy();
  });
});
