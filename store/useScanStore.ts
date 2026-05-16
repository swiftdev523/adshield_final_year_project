import { create } from "zustand";

type ScanState = {
  fileName: string | null;
  score: number;
  isNewScan: boolean;
  setScan: (fileName: string, score: number) => void;
  viewScan: (fileName: string, score: number) => void;
  clearNewScan: () => void;
};

export const useScanStore = create<ScanState>((set) => ({
  fileName: null,
  score: 72,
  isNewScan: false,
  /** Trigger a fresh scan — plays the scanning animation */
  setScan: (fileName, score) => set({ fileName, score, isNewScan: true }),
  /** View a previously-scanned result — skips the scanning animation */
  viewScan: (fileName, score) => set({ fileName, score, isNewScan: false }),
  clearNewScan: () => set({ isNewScan: false }),
}));
