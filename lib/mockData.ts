export type RiskLevel = "safe" | "caution" | "dangerous";

export type RecentScan = {
  id: string;
  name: string;
  status: RiskLevel;
  initials: string;
  color: string;
};

export type ActivityItem = {
  id: string;
  level: "safe" | "caution" | "dangerous";
  text: string;
  time: string;
};

export type ScanExample = {
  id: string;
  name: string;
  size: string;
  risk: RiskLevel;
};

export type NotificationApp = {
  id: string;
  rank: number;
  name: string;
  category: string;
  last: string;
  count: number;
  tag: "spam" | "suspicious" | "normal";
  score: number;
};

export const recentScans: RecentScan[] = [
  {
    id: "1",
    name: "TikTok",
    status: "safe",
    initials: "T",
    color: "#0EA5E9",
  },
  {
    id: "2",
    name: "WhatsApp",
    status: "safe",
    initials: "W",
    color: "#22C55E",
  },
  {
    id: "3",
    name: "Unknown.apk",
    status: "dangerous",
    initials: "?",
    color: "#EF4444",
  },
  {
    id: "4",
    name: "YouTube",
    status: "safe",
    initials: "Y",
    color: "#DC2626",
  },
  {
    id: "5",
    name: "GameMaster",
    status: "caution",
    initials: "G",
    color: "#8B5CF6",
  },
];

export const recentActivity: ActivityItem[] = [
  {
    id: "1",
    level: "dangerous",
    text: "Unknown.apk flagged as HIGH RISK",
    time: "2h ago",
  },
  {
    id: "2",
    level: "caution",
    text: "GameMaster scored Moderate (52)",
    time: "5h ago",
  },
  {
    id: "3",
    level: "dangerous",
    text: "ShopDeals Pro sending spam notifications",
    time: "1d ago",
  },
];

export const scanExamples: ScanExample[] = [
  {
    id: "1",
    name: "suspicious_game_v2.3.apk",
    size: "24.5 MB",
    risk: "dangerous",
  },
  {
    id: "2",
    name: "shopping_app_free.apk",
    size: "18.2 MB",
    risk: "caution",
  },
  {
    id: "3",
    name: "calculator_lite.apk",
    size: "3.1 MB",
    risk: "safe",
  },
  {
    id: "4",
    name: "flashlight_pro.apk",
    size: "5.8 MB",
    risk: "safe",
  },
  {
    id: "5",
    name: "weather_plus.apk",
    size: "12.4 MB",
    risk: "caution",
  },
];

export const notificationApps: NotificationApp[] = [
  {
    id: "1",
    rank: 1,
    name: "ShopDeals Pro",
    category: "Shopping",
    last: "12 min ago",
    count: 42,
    tag: "spam",
    score: 92,
  },
  {
    id: "2",
    rank: 2,
    name: "News Flash",
    category: "News",
    last: "35 min ago",
    count: 31,
    tag: "suspicious",
    score: 66,
  },
  {
    id: "3",
    rank: 3,
    name: "GameMaster",
    category: "Games",
    last: "1 hr ago",
    count: 24,
    tag: "suspicious",
    score: 58,
  },
  {
    id: "4",
    rank: 4,
    name: "CashLoan Fast",
    category: "Finance",
    last: "2 hr ago",
    count: 19,
    tag: "spam",
    score: 88,
  },
  {
    id: "5",
    rank: 5,
    name: "WhatsApp",
    category: "Social",
    last: "4 hr ago",
    count: 18,
    tag: "normal",
    score: 12,
  },
  {
    id: "6",
    rank: 6,
    name: "BetNow",
    category: "Finance",
    last: "6 hr ago",
    count: 15,
    tag: "spam",
    score: 85,
  },
  {
    id: "7",
    rank: 7,
    name: "PrizeAlert",
    category: "Games",
    last: "8 hr ago",
    count: 10,
    tag: "spam",
    score: 79,
  },
  {
    id: "8",
    rank: 8,
    name: "DailyDeals",
    category: "Shopping",
    last: "10 hr ago",
    count: 8,
    tag: "suspicious",
    score: 63,
  },
  {
    id: "9",
    rank: 9,
    name: "MapTracker",
    category: "Navigation",
    last: "12 hr ago",
    count: 4,
    tag: "normal",
    score: 8,
  },
  {
    id: "10",
    rank: 10,
    name: "NewsLine",
    category: "News",
    last: "14 hr ago",
    count: 3,
    tag: "suspicious",
    score: 45,
  },
];
