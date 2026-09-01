import type { ScanHistoryAssessmentInput } from "../../lib/history/createScanHistoryEntry";
import type { ScanHistoryRepository } from "../../services/history/scanHistoryRepository";
import { createScanHistoryStore } from "../../store/useScanHistoryStore";
import type { ScanHistoryEntry } from "../../types/scan-history";

function assessment(
  overrides: Partial<ScanHistoryAssessmentInput> = {},
): ScanHistoryAssessmentInput {
  return {
    app: {
      appName: "Example App",
      packageName: "com.example.app",
      filename: "example.apk",
    },
    overallRiskScore: 64,
    overallRiskLevel: "Suspicious",
    modelPrediction: "Malicious",
    installSourceDisplay: "APK sideload",
    threatAssessment: {
      status: "classified",
      likelyCategory: "Riskware",
    },
    ...overrides,
  };
}

function existingEntry(): ScanHistoryEntry {
  return {
    id: "existing-history",
    source: "Installed App",
    appName: "Existing App",
    packageOrFilename: "com.example.existing",
    timestamp: "2026-08-26T12:00:00.000Z",
    overallScore: 10,
    overallLevel: "Safe",
    binaryResult: "Benign",
    threatCategoryStatus: "not_applicable",
    threatCategory: null,
    installSourceDisplay: "Google Play",
  };
}

function memoryRepository(initial: ScanHistoryEntry[] = []): {
  repository: ScanHistoryRepository;
  load: jest.Mock<Promise<ScanHistoryEntry[]>, []>;
  save: jest.Mock<Promise<void>, [readonly ScanHistoryEntry[]]>;
  saved: () => ScanHistoryEntry[];
} {
  let persisted = [...initial];
  const load = jest.fn(async () => [...persisted]);
  const save = jest.fn(async (entries: readonly ScanHistoryEntry[]) => {
    persisted = [...entries];
  });

  return {
    repository: { load, save },
    load,
    save,
    saved: () => [...persisted],
  };
}

describe("useScanHistoryStore", () => {
  it("hydrates persisted history", async () => {
    const memory = memoryRepository([existingEntry()]);
    const store = createScanHistoryStore(memory.repository);

    await expect(store.getState().loadHistory()).resolves.toBe(true);

    expect(store.getState()).toMatchObject({
      entries: [existingEntry()],
      status: "ready",
      error: null,
    });
    expect(memory.load).toHaveBeenCalledTimes(1);
  });

  it("loads existing history before recording a successful APK scan", async () => {
    const memory = memoryRepository([existingEntry()]);
    const store = createScanHistoryStore(memory.repository);

    await expect(
      store.getState().recordApkScan(assessment(), "selected.apk"),
    ).resolves.toBe(true);

    expect(memory.load).toHaveBeenCalledTimes(1);
    expect(memory.save).toHaveBeenCalledTimes(1);
    expect(memory.saved()).toHaveLength(2);
    expect(memory.saved()[0]).toMatchObject({
      source: "APK",
      packageOrFilename: "selected.apk",
      threatCategory: "Riskware",
    });
    expect(memory.saved()[1]).toEqual(existingEntry());
  });

  it("serializes concurrent records so neither scan is lost", async () => {
    const memory = memoryRepository();
    const store = createScanHistoryStore(memory.repository);

    const results = await Promise.all([
      store.getState().recordInstalledAppScan(assessment()),
      store.getState().recordInstalledAppScan(
        assessment({
          app: {
            appName: "Second App",
            packageName: "com.example.second",
          },
        }),
      ),
    ]);

    expect(results).toEqual([true, true]);
    expect(memory.saved()).toHaveLength(2);
    expect(
      memory.saved().map(({ packageOrFilename }) => packageOrFilename),
    ).toEqual(["com.example.second", "com.example.app"]);
  });

  it("does not mutate visible history when persistence fails", async () => {
    const repository: ScanHistoryRepository = {
      load: async () => [existingEntry()],
      save: async () => {
        throw new Error("Storage write failed");
      },
    };
    const store = createScanHistoryStore(repository);

    await store.getState().loadHistory();
    await expect(
      store.getState().recordInstalledAppScan(assessment()),
    ).resolves.toBe(false);

    expect(store.getState().entries).toEqual([existingEntry()]);
    expect(store.getState().status).toBe("error");
    expect(store.getState().error).toBe("Storage write failed");
  });

  it("deletes one entry and clears all history through the repository", async () => {
    const second = {
      ...existingEntry(),
      id: "second-history",
      packageOrFilename: "com.example.second",
    };
    const memory = memoryRepository([existingEntry(), second]);
    const store = createScanHistoryStore(memory.repository);
    await store.getState().loadHistory();

    expect(store.getState().getEntryById("second-history")).toEqual(second);
    await expect(
      store.getState().deleteEntry("existing-history"),
    ).resolves.toBe(true);
    expect(store.getState().entries).toEqual([second]);

    await expect(store.getState().clearHistory()).resolves.toBe(true);
    expect(store.getState().entries).toEqual([]);
    expect(memory.saved()).toEqual([]);
  });
});
