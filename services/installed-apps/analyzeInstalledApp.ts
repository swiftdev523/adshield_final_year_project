import { mapInstalledAppResponse } from "../../lib/installed-apps/mapInstalledAppResponse";
import type { InstalledAppAssessment } from "../../types/installed-app-assessment";
import type { InstalledAppInfo } from "../../types/installed-apps";

type FetchLike = typeof fetch;

type AnalyzeInstalledAppOptions = {
  fetchImpl?: FetchLike;
  apiBaseUrl?: string;
};

export const NO_DECLARED_PERMISSIONS_MESSAGE =
  "No declared permissions were available for permission-based analysis.";

export function createAnalyzeInstalledApp({
  fetchImpl = fetch,
  apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://10.0.2.2:8000",
}: AnalyzeInstalledAppOptions = {}) {
  return async function analyzeInstalledApp(
    app: InstalledAppInfo,
  ): Promise<InstalledAppAssessment> {
    if (app.requestedPermissions.length === 0) {
      throw new Error(NO_DECLARED_PERMISSIONS_MESSAGE);
    }

    const response = await fetchImpl(`${apiBaseUrl.replace(/\/$/, "")}/analyze/apk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        package: app.packageName,
        permissions: app.requestedPermissions,
        install_source: app.installSource,
      }),
    });

    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail =
        body && typeof body === "object" && "detail" in body && typeof body.detail === "string"
          ? body.detail
          : `Analysis failed with HTTP ${response.status}.`;
      throw new Error(detail);
    }
    return mapInstalledAppResponse(body, app);
  };
}

export const analyzeInstalledApp = createAnalyzeInstalledApp();
