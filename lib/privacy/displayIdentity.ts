const MASK = "\u2022\u2022\u2022\u2022";

const normalized = (value: string | null | undefined) => value?.trim() ?? "";

export function displayAppName(
  value: string | null | undefined,
  privacyMode: boolean,
  fallback = "App",
): string {
  const name = normalized(value) || fallback;
  if (!privacyMode) return name;
  const first = Array.from(name).find((character) =>
    /[A-Za-z0-9]/.test(character),
  );
  return first ? `${first.toUpperCase()}${MASK}` : "App name hidden";
}

export function displayPackageName(
  value: string | null | undefined,
  privacyMode: boolean,
): string {
  const name = normalized(value);
  if (!name) return "Package unavailable";
  return privacyMode ? "Package name hidden" : name;
}

export function displayApkFilename(
  value: string | null | undefined,
  privacyMode: boolean,
): string {
  const name = normalized(value);
  if (!name) return "APK file";
  return privacyMode ? "APK filename hidden" : name;
}

type HistoryIdentity = {
  appName: string;
  packageOrFilename: string;
  source: "APK" | "Installed App";
};

export function displayHistoryName(
  entry: HistoryIdentity,
  privacyMode: boolean,
): string {
  const name = entry.appName.trim() || entry.packageOrFilename;
  return entry.source === "APK"
    ? displayApkFilename(name, privacyMode)
    : displayAppName(name, privacyMode);
}

export function displayHistoryIdentifier(
  entry: Pick<HistoryIdentity, "packageOrFilename" | "source">,
  privacyMode: boolean,
): string {
  return entry.source === "APK"
    ? displayApkFilename(entry.packageOrFilename, privacyMode)
    : displayPackageName(entry.packageOrFilename, privacyMode);
}
