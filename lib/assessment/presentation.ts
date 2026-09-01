export type AssessmentModelPrediction = "Benign" | "Malicious";

export type AssessmentRiskLevel = "Safe" | "Suspicious" | "High Risk";

export type AssessmentThreat =
  | { status: "classified"; likelyCategory: string }
  | { status: "uncertain"; message: string };

export type ThreatCategoryPresentation =
  | {
      state: "classified";
      heading: "Likely Threat Category";
      value: string;
      message: null;
    }
  | {
      state: "uncertain";
      heading: "Threat Category";
      value: "Uncertain";
      message: string;
    }
  | {
      state: "unavailable";
      heading: "Threat Category";
      value: "Unavailable";
      message: "The primary malware assessment completed, but category analysis was unavailable.";
    }
  | {
      state: "not-applicable";
      heading: "Threat Category";
      value: "Not applicable";
      message: "No malicious classification was made.";
    };

const benignReviewLabels: Record<AssessmentRiskLevel, string> = {
  Safe: "Low Permission Concern",
  Suspicious: "Permission Review Recommended",
  "High Risk": "Elevated Permission Concern",
};

const permissionDescriptions: Record<AssessmentRiskLevel, string> = {
  Safe: "The permissions checked look low risk.",
  Suspicious:
    "Some permissions are worth reviewing to make sure they fit what the app does.",
  "High Risk":
    "Several permissions need careful review before you use the app.",
};

function friendlyInstallContext(explanation: string): string | null {
  const normalized = explanation.trim().toLowerCase();
  if (!normalized) return null;

  if (normalized.includes("sideload") || normalized.includes("apk file")) {
    return "This app came from an APK file, so check that you trust where it came from.";
  }

  if (
    normalized.includes("google play") ||
    normalized.includes("app store") ||
    normalized.includes("recognised app store") ||
    normalized.includes("recognized app store")
  ) {
    return "It was reported as installed from an app store.";
  }

  if (
    normalized.includes("unknown") ||
    normalized.includes("could not") ||
    normalized.includes("unavailable")
  ) {
    return "The app's install source could not be confirmed.";
  }

  return null;
}

export function binaryAssessmentLabel(
  modelPrediction: AssessmentModelPrediction,
): "No malware indicated" | "Malware characteristics detected" {
  return modelPrediction === "Benign"
    ? "No malware indicated"
    : "Malware characteristics detected";
}

export function permissionReviewLabel(
  permissionRiskLevel: AssessmentRiskLevel,
): string {
  return benignReviewLabels[permissionRiskLevel];
}

export function overallReviewLabel(
  modelPrediction: AssessmentModelPrediction,
  overallRiskLevel: AssessmentRiskLevel,
): string {
  return modelPrediction === "Benign"
    ? benignReviewLabels[overallRiskLevel]
    : overallRiskLevel;
}

export function userFacingExplanation({
  modelPrediction,
  permissionRiskLevel,
  installContextExplanation,
  backendFinalExplanation,
}: {
  modelPrediction: AssessmentModelPrediction;
  permissionRiskLevel: AssessmentRiskLevel;
  installContextExplanation: string;
  backendFinalExplanation: string;
}): string {
  const assessmentSentence =
    modelPrediction === "Malicious"
      ? "The malware check found signs that may be linked to harmful apps."
      : "The malware check did not find a malware pattern.";
  const contextSentence = friendlyInstallContext(installContextExplanation);

  // `backendFinalExplanation` remains available in the mapped assessment for
  // advanced/debug use. Normal users receive one short explanation generated
  // from the final structured assessment instead of repeating backend prose.
  void backendFinalExplanation;

  return [
    assessmentSentence,
    permissionDescriptions[permissionRiskLevel],
    contextSentence,
  ]
    .filter((sentence): sentence is string => Boolean(sentence))
    .join(" ");
}

export function threatCategoryPresentation(
  modelPrediction: AssessmentModelPrediction,
  threatAssessment: AssessmentThreat | null,
): ThreatCategoryPresentation {
  if (modelPrediction === "Benign") {
    return {
      state: "not-applicable",
      heading: "Threat Category",
      value: "Not applicable",
      message: "No malicious classification was made.",
    };
  }

  if (threatAssessment?.status === "classified") {
    return {
      state: "classified",
      heading: "Likely Threat Category",
      value: threatAssessment.likelyCategory,
      message: null,
    };
  }

  if (threatAssessment?.status === "uncertain") {
    return {
      state: "uncertain",
      heading: "Threat Category",
      value: "Uncertain",
      message: threatAssessment.message,
    };
  }

  return {
    state: "unavailable",
    heading: "Threat Category",
    value: "Unavailable",
    message:
      "The primary malware assessment completed, but category analysis was unavailable.",
  };
}
