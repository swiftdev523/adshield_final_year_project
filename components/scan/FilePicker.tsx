import * as DocumentPicker from "expo-document-picker";
import { router } from "expo-router";
import { UploadCloud } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import Card from "../ui/Card";
import { useScanStore } from "../../store/useScanStore";

export default function FilePicker() {
  const setScan = useScanStore((state) => state.setScan);

  const handlePick = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ["application/vnd.android.package-archive"],
      multiple: false,
      copyToCacheDirectory: true,
    });

    if (result.canceled || result.assets.length === 0) {
      return;
    }

    const asset = result.assets[0];
    setScan(asset.name ?? "selected.apk", 72);
    router.push("/scan-result");
  };

  return (
    <Pressable onPress={handlePick} className="mt-6">
      <View
        className="items-center rounded-3xl p-6 bg-surfaceHigh/60"
        style={{
          borderWidth: 1.5,
          borderColor: "#58D6FF",
          borderStyle: "dashed",
          borderRadius: 24,
        }}
      >
        <View className="h-16 w-16 items-center justify-center rounded-3xl bg-surfaceHigh">
          <UploadCloud size={28} color="#58D6FF" />
        </View>
        <Text className="mt-4 text-base font-semibold text-textPrimary font-sans">
          Select APK File
        </Text>
        <Text className="mt-1 text-xs text-textMuted text-center font-sans">
          Tap to browse files or drag & drop
        </Text>
        <View className="mt-4 rounded-full bg-accent px-6 py-2.5">
          <Text className="text-xs font-semibold text-background font-sans">
            Browse Files
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
