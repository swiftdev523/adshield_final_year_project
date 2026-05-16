import { create } from "zustand";

type AlertState = {
  spamBannerDismissed: boolean;
  dismissSpamBanner: () => void;
  resetSpamBanner: () => void;
};

export const useAlertStore = create<AlertState>((set) => ({
  spamBannerDismissed: false,
  dismissSpamBanner: () => set({ spamBannerDismissed: true }),
  resetSpamBanner: () => set({ spamBannerDismissed: false }),
}));
