import {
  createSettingsRepository,
  SETTINGS_FILENAME,
  type SettingsFileSystem,
} from "../../services/settings/settingsRepository";

function memoryFileSystem(): {
  fileSystem: SettingsFileSystem;
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
        const value = files.get(uri);
        if (value === undefined) throw new Error("Missing in-memory file");
        return value;
      },
      writeAsStringAsync: async (uri, contents) => {
        files.set(uri, contents);
      },
    },
  };
}

const settingsPath = `file:///documents/settings/${SETTINGS_FILENAME}`;

describe("settingsRepository", () => {
  it("uses the safe default when no saved settings exist", async () => {
    const { fileSystem } = memoryFileSystem();
    await expect(createSettingsRepository(fileSystem).load()).resolves.toEqual({
      privacyMode: false,
    });
  });

  it("persists and reloads the versioned privacy preference", async () => {
    const { fileSystem, files } = memoryFileSystem();
    const repository = createSettingsRepository(fileSystem);

    await repository.save({ privacyMode: true });

    expect(JSON.parse(files.get(settingsPath)!)).toEqual({
      version: 1,
      privacyMode: true,
    });
    await expect(repository.load()).resolves.toEqual({ privacyMode: true });
  });

  it("rejects corrupt or unsupported settings instead of guessing", async () => {
    const { fileSystem, files } = memoryFileSystem();
    const repository = createSettingsRepository(fileSystem);
    files.set(settingsPath, "not-json");
    await expect(repository.load()).rejects.toThrow("not valid JSON");

    files.set(settingsPath, JSON.stringify({ version: 2, privacyMode: true }));
    await expect(repository.load()).rejects.toThrow("unsupported schema");
  });
});
