/** @jest-environment node */
import { readFileSync } from "fs";
import { resolve } from "path";

import { SCAN_HISTORY_PERSISTED_FIELDS } from "../../types/scan-history";

const projectRoot = process.cwd();

describe("Phase 3 production boundaries", () => {
  it("Home no longer imports demonstration recent scans", () => {
    const home = readFileSync(
      resolve(projectRoot, "app", "(tabs)", "index.tsx"),
      "utf8",
    );

    expect(home).toContain("useScanHistoryStore");
    expect(home).not.toMatch(/\brecentScans\b/);
    expect(home).not.toContain("Recently Scanned — Demo");
  });

  it("the persisted entry type contains exactly the approved summary fields", () => {
    expect(SCAN_HISTORY_PERSISTED_FIELDS).toEqual([
      "id",
      "source",
      "appName",
      "packageOrFilename",
      "timestamp",
      "overallScore",
      "overallLevel",
      "binaryResult",
      "threatCategoryStatus",
      "threatCategory",
      "installSourceDisplay",
    ]);
  });
});
