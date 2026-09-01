import { render, screen } from "@testing-library/react-native";
import React from "react";

import ActivityFeed from "../../components/home/ActivityFeed";
import HomeStats from "../../components/home/HomeStats";

describe("Home real-data components", () => {
  it("renders real counters and latest status without a percentage score", async () => {
    await render(
      <HomeStats safeResults={4} threats={1} latestStatus="Suspicious" />,
    );

    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
    expect(screen.getByText("Suspicious")).toBeTruthy();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.getByText("Safe Results")).toBeTruthy();
    expect(screen.getByText("Latest Scan")).toBeTruthy();
  });

  it(
    "shows honest loading and empty activity states",
    async () => {
      const loading = await render(<ActivityFeed data={[]} loading />);
      expect(
        screen.getByText("Loading recent security activity..."),
      ).toBeTruthy();
      await loading.rerender(<ActivityFeed data={[]} />);
      expect(screen.getByText("No recorded security activity yet")).toBeTruthy();
    },
    30_000,
  );

  it("renders an actual timestamped activity item", async () => {
    jest.spyOn(Date, "now").mockReturnValue(1_800_000_060_000);
    try {
      await render(
        <ActivityFeed
          data={[
            {
              id: "scan-real-1",
              level: "safe",
              text: "Calculator scan completed: Safe",
              occurredAt: 1_800_000_000_000,
            },
          ]}
        />,
      );
      expect(screen.getByText("Calculator scan completed: Safe")).toBeTruthy();
      expect(screen.getByText("1m ago")).toBeTruthy();
    } finally {
      jest.restoreAllMocks();
    }
  });
});
