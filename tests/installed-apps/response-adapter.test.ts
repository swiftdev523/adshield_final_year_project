import { mapInstalledAppResponse } from "../../lib/installed-apps/mapInstalledAppResponse";
import { installedApp, response } from "./fixtures";

describe("installed-app response adapter", () => {
  it("uses backend risk values directly and excludes diagnostics", () => {
    const result = mapInstalledAppResponse(response(), installedApp);
    expect(result.overallRiskScore).toBe(37);
    expect(result.overallRiskLevel).toBe("Suspicious");
    expect(result.permissionRiskScore).toBe(37);
    expect(result.permissionRiskLevel).toBe("Suspicious");
    expect(result.installContextExplanation).toContain(
      "no contextual risk adjustment",
    );
    expect(JSON.stringify(result)).not.toContain("must-not-leak");
    expect(result).not.toHaveProperty("malwareProbability");
    expect(result).not.toHaveProperty("confidence");
    expect(result).not.toHaveProperty("categoryScores");
  });

  it("never shows a category for a benign model prediction", () => {
    const result = mapInstalledAppResponse(response({
      model_prediction: "Benign",
      threat_assessment: { status: "classified", likely_category: "Adware" },
    }), installedApp);
    expect(result.threatAssessment).toBeNull();
  });

  it("maps a supported classified category", () => {
    const result = mapInstalledAppResponse(response({
      threat_assessment: { status: "classified", likely_category: "Banking Malware" },
    }), installedApp);
    expect(result.threatAssessment).toEqual({ status: "classified", likelyCategory: "Banking Malware" });
  });

  it("maps uncertainty using only the backend message", () => {
    const message = "The app's permission pattern does not clearly match one supported threat category.";
    const result = mapInstalledAppResponse(response({
      threat_assessment: { status: "uncertain", likely_category: null, message },
    }), installedApp);
    expect(result.threatAssessment).toEqual({ status: "uncertain", message });
  });

  it("keeps a null category null", () => {
    expect(mapInstalledAppResponse(response(), installedApp).threatAssessment).toBeNull();
  });
});
