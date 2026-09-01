import * as FileSystem from "expo-file-system/legacy";

import {
  SCAN_HISTORY_BINARY_RESULTS,
  SCAN_HISTORY_OVERALL_LEVELS,
  SCAN_HISTORY_SOURCES,
  SCAN_HISTORY_THREAT_CATEGORIES,
  THREAT_CATEGORY_STATUSES,
  type ScanHistoryBinaryResult,
  type ScanHistoryEntry,
  type ScanHistoryOverallLevel,
  type ScanHistorySource,
  type ScanHistoryThreatCategory,
  type ThreatCategoryStatus,
} from "../../types/scan-history";

const HISTORY_SCHEMA_VERSION = 1;
const HISTORY_DIRECTORY_NAME = "scan-history";
export const SCAN_HISTORY_FILENAME = "scan-history-v1.json";

interface PersistedScanHistory {
  version: typeof HISTORY_SCHEMA_VERSION;
  entries: ScanHistoryEntry[];
}

export interface ScanHistoryFileSystem {
  documentDirectory: string | null;
  getInfoAsync(uri: string): Promise<{ exists: boolean }>;
  makeDirectoryAsync(
    uri: string,
    options?: { intermediates?: boolean },
  ): Promise<unknown>;
  readAsStringAsync(uri: string): Promise<string>;
  writeAsStringAsync(uri: string, contents: string): Promise<unknown>;
}

