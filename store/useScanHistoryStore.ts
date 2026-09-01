import { create, type StoreApi, type UseBoundStore } from "zustand";

import {
  createApkScanHistoryEntry,
  createInstalledAppScanHistoryEntry,
  type ScanHistoryAssessmentInput,
  type ScanHistoryEntryIdentity,
} from "../lib/history/createScanHistoryEntry";
import {
  scanHistoryRepository,
  type ScanHistoryRepository,
} from "../services/history/scanHistoryRepository";
import type { ScanHistoryEntry } from "../types/scan-history";

export type ScanHistoryStatus = "idle" | "loading" | "ready" | "error";

export interface ScanHistoryState {
  entries: ScanHistoryEntry[];
  status: ScanHistoryStatus;
  error: string | null;
  loadHistory: (force?: boolean) => Promise<boolean>;
  recordApkScan: (
    assessment: ScanHistoryAssessmentInput,
    filename?: string | null,
  ) => Promise<boolean>;
  recordInstalledAppScan: (
    assessment: ScanHistoryAssessmentInput,
  ) => Promise<boolean>;
  deleteEntry: (id: string) => Promise<boolean>;
  clearHistory: () => Promise<boolean>;
  getEntryById: (id: string) => ScanHistoryEntry | undefined;
}

export type ScanHistoryStore = UseBoundStore<StoreApi<ScanHistoryState>>;

let identitySequence = 0;

function createHistoryIdentity(): ScanHistoryEntryIdentity {
  const timestamp = new Date().toISOString();
  identitySequence += 1;

  return {
    id: `scan-${Date.now()}-${identitySequence}-${Math.random()
      .toString(36)
      .slice(2, 10)}`,
    timestamp,
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Scan history could not be updated.";
}

export function createScanHistoryStore(
  repository: ScanHistoryRepository = scanHistoryRepository,
): ScanHistoryStore {
  let operationQueue: Promise<void> = Promise.resolve();

  function enqueue<T>(operation: () => Promise<T>): Promise<T> {
    const pending = operationQueue.then(operation, operation);
    operationQueue = pending.then(
      () => undefined,
      () => undefined,
    );
    return pending;
  }

  return create<ScanHistoryState>((set, get) => {
    async function loadWithinQueue(force = false): Promise<boolean> {
      if (!force && get().status === "ready") {
        return true;
      }

      set({ status: "loading", error: null });

      try {
        const entries = await repository.load();
        set({ entries, status: "ready", error: null });
        return true;
      } catch (error) {
        set({ status: "error", error: errorMessage(error) });
        return false;
      }
    }

    async function persistNewEntry(
      createEntry: () => ScanHistoryEntry,
    ): Promise<boolean> {
      return enqueue(async () => {
        if (get().status !== "ready") {
          const loaded = await loadWithinQueue();
          if (!loaded) {
            return false;
          }
        }

        try {
          const entry = createEntry();
          const entries = [entry, ...get().entries];
          await repository.save(entries);
          set({ entries, status: "ready", error: null });
          return true;
        } catch (error) {
          set({ status: "error", error: errorMessage(error) });
          return false;
        }
      });
    }

    return {
      entries: [],
      status: "idle",
      error: null,

      loadHistory: (force = false) =>
        enqueue(() => loadWithinQueue(force)),

      recordApkScan: (assessment, filename) =>
        persistNewEntry(() =>
          createApkScanHistoryEntry(
            assessment,
            filename,
            createHistoryIdentity(),
          ),
        ),

      recordInstalledAppScan: (assessment) =>
        persistNewEntry(() =>
          createInstalledAppScanHistoryEntry(
            assessment,
            createHistoryIdentity(),
          ),
        ),

      deleteEntry: (id) =>
        enqueue(async () => {
          if (get().status !== "ready") {
            const loaded = await loadWithinQueue();
            if (!loaded) {
              return false;
            }
          }

          const entries = get().entries.filter((entry) => entry.id !== id);

          if (entries.length === get().entries.length) {
            return true;
          }

          try {
            await repository.save(entries);
            set({ entries, status: "ready", error: null });
            return true;
          } catch (error) {
            set({ status: "error", error: errorMessage(error) });
            return false;
          }
        }),

      clearHistory: () =>
        enqueue(async () => {
          try {
            await repository.save([]);
            set({ entries: [], status: "ready", error: null });
            return true;
          } catch (error) {
            set({ status: "error", error: errorMessage(error) });
            return false;
          }
        }),

      getEntryById: (id) =>
        get().entries.find((entry) => entry.id === id),
    };
  });
}

export const useScanHistoryStore = createScanHistoryStore();
