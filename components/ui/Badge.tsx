import { Text, View } from "react-native";

export type BadgeVariant =
  | "safe"
  | "caution"
  | "dangerous"
  | "spam"
  | "suspicious"
  | "normal";

type BadgeProps = {
  variant: BadgeVariant;
  label?: string;
  className?: string;
};

const variantStyles: Record<
  BadgeVariant,
  { bg: string; text: string; label: string }
> = {
  safe: { bg: "bg-safe/20", text: "text-safe", label: "SAFE" },
  caution: { bg: "bg-warning/20", text: "text-warning", label: "CAUTION" },
  dangerous: { bg: "bg-danger/20", text: "text-danger", label: "HIGH" },
  spam: { bg: "bg-danger/25", text: "text-danger", label: "SPAM" },
  suspicious: {
    bg: "bg-warning/25",
    text: "text-warning",
    label: "SUSPICIOUS",
  },
  normal: { bg: "bg-safe/20", text: "text-safe", label: "NORMAL" },
};

export default function Badge({ variant, label, className }: BadgeProps) {
  const styles = variantStyles[variant];

  return (
    <View className={`rounded-full px-3 py-1 ${styles.bg} ${className ?? ""}`}>
      <Text
        className={`text-[10px] font-semibold tracking-widest ${styles.text} font-sans`}>
        {label ?? styles.label}
      </Text>
    </View>
  );
}
