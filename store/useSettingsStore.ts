import { create } from "zustand";

export type SettingItem = {
  id: string;
  title: string;
  description: string;
  value: boolean;
};

type SettingsState = {
  settings: SettingItem[];
  toggleSetting: (id: string) => void;
};

const initialSettings: SettingItem[] = [
  {
    id: "1",
    title: "Auto-scan downloads",
    description: "Scan new APKs after download",
    value: true,
  },
  {
    id: "2",
    title: "Real-time protection",
    description: "Monitor notifications for spam",
    value: true,
  },
  {
    id: "3",
    title: "Privacy mode",
    description: "Hide sensitive app names in reports",
    value: false,
  },
];

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: initialSettings,
  toggleSetting: (id) =>
    set((state) => ({
      settings: state.settings.map((item) =>
        item.id === id ? { ...item, value: !item.value } : item,
      ),
    })),
}));
