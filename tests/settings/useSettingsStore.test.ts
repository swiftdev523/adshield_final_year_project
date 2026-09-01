import type { SettingsRepository } from "../../services/settings/settingsRepository";
import { createSettingsStore } from "../../store/useSettingsStore";

function memoryRepository(initial = false): {
  repository: SettingsRepository;
  load: jest.Mock;
  save: jest.Mock;
} {
  let persisted = initial;
  const load = jest.fn(async () => ({ privacyMode: persisted }));
  const save = jest.fn(async ({ privacyMode }: { privacyMode: boolean }) => {
    persisted = privacyMode;
  });
  return { repository: { load, save }, load, save };
}

describe("useSettingsStore", () => {
  it("hydrates the persisted privacy preference", async () => {
    const memory = memoryRepository(true);
    const store = createSettingsStore(memory.repository);

    await expect(store.getState().hydrate()).resolves.toBe(true);
    expect(store.getState()).toMatchObject({
      privacyMode: true,
      status: "ready",
      error: null,
    });
  });

  it("writes before changing the visible preference", async () => {
    const memory = memoryRepository(false);
    const store = createSettingsStore(memory.repository);

    await expect(store.getState().setPrivacyMode(true)).resolves.toBe(true);
    expect(memory.load).toHaveBeenCalledTimes(1);
    expect(memory.save).toHaveBeenCalledWith({ privacyMode: true });
    expect(store.getState().privacyMode).toBe(true);
  });

  it("does not claim a change was saved when the write fails", async () => {
    const repository: SettingsRepository = {
      load: async () => ({ privacyMode: false }),
      save: async () => {
        throw new Error("Storage write failed");
      },
    };
    const store = createSettingsStore(repository);

    await expect(store.getState().setPrivacyMode(true)).resolves.toBe(false);
    expect(store.getState()).toMatchObject({
      privacyMode: false,
      status: "error",
      error: "Storage write failed",
    });
  });
});
