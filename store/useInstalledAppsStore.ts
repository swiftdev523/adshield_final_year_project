import { create } from "zustand";

import { analyzeInstalledApp } from "../services/installed-apps/analyzeInstalledApp";
import {
  getInstalledApp,
  getInstalledApps,
  refreshInstalledApps,
} from "../services/installed-apps/installedAppMonitor";
import type { InstalledAppAssessment } from "../types/installed-app-assessment";
import type { InstalledAppInfo } from "../types/installed-apps";
import { NO_DECLARED_PERMISSIONS_MESSAGE } from "../services/installed-apps/analyzeInstalledApp";
import { useScanHistoryStore } from "./useScanHistoryStore";

export type InventoryStatus = "idle" | "loading" | "success" | "error";
export type AnalysisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; assessment: InstalledAppAssessment }
  | { status: "error"; message: string }
  | { status: "unavailable"; message: string };

export type InstalledAppsDependencies = {
  getInstalledApps: typeof getInstalledApps;
  refreshInstalledApps: typeof refreshInstalledApps;
  getInstalledApp: typeof getInstalledApp;
  analyzeInstalledApp: typeof analyzeInstalledApp;
  recordSuccessfulScan?: (
    assessment: InstalledAppAssessment,
  ) => Promise<boolean> | boolean;
};

export type InstalledAppsState = {
  apps: InstalledAppInfo[];
  inventoryStatus: InventoryStatus;
  inventoryError: string | null;
  selectedApp: InstalledAppInfo | null;
  analysis: AnalysisState;
  loadApps(): Promise<void>;
  refreshApps(): Promise<void>;
  selectApp(app: InstalledAppInfo): void;
  loadSelectedApp(packageName: string): Promise<void>;
  analyzeSelectedApp(): Promise<void>;
  clearAnalysis(): void;
};

const message = (error: unknown, fallback: string) =>
  error instanceof Error && error.message ? error.message : fallback;

export function createInstalledAppsStore(dependencies: InstalledAppsDependencies) {
  return create<InstalledAppsState>((set, get) => ({
    apps: [],
    inventoryStatus: "idle",
    inventoryError: null,
    selectedApp: null,
    analysis: { status: "idle" },
    async loadApps() {
      set({ inventoryStatus: "loading", inventoryError: null });
      try {
        const apps = await dependencies.getInstalledApps();
        set({ apps, inventoryStatus: "success" });
      } catch (error) {
        set({
          inventoryStatus: "error",
          inventoryError: message(error, "Unable to read visible installed apps."),
        });
      }
    },
    async refreshApps() {
      set({ inventoryStatus: "loading", inventoryError: null });
      try {
        const apps = await dependencies.refreshInstalledApps();
        set({ apps, inventoryStatus: "success" });
      } catch (error) {
        set({
          inventoryStatus: "error",
          inventoryError: message(error, "Unable to refresh visible installed apps."),
        });
      }
    },
    selectApp(app) {
      set({ selectedApp: app, analysis: { status: "idle" } });
    },
    async loadSelectedApp(packageName) {
      const existing = get().apps.find((app) => app.packageName === packageName);
      if (existing) {
        set({ selectedApp: existing, analysis: { status: "idle" } });
        return;
      }
      try {
        const app = await dependencies.getInstalledApp(packageName);
        set({ selectedApp: app, analysis: { status: "idle" } });
      } catch (error) {
        set({
          selectedApp: null,
          analysis: { status: "error", message: message(error, "Unable to read this app.") },
        });
      }
    },
    async analyzeSelectedApp() {
      const app = get().selectedApp;
      if (!app) {
        set({ analysis: { status: "error", message: "No installed app is selected." } });
        return;
      }
      if (app.requestedPermissions.length === 0) {
        set({
          analysis: { status: "unavailable", message: NO_DECLARED_PERMISSIONS_MESSAGE },
        });
        return;
      }
      set({ analysis: { status: "loading" } });
      try {
        const assessment = await dependencies.analyzeInstalledApp(app);
        set({ analysis: { status: "success", assessment } });
        try {
          await dependencies.recordSuccessfulScan?.(assessment);
        } catch {
          // Do not convert a valid backend result into an analysis failure
          // when only local history persistence is unavailable.
        }
      } catch (error) {
        set({
          analysis: { status: "error", message: message(error, "Unable to analyze this app.") },
        });
      }
    },
    clearAnalysis() {
      set({ analysis: { status: "idle" } });
    },
  }));
}

export const useInstalledAppsStore = createInstalledAppsStore({
  getInstalledApps,
  refreshInstalledApps,
  getInstalledApp,
  analyzeInstalledApp,
  recordSuccessfulScan: (assessment) =>
    useScanHistoryStore.getState().recordInstalledAppScan(assessment),
});
