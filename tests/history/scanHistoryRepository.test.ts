import {
  createScanHistoryRepository,
  SCAN_HISTORY_FILENAME,
  type ScanHistoryFileSystem,
} from "../../services/history/scanHistoryRepository";
import type { ScanHistoryEntry } from "../../types/scan-history";

function entry(overrides: Partial<ScanHistoryEntry> = {}): ScanHistoryEntry {
  return {
    id: "history-001",
    source: "APK",
    appName: "Example App",
    packageOrFilename: "example.apk",
    timestamp: "2026-08-27T12:00:00.000Z",
    overallScore: 64,
    overallLevel: "Suspicious",
    binaryResult: "Malicious",
    threatCategoryStatus: "classified",
    threatCategory: "Riskware",
    installSourceDisplay: "APK sideload",
    ...overrides,
  };
}

function memoryFileSystem(): {
  fileSystem: ScanHistoryFileSystem;
  files: Map<string, string>;
} {
  const files = new Map<string, string>();
  const directories = new Set<string>();

  return {
    files,
    fileSystem: {
      documentDirectory: "file:///documents/",
      getInfoAsync: async (uri) => ({
        exists: files.has(uri) || directories.has(uri),
      }),
      makeDirectoryAsync: async (uri) => {
        directories.add(uri);
      },
      readAsStringAsync: async (uri) => {
        const contents = files.get(uri);
        if (contents === undefined) {
          throw new Error(`Missing in-memory file: ${uri}`);
        }
        return contents;
      },
      writeAsStringAsync: async (uri, contents) => {
        files.set(uri, contents);
      },
    },
  };
}

const historyPath = `file:///documents/scan-history/${SCAN_HISTORY_FILENAME}`;

describe("scanHistoryRepository", () => {
  it("returns an empty list when no history file exists", async () => {
    const { fileSystem } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);

    await expect(repository.load()).resolves.toEqual([]);
  });

  it("round-trips valid entries newest first", async () => {
    const { fileSystem } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);

    await repository.save([
      entry(),
      entry({
        id: "history-002",
        timestamp: "2026-08-27T13:00:00.000Z",
      }),
    ]);

    const loaded = await repository.load();
    expect(loaded.map(({ id }) => id)).toEqual(["history-002", "history-001"]);
  });

  it("serializes only the approved allowlist", async () => {
    const { fileSystem, files } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);
    const runtimeEntry = {
      ...entry(),
      apkBytes: "not-permitted",
      permissions: ["android.permission.READ_SMS"],
      notificationBody: "not-permitted",
      modelMargin: 0.9,
      secret: "not-permitted",
    } as ScanHistoryEntry;

    await repository.save([runtimeEntry]);

    const persisted = files.get(historyPath);
    expect(persisted).toBeDefined();
    expect(persisted).not.toContain("apkBytes");
    expect(persisted).not.toContain("permissions");
    expect(persisted).not.toContain("notificationBody");
    expect(persisted).not.toContain("modelMargin");
    expect(persisted).not.toContain("secret");
  });

  it("removes category labels when the status is not classified", async () => {
    const { fileSystem } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);

    await repository.save([
      entry({
        threatCategoryStatus: "uncertain",
        threatCategory: "Must not be retained" as never,
      }),
    ]);

    await expect(repository.load()).resolves.toEqual([
      entry({
        threatCategoryStatus: "uncertain",
        threatCategory: null,
      }),
    ]);
  });

  it("rejects unsupported or corrupt persisted schemas", async () => {
    const { fileSystem, files } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);
    files.set(historyPath, JSON.stringify({ version: 2, entries: [] }));

    await expect(repository.load()).rejects.toThrow("unsupported schema");

    files.set(historyPath, "not-json");
    await expect(repository.load()).rejects.toThrow("not valid JSON");
  });

  it("rejects duplicate IDs rather than silently replacing an entry", async () => {
    const { fileSystem } = memoryFileSystem();
    const repository = createScanHistoryRepository(fileSystem);

    await expect(repository.save([entry(), entry()])).rejects.toThrow(
      "Duplicate history ID",
    );
  });
});
