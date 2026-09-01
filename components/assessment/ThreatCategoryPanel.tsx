import { Text, View } from "react-native";

import {
  threatCategoryPresentation,
  type AssessmentModelPrediction,
  type AssessmentThreat,
  type ThreatCategoryPresentation,
} from "../../lib/assessment/presentation";

type Props = {
  modelPrediction: AssessmentModelPrediction;
  threatAssessment: AssessmentThreat | null;
};

const panelStyles: Record<ThreatCategoryPresentation["state"], string> = {
  classified: "border-danger/40 bg-danger/10",
  uncertain: "border-warning/40 bg-warning/10",
  unavailable: "border-border bg-surfaceHigh/80",
  "not-applicable": "border-border bg-surfaceHigh/80",
};

const valueStyles: Record<ThreatCategoryPresentation["state"], string> = {
  classified: "text-danger",
  uncertain: "text-warning",
  unavailable: "text-textPrimary",
  "not-applicable": "text-safe",
};

export default function ThreatCategoryPanel({
  modelPrediction,
  threatAssessment,
}: Props) {
  const presentation = threatCategoryPresentation(
    modelPrediction,
    threatAssessment,
  );

  return (
    <View
      accessibilityLabel={`Threat category: ${presentation.value}`}
      className={`mt-4 rounded-3xl border p-5 ${panelStyles[presentation.state]}`}
    >
      <Text className="text-xs font-semibold uppercase tracking-wider text-textMuted font-sans">
        {presentation.heading}
      </Text>
      <Text
        className={`mt-2 font-heading text-xl ${valueStyles[presentation.state]}`}
      >
        {presentation.value}
      </Text>
      {presentation.message ? (
        <Text className="mt-2 text-sm leading-5 text-textMuted font-sans">
          {presentation.message}
        </Text>
      ) : null}
    </View>
  );
}
