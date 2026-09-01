import { useEffect, useMemo } from "react";
import { Text, View } from "react-native";
import Animated, {
  Easing,
  useAnimatedProps,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle } from "react-native-svg";

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

type RiskMeterProps = {
  score: number;
  level: "Safe" | "Suspicious" | "High Risk";
  reviewLabel?: string;
};

const levelColors: Record<RiskMeterProps["level"], string> = {
  Safe: "#22C55E",
  Suspicious: "#F59E0B",
  "High Risk": "#EF4444",
};

export default function RiskMeter({
  score,
  level,
  reviewLabel = level,
}: RiskMeterProps) {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withTiming(Math.min(score, 100) / 100, {
      duration: 900,
      easing: Easing.out(Easing.cubic),
    });
  }, [score, progress]);

  const { size, strokeWidth, radius, center, circumference, arcLength } =
    useMemo(() => {
      const sizeValue = 220;
      const stroke = 14;
      const radiusValue = (sizeValue - stroke) / 2 - 6;
      const centerValue = sizeValue / 2;
      const circumferenceValue = 2 * Math.PI * radiusValue;
      const arcValue = circumferenceValue * 0.75;
      return {
        size: sizeValue,
        strokeWidth: stroke,
        radius: radiusValue,
        center: centerValue,
        circumference: circumferenceValue,
        arcLength: arcValue,
      };
    }, []);

  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: arcLength * (1 - progress.value),
  }));

  const color = levelColors[level];

  return (
    <View className="items-center justify-center">
      <View className="items-center justify-center">
        <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <Circle
            cx={center}
            cy={center}
            r={radius}
            stroke="#22304A"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${circumference}`}
            transform={`rotate(135 ${center} ${center})`}
          />
          <AnimatedCircle
            cx={center}
            cy={center}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${circumference}`}
            animatedProps={animatedProps}
            transform={`rotate(135 ${center} ${center})`}
          />
        </Svg>
        <View className="absolute items-center">
          <Text className="font-heading text-4xl text-textPrimary">
            {Math.round(score)}
          </Text>
          <Text className="mt-1 text-[10px] text-textMuted font-sans">
            out of 100
          </Text>
        </View>
      </View>
      <Text className="-mt-4 text-xs uppercase tracking-wider text-textMuted font-sans">
        Overall review
      </Text>
      <Text
        className="mt-2 text-center text-sm font-semibold font-sans"
        style={{ color }}
      >
        {reviewLabel}
      </Text>
    </View>
  );
}
