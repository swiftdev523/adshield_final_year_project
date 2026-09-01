import { render, screen } from "@testing-library/react-native";

import RiskMeter from "../../components/ui/RiskMeter";

describe("RiskMeter", () => {
  it("renders the supplied backend risk level instead of deriving a local band", async () => {
    await render(
      <RiskMeter
        score={99}
        level="Safe"
        reviewLabel="Low Permission Concern"
      />,
    );

    expect(screen.getByText("99")).toBeTruthy();
    expect(screen.getByText("out of 100")).toBeTruthy();
    expect(screen.getByText("Low Permission Concern")).toBeTruthy();
    expect(screen.queryByText("HIGH RISK")).toBeNull();
  });
});
