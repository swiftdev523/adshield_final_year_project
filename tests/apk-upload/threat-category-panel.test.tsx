import { render, screen } from "@testing-library/react-native";

import ThreatCategoryPanel from "../../components/assessment/ThreatCategoryPanel";

describe("ThreatCategoryPanel", () => {
  it("renders the shared classified state", async () => {
    await render(
      <ThreatCategoryPanel
        modelPrediction="Malicious"
        threatAssessment={{
          status: "classified",
          likelyCategory: "Riskware",
        }}
      />,
    );
    expect(screen.getByText("Likely Threat Category")).toBeTruthy();
    expect(screen.getByText("Riskware")).toBeTruthy();
  });

  it("renders the shared uncertain state using the backend message", async () => {
    await render(
      <ThreatCategoryPanel
        modelPrediction="Malicious"
        threatAssessment={{
          status: "uncertain",
          message: "The category cannot be assigned safely.",
        }}
      />,
    );
    expect(screen.getByText("Uncertain")).toBeTruthy();
    expect(
      screen.getByText("The category cannot be assigned safely."),
    ).toBeTruthy();
  });

  it("distinguishes unavailable from uncertain", async () => {
    await render(
      <ThreatCategoryPanel
        modelPrediction="Malicious"
        threatAssessment={null}
      />,
    );
    expect(screen.getByText("Unavailable")).toBeTruthy();
    expect(screen.queryByText("Uncertain")).toBeNull();
  });

  it("renders not applicable for Benign even if stale category data exists", async () => {
    await render(
      <ThreatCategoryPanel
        modelPrediction="Benign"
        threatAssessment={{ status: "classified", likelyCategory: "Adware" }}
      />,
    );
    expect(screen.getByText("Not applicable")).toBeTruthy();
    expect(screen.getByText("No malicious classification was made.")).toBeTruthy();
    expect(screen.queryByText("Adware")).toBeNull();
  });
});
