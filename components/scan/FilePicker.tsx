import * as DocumentPicker from "expo-document-picker";
import { router } from "expo-router";
import { CheckCircle2, UploadCloud } from "lucide-react-native";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";

import { useScanStore } from "../../store/useScanStore";

export default function FilePicker() {
  const process = useScanStore((state) => state.process);
  const selectApk = useScanStore((state) => state.selectApk);
  const analyzeSelectedApk = useScanStore(
    (state) => state.analyzeSelectedApk,
  );

  const busy = process.status === "uploading" || process.status === "analysing";
  const selectedAsset = "asset" in process ? process.asset : null;

  const handlePick = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/vnd.android.package-archive"],
        multiple: false,
        copyToCacheDirectory: true,
      });

      if (result.canceled || result.assets.length === 0) return;

      const asset = result.assets[0];
      selectApk({
        uri: asset.uri,
        name: asset.name ?? "selected.apk",
        mimeType:
          asset.mimeType ?? "application/vnd.android.package-archive",
        file: asset.file,
      });
    } catch (error) {
      Alert.alert(
        "Unable to open files",
        error instanceof Error
          ? error.message
          : "The Android file picker could not be opened.",
      );
    }
  };

  const handleAnalyze = async () => {
    const completed = await analyzeSelectedApk();
    if (completed) router.push("/scan-result");
  };

  return (
    <View className="mt-6">
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Select APK file"
        disabled={busy}
        onPress={handlePick}
      >
        <View
          className="items-center rounded-3xl bg-surfaceHigh/60 p-6"
          style={{
            borderWidth: 1.5,
            borderColor: "#58D6FF",
            borderStyle: "dashed",
            borderRadius: 24,
            opacity: busy ? 0.7 : 1,
          }}
        >
          <View className="h-16 w-16 items-center justify-center rounded-3xl bg-surfaceHigh">
            {process.status === "success" ? (
              <CheckCircle2 size={28} color="#22C55E" />
            ) : busy ? (
              <ActivityIndicator color="#58D6FF" />
            ) : (
              <UploadCloud size={28} color="#58D6FF" />
            )}
          </View>

          <Text className="mt-4 text-center text-base font-semibold text-textPrimary font-sans">
            {selectedAsset?.name ?? "Select APK File"}
          </Text>
          <Text className="mt-1 text-center text-xs text-textMuted font-sans">
            {process.status === "uploading"
              ? "Uploading the selected APK…"
              : process.status === "analysing"
                ? "Backend analysis is in progress…"
                : selectedAsset
                  ? "Tap here to choose a different APK"
                  : "Tap to browse Android package files"}
          </Text>
        </View>
      </Pressable>

      {process.status === "selected" ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Analyze selected APK"
          onPress={() => void handleAnalyze()}
          className="mt-4 items-center rounded-2xl bg-accent px-5 py-4"
        >
          <Text className="font-semibold text-background font-sans">
            Analyze Selected APK
          </Text>
        </Pressable>
      ) : null}

      {busy ? (
        <View className="mt-4 rounded-2xl border border-accent/30 bg-accent/10 px-4 py-3">
          <Text className="text-center text-sm text-accent font-sans">
            {process.status === "uploading"
              ? "Uploading APK to the configured backend"
              : "Extracting permissions and generating the assessment"}
          </Text>
        </View>
      ) : null}

      {process.status === "error" ? (
        <View className="mt-4 rounded-2xl border border-danger/40 bg-danger/10 p-4">
          <Text className="font-semibold text-danger font-sans">
            Analysis failed
          </Text>
          <Text className="mt-2 text-sm leading-5 text-textMuted font-sans">
            {process.message}
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Retry APK analysis"
            onPress={() => void handleAnalyze()}
            className="mt-4 items-center rounded-xl bg-accent px-4 py-3"
          >
            <Text className="font-semibold text-background font-sans">
              Try Again
            </Text>
          </Pressable>
        </View>
      ) : null}

      {process.status === "success" ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="View APK analysis result"
          onPress={() => router.push("/scan-result")}
          className="mt-4 items-center rounded-2xl border border-safe/40 bg-safe/10 px-5 py-4"
        >
          <Text className="font-semibold text-safe font-sans">View Result</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
