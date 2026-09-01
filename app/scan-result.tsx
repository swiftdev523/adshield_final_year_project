import { router } from "expo-router";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react-native";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import ThreatCategoryPanel from "../components/assessment/ThreatCategoryPanel";
import Badge, { type BadgeVariant } from "../components/ui/Badge";
import Card from "../components/ui/Card";
import RiskMeter from "../components/ui/RiskMeter";
import {
  binaryAssessmentLabel,
  overallReviewLabel,
  permissionReviewLabel,
  userFacingExplanation,
} from "../lib/assessment/presentation";
import {
  displayApkFilename,
  displayAppName,
  displayPackageName,
} from "../lib/privacy/displayIdentity";
import { useScanStore } from "../store/useScanStore";
import { useSettingsStore } from "../store/useSettingsStore";
import type { ScanOverallRiskLevel } from "../types/scan-assessment";

const riskVariants: Record<ScanOverallRiskLevel, BadgeVariant> = {
  Safe: "safe",
  Suspicious: "caution",
  "High Risk": "dangerous",
};

export default function ScanResultScreen() {
  const process = useScanStore((state) => state.process);
  const privacyMode = useSettingsStore((state) => state.privacyMode);
  const [showMoreInformation, setShowMoreInformation] = useState(false);

  const handleBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace("/(tabs)/scan");
  };

  if (process.status !== "success") {
    return (
      <SafeAreaView
        style={{ flex: 1, backgroundColor: "#0B1020" }}
        edges={["top", "bottom"]}
      >
        <View className="px-6 pt-4">
          <Pressable
            accessibilityLabel="Go back"
            onPress={handleBack}
            className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
          >
            <ArrowLeft size={18} color="#8EA0C6" />
          </Pressable>
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <FileCheck2 size={42} color="#8EA0C6" />
          <Text className="mt-5 text-center font-heading text-xl text-textPrimary">
            No completed APK assessment
          </Text>
          <Text className="mt-2 text-center text-sm leading-5 text-textMuted font-sans">
            Select an APK and wait for a valid backend response before opening
            this screen.
          </Text>
          <Pressable
            onPress={() => router.replace("/(tabs)/scan")}
            className="mt-6 rounded-2xl bg-accent px-6 py-3"
          >
            <Text className="font-semibold text-background font-sans">
              Go to APK Scanner
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const assessment = process.assessment;
  const rawDisplayName =
    assessment.app.appName ??
    assessment.app.filename ??
    assessment.app.packageName ??
    "Analyzed APK";
  const displayName = assessment.app.appName
    ? displayAppName(rawDisplayName, privacyMode)
    : assessment.app.filename
      ? displayApkFilename(rawDisplayName, privacyMode)
      : displayPackageName(rawDisplayName, privacyMode);
  const variant = riskVariants[assessment.overallRiskLevel];
  const binaryLabel = binaryAssessmentLabel(assessment.modelPrediction);
  const permissionLabel = permissionReviewLabel(
    assessment.permissionRiskLevel,
  );
  const reviewLabel = overallReviewLabel(
    assessment.modelPrediction,
    assessment.overallRiskLevel,
  );
  const explanation = userFacingExplanation({
    modelPrediction: assessment.modelPrediction,
    permissionRiskLevel: assessment.permissionRiskLevel,
    installContextExplanation: assessment.installContextExplanation,
    backendFinalExplanation: assessment.finalExplanation,
  });

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#0B1020" }}
      edges={["top", "bottom"]}
    >
      <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 48 }}>
        <View className="mb-5 flex-row items-center gap-3">
          <Pressable
            accessibilityLabel="Go back"
            onPress={handleBack}
            className="h-10 w-10 items-center justify-center rounded-full border border-border bg-surfaceHigh"
          >
            <ArrowLeft size={18} color="#8EA0C6" />
          </Pressable>
          <View className="flex-1">
            <Text className="font-heading text-2xl text-textPrimary">
              APK Analysis Result
            </Text>
            <Text className="text-xs text-textMuted font-sans">
              Real backend assessment
            </Text>
          </View>
        </View>

        <Card className="mb-4 bg-surfaceHigh/80">
          <View className="flex-row items-start justify-between gap-3">
            <View className="flex-1">
              <Text
                className="text-base font-semibold text-textPrimary font-sans"
                numberOfLines={2}
              >
                {displayName}
              </Text>
              {assessment.app.packageName ? (
                <Text className="mt-1 text-xs text-textMuted font-sans">
                  {displayPackageName(assessment.app.packageName, privacyMode)}
                </Text>
              ) : null}
              {assessment.app.filename &&
              assessment.app.filename !== rawDisplayName ? (
                <Text className="mt-1 text-xs text-textDim font-sans">
                  {displayApkFilename(assessment.app.filename, privacyMode)}
                </Text>
              ) : null}
            </View>
            <Badge variant={variant} label={reviewLabel} />
          </View>
        </Card>

        <RiskMeter
          score={assessment.overallRiskScore}
          level={assessment.overallRiskLevel}
          reviewLabel={reviewLabel}
        />

        <Card className="mt-4 bg-surfaceHigh/80">
          <Text className="font-heading text-base text-textPrimary">
            Final assessment
          </Text>
          <Text className="mt-3 text-sm leading-6 text-textMuted font-sans">
            {explanation}
          </Text>
          <Text className="mt-4 text-xs font-semibold uppercase tracking-wider text-accent font-sans">
            Recommendation
          </Text>
          <Text className="mt-2 text-sm leading-5 text-textPrimary font-sans">
            {assessment.recommendation}
          </Text>
        </Card>

        <ThreatCategoryPanel
          modelPrediction={assessment.modelPrediction}
          threatAssessment={assessment.threatAssessment}
        />

        <Card className="mt-4 bg-surfaceHigh/80">
          <Text className="font-heading text-base text-textPrimary">
            Important reasons
          </Text>
          {assessment.importantReasons.map((reason, index) => (
            <View key={`${index}-${reason}`} className="mt-3 flex-row">
              <Text className="mr-2 text-accent">•</Text>
              <Text className="flex-1 text-sm leading-5 text-textMuted font-sans">
                {reason}
              </Text>
            </View>
          ))}
        </Card>

        <View className="mt-4 flex-row gap-3">
          <Card className="flex-1 items-center bg-surfaceHigh/80">
            <ShieldCheck size={20} color="#58D6FF" />
            <Text className="mt-2 text-2xl font-bold text-textPrimary font-sans">
              {assessment.totalPermissionCount}
            </Text>
            <Text className="mt-1 text-center text-[10px] text-textMuted font-sans">
              Declared permissions
            </Text>
          </Card>
          <Card className="flex-1 items-center bg-surfaceHigh/80">
            <ShieldAlert size={20} color="#F59E0B" />
            <Text className="mt-2 text-2xl font-bold text-textPrimary font-sans">
              {assessment.curatedSensitivePermissionCount}
            </Text>
            <Text className="mt-1 text-center text-[10px] text-textMuted font-sans">
              Permissions worth reviewing
            </Text>
          </Card>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="More information about this APK"
          accessibilityState={{ expanded: showMoreInformation }}
          onPress={() => setShowMoreInformation((visible) => !visible)}
          className="mt-4"
        >
          <Card className="bg-surfaceHigh/80">
            <View className="flex-row items-center justify-between">
              <View className="flex-1 pr-3">
                <Text className="font-heading text-base text-textPrimary">
                  More information about this APK
                </Text>
                <Text className="mt-1 text-xs text-textMuted font-sans">
                  Assessment details and permission findings
                </Text>
              </View>
              {showMoreInformation ? (
                <ChevronUp size={20} color="#58D6FF" />
              ) : (
                <ChevronDown size={20} color="#58D6FF" />
              )}
            </View>
          </Card>
        </Pressable>

        {showMoreInformation ? (
          <>
            <Card className="mt-3 bg-surfaceHigh/80">
              <Text className="font-heading text-base text-textPrimary">
                Assessment overview
              </Text>
              <View className="mt-3 gap-1">
                <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
                  Malware assessment
                </Text>
                <Text
                  className={`text-sm font-semibold font-sans ${
                    assessment.modelPrediction === "Malicious"
                      ? "text-danger"
                      : "text-safe"
                  }`}
                >
                  {binaryLabel}
                </Text>
              </View>
              <View className="mt-4 gap-1">
                <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
                  Permission review
                </Text>
                <Text className="text-sm font-semibold text-textPrimary font-sans">
                  {permissionLabel}
                </Text>
                <Text className="text-xs text-textDim font-sans">
                  {assessment.permissionRiskScore} / 100
                </Text>
              </View>
              <View className="mt-4 gap-1">
                <Text className="text-xs uppercase tracking-wider text-textMuted font-sans">
                  Installation source
                </Text>
                <Text className="text-sm text-textPrimary font-sans">
                  {assessment.installSourceDisplay}
                </Text>
                <Text className="mt-1 text-sm leading-5 text-textMuted font-sans">
                  {assessment.installContextExplanation}
                </Text>
              </View>
            </Card>

            <Card className="mt-3 bg-surfaceHigh/80">
              <Text className="font-heading text-base text-textPrimary">
                Permission findings
              </Text>
              {assessment.permissionFindings.length > 0 ? (
                assessment.permissionFindings.map((finding, index) => (
                  <View key={`${index}-${finding}`} className="mt-3 flex-row">
                    <CheckCircle2 size={16} color="#58D6FF" />
                    <Text className="ml-2 flex-1 text-sm leading-5 text-textMuted font-sans">
                      {finding}
                    </Text>
                  </View>
                ))
              ) : (
                <Text className="mt-3 text-sm leading-5 text-textMuted font-sans">
                  No additional permission findings were provided.
                </Text>
              )}
            </Card>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
