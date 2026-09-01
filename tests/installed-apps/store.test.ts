import { createInstalledAppsStore, type InstalledAppsDependencies } from "../../store/useInstalledAppsStore";
import { NO_DECLARED_PERMISSIONS_MESSAGE } from "../../services/installed-apps/analyzeInstalledApp";
import { mapInstalledAppResponse } from "../../lib/installed-apps/mapInstalledAppResponse";
import { installedApp, response } from "./fixtures";

function dependencies(overrides: Partial<InstalledAppsDependencies> = {}): InstalledAppsDependencies {
  return {
    getInstalledApps: jest.fn().mockResolvedValue([installedApp]),
    refreshInstalledApps: jest.fn().mockResolvedValue([installedApp]),
    getInstalledApp: jest.fn().mockResolvedValue(installedApp),
    analyzeInstalledApp: jest.fn().mockResolvedValue(mapInstalledAppResponse(response(), installedApp)),
    ...overrides,
  };
}

describe("installed-app store", () => {
  it("loads the launcher-visible inventory", async () => {
    const store = createInstalledAppsStore(dependencies());
    const promise = store.getState().loadApps();
    expect(store.getState().inventoryStatus).toBe("loading");
    await promise;
    expect(store.getState().inventoryStatus).toBe("success");
    expect(store.getState().apps).toEqual([installedApp]);
  });

  it("supports loading and success analysis states", async () => {
    let resolve!: (value: ReturnType<typeof mapInstalledAppResponse>) => void;
    const deferred = new Promise<ReturnType<typeof mapInstalledAppResponse>>((done) => { resolve = done; });
    const deps = dependencies({ analyzeInstalledApp: jest.fn().mockReturnValue(deferred) });
    const recordSuccessfulScan = jest.fn().mockResolvedValue(true);
    const store = createInstalledAppsStore({ ...deps, recordSuccessfulScan });
    store.getState().selectApp(installedApp);
    const promise = store.getState().analyzeSelectedApp();
    expect(store.getState().analysis.status).toBe("loading");
    resolve(mapInstalledAppResponse(response(), installedApp));
    await promise;
    expect(store.getState().analysis.status).toBe("success");
    expect(recordSuccessfulScan).toHaveBeenCalledTimes(1);
    expect(recordSuccessfulScan).toHaveBeenCalledWith(
      mapInstalledAppResponse(response(), installedApp),
    );
  });

  it("supports analysis errors", async () => {
    const recordSuccessfulScan = jest.fn();
    const store = createInstalledAppsStore(dependencies({
      analyzeInstalledApp: jest.fn().mockRejectedValue(new Error("Backend offline")),
      recordSuccessfulScan,
    }));
    store.getState().selectApp(installedApp);
    await store.getState().analyzeSelectedApp();
    expect(store.getState().analysis).toEqual({ status: "error", message: "Backend offline" });
    expect(recordSuccessfulScan).not.toHaveBeenCalled();
  });

  it("returns unavailable without a backend call for an empty permission list", async () => {
    const analyze = jest.fn();
    const recordSuccessfulScan = jest.fn();
    const store = createInstalledAppsStore(dependencies({
      analyzeInstalledApp: analyze,
      recordSuccessfulScan,
    }));
    store.getState().selectApp({ ...installedApp, requestedPermissions: [], totalPermissionCount: 0 });
    await store.getState().analyzeSelectedApp();
    expect(store.getState().analysis).toEqual({ status: "unavailable", message: NO_DECLARED_PERMISSIONS_MESSAGE });
    expect(analyze).not.toHaveBeenCalled();
    expect(recordSuccessfulScan).not.toHaveBeenCalled();
  });

  it("keeps a valid assessment successful when local history storage fails", async () => {
    const recordSuccessfulScan = jest
      .fn()
      .mockRejectedValue(new Error("Local storage unavailable"));
    const store = createInstalledAppsStore(dependencies({ recordSuccessfulScan }));
    store.getState().selectApp(installedApp);

    await store.getState().analyzeSelectedApp();

    expect(store.getState().analysis.status).toBe("success");
    expect(recordSuccessfulScan).toHaveBeenCalledTimes(1);
  });
});
