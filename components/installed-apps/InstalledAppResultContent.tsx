import { ChevronDown, ChevronUp, ShieldAlert, ShieldCheck } from "lucide-react-native";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";

import type { AnalysisState } from "../../store/useInstalledAppsStore";
import {
  binaryAssessmentLabel,
  overallReviewLabel,
  permissionReviewLabel,
  userFacingExplanation,
} from "../../lib/assessment/presentation";
import {
  displayAppName,
  displayPackageName,
} from "../../lib/privacy/displayIdentity";
import { useSettingsStore } from "../../store/useSettingsStore";
import ThreatCategoryPanel from "../assessment/ThreatCategoryPanel";
import AssessmentRiskMeter from "./AssessmentRiskMeter";

type Props = { state: AnalysisState; onRetry(): void };

function StatusPanel({ title, message }: { title: string; message: string }) {
  return (
    <View className="rounded-3xl border border-border bg-surface p-5">
      <Text className="font-heading text-lg text-textPrimary">{title}</Text>
      <Text className="mt-2 text-sm leading-5 text-textMuted">{message}</Text>
    </View>
  );
}

export default function InstalledAppResultContent({ state, onRetry }: Props) {
  const privacyMode = useSettingsStore((settings) => settings.privacyMode);
  const [showMoreInformation, setShowMoreInformation] = useState(false);

  if (state.status === "idle" || state.status === "loading") {
    return (
      <View className="flex-1 items-center justify-center px-6">
        <ActivityIndicator size="large" color="#58D6FF" />
        <Text className="mt-4 font-heading text-lg text-textPrimary">
          Analyzing app
        </Text>
        <Text className="mt-2 text-center text-sm text-textMuted">
          Sending the selected app&apos;s declared permissions for assessment…
        </Text>
      </View>
    );
  }

  if (state.status === "error") {
    return (
      <View className="flex-1 justify-center px-6">
        <StatusPanel title="Analysis failed" message={state.message} />
        <Pressable
          onPress={onRetry}
          className="mt-4 items-center rounded-2xl bg-accent px-4 py-4"
        >
          <Text className="font-semibold text-background">Try again</Text>
        </Pressable>
      </View>
    );
  }

  if (state.status === "unavailable") {
    return (
      <View className="flex-1 justify-center px-6">
        <StatusPanel
          title="Permission analysis unavailable"
          message={state.message}
        />
      </View>
    );
  }

  const result = state.assessment;
  const binaryLabel = binaryAssessmentLabel(result.modelPrediction);
  const permissionLabel = permissionReviewLabel(result.permissionRiskLevel);
  const reviewLabel = overallReviewLabel(
    result.modelPrediction,
    result.overallRiskLevel,
  );
  const explanation = userFacingExplanation({
    modelPrediction: result.modelPrediction,
    permissionRiskLevel: result.permissionRiskLevel,
    installContextExplanation: result.installContextExplanation,
    backendFinalExplanation: result.finalExplanation,
  });

  return (
    <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 48 }}>
      <View className="mb-5">
        <Text className="font-heading text-2xl text-textPrimary">
          {displayAppName(result.app.appName, privacyMode)}
        </Text>
        <Text className="mt-1 text-xs text-textMuted">
          {displayPackageName(result.app.packageName, privacyMode)}
        </Text>
      </View>

      <AssessmentRiskMeter
        score={result.overallRiskScore}
        level={result.overallRiskLevel}
        reviewLabel={reviewLabel}
      />

      <View className="mt-4 rounded-3xl border border-border bg-surface p-5">
        <Text className="font-heading text-base text-textPrimary">
          Final assessment
        </Text>
        <Text className="mt-3 text-sm leading-6 text-textMuted">
          {explanation}
        </Text>
        <Text className="mt-4 text-xs font-semibold uppercase tracking-wider text-accent">
          Recommendation
        </Text>
        <Text className="mt-2 text-sm leading-5 text-textPrimary">
          {result.recommendation}
        </Text>
      </View>

      <ThreatCategoryPanel
        modelPrediction={result.modelPrediction}
        threatAssessment={result.threatAssessment}
      />

      <View className="mt-4 flex-row gap-3">
        <View className="flex-1 items-center rounded-3xl border border-border bg-surface p-4">
          <ShieldCheck size={20} color="#58D6FF" />
          <Text className="mt-2 text-2xl font-bold text-textPrimary">
            {result.totalPermissionCount}
          </Text>
          <Text className="mt-1 text-center text-[10px] text-textMuted">
            Declared permissions
          </Text>
        </View>
        <View className="flex-1 items-center rounded-3xl border border-border bg-surface p-4">
          <ShieldAlert size={20} color="#F59E0B" />
          <Text className="mt-2 text-2xl font-bold text-textPrimary">
            {result.curatedSensitivePermissionCount}
          </Text>
          <Text className="mt-1 text-center text-[10px] text-textMuted">
            Permissions worth reviewing
          </Text>
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="More information about this app"
        accessibilityState={{ expanded: showMoreInformation }}
        onPress={() => setShowMoreInformation((visible) => !visible)}
        className="mt-4 rounded-3xl border border-border bg-surface p-5"
      >
        <View className="flex-row items-center justify-between">
          <View className="flex-1 pr-3">
            <Text className="font-heading text-base text-textPrimary">
              More information about this app
            </Text>
            <Text className="mt-1 text-xs text-textMuted">
              Assessment and permission details
            </Text>
          </View>
          {showMoreInformation ? (
            <ChevronUp size={20} color="#58D6FF" />
          ) : (
            <ChevronDown size={20} color="#58D6FF" />
          )}
        </View>
      </Pressable>

      {showMoreInformation ? (
        <>
          <View className="mt-3 rounded-3xl border border-border bg-surface p-5">
            <Text className="font-heading text-base text-textPrimary">
              Assessment overview
            </Text>
            <View className="mt-3 gap-1">
              <Text className="text-xs uppercase tracking-wider text-textMuted">
                Malware assessment
              </Text>
              <Text
                className={`text-sm font-semibold ${
                  result.modelPrediction === "Malicious"
                    ? "text-danger"
                    : "text-safe"
                }`}
              >
                {binaryLabel}
              </Text>
            </View>
            <View className="mt-4 gap-1">
              <Text className="text-xs uppercase tracking-wider text-textMuted">
                Permission review
              </Text>
              <Text className="text-sm font-semibold text-textPrimary">
                {permissionLabel}
              </Text>
              <Text className="text-xs text-textDim">
                {result.permissionRiskScore} / 100
              </Text>
            </View>
            <View className="mt-4 gap-1">
              <Text className="text-xs uppercase tracking-wider text-textMuted">
                Installation source
              </Text>
              <Text className="text-sm text-textPrimary">
                {result.installSourceDisplay}
              </Text>
              <Text className="mt-1 text-sm leading-5 text-textMuted">
                {result.installContextExplanation}
              </Text>
            </View>
          </View>

          <View className="mt-3 rounded-3xl border border-border bg-surface p-5">
            <Text className="font-heading text-base text-textPrimary">
              Permission overview
            </Text>
            <Text className="mt-3 text-sm text-textMuted">
              Declared permissions: {result.totalPermissionCount}
            </Text>
            <Text className="mt-2 text-sm text-textMuted">
              Permissions worth reviewing: {result.curatedSensitivePermissionCount}
            </Text>
            {result.curatedSensitivePermissions.map((permission) => (
              <View
                key={`${permission.label}-${permission.category}`}
                className="mt-3 border-t border-border pt-3"
              >
                <Text className="text-sm text-textPrimary">
                  {permission.description}
                </Text>
                <Text className="mt-1 text-xs text-textDim">
                  {permission.group} · {permission.severity}
                </Text>
              </View>
            ))}
          </View>

          <View className="mt-3 rounded-3xl border border-border bg-surface p-5">
            <Text className="font-heading text-base text-textPrimary">
              Permission findings
            </Text>
            {result.permissionFindings.length > 0 ? (
              result.permissionFindings.map((finding, index) => (
                <View key={`${index}-${finding}`} className="mt-3 flex-row">
                  <Text className="mr-2 text-accent">{"\u2022"}</Text>
                  <Text className="flex-1 text-sm leading-5 text-textMuted">
                    {finding}
                  </Text>
                </View>
              ))
            ) : (
              <Text className="mt-3 text-sm leading-5 text-textMuted">
                No additional permission findings were provided.
              </Text>
            )}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}
