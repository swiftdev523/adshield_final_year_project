import { ReactNode } from "react";
import { View, ViewStyle } from "react-native";

type CardProps = {
  children: ReactNode;
  className?: string;
  glowColor?: string;
};

export default function Card({ children, className, glowColor }: CardProps) {
  const baseShadow: ViewStyle = {
    shadowColor: "#070B16",
    shadowOpacity: 0.35,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  };

  const glowStyle: ViewStyle | undefined = glowColor
    ? {
        borderColor: glowColor,
        shadowColor: glowColor,
        shadowOpacity: 0.45,
        shadowRadius: 18,
        shadowOffset: { width: 0, height: 10 },
        elevation: 8,
      }
    : undefined;

  return (
    <View
      className={`rounded-3xl border border-border bg-surface p-4 ${
        className ?? ""
      }`}
      style={glowStyle ? [baseShadow, glowStyle] : baseShadow}>
      {children}
    </View>
  );
}
