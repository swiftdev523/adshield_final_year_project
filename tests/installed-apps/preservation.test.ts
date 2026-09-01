/** @jest-environment node */
import { createHash } from "crypto";
import { readFileSync } from "fs";
import { resolve } from "path";

const workspaceRoot = resolve(process.cwd(), "..");
const manifestPath = resolve(
  workspaceRoot,
  "backups/phase1_20260808_preimplementation/protected-files.sha256",
);

// These files are intentionally in scope for the approved assessment,
// category-eligibility and binary-contract diagnostic phases. The boundary
// continues to protect model artifacts, native scanner code, transports,
// stores, package files and all dependency patches except the explicitly
// approved Gradle-plugin path fix and later user-approved UI corrections below.
const approvedChanges = new Set([
  "adshield_final_year_project-main/package.json",
  "adshield_final_year_project-main/package-lock.json",
  "adshield_final_year_project-main/store/useScanStore.ts",
  "adshield_final_year_project-main/store/useInstalledAppsStore.ts",
  "adshield_final_year_project-main/tests/installed-apps/store.test.ts",
  "adshield_final_year_project-main/components/installed-apps/AssessmentRiskMeter.tsx",
  "adshield_final_year_project-main/components/installed-apps/InstalledAppResultContent.tsx",
  "adshield_final_year_project-main/app/installed-app-details.tsx",
  "adshield_final_year_project-main/lib/installed-apps/mapInstalledAppResponse.ts",
  "adshield_final_year_project-main/tests/installed-apps/fixtures.ts",
  "adshield_final_year_project-main/tests/installed-apps/response-adapter.test.ts",
  "adshield_final_year_project-main/tests/installed-apps/result-content.test.tsx",
  "adshield_final_year_project-main/types/installed-app-assessment.ts",
  "adshield_final_year_project-main/patches/@react-native+gradle-plugin+0.81.5.patch",
  "backend/app/config.py",
  "backend/app/schemas/assessment.py",
  "backend/app/services/apk_model_service.py",
  "backend/app/services/assessment_integrator.py",
  "backend/app/services/category_model_service.py",
]);

const protectedHashes = readFileSync(manifestPath, "utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => {
    const match = /^([a-f0-9]{64})  (.+)$/.exec(line);
    if (!match) throw new Error(`Invalid protected-file manifest line: ${line}`);
    return { expected: match[1], path: match[2] };
  })
  .filter(({ path }) => !approvedChanges.has(path));

describe("Phase 1 Installed App Scanner preservation boundary", () => {
  test.each(protectedHashes)("$path remains byte-for-byte unchanged", ({ path, expected }) => {
    const digest = createHash("sha256")
      .update(readFileSync(resolve(workspaceRoot, path)))
      .digest("hex");
    expect(digest).toBe(expected);
  });
});
