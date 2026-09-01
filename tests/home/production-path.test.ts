/** @jest-environment node */
import { readFileSync } from "fs";
import { resolve } from "path";

const projectRoot = resolve(__dirname, "../..");

describe("Phase 4 production Home path", () => {
  it("contains no fixed protection statistics or fabricated activity import", () => {
    const home = readFileSync(
      resolve(projectRoot, "app/(tabs)/index.tsx"),
      "utf8",
    );
    const mocks = readFileSync(resolve(projectRoot, "lib/mockData.ts"), "utf8");

    expect(home).not.toMatch(/recentActivity|DEVICE PROTECTED|All systems active/);
    expect(home).not.toMatch(/safeApps=\{21\}|threats=\{2\}|score=\{98\}/);
    expect(home).not.toMatch(/Last scan: 2 hours ago|>\s*23\s*</);
    expect(mocks).not.toMatch(/recentActivity|Unknown\.apk flagged|ShopDeals Pro sending spam/);
  });

  it("derives Home from the real scan-history and notification stores", () => {
    const home = readFileSync(
      resolve(projectRoot, "app/(tabs)/index.tsx"),
      "utf8",
    );

    expect(home).toMatch(/useScanHistoryStore/);
    expect(home).toMatch(/useAlertStore/);
    expect(home).toMatch(/deriveHomeMetrics/);
    expect(home).toMatch(/deriveHomeActivity/);
  });
});
