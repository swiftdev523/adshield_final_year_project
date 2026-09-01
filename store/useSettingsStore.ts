import { create, type StoreApi, type UseBoundStore } from "zustand";

import {
  settingsRepository,
  type SettingsRepository,
} from "../services/settings/settingsRepository";

export type SettingsStatus = "idle" | "loading" | "ready" | "error";

export interface SettingsState {
  privacyMode: boolean;
  status: SettingsStatus;
  error: string | null;
  hydrate(force?: boolean): Promise<boolean>;
  setPrivacyMode(enabled: boolean): Promise<boolean>;
}

export type SettingsStore = UseBoundStore<StoreApi<SettingsState>>;

const errorMessage = (error: unknown) =>
  error instanceof Error && error.message
    ? error.message
    : "Settings could not be saved.";

export function createSettingsStore(
  repository: SettingsRepository = settingsRepository,
): SettingsStore {
  let operationQueue: Promise<void> = Promise.resolve();
  function enqueue<T>(operation: () => Promise<T>): Promise<T> {
    const pending = operationQueue.then(operation, operation);
    operationQueue = pending.then(
      () => undefined,
      () => undefined,
    );
    return pending;
  }

  return create<SettingsState>((set, get) => {
    async function hydrateWithinQueue(force = false): Promise<boolean> {
      if (!force && get().status === "ready") return true;
      set({ status: "loading", error: null });
      try {
        const settings = await repository.load();
        set({
          privacyMode: settings.privacyMode,
          status: "ready",
          error: null,
        });
        return true;
      } catch (error) {
        set({ status: "error", error: errorMessage(error) });
        return false;
      }
    }

    return {
      privacyMode: false,
      status: "idle",
      error: null,
      hydrate: (force = false) => enqueue(() => hydrateWithinQueue(force)),
      setPrivacyMode: (enabled) =>
        enqueue(async () => {
          if (get().status !== "ready") {
            const loaded = await hydrateWithinQueue();
            if (!loaded) return false;
          }
          try {
            await repository.save({ privacyMode: enabled });
            set({ privacyMode: enabled, status: "ready", error: null });
            return true;
          } catch (error) {
            set({ status: "error", error: errorMessage(error) });
            return false;
          }
        }),
    };
  });
}

export const useSettingsStore = createSettingsStore();
