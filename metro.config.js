const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);

// Expo SDK 54 enables unstable_enablePackageExports by default, which causes
// Metro to prefer the ESM (`module`) field of lucide-react-native@0.303.0.
// The ESM build requires `prop-types` which React 19 no longer bundles.
// This override forces Metro to always resolve lucide-react-native via its
// CJS single-bundle, bypassing the ESM path entirely.
const originalResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === "lucide-react-native") {
    return {
      filePath: path.resolve(
        __dirname,
        "node_modules/lucide-react-native/dist/cjs/lucide-react-native.js",
      ),
      type: "sourceFile",
    };
  }
  if (originalResolveRequest) {
    return originalResolveRequest(context, moduleName, platform);
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = withNativeWind(config, { input: "./global.css" });
