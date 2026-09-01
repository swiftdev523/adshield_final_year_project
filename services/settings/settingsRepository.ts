import * as FileSystem from "expo-file-system/legacy";

const SETTINGS_SCHEMA_VERSION = 1;
const SETTINGS_DIRECTORY_NAME = "settings";
export const SETTINGS_FILENAME = "adshield-settings-v1.json";

export type PersistedSettings = { privacyMode: boolean };

interface PersistedSettingsDocument extends PersistedSettings {
  version: typeof SETTINGS_SCHEMA_VERSION;
}

export interface SettingsFileSystem {
  documentDirectory: string | null;
  getInfoAsync(uri: string): Promise<{ exists: boolean }>;
  makeDirectoryAsync(
    uri: string,
    options?: { intermediates?: boolean },
  ): Promise<unknown>;
  readAsStringAsync(uri: string): Promise<string>;
  writeAsStringAsync(uri: string, contents: string): Promise<unknown>;
}

export interface SettingsRepository {
  load(): Promise<PersistedSettings>;
  save(settings: PersistedSettings): Promise<void>;
}

export const DEFAULT_SETTINGS: PersistedSettings = { privacyMode: false };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const defaultFileSystem: SettingsFileSystem = {
  documentDirectory: FileSystem.documentDirectory,
  getInfoAsync: async (uri) => FileSystem.getInfoAsync(uri),
  makeDirectoryAsync: async (uri, options) =>
    FileSystem.makeDirectoryAsync(uri, options),
  readAsStringAsync: async (uri) => FileSystem.readAsStringAsync(uri),
  writeAsStringAsync: async (uri, contents) =>
    FileSystem.writeAsStringAsync(uri, contents),
};

export function createSettingsRepository(
  fileSystem: SettingsFileSystem = defaultFileSystem,
): SettingsRepository {
  function resolvePaths(): { directory: string; file: string } {
    if (!fileSystem.documentDirectory) {
      throw new Error("Local settings storage is unavailable.");
    }
    const root = fileSystem.documentDirectory.endsWith("/")
      ? fileSystem.documentDirectory.slice(0, -1)
      : fileSystem.documentDirectory;
    const directory = `${root}/${SETTINGS_DIRECTORY_NAME}`;
    return { directory, file: `${directory}/${SETTINGS_FILENAME}` };
  }

  return {
    async load(): Promise<PersistedSettings> {
      const { file } = resolvePaths();
      const info = await fileSystem.getInfoAsync(file);
      if (!info.exists) return { ...DEFAULT_SETTINGS };

      let parsed: unknown;
      try {
        parsed = JSON.parse(await fileSystem.readAsStringAsync(file));
      } catch {
        throw new Error("Saved settings are not valid JSON.");
      }
      if (
        !isRecord(parsed) ||
        parsed.version !== SETTINGS_SCHEMA_VERSION ||
        typeof parsed.privacyMode !== "boolean"
      ) {
        throw new Error("Saved settings have an unsupported schema.");
      }
      return { privacyMode: parsed.privacyMode };
    },

    async save(settings: PersistedSettings): Promise<void> {
      const { directory, file } = resolvePaths();
      const payload: PersistedSettingsDocument = {
        version: SETTINGS_SCHEMA_VERSION,
        privacyMode: settings.privacyMode,
      };
      await fileSystem.makeDirectoryAsync(directory, { intermediates: true });
      await fileSystem.writeAsStringAsync(file, JSON.stringify(payload));
    },
  };
}

export const settingsRepository = createSettingsRepository();