export interface ScanHistoryRepository {
  load(): Promise<ScanHistoryEntry[]>;
  save(entries: readonly ScanHistoryEntry[]): Promise<void>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSource(value: unknown): value is ScanHistorySource {
  return (
    typeof value === "string" &&
    (SCAN_HISTORY_SOURCES as readonly string[]).includes(value)
  );
}

function isCategoryStatus(value: unknown): value is ThreatCategoryStatus {
  return (
    typeof value === "string" &&
    (THREAT_CATEGORY_STATUSES as readonly string[]).includes(value)
  );
}

function isOverallLevel(value: unknown): value is ScanHistoryOverallLevel {
  return (
    typeof value === "string" &&
    (SCAN_HISTORY_OVERALL_LEVELS as readonly string[]).includes(value)
  );
}

function isBinaryResult(value: unknown): value is ScanHistoryBinaryResult {
  return (
    typeof value === "string" &&
    (SCAN_HISTORY_BINARY_RESULTS as readonly string[]).includes(value)
  );
}

function isThreatCategory(value: unknown): value is ScanHistoryThreatCategory {
  return (
    typeof value === "string" &&
    (SCAN_HISTORY_THREAT_CATEGORIES as readonly string[]).includes(value)
  );
}

function normalizeEntry(value: unknown, index: number): ScanHistoryEntry {
  if (!isRecord(value)) {
    throw new Error(`History entry ${index} is not an object.`);
  }

  if (!isNonEmptyString(value.id)) {
    throw new Error(`History entry ${index} has no valid ID.`);
  }

  if (!isSource(value.source)) {
    throw new Error(`History entry ${index} has an invalid source.`);
  }

  if (!isNonEmptyString(value.appName)) {
    throw new Error(`History entry ${index} has no app name.`);
  }

  if (!isNonEmptyString(value.packageOrFilename)) {
    throw new Error(`History entry ${index} has no package or filename.`);
  }

  if (
    !isNonEmptyString(value.timestamp) ||
    !Number.isFinite(Date.parse(value.timestamp))
  ) {
    throw new Error(`History entry ${index} has an invalid timestamp.`);
  }

  if (
    typeof value.overallScore !== "number" ||
    !Number.isFinite(value.overallScore) ||
    value.overallScore < 0 ||
    value.overallScore > 100
  ) {
    throw new Error(`History entry ${index} has an invalid overall score.`);
  }

  if (!isOverallLevel(value.overallLevel)) {
    throw new Error(`History entry ${index} has an invalid overall level.`);
  }

  if (!isBinaryResult(value.binaryResult)) {
    throw new Error(`History entry ${index} has an invalid binary result.`);
  }

  if (!isCategoryStatus(value.threatCategoryStatus)) {
    throw new Error(`History entry ${index} has an invalid category status.`);
  }

  const threatCategory =
    value.threatCategoryStatus === "classified"
      ? value.threatCategory
      : null;

  if (
    value.threatCategoryStatus === "classified" &&
    !isThreatCategory(threatCategory)
  ) {
    throw new Error(`History entry ${index} has no classified category.`);
  }

  if (!isNonEmptyString(value.installSourceDisplay)) {
    throw new Error(`History entry ${index} has no install-source display.`);
  }

  // Reconstruct explicitly so runtime-only or sensitive extra properties are
  // never copied into the persisted representation.
  return {
    id: value.id.trim(),
    source: value.source,
    appName: value.appName.trim(),
    packageOrFilename: value.packageOrFilename.trim(),
    timestamp: value.timestamp.trim(),
    overallScore: value.overallScore,
    overallLevel: value.overallLevel,
    binaryResult: value.binaryResult,
    threatCategoryStatus: value.threatCategoryStatus,
    threatCategory:
      isThreatCategory(threatCategory) ? threatCategory : null,
    installSourceDisplay: value.installSourceDisplay.trim(),
  };
}

function normalizeEntries(entries: readonly unknown[]): ScanHistoryEntry[] {
  const normalized = entries.map(normalizeEntry);
  const seenIds = new Set<string>();

  for (const entry of normalized) {
    if (seenIds.has(entry.id)) {
      throw new Error(`Duplicate history ID: ${entry.id}`);
    }

    seenIds.add(entry.id);
  }

  return normalized;
}

function directoryPath(documentDirectory: string): string {
  const separator = documentDirectory.endsWith("/") ? "" : "/";
  return `${documentDirectory}${separator}${HISTORY_DIRECTORY_NAME}`;
}

const defaultFileSystem: ScanHistoryFileSystem = {
  documentDirectory: FileSystem.documentDirectory,
  getInfoAsync: async (uri) => FileSystem.getInfoAsync(uri),
  makeDirectoryAsync: async (uri, options) =>
    FileSystem.makeDirectoryAsync(uri, options),
  readAsStringAsync: async (uri) => FileSystem.readAsStringAsync(uri),
  writeAsStringAsync: async (uri, contents) =>
    FileSystem.writeAsStringAsync(uri, contents),
};

export function createScanHistoryRepository(
  fileSystem: ScanHistoryFileSystem = defaultFileSystem,
): ScanHistoryRepository {
  function resolvePaths(): { directory: string; file: string } {
    if (!fileSystem.documentDirectory) {
      throw new Error("Local document storage is unavailable.");
    }

    const directory = directoryPath(fileSystem.documentDirectory);
    return {
      directory,
      file: `${directory}/${SCAN_HISTORY_FILENAME}`,
    };
  }

  return {
    async load(): Promise<ScanHistoryEntry[]> {
      const { file } = resolvePaths();
      const fileInfo = await fileSystem.getInfoAsync(file);

      if (!fileInfo.exists) {
        return [];
      }

      const raw = await fileSystem.readAsStringAsync(file);
      let parsed: unknown;

      try {
        parsed = JSON.parse(raw);
      } catch {
        throw new Error("Saved scan history is not valid JSON.");
      }

      if (
        !isRecord(parsed) ||
        parsed.version !== HISTORY_SCHEMA_VERSION ||
        !Array.isArray(parsed.entries)
      ) {
        throw new Error("Saved scan history has an unsupported schema.");
      }

      return normalizeEntries(parsed.entries).sort(
        (left, right) =>
          Date.parse(right.timestamp) - Date.parse(left.timestamp),
      );
    },

    async save(entries: readonly ScanHistoryEntry[]): Promise<void> {
      const { directory, file } = resolvePaths();
      const normalizedEntries = normalizeEntries(entries);
      const payload: PersistedScanHistory = {
        version: HISTORY_SCHEMA_VERSION,
        entries: normalizedEntries,
      };

      await fileSystem.makeDirectoryAsync(directory, { intermediates: true });
      await fileSystem.writeAsStringAsync(file, JSON.stringify(payload));
    },
  };
}

export const scanHistoryRepository = createScanHistoryRepository();
