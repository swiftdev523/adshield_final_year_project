import { createAnalyzeInstalledApp, NO_DECLARED_PERMISSIONS_MESSAGE } from "../../services/installed-apps/analyzeInstalledApp";
import { installedApp, response } from "./fixtures";

describe("selected-app transport", () => {
  it("submits only the selected app contract", async () => {
    const fetchImpl = jest.fn().mockResolvedValue({ ok: true, status: 200, json: async () => response() }) as unknown as typeof fetch;
    const analyze = createAnalyzeInstalledApp({ fetchImpl, apiBaseUrl: "http://backend.test/" });
    await analyze(installedApp);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(fetchImpl).toHaveBeenCalledWith("http://backend.test/analyze/apk", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        package: installedApp.packageName,
        permissions: installedApp.requestedPermissions,
        install_source: installedApp.installSource,
      }),
    }));
  });

  it("does not call the backend when no permissions are declared", async () => {
    const fetchImpl = jest.fn() as unknown as typeof fetch;
    const analyze = createAnalyzeInstalledApp({ fetchImpl });
    await expect(analyze({ ...installedApp, requestedPermissions: [], totalPermissionCount: 0 })).rejects.toThrow(NO_DECLARED_PERMISSIONS_MESSAGE);
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("reports the backend error detail", async () => {
    const fetchImpl = jest.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: "Invalid permission data." }) }) as unknown as typeof fetch;
    await expect(createAnalyzeInstalledApp({ fetchImpl })(installedApp)).rejects.toThrow("Invalid permission data.");
  });
});
