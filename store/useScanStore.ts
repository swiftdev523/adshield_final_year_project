import { create } from "zustand";

import {
  uploadApk,
  type ApkUploadAsset,
  type ApkUploadPhase,
} from "../services/apk/uploadApk";
import type { ScanAssessment } from "../types/scan-assessment";
import { useScanHistoryStore } from "./useScanHistoryStore";

export type ScanProcess =
  | { status: "idle" }
  | { status: "selected"; asset: ApkUploadAsset }
  | { status: "uploading"; asset: ApkUploadAsset }
  | { status: "analysing"; asset: ApkUploadAsset }
  | { status: "success"; asset: ApkUploadAsset; assessment: ScanAssessment }
  | { status: "error"; asset: ApkUploadAsset; message: string };

type ScanDependencies = {
  uploadApk: typeof uploadApk;
  recordSuccessfulScan?: (
    assessment: ScanAssessment,
    filename: string,
  ) => Promise<boolean> | boolean;
};

export type ScanState = {
  process: ScanProcess;
  selectApk(asset: ApkUploadAsset): void;
  analyzeSelectedApk(): Promise<boolean>;
  reset(): void;
};

const errorMessage = (error: unknown) =>
  error instanceof Error && error.message
    ? error.message
    : "APK analysis failed. Please try again.";

export function createScanStore(dependencies: ScanDependencies) {
  let requestSequence = 0;

  return create<ScanState>((set, get) => ({
    process: { status: "idle" },

    selectApk(asset) {
      requestSequence += 1;
      set({ process: { status: "selected", asset } });
    },

    async analyzeSelectedApk() {
      const current = get().process;
      if (current.status !== "selected" && current.status !== "error") {
        return false;
      }

      const { asset } = current;
      const requestId = ++requestSequence;
      set({ process: { status: "uploading", asset } });

      const onPhaseChange = (phase: ApkUploadPhase) => {
        if (requestSequence === requestId) {
          set({ process: { status: phase, asset } });
        }
      };

      try {
        const assessment = await dependencies.uploadApk(
          { asset, installSource: "apk_sideload" },
          { onPhaseChange },
        );
        if (requestSequence !== requestId) return false;
        set({ process: { status: "success", asset, assessment } });
        try {
          await dependencies.recordSuccessfulScan?.(assessment, asset.name);
        } catch {
          // The completed backend assessment remains valid even if local
          // history storage is temporarily unavailable.
        }
        return (
          requestSequence === requestId &&
          get().process.status === "success"
        );
      } catch (error) {
        if (requestSequence !== requestId) return false;
        set({
          process: {
            status: "error",
            asset,
            message: errorMessage(error),
          },
        });
        return false;
      }
    },

    reset() {
      requestSequence += 1;
      set({ process: { status: "idle" } });
    },
  }));
}

export const useScanStore = createScanStore({
  uploadApk,
  recordSuccessfulScan: (assessment, filename) =>
    useScanHistoryStore.getState().recordApkScan(assessment, filename),
});
