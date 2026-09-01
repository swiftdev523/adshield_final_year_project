/** @jest-environment node */
import { readFileSync } from "fs";
import { resolve } from "path";

const productionFiles = [
  "app/(tabs)/alerts.tsx",
  "components/alerts/NotificationListItem.tsx",
  "components/alerts/SpamBanner.tsx",
  "components/alerts/StatBar.tsx",
  "store/useAlertStore.ts",
  "services/notifications/notificationMonitor.ts",
  "services/notifications/analyzeNotification.ts",
  "lib/notifications/eventSummary.ts",
];

describe("notification production data boundary", () => {
  test.each(productionFiles)("%s does not consume mock notification data", (path) => {
    const source = readFileSync(resolve(process.cwd(), path), "utf8");
    expect(source).not.toMatch(/mockData|notificationApps/);
    expect(source).not.toContain("ShopDeals Pro");
    expect(source).not.toContain("CashLoan Fast");
    expect(source).not.toContain("BetNow");
    expect(source).not.toContain("10 apps monitored");
  });
});

describe("notification event-level production boundary", () => {
  it("does not restore package-level classifier state or automatic analysis", () => {
    const storeSource = readFileSync(
      resolve(process.cwd(), "store/useAlertStore.ts"),
      "utf8",
    );

    expect(storeSource).not.toContain("analysisByPackage");
    expect(storeSource).not.toContain("analyzePackage");
    expect(storeSource).toContain("analysisByEventKey");
    expect(storeSource).toContain("analyzeEvent(eventKey");
  });

  it("keeps the backend payload text-only and bulk native history metadata-only", () => {
    const transportSource = readFileSync(
      resolve(process.cwd(), "services/notifications/analyzeNotification.ts"),
      "utf8",
    );
    const typeSource = readFileSync(
      resolve(process.cwd(), "types/notifications.ts"),
      "utf8",
    );

    expect(transportSource).toContain("JSON.stringify({ text: cleaned })");
    expect(transportSource).not.toContain("JSON.stringify({ text: cleaned, package");
    const observedType = typeSource.slice(
      typeSource.indexOf("export type ObservedNotification"),
      typeSource.indexOf("export type NotificationAnalysisText"),
    );
    expect(observedType).not.toContain("analysisText");
  });
});
