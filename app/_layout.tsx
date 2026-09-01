import "../global.css";

import {
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_700Bold,
} from "@expo-google-fonts/space-grotesk";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { useSettingsStore } from "../store/useSettingsStore";

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const hydrateSettings = useSettingsStore((state) => state.hydrate);
  const [fontsLoaded] = useFonts({
    SpaceGrotesk_400Regular,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_700Bold,
  });

  useEffect(() => {
    void hydrateSettings();
  }, [hydrateSettings]);

  useEffect(() => {
    if (fontsLoaded) {
      void SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) {
    return <View style={{ flex: 1, backgroundColor: "#0B1020" }} />;
  }

  return (
    <SafeAreaProvider>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#0B1020" },
        }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="scan-result" />
        <Stack.Screen name="installed-apps" />
        <Stack.Screen name="installed-app-details" />
        <Stack.Screen name="installed-app-result" />
        <Stack.Screen name="scan-history" />
        <Stack.Screen name="scan-history-detail" />
        <Stack.Screen name="settings-info" />
      </Stack>
    </SafeAreaProvider>
  );
}
