/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        background: "#0B1020",
        surface: "#121A2B",
        surfaceHigh: "#19243A",
        border: "#26324A",
        accent: "#58D6FF",
        accentDim: "#2FA6C8",
        safe: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        spam: "#FF375F",
        suspicious: "#F59E0B",
        normal: "#22C55E",
        textPrimary: "#EAF1FF",
        textMuted: "#8EA0C6",
        textDim: "#5B6A8C",
      },
      fontFamily: {
        sans: ["SpaceGrotesk_400Regular"],
        medium: ["SpaceGrotesk_500Medium"],
        bold: ["SpaceGrotesk_700Bold"],
        heading: ["SpaceGrotesk_700Bold"],
      },
      borderRadius: {
        card: "16px",
        pill: "999px",
      },
    },
  },
  plugins: [],
};
