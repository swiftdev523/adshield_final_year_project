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
};

const getColor = (score: number) => {
  if (score >= 70) return "#EF4444";
  if (score >= 40) return "#F59E0B";
  return "#22C55E";
};

const getLabel = (score: number) => {
  if (score >= 70) return "HIGH RISK";
  if (score >= 40) return "MODERATE";
  return "LOW RISK";
};

export default function RiskMeter({ score }: RiskMeterProps) {
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

  const color = getColor(score);
  const label = getLabel(score);

  return (
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
        <Text
          className="text-xs font-semibold tracking-widest font-sans"
          style={{ color }}>
          {label}
        </Text>
      </View>
    </View>
  );
}
