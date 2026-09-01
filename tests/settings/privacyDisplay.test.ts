import {
  displayApkFilename,
  displayAppName,
  displayHistoryIdentifier,
  displayHistoryName,
  displayPackageName,
} from "../../lib/privacy/displayIdentity";

describe("privacy display helpers", () => {
  it("preserves identities when privacy mode is off", () => {
    expect(displayAppName("WhatsApp", false)).toBe("WhatsApp");
    expect(displayPackageName("com.whatsapp", false)).toBe("com.whatsapp");
    expect(displayApkFilename("sample.apk", false)).toBe("sample.apk");
  });

  it("shortens app names and hides package and APK identifiers", () => {
    expect(displayAppName("WhatsApp", true)).toBe("W\u2022\u2022\u2022\u2022");
    expect(displayPackageName("com.whatsapp", true)).toBe(
      "Package name hidden",
    );
    expect(displayApkFilename("sample.apk", true)).toBe(
      "APK filename hidden",
    );
  });

  it("uses the correct masking for both history source types", () => {
    expect(
      displayHistoryName(
        {
          source: "Installed App",
          appName: "Example Bank",
          packageOrFilename: "com.example.bank",
        },
        true,
      ),
    ).toBe("E\u2022\u2022\u2022\u2022");
    expect(
      displayHistoryIdentifier(
        { source: "APK", packageOrFilename: "riskware.apk" },
        true,
      ),
    ).toBe("APK filename hidden");
  });
});
