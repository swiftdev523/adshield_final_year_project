import {
  binaryAssessmentLabel,
  overallReviewLabel,
  permissionReviewLabel,
  threatCategoryPresentation,
  userFacingExplanation,
} from "../../lib/assessment/presentation";

describe("shared assessment presentation", () => {
  it.each([
    ["Safe", "Low Permission Concern"],
    ["Suspicious", "Permission Review Recommended"],
    ["High Risk", "Elevated Permission Concern"],
  ] as const)(
    "maps a Benign %s band to %s",
    (riskLevel, expectedLabel) => {
      expect(permissionReviewLabel(riskLevel)).toBe(expectedLabel);
      expect(overallReviewLabel("Benign", riskLevel)).toBe(expectedLabel);
    },
  );

  it("keeps the technical binary value out of the normal user phrase", () => {
    expect(binaryAssessmentLabel("Benign")).toBe("No malware indicated");
    expect(binaryAssessmentLabel("Malicious")).toBe(
      "Malware characteristics detected",
    );
  });

  it("generates neutral Benign wording from assessment state", () => {
    const explanation = userFacingExplanation({
      modelPrediction: "Benign",
      permissionRiskLevel: "Suspicious",
      installContextExplanation:
        "Reported as installed from an app store. This source adds no contextual risk adjustment.",
      backendFinalExplanation: "Overall risk is Suspicious (40/100).",
    });

    expect(explanation).toBe(
      "The malware check did not find a malware pattern. Some permissions are worth reviewing to make sure they fit what the app does. It was reported as installed from an app store.",
    );
    expect(explanation).not.toContain("Overall risk is Suspicious");
    expect(explanation).not.toContain("not a guarantee");
  });

  it("keeps malicious wording short and treats sideloading as source advice", () => {
    const explanation = userFacingExplanation({
      modelPrediction: "Malicious",
      permissionRiskLevel: "High Risk",
      installContextExplanation:
        "Reported as installed by sideloading an APK. This can make publisher and origin verification harder, adding contextual uncertainty; sideloading alone is not evidence that the app is malware.",
      backendFinalExplanation:
        "A long backend explanation that must not be shown to normal users.",
    });

    expect(explanation).toBe(
      "The malware check found signs that may be linked to harmful apps. Several permissions need careful review before you use the app. This app came from an APK file, so check that you trust where it came from.",
    );
    expect(explanation).not.toContain("contextual uncertainty");
    expect(explanation).not.toContain("long backend explanation");
  });

  it("defines exactly the classified, uncertain, unavailable and not-applicable states", () => {
    const presentations = [
      threatCategoryPresentation("Malicious", {
        status: "classified",
        likelyCategory: "Adware",
      }),
      threatCategoryPresentation("Malicious", {
        status: "uncertain",
        message: "The category cannot be assigned safely.",
      }),
      threatCategoryPresentation("Malicious", null),
      threatCategoryPresentation("Benign", {
        status: "classified",
        likelyCategory: "Adware",
      }),
    ];

    expect(presentations.map(({ state }) => state)).toEqual([
      "classified",
      "uncertain",
      "unavailable",
      "not-applicable",
    ]);
    expect(presentations[2]).toMatchObject({
      value: "Unavailable",
      message:
        "The primary malware assessment completed, but category analysis was unavailable.",
    });
    expect(presentations[3]).toMatchObject({
      value: "Not applicable",
      message: "No malicious classification was made.",
    });
  });
});
