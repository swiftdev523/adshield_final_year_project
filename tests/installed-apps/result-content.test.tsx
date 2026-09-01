import { fireEvent, render, screen } from "@testing-library/react-native";

import InstalledAppResultContent from "../../components/installed-apps/InstalledAppResultContent";
import { mapInstalledAppResponse } from "../../lib/installed-apps/mapInstalledAppResponse";
import {
  benignModerateResponse,
  installedApp,
  response,
} from "./fixtures";

jest.setTimeout(30_000);

describe("installed-app result content", () => {
  it("renders loading and error states", async () => {
    const retry = jest.fn();
    const loading = await render(
      <InstalledAppResultContent
        state={{ status: "loading" }}
        onRetry={retry}
      />,
    );
    expect(screen.getByText("Analyzing app")).toBeTruthy();
    await loading.rerender(
      <InstalledAppResultContent
        state={{ status: "error", message: "Backend offline" }}
        onRetry={retry}
      />,
    );
    expect(screen.getByText("Backend offline")).toBeTruthy();
    fireEvent.press(screen.getByText("Try again"));
    expect(retry).toHaveBeenCalledTimes(1);
  });

  it("renders the required neutral unavailable analysis state", async () => {
    await render(
      <InstalledAppResultContent
        state={{
          status: "unavailable",
          message:
            "No declared permissions were available for permission-based analysis.",
        }}
        onRetry={jest.fn()}
      />,
    );
    expect(screen.getByText("Permission analysis unavailable")).toBeTruthy();
  });

  it("renders all four threat-category states explicitly", async () => {
    const classified = mapInstalledAppResponse(
      response({
        threat_assessment: {
          status: "classified",
          likely_category: "SMS Malware",
        },
      }),
      installedApp,
    );
    const view = await render(
      <InstalledAppResultContent
        state={{ status: "success", assessment: classified }}
        onRetry={jest.fn()}
      />,
    );
    expect(screen.getByText("Likely Threat Category")).toBeTruthy();
    expect(screen.getByText("SMS Malware")).toBeTruthy();

    const uncertain = mapInstalledAppResponse(
      response({
        threat_assessment: {
          status: "uncertain",
          message: "Category unavailable safely.",
        },
      }),
      installedApp,
    );
    await view.rerender(
      <InstalledAppResultContent
        state={{ status: "success", assessment: uncertain }}
        onRetry={jest.fn()}
      />,
    );
    expect(screen.getByText("Uncertain")).toBeTruthy();
    expect(screen.getByText("Category unavailable safely.")).toBeTruthy();

    const unavailable = mapInstalledAppResponse(response(), installedApp);
    await view.rerender(
      <InstalledAppResultContent
        state={{ status: "success", assessment: unavailable }}
        onRetry={jest.fn()}
      />,
    );
    expect(screen.getByText("Unavailable")).toBeTruthy();
    expect(
      screen.getByText(
        "The primary malware assessment completed, but category analysis was unavailable.",
      ),
    ).toBeTruthy();

    const notApplicable = mapInstalledAppResponse(
      benignModerateResponse(),
      installedApp,
    );
    await view.rerender(
      <InstalledAppResultContent
        state={{ status: "success", assessment: notApplicable }}
        onRetry={jest.fn()}
      />,
    );
    expect(screen.getByText("Not applicable")).toBeTruthy();
    expect(
      screen.getByText("No malicious classification was made."),
    ).toBeTruthy();
  });

  it("presents a generic Benign 40/100 result as permission review, not malware", async () => {
    const benign = mapInstalledAppResponse(
      benignModerateResponse(),
      installedApp,
    );
    await render(
      <InstalledAppResultContent
        state={{ status: "success", assessment: benign }}
        onRetry={jest.fn()}
      />,
    );

    expect(
      screen.getAllByText("Permission Review Recommended").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("40")).toBeTruthy();
    expect(
      screen.getByText(/did not find a malware pattern/),
    ).toBeTruthy();
    expect(screen.getByText("Permissions worth reviewing")).toBeTruthy();
    expect(screen.queryByText("Important reasons")).toBeNull();
    expect(screen.queryByText("Assessment overview")).toBeNull();
    expect(screen.queryByText("Permission overview")).toBeNull();
    expect(screen.queryByText("This app can use the camera.")).toBeNull();
    expect(screen.queryByText("No malware indicated")).toBeNull();
    expect(screen.queryByText("Benign")).toBeNull();
    expect(screen.queryByText("Malware characteristics detected")).toBeNull();
    expect(screen.queryByText("Overall risk is Suspicious (40/100).")).toBeNull();

    await fireEvent.press(
      screen.getByLabelText("More information about this app"),
    );

    expect(screen.getByText("Assessment overview")).toBeTruthy();
    expect(screen.getByText("Permission overview")).toBeTruthy();
    expect(screen.getByText("Malware assessment")).toBeTruthy();
    expect(screen.getByText("No malware indicated")).toBeTruthy();
    expect(screen.getByText("40 / 100")).toBeTruthy();
    expect(screen.getByText("This app can use the camera.")).toBeTruthy();
  });

  it("does not expose probability, threshold, margin, model or diagnostics", async () => {
    const benign = mapInstalledAppResponse(
      benignModerateResponse(),
      installedApp,
    );
    const view = await render(
      <InstalledAppResultContent
        state={{ status: "success", assessment: benign }}
        onRetry={jest.fn()}
      />,
    );
    const rendered = JSON.stringify(view.toJSON());

    for (const forbidden of [
      "malware_probability",
      "confidence",
      "category_scores",
      "decision_threshold",
      "top_score",
      "margin",
      "must-not-leak",
    ]) {
      expect(rendered).not.toContain(forbidden);
    }
  });
});
